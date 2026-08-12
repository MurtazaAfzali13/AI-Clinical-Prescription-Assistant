"""Extractor Agent.

Responsible for turning a doctor's free-text note (English) into a
structured `PrescriptionExtraction` object using an LLM with structured
output. Kept as a pure function of state -> state so it can be unit
tested with a fake/mocked LLM.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.agents.state import GraphState
from app.core.exceptions import ExtractionError
from app.core.logging import get_logger
from app.models.schemas import PrescriptionExtraction

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a clinical documentation assistant embedded in a \
hospital prescription system. Convert the doctor's free-text note into \
strictly structured data.

Rules:
- Output must be in English only, even if the input contains other languages.
- `medications` is ONLY for drugs the doctor is newly prescribing in this \
encounter (e.g. "prescribe X", "give X", "start X"). Extract each with its \
dosage, frequency, and duration if stated. If a field is not stated, omit \
it rather than guessing.
- `current_medications` is for drugs the patient is already taking that are \
NOT being newly prescribed here -- e.g. mentioned as "currently on X", \
"already takes X", "is on X therapy". List just the drug names. This is \
critical: these existing medications must still be checked for interactions \
against anything newly prescribed, so never drop them or merge them into \
`medications`.
- The `diagnosis` field is required; infer it conservatively from the note \
if the doctor did not state it explicitly.
- Do not invent medications, dosages, or advice that are not present in the \
note. Precision matters: this output is used for a real prescription.
"""


def build_extractor_chain(llm: BaseChatModel):
    """Builds a runnable that returns a `PrescriptionExtraction`."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "Doctor's note:\n{raw_text}"),
        ]
    )
    structured_llm = llm.with_structured_output(PrescriptionExtraction)
    return prompt | structured_llm


def extractor_node(state: GraphState, llm: BaseChatModel) -> GraphState:
    """LangGraph node: raw_text -> extraction."""
    raw_text = state.get("raw_text", "")
    if not raw_text.strip():
        raise ExtractionError("raw_text is empty; nothing to extract")

    chain = build_extractor_chain(llm)
    try:
        extraction: PrescriptionExtraction = chain.invoke({"raw_text": raw_text})
    except Exception as exc:  # noqa: BLE001 - normalise all LLM/parse errors
        logger.error("extraction_failed", extra={"extra_fields": {"error": str(exc)}})
        return {"extraction": None, "extraction_error": str(exc)}

    # Preserve any patient info already supplied by the frontend form.
    if state.get("patient") and state["patient"].name:
        extraction.patient = state["patient"]

    return {"extraction": extraction, "extraction_error": None}
