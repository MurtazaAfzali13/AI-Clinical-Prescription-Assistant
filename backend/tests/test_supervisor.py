import pytest

from app.agents.cdss_state import create_initial_cdss_state
from app.agents.supervisor import supervisor_node
import app.agents.supervisor as supervisor_module
from app.models.cdss_schemas import RoutingDecision
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction


class _FakeChain:
    def __init__(self, result=None, raise_error=False):
        self._result = result
        self._raise_error = raise_error

    def invoke(self, _inputs):
        if self._raise_error:
            raise RuntimeError("router boom")
        return self._result


class _FakeLLM:
    """Never actually exercised (build_supervisor_chain is monkeypatched
    in these tests), but supervisor_node's signature still requires an
    llm argument to pass through."""


@pytest.fixture
def extraction() -> PrescriptionExtraction:
    return PrescriptionExtraction(
        patient=PatientInfo(name="Ahmad Karimi"),
        diagnosis="Essential hypertension",
        medications=[Medication(name="Amlodipine", dosage="5mg", frequency="once daily")],
        current_medications=[],
        advice="Reduce salt intake.",
    )


def test_supervisor_node_returns_llm_decision(extraction, monkeypatch):
    decision = RoutingDecision(run_dose_agent=True, run_guideline_agent=True, reasoning="dose+guideline relevant")
    monkeypatch.setattr(supervisor_module, "build_supervisor_chain", lambda llm: _FakeChain(result=decision))

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = extraction

    result = supervisor_node(state, llm=_FakeLLM())

    assert result["routing_decision"] == decision


def test_supervisor_node_no_extraction_skips_everything():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = None

    result = supervisor_node(state, llm=_FakeLLM())

    decision = result["routing_decision"]
    assert decision.run_dose_agent is False
    assert decision.run_lab_agent is False
    assert decision.run_contraindication_agent is False
    assert decision.run_guideline_agent is False


def test_supervisor_node_fails_open_on_llm_error(extraction, monkeypatch):
    """If the router itself breaks, we run everything rather than silently
    skipping specialist checks."""
    monkeypatch.setattr(
        supervisor_module, "build_supervisor_chain", lambda llm: _FakeChain(raise_error=True)
    )

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = extraction

    result = supervisor_node(state, llm=_FakeLLM())

    decision = result["routing_decision"]
    assert decision.run_dose_agent is True
    assert decision.run_lab_agent is True
    assert decision.run_contraindication_agent is True
    assert decision.run_guideline_agent is True
    assert "failed" in decision.reasoning.lower()
