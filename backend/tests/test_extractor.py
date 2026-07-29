import pytest

from app.agents.extractor import extractor_node
from app.agents.state import create_initial_state
from app.core.exceptions import ExtractionError
from app.models.schemas import PatientInfo


class _FakeStructuredRunnable:
    """Mimics `prompt | llm.with_structured_output(...)` for a fixed output."""

    def __init__(self, result):
        self._result = result

    def invoke(self, _inputs):
        return self._result


class _FakeLLM:
    """Mimics a LangChain chat model enough for `build_extractor_chain`."""

    def __init__(self, result=None, raise_error=False):
        self._result = result
        self._raise_error = raise_error

    def with_structured_output(self, _schema):
        if self._raise_error:
            class _Raiser:
                def invoke(self, _inputs):
                    raise RuntimeError("LLM parsing failed")
            return _Raiser()
        return _FakeStructuredRunnable(self._result)


def test_extractor_node_success(sample_extraction, monkeypatch):
    # The prompt object is a real ChatPromptTemplate; piping `prompt | structured_llm`
    # requires structured_llm to be a Runnable. We patch build_extractor_chain instead
    # to isolate the node's orchestration logic.
    import app.agents.extractor as extractor_module

    monkeypatch.setattr(
        extractor_module,
        "build_extractor_chain",
        lambda llm: _FakeStructuredRunnable(sample_extraction),
    )

    state = create_initial_state("Patient has a cold.", PatientInfo(), "trace-1")
    result = extractor_node(state, llm=_FakeLLM())

    assert result["extraction"] == sample_extraction
    assert result["extraction_error"] is None


def test_extractor_node_preserves_supplied_patient(sample_extraction, monkeypatch):
    import app.agents.extractor as extractor_module

    monkeypatch.setattr(
        extractor_module,
        "build_extractor_chain",
        lambda llm: _FakeStructuredRunnable(sample_extraction),
    )

    supplied_patient = PatientInfo(name="Alice Smith", age=29, record_no="REC-777")
    state = create_initial_state("Patient has a cold.", supplied_patient, "trace-1")
    result = extractor_node(state, llm=_FakeLLM())

    assert result["extraction"].patient.name == "Alice Smith"
    assert result["extraction"].patient.record_no == "REC-777"


def test_extractor_node_empty_raw_text_raises():
    state = create_initial_state("   ", PatientInfo(), "trace-1")
    with pytest.raises(ExtractionError):
        extractor_node(state, llm=_FakeLLM())


def test_extractor_node_handles_llm_failure(monkeypatch):
    import app.agents.extractor as extractor_module

    def _raise(llm):
        class _Raiser:
            def invoke(self, _inputs):
                raise RuntimeError("boom")
        return _Raiser()

    monkeypatch.setattr(extractor_module, "build_extractor_chain", _raise)

    state = create_initial_state("Patient has a cold.", PatientInfo(), "trace-1")
    result = extractor_node(state, llm=_FakeLLM())

    assert result["extraction"] is None
    assert "boom" in result["extraction_error"]
