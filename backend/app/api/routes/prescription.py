"""Prescription pipeline endpoints.

- POST /prescriptions          run Extractor -> Safety Checker, return the full result
- GET  /prescriptions/stream   same pipeline, but streamed as Server-Sent Events so the
                                 UI can show live agent status ("Extractor agent running...")
- POST /prescriptions/override  human-in-the-loop: doctor force-approves an unsafe prescription
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from app.agents.graph import build_prescription_graph
from app.agents.safety_checker import safety_node
from app.agents.state import create_initial_state
from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.core.exceptions import ExtractionError
from app.models.schemas import (
    ManualPrescriptionRequest,
    OverrideRequest,
    OverrideResponse,
    PrescriptionRequest,
    PrescriptionResponse,
    PrescriptionExtraction,
)
from app.services.pinecone_service import PineconeService
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


def get_llm(settings: Settings = Depends(get_settings)) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


def get_pinecone_service(settings: Settings = Depends(get_settings)) -> PineconeService:
    return PineconeService(settings=settings)


def get_supabase_service(settings: Settings = Depends(get_settings)) -> SupabaseService:
    return SupabaseService(settings=settings)


def _run_pipeline(payload: PrescriptionRequest, llm, pinecone_service: PineconeService):
    trace_id = str(uuid.uuid4())
    graph = build_prescription_graph(llm=llm, pinecone_service=pinecone_service)
    initial_state = create_initial_state(
        raw_text=payload.raw_text, patient=payload.patient, trace_id=trace_id
    )
    return graph, initial_state, trace_id


@router.post("", response_model=PrescriptionResponse)
def create_prescription(
    payload: PrescriptionRequest,
    llm: ChatOpenAI = Depends(get_llm),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> PrescriptionResponse:
    """Run the doctor's free-text note through Extractor -> Safety Checker."""
    graph, initial_state, trace_id = _run_pipeline(payload, llm, pinecone_service)
    final_state = graph.invoke(initial_state)

    if final_state.get("extraction") is None:
        raise ExtractionError(
            final_state.get("extraction_error") or "Failed to extract prescription data"
        )

    response = PrescriptionResponse(
        extraction=final_state["extraction"],
        warnings=final_state.get("warnings", []),
        is_safe=final_state.get("is_safe", True),
        trace_id=trace_id,
    )

    supabase_service.save_prescription(
        doctor_id=doctor.id, response=response, patient_record_no=payload.patient.record_no
    )
    return response


@router.post("/manual", response_model=PrescriptionResponse)
def create_manual_prescription(
    payload: ManualPrescriptionRequest,
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> PrescriptionResponse:
    """Doctor-authored prescription: skips the Extractor agent entirely
    (the doctor already typed structured diagnosis + medications) but
    still runs the Safety Checker agent before it can be printed."""
    trace_id = str(uuid.uuid4())

    extraction = PrescriptionExtraction(
        patient=payload.patient,
        diagnosis=payload.diagnosis,
        medications=payload.medications,
        current_medications=payload.current_medications,
        advice=payload.advice,
    )
    state = create_initial_state(raw_text="", patient=payload.patient, trace_id=trace_id)
    state["extraction"] = extraction

    final_state = safety_node(state, pinecone_service=pinecone_service)

    response = PrescriptionResponse(
        extraction=extraction,
        warnings=final_state.get("warnings", []),
        is_safe=final_state.get("is_safe", True),
        trace_id=trace_id,
    )

    supabase_service.save_prescription(
        doctor_id=doctor.id, response=response, patient_record_no=payload.patient.record_no
    )
    return response


_STAGE_LABELS = {
    "extractor": "Extractor agent is structuring the encounter note...",
    "safety_checker": "Safety agent is checking for drug interactions...",
}


@router.get("/stream")
def stream_prescription(
    raw_text: str,
    llm: ChatOpenAI = Depends(get_llm),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> StreamingResponse:
    """Server-Sent Events stream of agent progress, ending with the final result.

    Each event is a JSON payload: {"type": "status" | "result" | "error", ...}
    """
    payload = PrescriptionRequest(raw_text=raw_text, patient={})
    graph, initial_state, trace_id = _run_pipeline(payload, llm, pinecone_service)

    def event_stream():
        try:
            final_state = dict(initial_state)
            for chunk in graph.stream(initial_state):
                for node_name, node_output in chunk.items():
                    final_state.update(node_output)
                    label = _STAGE_LABELS.get(node_name, f"{node_name} running...")
                    yield f"data: {json.dumps({'type': 'status', 'stage': node_name, 'label': label})}\n\n"

            if final_state.get("extraction") is None:
                yield f"data: {json.dumps({'type': 'error', 'message': final_state.get('extraction_error') or 'Extraction failed'})}\n\n"
                return

            response = PrescriptionResponse(
                extraction=final_state["extraction"],
                warnings=final_state.get("warnings", []),
                is_safe=final_state.get("is_safe", True),
                trace_id=trace_id,
            )
            supabase_service.save_prescription(
                doctor_id=doctor.id, response=response, patient_record_no=None
            )
            yield f"data: {json.dumps({'type': 'result', 'payload': response.model_dump()})}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface any failure to the stream client
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/override", response_model=OverrideResponse)
def override_prescription(
    payload: OverrideRequest,
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> OverrideResponse:
    """Human-in-the-loop: the attending physician force-approves a prescription
    that the Safety agent flagged, recording a mandatory clinical justification."""
    supabase_service.record_override(
        prescription_trace_id=payload.trace_id, doctor_id=doctor.id, reason=payload.reason
    )
    return OverrideResponse(trace_id=payload.trace_id)
