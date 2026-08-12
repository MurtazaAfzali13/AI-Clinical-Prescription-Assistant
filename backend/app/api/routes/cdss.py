"""CDSS (Copilot Mode) endpoints.

Separate from app/api/routes/prescription.py's original endpoints, which
stay completely untouched -- this is purely additive. The frontend's
`use_copilot_mode` toggle decides which pipeline endpoint gets called:
the original `/prescriptions` (Extractor -> Safety, always) or these
`/cdss/prescriptions` endpoints (which internally branch to Fast Mode or
full Copilot Mode based on the `use_copilot_mode` field in the request).
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from app.agents.cdss_graph import build_cdss_graph, build_cdss_graph_from_structured_data
from app.agents.cdss_state import create_initial_cdss_state
from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.core.exceptions import ExtractionError
from app.models.cdss_schemas import (
    CDSSManualPrescriptionRequest,
    CDSSPrescriptionRequest,
    CDSSPrescriptionResponse,
)
from app.services.pinecone_service import PineconeService
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/cdss", tags=["cdss"])


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


@router.post("/prescriptions", response_model=CDSSPrescriptionResponse)
def create_cdss_prescription(
    payload: CDSSPrescriptionRequest,
    llm: ChatOpenAI = Depends(get_llm),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> CDSSPrescriptionResponse:
    """Runs Fast Mode or full Copilot Mode depending on
    `payload.use_copilot_mode`, using the same compiled graph either way."""
    trace_id = str(uuid.uuid4())
    graph = build_cdss_graph(llm=llm, pinecone_service=pinecone_service, supabase_service=supabase_service)

    initial_state = create_initial_cdss_state(
        raw_text=payload.raw_text,
        patient=payload.patient,
        trace_id=trace_id,
        use_copilot_mode=payload.use_copilot_mode,
    )
    final_state = graph.invoke(initial_state)

    if final_state.get("extraction") is None:
        raise ExtractionError(final_state.get("extraction_error") or "Failed to extract prescription data")

    review = final_state["review"]
    supabase_service.save_prescription(
        doctor_id=doctor.id,
        response=_review_to_legacy_response(review, final_state, trace_id),
        patient_record_no=payload.patient.record_no,
    )

    return CDSSPrescriptionResponse(review=review, extraction=final_state["extraction"], trace_id=trace_id)


@router.post("/prescriptions/manual", response_model=CDSSPrescriptionResponse)
def create_cdss_manual_prescription(
    payload: CDSSManualPrescriptionRequest,
    llm: ChatOpenAI = Depends(get_llm),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> CDSSPrescriptionResponse:
    """Manual entry, with the SAME Supervisor routing as AI dictation.

    This is the fix for a real gap: the original `/prescriptions/manual`
    endpoint only ever ran the Safety agent, regardless of how thorough a
    workup the doctor might want -- a manually-typed prescription never
    reached the Supervisor at all. This endpoint uses
    `build_cdss_graph_from_structured_data`, which shares 100% of the
    Supervisor/fan-out/fan-in logic with the AI-dictation graph; only the
    entry point differs (skips Extractor, since the doctor already
    supplied structured data)."""
    from app.models.schemas import Medication, PrescriptionExtraction

    trace_id = str(uuid.uuid4())
    graph = build_cdss_graph_from_structured_data(
        llm=llm, pinecone_service=pinecone_service, supabase_service=supabase_service
    )

    extraction = PrescriptionExtraction(
        patient=payload.patient,
        diagnosis=payload.diagnosis,
        medications=[Medication(**m.model_dump()) for m in payload.medications],
        current_medications=payload.current_medications,
        advice=payload.advice,
    )
    initial_state = create_initial_cdss_state(
        raw_text="", patient=payload.patient, trace_id=trace_id, use_copilot_mode=payload.use_copilot_mode
    )
    initial_state["extraction"] = extraction

    final_state = graph.invoke(initial_state)

    review = final_state["review"]
    supabase_service.save_prescription(
        doctor_id=doctor.id,
        response=_review_to_legacy_response(review, final_state, trace_id),
        patient_record_no=payload.patient.record_no,
    )

    return CDSSPrescriptionResponse(review=review, extraction=final_state["extraction"], trace_id=trace_id)


_STAGE_LABELS = {
    "extractor": "Extractor agent is structuring the encounter note...",
    "supervisor": "Supervisor is deciding which specialist checks are needed...",
    "safety_checker": "Safety agent is checking for drug interactions...",
    "lab_node": "Context/Lab agent is pulling patient clinical data...",
    "dose_node": "Dose agent is verifying dosing (deterministic calculation)...",
    "contraindication_node": "Contraindication agent is checking patient conditions...",
    "guideline_node": "Guideline agent is checking treatment protocols...",
    "reflection_gate": "Consolidating specialist findings...",
    "alternative_therapy": "Alternative Therapy agent is looking for safer options...",
    "reflection_node": "Reflection agent (attending physician review) is synthesizing a verdict...",
    "reviewer": "Reviewer agent is finalizing the report...",
}


@router.get("/prescriptions/stream")
def stream_cdss_prescription(
    raw_text: str,
    use_copilot_mode: bool = False,
    llm: ChatOpenAI = Depends(get_llm),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> StreamingResponse:
    """Server-Sent Events stream of agent progress through the CDSS graph
    (Fast Mode or Copilot Mode fan-out/fan-in), ending with the final
    review payload. Each event: {"type": "status"|"result"|"error", ...}."""
    trace_id = str(uuid.uuid4())
    graph = build_cdss_graph(llm=llm, pinecone_service=pinecone_service, supabase_service=supabase_service)

    from app.models.schemas import PatientInfo

    initial_state = create_initial_cdss_state(
        raw_text=raw_text, patient=PatientInfo(), trace_id=trace_id, use_copilot_mode=use_copilot_mode
    )

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

            review = final_state["review"]
            supabase_service.save_prescription(
                doctor_id=doctor.id,
                response=_review_to_legacy_response(review, final_state, trace_id),
                patient_record_no=None,
            )

            response = CDSSPrescriptionResponse(review=review, extraction=final_state["extraction"], trace_id=trace_id)
            yield f"data: {json.dumps({'type': 'result', 'payload': response.model_dump()})}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _review_to_legacy_response(review, final_state, trace_id):
    """Adapts a CDSSReview into the original PrescriptionResponse shape
    so SupabaseService.save_prescription (shared with Fast Mode) can
    persist it without needing a second, duplicated persistence path."""
    from app.models.schemas import PrescriptionResponse

    return PrescriptionResponse(
        extraction=final_state["extraction"],
        warnings=final_state.get("warnings", []),
        is_safe=review.is_safe,
        trace_id=trace_id,
    )
