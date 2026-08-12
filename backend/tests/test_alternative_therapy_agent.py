import app.agents.alternative_therapy_agent as alt_module
from app.agents.alternative_therapy_agent import (
    _AlternativeSuggestion,
    alternative_therapy_node,
    should_run_alternative_agent,
)
from app.agents.cdss_state import create_initial_cdss_state
from app.models.schemas import InteractionWarning, PatientInfo


class _FakeChain:
    def __init__(self, result):
        self._result = result

    def invoke(self, _inputs):
        return self._result


class _FakePineconeService:
    def __init__(self, matches=None):
        self._matches = matches or []

    def query_namespace(self, query_text, namespace, top_k=5, filter=None):
        return self._matches


def test_should_run_alternative_agent_true_when_safety_warning_present():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = [InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="x")]
    assert should_run_alternative_agent(state) is True


def test_should_run_alternative_agent_false_when_nothing_flagged():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    assert should_run_alternative_agent(state) is False


def test_alternative_therapy_node_suggests_grounded_alternative(monkeypatch):
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = [
        InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="bleeding risk")
    ]

    suggestion = _AlternativeSuggestion(
        has_alternative=True, alternative_drug="Acetaminophen", rationale="Lower bleeding risk per guideline."
    )
    monkeypatch.setattr(alt_module, "_build_chain", lambda llm: _FakeChain(suggestion))

    pinecone_service = _FakePineconeService(
        matches=[{"content": "Acetaminophen preferred over NSAIDs in anticoagulated patients.", "metadata": {}, "score": 0.88}]
    )

    result = alternative_therapy_node(state, llm=object(), pinecone_service=pinecone_service)

    assert len(result["alternative_therapies"]) == 1
    alt = result["alternative_therapies"][0]
    assert alt.original_medication == "Ibuprofen"
    assert alt.suggested_alternative == "Acetaminophen"
    assert alt.evidence is not None


def test_alternative_therapy_node_skips_when_llm_finds_no_grounded_alternative(monkeypatch):
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = [
        InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="bleeding risk")
    ]

    suggestion = _AlternativeSuggestion(has_alternative=False)
    monkeypatch.setattr(alt_module, "_build_chain", lambda llm: _FakeChain(suggestion))

    pinecone_service = _FakePineconeService(matches=[{"content": "unrelated text", "metadata": {}, "score": 0.5}])

    result = alternative_therapy_node(state, llm=object(), pinecone_service=pinecone_service)

    assert result["alternative_therapies"] == []


def test_alternative_therapy_node_skips_when_nothing_retrieved(monkeypatch):
    """No retrieved text -> nothing to ground a suggestion in -> the chain
    is built (since something was flagged) but never invoked."""
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = [
        InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="bleeding risk")
    ]

    invoke_calls = []

    class _TrackingFakeChain:
        def invoke(self, _inputs):
            invoke_calls.append("invoked")
            return None

    monkeypatch.setattr(alt_module, "_build_chain", lambda llm: _TrackingFakeChain())

    pinecone_service = _FakePineconeService(matches=[])

    result = alternative_therapy_node(state, llm=object(), pinecone_service=pinecone_service)

    assert result["alternative_therapies"] == []
    assert invoke_calls == []  # never actually invoked, since no matches were retrieved


def test_alternative_therapy_node_no_flags_returns_empty():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)

    result = alternative_therapy_node(state, llm=object(), pinecone_service=_FakePineconeService())

    assert result["alternative_therapies"] == []
