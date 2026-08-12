"""Reviewer Agent.

Pure formatting -- no LLM call. Assembles everything the specialist
agents (and Reflection, if it ran) produced into the final `CDSSReview`
payload the frontend renders, upgrading each Safety warning with an
EvidenceObject placeholder so Copilot Mode's warnings are structurally
consistent with the rest of the CDSS output. Handles BOTH pipelines:
Fast Mode (no Supervisor/Reflection ran) and Copilot Mode (everything ran).
"""
from __future__ import annotations

from app.agents.cdss_state import CDSSState
from app.models.cdss_schemas import CDSSReview, EvidenceBackedWarning
from app.models.schemas import Severity

_SEVERITY_ORDER = [Severity.NONE, Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
_BLOCKING_SEVERITIES = {Severity.HIGH, Severity.CRITICAL}


def _upgrade_safety_warnings(state: CDSSState) -> list[EvidenceBackedWarning]:
    return [
        EvidenceBackedWarning(medications=w.medications, severity=w.severity, explanation=w.explanation, evidence=None)
        for w in state.get("warnings", [])
    ]


def _highest_severity(*severities: Severity) -> Severity:
    highest = Severity.NONE
    for s in severities:
        if _SEVERITY_ORDER.index(s) > _SEVERITY_ORDER.index(highest):
            highest = s
    return highest


def reviewer_node(state: CDSSState) -> CDSSState:
    use_copilot_mode = bool(state.get("use_copilot_mode"))
    safety_warnings = _upgrade_safety_warnings(state)
    reflection = state.get("reflection")

    if reflection is not None:
        # Copilot Mode: trust Reflection's synthesized verdict -- it already
        # resolved cross-agent contradictions.
        is_safe = reflection.is_safe
        overall_severity = reflection.overall_severity
        summary = reflection.summary
    else:
        # Fast Mode: no Reflection ran, so derive the verdict directly from
        # Safety's own severities (mirrors the original Fast-Mode behavior).
        worst = _highest_severity(*(w.severity for w in safety_warnings)) if safety_warnings else Severity.NONE
        is_safe = worst not in _BLOCKING_SEVERITIES
        overall_severity = worst
        summary = "Fast mode: only the Safety agent ran." if not safety_warnings else "Drug interaction(s) flagged."

    review = CDSSReview(
        is_safe=is_safe,
        overall_severity=overall_severity,
        summary=summary,
        safety_warnings=safety_warnings,
        dose_results=state.get("dose_results", []),
        contraindications=state.get("contraindication_warnings", []),
        guideline_recommendations=state.get("guideline_recommendations", []),
        alternative_therapies=state.get("alternative_therapies", []),
        lab_context=state.get("lab_context"),
        used_copilot_mode=use_copilot_mode,
    )
    return {"review": review}
