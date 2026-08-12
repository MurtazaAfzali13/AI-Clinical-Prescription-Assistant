"""Supervisor Agent (Smart Router).

The whole point of this node is to SAVE cost and latency: given the
Extractor's structured output, it decides which of the expensive
specialist agents (Lab, Dose, Contraindication, Guideline) are actually
worth running for this specific prescription, instead of always running
everything "just in case". Safety (drug-drug interaction) is not
Supervisor-gated -- it always runs, since it's the non-negotiable
baseline check.

Uses a fast/cheap model (the caller is expected to pass something like
gpt-4o-mini) since this is a routing decision, not a clinical judgment.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import RoutingDecision

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a triage router in a clinical decision support system. \
Given a structured prescription extraction, decide which specialist checks are \
actually relevant -- do not enable a check "just in case".

Guidance:
- `run_dose_agent`: true if ANY medication has a numeric dosage that could be \
verified against a reference range (skip only if no medications have parseable doses).
- `run_lab_agent`: true if any prescribed medication is commonly weight-based or \
renally/hepatically cleared (e.g. antibiotics dosed by weight, NSAIDs, metformin, \
ACE inhibitors/ARBs), OR the patient has any other medication on file suggesting \
relevant lab context matters (e.g. existing renal or hepatic therapy).
- `run_contraindication_agent`: true if the patient has any other medication on \
file that could plausibly indicate a comorbidity relevant to a prescribed \
medication's class (e.g. already on an anticoagulant, an antidiabetic, etc.).
- `run_guideline_agent`: true if the diagnosis is a well-defined condition with \
established treatment guidelines worth checking against (most diagnoses qualify; \
skip only for very vague or non-clinical notes).

Always provide brief `reasoning` for your choices.
"""


def build_supervisor_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Diagnosis: {diagnosis}\nNewly prescribed medications: {medications}\n"
                "Patient's other current medications (on file): {current_medications}",
            ),
        ]
    )
    structured_llm = llm.with_structured_output(RoutingDecision)
    return prompt | structured_llm


def supervisor_node(state: CDSSState, llm: BaseChatModel) -> CDSSState:
    extraction = state.get("extraction")
    if extraction is None:
        # Nothing to route on -- shouldn't normally happen (Extractor runs
        # first), but fail closed: run nothing rather than guess.
        decision = RoutingDecision(reasoning="No extraction available; skipping all specialist agents.")
        return {"routing_decision": decision}

    chain = build_supervisor_chain(llm)
    med_summary = ", ".join(f"{m.name} {m.dosage}" for m in extraction.medications) or "none"
    current_meds_summary = ", ".join(extraction.current_medications) or "none on file"

    try:
        decision: RoutingDecision = chain.invoke(
            {
                "diagnosis": extraction.diagnosis,
                "medications": med_summary,
                "current_medications": current_meds_summary,
            }
        )
    except Exception as exc:  # noqa: BLE001
        # Fail OPEN here, deliberately: if the router itself breaks, running
        # every specialist agent is safer than silently running none.
        logger.error("supervisor_failed", extra={"extra_fields": {"error": str(exc)}})
        decision = RoutingDecision(
            run_dose_agent=True,
            run_lab_agent=True,
            run_contraindication_agent=True,
            run_guideline_agent=True,
            reasoning=f"Supervisor failed ({exc}); running all specialist agents as a safe fallback.",
        )

    logger.info(
        "routing_decision",
        extra={"extra_fields": {"decision": decision.model_dump()}},
    )
    return {"routing_decision": decision}
