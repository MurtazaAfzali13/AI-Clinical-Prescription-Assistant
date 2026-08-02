"""Safety Checker Agent (RAG).

Takes the medications produced by the Extractor agent, looks each one up
in the Pinecone drug-interaction knowledge base, and produces structured
`InteractionWarning`s. This node never raises on a "found an interaction"
case -- that is a normal, expected result. It only raises on infrastructure
failures (handled upstream by the caller / API layer).
"""
from __future__ import annotations

from app.agents.state import GraphState
from app.core.logging import get_logger
from app.models.schemas import InteractionWarning, Severity
from app.services.pinecone_service import PineconeService

logger = get_logger(__name__)

_SEVERITY_ORDER = [Severity.NONE, Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
_BLOCKING_SEVERITIES = {Severity.HIGH, Severity.CRITICAL}


def safety_node(state: GraphState, pinecone_service: PineconeService) -> GraphState:
    """LangGraph node: extraction -> warnings + is_safe."""
    extraction = state.get("extraction")
    if extraction is None:
        # Nothing to check if extraction failed upstream.
        return {**state, "warnings": [], "is_safe": False}

    warnings: list[InteractionWarning] = []
    # Compare each newly prescribed drug against every OTHER drug the patient
    # will be exposed to -- both the other freshly prescribed drugs and the
    # patient's existing/home medications. Without including
    # current_medications here, a drug the patient is "currently on" (not
    # newly prescribed) would never be checked against, even though it's
    # exactly the case that matters clinically.
    new_med_names = [m.name for m in extraction.medications]
    current_med_names = list(extraction.current_medications)
    all_other_names_lower = {n.lower() for n in (*new_med_names, *current_med_names)}

    for medication in extraction.medications:
        matches = pinecone_service.find_interactions(medication.name)
        for match in matches:
            # Pinecone's similarity search is semantic, not exact: querying
            # "Ibuprofen" can also return the Acetaminophen/Amoxicillin
            # records because their seed sentences are worded almost
            # identically ("X interacts with warfarin: ..."). Without this
            # check, we'd attach a *different* drug's explanation to this
            # medication's warning. Only trust a match that's actually about
            # the medication we queried.
            if match.drug_name.strip().lower() != medication.name.strip().lower():
                continue

            # Exclude the medication itself from the comparison set.
            comparison_set = all_other_names_lower - {medication.name.lower()}
            overlapping = set(match.interacts_with) & comparison_set
            if not overlapping:
                continue
            severity = Severity(match.severity) if match.severity in Severity.__members__.values() else Severity.LOW
            warnings.append(
                InteractionWarning(
                    medications=[medication.name, *sorted(overlapping)],
                    severity=severity,
                    explanation=match.explanation or "Potential interaction detected.",
                )
            )

    is_safe = not any(w.severity in _BLOCKING_SEVERITIES for w in warnings)

    logger.info(
        "safety_check_complete",
        extra={"extra_fields": {"warning_count": len(warnings), "is_safe": is_safe}},
    )
    return {**state, "warnings": warnings, "is_safe": is_safe}
