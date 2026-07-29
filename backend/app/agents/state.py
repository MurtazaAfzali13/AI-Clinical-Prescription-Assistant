"""LangGraph shared state for the prescription pipeline.

Two nodes operate on this state:
  1. extractor_node  -> turns raw doctor text into structured data
  2. safety_node      -> checks the extracted medications against the
                          Pinecone drug-interaction knowledge base
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models.schemas import InteractionWarning, PatientInfo, PrescriptionExtraction


class GraphState(TypedDict, total=False):
    # Conversation trace (kept for debuggability / future HITL support)
    messages: Annotated[list, add_messages]

    # Inputs
    raw_text: str
    patient: PatientInfo

    # Produced by extractor_node
    extraction: PrescriptionExtraction | None
    extraction_error: str | None

    # Produced by safety_node
    warnings: list[InteractionWarning]
    is_safe: bool

    trace_id: str


def create_initial_state(raw_text: str, patient: PatientInfo, trace_id: str) -> GraphState:
    """Factory that builds a clean initial state for a new pipeline run."""
    return GraphState(
        messages=[],
        raw_text=raw_text,
        patient=patient,
        extraction=None,
        extraction_error=None,
        warnings=[],
        is_safe=True,
        trace_id=trace_id,
    )
