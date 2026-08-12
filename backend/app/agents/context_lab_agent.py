"""Context/Lab Agent.

Pure data-fetch node -- no LLM call at all. Pulls the patient's weight,
age, eGFR (renal function), and liver panel status from Supabase via
`SupabaseService.get_lab_context`, so the Dose and Contraindication agents
have real clinical context instead of guessing from the encounter note.
"""
from __future__ import annotations

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import LabContext
from app.services.supabase_service import SupabaseService

logger = get_logger(__name__)


def lab_node(state: CDSSState, supabase_service: SupabaseService) -> CDSSState:
    patient = state.get("patient")
    record_no = patient.record_no if patient else None

    row = supabase_service.get_lab_context(record_no=record_no)
    if row is None:
        # No lab data on file -- not an error, just means Dose/Contraindication
        # agents will work with less information (and say so explicitly).
        logger.info("lab_context_unavailable", extra={"extra_fields": {"record_no": record_no}})
        return {"lab_context": None}

    lab_context = LabContext(
        weight_kg=row.get("weight_kg"),
        age=row.get("age"),
        egfr=row.get("egfr"),
        liver_panel_normal=row.get("liver_panel_normal"),
        labs_recorded_at=row.get("labs_recorded_at"),
        chronic_conditions=row.get("chronic_conditions") or [],
        allergies=row.get("allergies") or [],
    )
    return {"lab_context": lab_context}
