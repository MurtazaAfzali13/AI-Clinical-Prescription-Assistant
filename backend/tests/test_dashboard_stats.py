from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.services.supabase_service import SupabaseService


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []  # list of (column, op, value)

    def select(self, *_a, **_k):
        return self

    def eq(self, column, value):
        self._filters.append((column, "eq", value))
        return self

    def gte(self, column, value):
        self._filters.append((column, "gte", value))
        return self

    def in_(self, column, values):
        self._filters.append((column, "in", set(values)))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = self._rows
        for column, op, value in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(column) == value]
            elif op == "gte":
                rows = [r for r in rows if str(r.get(column, "")) >= value]
            elif op == "in":
                rows = [r for r in rows if r.get(column) in value]

        class _Result:
            def __init__(self, data):
                self.data = data

        return _Result(rows)


class _FakeClient:
    def __init__(self, prescriptions=None, treatment_relationships=None, patients=None):
        self._prescriptions = prescriptions or []
        self._treatment_relationships = treatment_relationships or []
        self._patients = patients or []

    def table(self, name):
        if name == "prescriptions":
            return _FakeQuery(self._prescriptions)
        if name == "treatment_relationships":
            return _FakeQuery(self._treatment_relationships)
        if name == "patients":
            return _FakeQuery(self._patients)
        raise AssertionError(f"Unexpected table: {name}")


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def test_dashboard_stats_not_configured_returns_zeros():
    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)

    stats = service.get_dashboard_stats(doctor_id="doctor-1")

    assert stats.today_patients == 0
    assert stats.today_prescriptions == 0
    assert stats.daily_series == []


def test_dashboard_stats_counts_today_and_active_patients():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        prescriptions=[
            {"doctor_id": "doctor-1", "patient_id": "p1", "diagnosis": "Headache", "created_at": _iso(0), "status": "draft", "is_safe": True, "warnings": []},
            {"doctor_id": "doctor-1", "patient_id": "p2", "diagnosis": "Flu", "created_at": _iso(0), "status": "printed", "is_safe": True, "warnings": []},
            {"doctor_id": "doctor-1", "patient_id": "p1", "diagnosis": "Follow-up", "created_at": _iso(0), "status": "draft", "is_safe": False, "warnings": [{"severity": "high"}]},
            {"doctor_id": "doctor-1", "patient_id": "p3", "diagnosis": "Headache", "created_at": _iso(3), "status": "draft", "is_safe": True, "warnings": []},
        ],
        treatment_relationships=[
            {"doctor_id": "doctor-1", "patient_id": "p1", "status": "active"},
            {"doctor_id": "doctor-1", "patient_id": "p2", "status": "active"},
        ],
        patients=[
            {"id": "p1", "full_name": "Ahmad Karimi"},
            {"id": "p2", "full_name": "Sara Ahmadi"},
            {"id": "p3", "full_name": "Ali Rezaei"},
        ],
    )
    service = SupabaseService(settings=settings, client=fake_client)

    stats = service.get_dashboard_stats(doctor_id="doctor-1")

    # Two distinct patients (p1, p2) were seen today across 3 today-rows.
    assert stats.today_patients == 2
    assert stats.today_prescriptions == 3
    assert stats.active_patients == 2
    assert stats.safety_warnings_today == 1  # one warning on the p1 follow-up

    # Daily series should have an entry for today with count 3.
    today_entry = next(d for d in stats.daily_series if d.date == datetime.now(timezone.utc).date().isoformat())
    assert today_entry.count == 3

    # Top diagnoses: Headache appears twice.
    top_labels = {d.label: d.count for d in stats.top_diagnoses}
    assert top_labels["Headache"] == 2

    # Recent prescriptions resolve patient names via the patients table.
    assert any(r.patient_name == "Ahmad Karimi" for r in stats.recent_prescriptions)


def test_dashboard_stats_daily_series_covers_requested_range_with_zeros():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(prescriptions=[], treatment_relationships=[], patients=[])
    service = SupabaseService(settings=settings, client=fake_client)

    stats = service.get_dashboard_stats(doctor_id="doctor-1", days=7)

    assert len(stats.daily_series) == 7
    assert all(d.count == 0 for d in stats.daily_series)
