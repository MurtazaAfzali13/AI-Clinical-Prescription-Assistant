"""Guideline Agent.

Queries the `clinical-guidelines` Pinecone namespace for the diagnosis,
surfacing evidence-backed treatment recommendations. Purely retrieval --
no LLM synthesis here, so every recommendation is traceable straight back
to a retrieved guideline chunk (via EvidenceObject), not a model paraphrase.
"""
from __future__ import annotations

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import EvidenceObject, GuidelineRecommendation
from app.services.pinecone_service import PineconeService

logger = get_logger(__name__)

NAMESPACE = "clinical-guidelines"


def guideline_node(state: CDSSState, pinecone_service: PineconeService) -> CDSSState:
    extraction = state.get("extraction")
    if extraction is None:
        return {"guideline_recommendations": []}

    try:
        matches = pinecone_service.query_namespace(query_text=extraction.diagnosis, namespace=NAMESPACE, top_k=3)
    except Exception as exc:  # noqa: BLE001 - a namespace outage shouldn't crash the whole pipeline
        logger.error("guideline_query_failed", extra={"extra_fields": {"error": str(exc)}})
        return {"guideline_recommendations": []}

    recommendations: list[GuidelineRecommendation] = []
    for match in matches:
        meta = match.get("metadata", {})
        recommendation_text = meta.get("recommendation") or match.get("content", "")
        if not recommendation_text:
            continue
        recommendations.append(
            GuidelineRecommendation(
                diagnosis=extraction.diagnosis,
                recommendation=recommendation_text,
                evidence=EvidenceObject(
                    source=f"Pinecone: {NAMESPACE}",
                    confidence=float(match.get("score", 0.0)),
                    guideline_section=meta.get("guideline_section"),
                ),
            )
        )

    return {"guideline_recommendations": recommendations}
