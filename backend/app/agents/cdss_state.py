"""Shared LangGraph state for the CDSS (Copilot Mode) pipeline.

Extends the same shape as app/agents/state.py's GraphState but adds every
field the Supervisor and specialist agents read/write. Kept as a separate
TypedDict (not a modification of the original) so the Fast Mode pipeline
in app/agents/graph.py remains completely untouched.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models.cdss_schemas import (
    AlternativeTherapy,
    CDSSReview,
    ContraindicationWarning,
    DoseCheckResult,
    GuidelineRecommendation,
    LabContext,
    ReflectionVerdict,
    RoutingDecision,
)
from app.models.schemas import InteractionWarning, PatientInfo, PrescriptionExtraction


class CDSSState(TypedDict, total=False):
    messages: Annotated[list, add_messages]

    # Inputs
    raw_text: str
    patient: PatientInfo
    use_copilot_mode: bool
    trace_id: str

    # Extractor output (shared with Fast Mode)
    extraction: PrescriptionExtraction | None
    extraction_error: str | None

    # Supervisor output
    routing_decision: RoutingDecision | None

    # Specialist agent outputs
    warnings: list[InteractionWarning]
    is_safe: bool
    lab_context: LabContext | None
    dose_results: list[DoseCheckResult]
    contraindication_warnings: list[ContraindicationWarning]
    guideline_recommendations: list[GuidelineRecommendation]
    alternative_therapies: list[AlternativeTherapy]

    # Convergence
    reflection: ReflectionVerdict | None
    review: CDSSReview | None


def create_initial_cdss_state(
    raw_text: str, patient: PatientInfo, trace_id: str, use_copilot_mode: bool = False
) -> CDSSState:
    return CDSSState(
        messages=[],
        raw_text=raw_text,
        patient=patient,
        use_copilot_mode=use_copilot_mode,
        trace_id=trace_id,
        extraction=None,
        extraction_error=None,
        routing_decision=None,
        warnings=[],
        is_safe=True,
        lab_context=None,
        dose_results=[],
        contraindication_warnings=[],
        guideline_recommendations=[],
        alternative_therapies=[],
        reflection=None,
        review=None,
    )
