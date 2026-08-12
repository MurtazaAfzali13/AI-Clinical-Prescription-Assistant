from app.agents.cdss_state import create_initial_cdss_state
from app.agents.context_lab_agent import lab_node
from app.models.schemas import PatientInfo


class _FakeSupabaseService:
    def __init__(self, row=None):
        self._row = row

    def get_lab_context(self, record_no, national_id=None):
        return self._row


def test_lab_node_populates_lab_context():
    state = create_initial_cdss_state("note", PatientInfo(record_no="REC-0001"), "t1", use_copilot_mode=True)
    fake_service = _FakeSupabaseService(
        row={
            "weight_kg": 80,
            "age": 45,
            "egfr": 55,
            "liver_panel_normal": True,
            "labs_recorded_at": "2026-07-01T00:00:00+00:00",
            "chronic_conditions": ["hypertension"],
            "allergies": [],
        }
    )

    result = lab_node(state, supabase_service=fake_service)

    assert result["lab_context"] is not None
    assert result["lab_context"].weight_kg == 80
    assert result["lab_context"].egfr == 55
    assert result["lab_context"].chronic_conditions == ["hypertension"]


def test_lab_node_handles_no_data_on_file():
    state = create_initial_cdss_state("note", PatientInfo(record_no="REC-9999"), "t1", use_copilot_mode=True)
    fake_service = _FakeSupabaseService(row=None)

    result = lab_node(state, supabase_service=fake_service)

    assert result["lab_context"] is None
