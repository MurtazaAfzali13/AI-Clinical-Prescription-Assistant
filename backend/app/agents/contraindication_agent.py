"""Contraindication Agent.

For each newly-prescribed medication, checks it against the patient's
existing medications/conditions (from Lab context and the extraction's
`current_medications`) via the `contraindications` Pinecone namespace --
isolated from `clinical-guidelines` and the default drug-interaction
namespace so unrelated content can never leak across concerns.
"""
from __future__ import annotations

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import ContraindicationWarning, EvidenceObject
from app.models.schemas import Severity
from app.services.pinecone_service import PineconeService

logger = get_logger(__name__)

NAMESPACE = "contraindications"
_VALID_SEVERITIES = {s.value for s in Severity}


def contraindication_node(state: CDSSState, pinecone_service: PineconeService) -> CDSSState:
    extraction = state.get("extraction")
    if extraction is None:
        return {"contraindication_warnings": []}

    lab_context = state.get("lab_context")
    known_conditions = set(extraction.current_medications)
    if lab_context:
        known_conditions.update(lab_context.chronic_conditions)

    warnings: list[ContraindicationWarning] = []
    for medication in extraction.medications:
        try:
            matches = pinecone_service.query_namespace(
                query_text=f"{medication.name} contraindicated in patients with", namespace=NAMESPACE, top_k=5
            )
        except Exception as exc:  # noqa: BLE001 - a namespace outage shouldn't crash the whole pipeline
            logger.error("contraindication_query_failed", extra={"extra_fields": {"error": str(exc)}})
            continue

        for match in matches:
            meta = match.get("metadata", {})
            match_drug = str(meta.get("drug_name", "")).strip().lower()
            if match_drug != medication.name.strip().lower():
                continue  # same semantic-similarity guard used in Safety Checker

            condition = str(meta.get("condition", "")).strip()
            if not condition or condition.lower() not in {c.lower() for c in known_conditions}:
                continue  # only flag conditions the patient actually has on file

            severity_raw = str(meta.get("severity", "low")).lower()
            severity = Severity(severity_raw) if severity_raw in _VALID_SEVERITIES else Severity.LOW

            warnings.append(
                ContraindicationWarning(
                    medication_name=medication.name,
                    condition=condition,
                    severity=severity,
                    explanation=meta.get("explanation", match.get("content", "")),
                    evidence=EvidenceObject(
                        source=f"Pinecone: {NAMESPACE}",
                        confidence=float(match.get("score", 0.0)),
                        guideline_section=meta.get("guideline_section"),
                    ),
                )
            )

    return {"contraindication_warnings": warnings}
