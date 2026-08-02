from app.core.config import Settings
from app.services.supabase_service import SupabaseService


def test_supabase_service_not_configured_by_default():
    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)
    assert service.is_configured is False


def test_supabase_service_save_prescription_noops_without_config(sample_extraction):
    from app.models.schemas import PrescriptionResponse

    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)
    response = PrescriptionResponse(
        extraction=sample_extraction, warnings=[], is_safe=True, trace_id="trace-1"
    )

    # Should not raise even though no Supabase client is configured.
    service.save_prescription(doctor_id="doctor-1", response=response, patient_record_no="REC-001")


def test_supabase_service_record_override_noops_without_config():
    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)

    service.record_override(prescription_trace_id="trace-1", doctor_id="doctor-1", reason="Clinically justified")


def test_get_patient_full_record_not_configured():
    settings = Settings(supabase_url="", supabase_service_key="")
    service = SupabaseService(settings=settings)

    result = service.get_patient_full_record(doctor_id="doctor-1", record_no="REC-0001")
    assert "not configured" in result


def test_get_patient_full_record_requires_search_term():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    service = SupabaseService(settings=settings, client=object())

    result = service.get_patient_full_record(doctor_id="doctor-1")
    assert "provide either" in result


class _FakeQuery:
    """Minimal stand-in for the Supabase/PostgREST fluent query builder."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: dict[str, object] = {}

    def select(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def ilike(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def in_(self, column, values):
        self._filters[column] = set(values)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self._rows
        for column, expected in self._filters.items():
            if isinstance(expected, set):
                rows = [r for r in rows if r.get(column) in expected]
            else:
                rows = [r for r in rows if r.get(column) == expected]

        class _Result:
            def __init__(self, data):
                self.data = data

        return _Result(rows)


class _FakeClient:
    """Simulates the tables this service touches: patients, prescriptions,
    treatment_relationships, and patient_lookup_audit_log."""

    def __init__(
        self,
        patients: list[dict],
        prescriptions: list[dict],
        treatment_relationships: list[dict] | None = None,
    ):
        self._patients = patients
        self._prescriptions = prescriptions
        self._treatment_relationships = treatment_relationships or []
        self.inserted_audit_rows: list[dict] = []

    def table(self, name: str):
        if name == "patients":
            return _FakeQuery(self._patients)
        if name == "prescriptions":
            return _FakeQuery(self._prescriptions)
        if name == "treatment_relationships":
            return _FakeQuery(self._treatment_relationships)
        if name == "patient_lookup_audit_log":
            query = _FakeQuery([])
            original_insert = query.insert

            def _tracking_insert(payload, *args, **kwargs):
                self.inserted_audit_rows.append(payload)
                return original_insert(payload, *args, **kwargs)

            query.insert = _tracking_insert
            return query
        raise AssertionError(f"Unexpected table: {name}")


def _active_relationship(doctor_id: str, patient_id: str) -> dict:
    return {"doctor_id": doctor_id, "patient_id": patient_id, "status": "active"}


def test_get_patient_full_record_found_single_match_with_relationship():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[
            {
                "id": "patient-1",
                "record_no": "REC-0001",
                "national_id": "1234567",
                "full_name": "Ahmad Karimi",
                "father_name": "Mohammad Karimi",
                "age": 45,
                "gender": "male",
                "allergies": ["Penicillin"],
                "chronic_conditions": ["Atrial fibrillation"],
            }
        ],
        prescriptions=[
            {
                "patient_id": "patient-1",
                "created_at": "2026-07-29T10:00:00+00:00",
                "diagnosis": "Headache",
                "medications": [{"name": "Ibuprofen"}],
                "status": "overridden",
            }
        ],
        treatment_relationships=[_active_relationship("doctor-1", "patient-1")],
    )
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.get_patient_full_record(doctor_id="doctor-1", record_no="REC-0001")

    assert "Ahmad Karimi" in result
    assert "Mohammad Karimi" in result
    assert "Penicillin" in result
    assert "Atrial fibrillation" in result
    assert "Ibuprofen" in result
    assert "overridden" in result
    # Confirms the lookup was audited.
    assert len(fake_client.inserted_audit_rows) == 1
    assert fake_client.inserted_audit_rows[0]["found"] is True
    assert fake_client.inserted_audit_rows[0]["patient_id"] == "patient-1"


def test_get_patient_full_record_denied_without_treatment_relationship():
    """The core access-control behavior: a doctor with no treatment
    relationship must NOT see the patient's record, even though the
    patient row exists and matches the search."""
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[
            {"id": "patient-1", "record_no": "REC-0001", "full_name": "Ahmad Karimi", "father_name": "Mohammad"}
        ],
        prescriptions=[{"patient_id": "patient-1", "diagnosis": "Secret condition", "medications": []}],
        treatment_relationships=[],  # no relationship for doctor-2
    )
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.get_patient_full_record(doctor_id="doctor-2", record_no="REC-0001")

    # Must not leak the patient's data...
    assert "Secret condition" not in result
    # ...and must not even confirm the patient exists.
    assert "Ahmad Karimi" not in result
    assert "No matching patient found" in result


def test_get_patient_full_record_multiple_matches_only_within_doctors_relationships():
    """Two patients share a name; the doctor only treats one of them.
    Disambiguation must only ever mention patients within the doctor's
    own treatment relationships -- never the other one."""
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[
            {"id": "p1", "record_no": "REC-0001", "full_name": "Ahmad Karimi", "father_name": "Mohammad"},
            {"id": "p2", "record_no": "REC-0002", "full_name": "Ahmad Karimi", "father_name": "Ali"},
        ],
        prescriptions=[],
        treatment_relationships=[_active_relationship("doctor-1", "p1")],  # only p1
    )
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.get_patient_full_record(doctor_id="doctor-1", full_name="Ahmad Karimi")

    # Only the patient this doctor treats should surface -- single match,
    # not a disambiguation prompt, and the other patient must not appear.
    assert "REC-0001" in result
    assert "REC-0002" not in result
    assert "Multiple patients matched" not in result


def test_get_patient_full_record_no_match():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(patients=[], prescriptions=[])
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.get_patient_full_record(doctor_id="doctor-1", record_no="REC-9999")

    assert "No matching patient found" in result
    assert fake_client.inserted_audit_rows[0]["found"] is False


def test_has_treatment_relationship_true_and_false():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[],
        prescriptions=[],
        treatment_relationships=[_active_relationship("doctor-1", "patient-1")],
    )
    service = SupabaseService(settings=settings, client=fake_client)

    assert service.has_treatment_relationship("doctor-1", "patient-1") is True
    assert service.has_treatment_relationship("doctor-2", "patient-1") is False


def test_refer_patient_requires_existing_relationship():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(patients=[], prescriptions=[], treatment_relationships=[])
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.refer_patient(from_doctor_id="doctor-1", to_doctor_id="doctor-2", patient_id="patient-1")

    assert "don't have an active treatment relationship" in result


def test_refer_patient_succeeds_when_referrer_has_relationship():
    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeClient(
        patients=[],
        prescriptions=[],
        treatment_relationships=[_active_relationship("doctor-1", "patient-1")],
    )
    service = SupabaseService(settings=settings, client=fake_client)

    result = service.refer_patient(
        from_doctor_id="doctor-1", to_doctor_id="doctor-2", patient_id="patient-1", reason="Specialist opinion"
    )

    assert "Referral created" in result
