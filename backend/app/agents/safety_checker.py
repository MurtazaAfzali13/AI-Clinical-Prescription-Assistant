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
    med_names = [m.name for m in extraction.medications]

    for medication in extraction.medications:
        matches = pinecone_service.find_interactions(medication.name)
        for match in matches:
            overlapping = set(match.interacts_with) & {n.lower() for n in med_names}
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
