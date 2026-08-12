"""Deterministic dose-checking tool.

CRITICAL constraint from the spec: dose arithmetic must NEVER be done by
an LLM. This module is pure Python -- the Dose agent extracts the drug
name/dosage/patient variables (already structured by the Extractor) and
calls straight into this table-driven calculator. No prompt, no model
call, no chance of the LLM "confidently" getting a decimal point wrong.

The reference ranges below are a small illustrative set (mirroring the
project's existing seed-data pattern for drug interactions) -- NOT a
substitute for a licensed drug-dosing database (e.g. Lexicomp, Micromedex)
in a real deployment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DoseRange:
    min_mg: float
    max_mg: float
    # If set, this drug's max safe dose is reduced when eGFR is below the
    # threshold -- a simplified stand-in for real renal-dosing tables.
    renal_egfr_threshold: float | None = None
    renal_adjusted_max_mg: float | None = None


# Adult reference ranges, per single dose, for the medications this
# project's seed drug-interaction dataset already covers.
DOSE_TABLE: dict[str, DoseRange] = {
    "acetaminophen": DoseRange(min_mg=325, max_mg=1000),
    "ibuprofen": DoseRange(min_mg=200, max_mg=800, renal_egfr_threshold=60, renal_adjusted_max_mg=400),
    "amoxicillin": DoseRange(min_mg=250, max_mg=1000),
    "sildenafil": DoseRange(min_mg=25, max_mg=100),
    "metformin": DoseRange(min_mg=500, max_mg=1000, renal_egfr_threshold=45, renal_adjusted_max_mg=500),
    "simvastatin": DoseRange(min_mg=5, max_mg=40),
    "lisinopril": DoseRange(min_mg=2.5, max_mg=40, renal_egfr_threshold=30, renal_adjusted_max_mg=20),
    "amlodipine": DoseRange(min_mg=2.5, max_mg=10),
    "losartan": DoseRange(min_mg=25, max_mg=100, renal_egfr_threshold=30, renal_adjusted_max_mg=50),
}


def parse_dose_mg(dosage_text: str) -> float | None:
    """Extracts a numeric mg value from free text like '500mg' or '5 mg'.
    Returns None if it can't confidently parse one (never guesses)."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*mg", dosage_text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def calculate_dose(
    drug_name: str,
    dosage_text: str,
    weight_kg: float | None = None,
    age: int | None = None,
    egfr: float | None = None,
) -> dict:
    """Checks a prescribed dose against the reference table, applying a
    renal adjustment when eGFR data is available and below the drug's
    threshold. Returns a plain dict (not a Pydantic model) so this stays
    a dependency-free, easily-unit-testable pure function; the calling
    agent node wraps the result in `DoseCheckResult`.
    """
    key = drug_name.strip().lower()
    prescribed_mg = parse_dose_mg(dosage_text)

    reference = DOSE_TABLE.get(key)
    if reference is None:
        return {
            "prescribed_dose_mg": prescribed_mg,
            "recommended_min_mg": None,
            "recommended_max_mg": None,
            "is_within_range": None,
            "renal_adjustment_applied": False,
            "explanation": f"No reference dosing range on file for '{drug_name}'; unable to verify.",
        }

    max_mg = reference.max_mg
    renal_adjustment_applied = False
    if (
        egfr is not None
        and reference.renal_egfr_threshold is not None
        and egfr < reference.renal_egfr_threshold
        and reference.renal_adjusted_max_mg is not None
    ):
        max_mg = reference.renal_adjusted_max_mg
        renal_adjustment_applied = True

    if prescribed_mg is None:
        return {
            "prescribed_dose_mg": None,
            "recommended_min_mg": reference.min_mg,
            "recommended_max_mg": max_mg,
            "is_within_range": None,
            "renal_adjustment_applied": renal_adjustment_applied,
            "explanation": f"Could not parse a numeric mg dose from '{dosage_text}'; unable to verify.",
        }

    is_within_range = reference.min_mg <= prescribed_mg <= max_mg

    if is_within_range:
        explanation = f"{prescribed_mg}mg is within the typical {reference.min_mg}-{max_mg}mg range."
    elif prescribed_mg > max_mg:
        explanation = f"{prescribed_mg}mg exceeds the typical max of {max_mg}mg."
    else:
        explanation = f"{prescribed_mg}mg is below the typical min of {reference.min_mg}mg."

    if renal_adjustment_applied:
        explanation += f" (Max reduced from {reference.max_mg}mg due to eGFR {egfr} < {reference.renal_egfr_threshold}.)"

    return {
        "prescribed_dose_mg": prescribed_mg,
        "recommended_min_mg": reference.min_mg,
        "recommended_max_mg": max_mg,
        "is_within_range": is_within_range,
        "renal_adjustment_applied": renal_adjustment_applied,
        "explanation": explanation,
    }
