from app.agents.state import create_initial_state
from app.models.schemas import PatientInfo


def test_create_initial_state_defaults():
    state = create_initial_state(
        raw_text="Patient has a headache.",
        patient=PatientInfo(name="Jane"),
        trace_id="trace-1",
    )

    assert state["raw_text"] == "Patient has a headache."
    assert state["patient"].name == "Jane"
    assert state["extraction"] is None
    assert state["extraction_error"] is None
    assert state["warnings"] == []
    assert state["is_safe"] is True
    assert state["trace_id"] == "trace-1"
    assert state["messages"] == []
