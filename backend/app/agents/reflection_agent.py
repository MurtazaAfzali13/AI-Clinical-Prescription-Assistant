"""Reflection Agent.

Acts as the attending physician: ingests every specialist agent's output
(fan-in point) and resolves contradictions -- e.g. Dose says the amount is
fine, but Lab says eGFR is critically low, so the unified verdict must
still flag it. Unlike the Supervisor (which fails OPEN on error, since
running extra checks is the safe default), Reflection fails CLOSED: if
synthesis itself breaks, we cannot silently claim the prescription is
safe, so the fallback verdict is unsafe until a human reviews it.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.agents.cdss_state import CDSSState
from app.core.logging import get_logger
from app.models.cdss_schemas import ReflectionVerdict
from app.models.schemas import Severity

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the attending physician performing a final review of \
everything the specialist agents found. Synthesize their outputs into ONE unified \
verdict.

Critical: actively look for CONTRADICTIONS between agents and resolve them \
conservatively (favor safety). For example, if the Dose agent says a dose is within \
the normal range but the Lab agent shows severely reduced renal function (low eGFR) \
that the Dose agent's renal adjustment didn't fully account for, or if a \
Contraindication warning conflicts with an otherwise-clean Safety check, the overall \
severity must reflect the more serious finding -- never average it away or default \
to the more lenient agent.

Set `overall_severity` to the highest severity among everything reported. Set \
`is_safe` to false if overall_severity is high or critical. List any contradictions \
you resolved in `contradictions_resolved`, even if the resolution was "no real \
contradiction, just different framings."
"""

_SEVERITY_ORDER = [Severity.NONE, Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]


def _summarize_findings(state: CDSSState) -> str:
    lines: list[str] = []

    safety_warnings = state.get("warnings", [])
    if safety_warnings:
        lines.append("Safety (drug-drug interaction) warnings:")
        for w in safety_warnings:
            lines.append(f"  - {', '.join(w.medications)} [{w.severity}]: {w.explanation}")
    else:
        lines.append("Safety: no drug-drug interactions found.")

    lab_context = state.get("lab_context")
    if lab_context:
        lines.append(
            f"Lab context: weight={lab_context.weight_kg}kg, eGFR={lab_context.egfr}, "
            f"liver panel normal={lab_context.liver_panel_normal}"
        )
    else:
        lines.append("Lab context: not on file.")

    dose_results = state.get("dose_results", [])
    for d in dose_results:
        status = "within range" if d.is_within_range else ("out of range" if d.is_within_range is False else "unverifiable")
        lines.append(f"Dose check - {d.medication_name}: {status}. {d.explanation}")

    contraindications = state.get("contraindication_warnings", [])
    for c in contraindications:
        lines.append(f"Contraindication - {c.medication_name} vs {c.condition} [{c.severity}]: {c.explanation}")

    guidelines = state.get("guideline_recommendations", [])
    for g in guidelines:
        lines.append(f"Guideline recommendation: {g.recommendation}")

    alternatives = state.get("alternative_therapies", [])
    for a in alternatives:
        lines.append(f"Suggested alternative: {a.original_medication} -> {a.suggested_alternative} ({a.rationale})")

    return "\n".join(lines)


def build_reflection_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "Findings from all specialist agents:\n\n{findings}"),
        ]
    )
    return prompt | llm.with_structured_output(ReflectionVerdict)


def reflection_node(state: CDSSState, llm: BaseChatModel) -> CDSSState:
    findings = _summarize_findings(state)
    chain = build_reflection_chain(llm)

    try:
        verdict: ReflectionVerdict = chain.invoke({"findings": findings})
    except Exception as exc:  # noqa: BLE001
        # Fail CLOSED: synthesis breaking must not be silently read as "safe".
        logger.error("reflection_failed", extra={"extra_fields": {"error": str(exc)}})
        verdict = ReflectionVerdict(
            is_safe=False,
            overall_severity=Severity.HIGH,
            summary=f"Automated review failed ({exc}); manual physician review required before printing.",
            contradictions_resolved=[],
        )

    return {"reflection": verdict}
