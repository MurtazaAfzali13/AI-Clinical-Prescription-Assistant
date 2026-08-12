"""Dose Agent.

MUST NOT do math via LLM (per spec). Extracts the drug name/dosage
straight from the Extractor's structured output and calls the pure
Python `calculate_dose` tool. If Lab context is available (weight/eGFR),
passes it through for renal-adjusted limits.
"""
from __future__ import annotations

from app.agents.cdss_state import CDSSState
from app.models.cdss_schemas import DoseCheckResult
from app.tools.dose_calculator import calculate_dose


def dose_node(state: CDSSState) -> CDSSState:
    extraction = state.get("extraction")
    if extraction is None:
        return {"dose_results": []}

    lab_context = state.get("lab_context")
    egfr = lab_context.egfr if lab_context else None
    weight_kg = lab_context.weight_kg if lab_context else None
    age = lab_context.age if lab_context else None

    results: list[DoseCheckResult] = []
    for medication in extraction.medications:
        raw = calculate_dose(
            drug_name=medication.name,
            dosage_text=medication.dosage,
            weight_kg=weight_kg,
            age=age,
            egfr=egfr,
        )
        results.append(
            DoseCheckResult(
                medication_name=medication.name,
                prescribed_dose_mg=raw["prescribed_dose_mg"],
                recommended_min_mg=raw["recommended_min_mg"],
                recommended_max_mg=raw["recommended_max_mg"],
                is_within_range=raw["is_within_range"],
                renal_adjustment_applied=raw["renal_adjustment_applied"],
                explanation=raw["explanation"],
            )
        )

    return {"dose_results": results}
