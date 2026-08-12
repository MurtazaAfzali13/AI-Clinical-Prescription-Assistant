import app.agents.reflection_agent as reflection_module
from app.agents.cdss_state import create_initial_cdss_state
from app.agents.reflection_agent import reflection_node
from app.models.cdss_schemas import ReflectionVerdict
from app.models.schemas import InteractionWarning, PatientInfo, Severity


class _FakeChain:
    def __init__(self, result=None, raise_error=False):
        self._result = result
        self._raise_error = raise_error

    def invoke(self, _inputs):
        if self._raise_error:
            raise RuntimeError("reflection boom")
        return self._result


def test_reflection_node_returns_llm_verdict(monkeypatch):
    verdict = ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="all clear")
    monkeypatch.setattr(reflection_module, "build_reflection_chain", lambda llm: _FakeChain(result=verdict))

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = []

    result = reflection_node(state, llm=object())

    assert result["reflection"] == verdict


def test_reflection_node_fails_closed_on_error(monkeypatch):
    """Unlike the Supervisor (fails open), Reflection must fail CLOSED --
    a broken synthesis step must never silently read as 'safe'."""
    monkeypatch.setattr(
        reflection_module, "build_reflection_chain", lambda llm: _FakeChain(raise_error=True)
    )

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)

    result = reflection_node(state, llm=object())

    verdict = result["reflection"]
    assert verdict.is_safe is False
    assert verdict.overall_severity == Severity.HIGH
    assert "manual physician review" in verdict.summary.lower()


def test_reflection_node_summarizes_all_agent_findings(monkeypatch):
    """Sanity check that the findings summary actually includes data from
    each specialist agent's output field (not just safety)."""
    captured_findings = {}

    class _CapturingChain:
        def invoke(self, inputs):
            captured_findings["text"] = inputs["findings"]
            return ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="ok")

    monkeypatch.setattr(reflection_module, "build_reflection_chain", lambda llm: _CapturingChain())

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = [
        InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="bleeding risk")
    ]

    reflection_node(state, llm=object())

    assert "Ibuprofen" in captured_findings["text"]
    assert "bleeding risk" in captured_findings["text"]
