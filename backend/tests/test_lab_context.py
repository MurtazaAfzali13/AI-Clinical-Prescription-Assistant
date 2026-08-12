from app.core.config import Settings
from app.services.supabase_service import SupabaseService


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def or_(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        class _Result:
            def __init__(self, data):
                self.data = data

        return _Result(self._rows)


class _FakeClient:
    def __init__(self, patients):
        self._patients = patients

    def table(self, name):
        if name == "patients":
            return _FakeQuery(self._patients)
        raise AssertionError(f"Unexpected table: {name}")


def test_get_lab_context_not_configured_returns_none():
    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)
    assert service.get_lab_context(record_no="REC-0001") is None


def test_get_lab_context_requires_a_lookup_value():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    service = SupabaseService(settings=settings, client=object())
    assert service.get_lab_context(record_no=None, national_id=None) is None


def test_get_lab_context_returns_row():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[
            {
                "full_name": "Ahmad Karimi",
                "age": 45,
                "weight_kg": 80,
                "egfr": 55,
                "liver_panel_normal": True,
                "labs_recorded_at": "2026-07-01T00:00:00+00:00",
                "chronic_conditions": ["hypertension"],
                "allergies": ["penicillin"],
            }
        ]
    )
    service = SupabaseService(settings=settings, client=fake_client)

    context = service.get_lab_context(record_no="REC-0001")

    assert context is not None
    assert context["weight_kg"] == 80
    assert context["egfr"] == 55


def test_get_lab_context_no_match_returns_none():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    service = SupabaseService(settings=settings, client=_FakeClient(patients=[]))

    assert service.get_lab_context(record_no="REC-9999") is None
