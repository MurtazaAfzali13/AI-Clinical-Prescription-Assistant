"""Alternative Therapy Agent.

Only runs when Safety or Contraindication flagged something (see
`should_run_alternative_agent`, used by the graph's conditional edge) --
there's nothing to suggest an alternative to otherwise. For each flagged
medication, retrieves guideline text about alternatives in the same
namespace used by the Guideline agent, then asks the LLM to decide
whether a safe alternative exists -- STRICTLY grounded in the retrieved
text. The prompt explicitly forbids suggesting a drug that isn't named in
the retrieved passages, which is the anti-hallucination guarantee here:
if nothing relevant was retrieved, the agent must say so rather than
invent a plausible-sounding alternative.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import AlternativeTherapy, EvidenceObject
from app.services.pinecone_service import PineconeService

logger = get_logger(__name__)

NAMESPACE = "clinical-guidelines"

SYSTEM_PROMPT = """You suggest alternative medications, but ONLY using the retrieved \
guideline text provided to you -- never from general knowledge. If the retrieved \
text does not clearly name a safe alternative for this specific medication, set \
`has_alternative` to false. Do not guess or infer a plausible-sounding drug that \
isn't explicitly present in the retrieved text.
"""


class _AlternativeSuggestion(BaseModel):
    has_alternative: bool
    alternative_drug: str | None = None
    rationale: str | None = None


def should_run_alternative_agent(state: CDSSState) -> bool:
    """Gate condition for the graph: only worth running if something was
    actually flagged by Safety or Contraindication."""
    return bool(state.get("warnings")) or bool(state.get("contraindication_warnings"))


def _build_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Flagged medication: {medication}\nReason flagged: {reason}\n\n"
                "Retrieved guideline text:\n{retrieved_text}",
            ),
        ]
    )
    return prompt | llm.with_structured_output(_AlternativeSuggestion)


def _flagged_medications(state: CDSSState) -> list[tuple[str, str]]:
    """Returns (medication_name, reason) pairs from Safety + Contraindication warnings."""
    flagged: list[tuple[str, str]] = []
    for warning in state.get("warnings", []):
        if warning.medications:
            flagged.append((warning.medications[0], warning.explanation))
    for warning in state.get("contraindication_warnings", []):
        flagged.append((warning.medication_name, warning.explanation))
    return flagged


def alternative_therapy_node(state: CDSSState, llm: BaseChatModel, pinecone_service: PineconeService) -> CDSSState:
    flagged = _flagged_medications(state)
    if not flagged:
        return {"alternative_therapies": []}

    chain = _build_chain(llm)
    alternatives: list[AlternativeTherapy] = []

    for medication_name, reason in flagged:
        try:
            matches = pinecone_service.query_namespace(
                query_text=f"alternative to {medication_name}", namespace=NAMESPACE, top_k=3
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("alternative_therapy_query_failed", extra={"extra_fields": {"error": str(exc)}})
            continue

        if not matches:
            continue  # nothing retrieved -> nothing to ground a suggestion in

        retrieved_text = "\n---\n".join(m.get("content", "") for m in matches)

        try:
            suggestion: _AlternativeSuggestion = chain.invoke(
                {"medication": medication_name, "reason": reason, "retrieved_text": retrieved_text}
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("alternative_therapy_llm_failed", extra={"extra_fields": {"error": str(exc)}})
            continue

        if not suggestion.has_alternative or not suggestion.alternative_drug:
            continue

        best_match = max(matches, key=lambda m: m.get("score", 0.0))
        alternatives.append(
            AlternativeTherapy(
                original_medication=medication_name,
                suggested_alternative=suggestion.alternative_drug,
                rationale=suggestion.rationale or "See retrieved guideline text.",
                evidence=EvidenceObject(
                    source=f"Pinecone: {NAMESPACE}",
                    confidence=float(best_match.get("score", 0.0)),
                    guideline_section=best_match.get("metadata", {}).get("guideline_section"),
                ),
            )
        )

    return {"alternative_therapies": alternatives}
