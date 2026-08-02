from app.tools.patient_tools import build_patient_tools


class _FakeSupabaseService:
    """Records calls instead of hitting a real database, so we can assert
    the tools delegate with exactly the right arguments."""

    def __init__(
        self,
        record_result: str = "ok",
        patient_id: str | None = "patient-1",
        to_doctor_id: str | None = "doctor-2",
        refer_result: str = "Referral created: the receiving doctor now has access to this patient's record.",
    ):
        self.record_result = record_result
        self.patient_id = patient_id
        self.to_doctor_id = to_doctor_id
        self.refer_result = refer_result
        self.calls: list[tuple[str, dict]] = []

    def get_patient_full_record(self, **kwargs):
        self.calls.append(("get_patient_full_record", kwargs))
        return self.record_result

    def find_patient_id_by_record_no(self, record_no: str):
        self.calls.append(("find_patient_id_by_record_no", {"record_no": record_no}))
        return self.patient_id

    def find_doctor_id_by_email(self, email: str):
        self.calls.append(("find_doctor_id_by_email", {"email": email}))
        return self.to_doctor_id

    def refer_patient(self, **kwargs):
        self.calls.append(("refer_patient", kwargs))
        return self.refer_result


def test_build_patient_tools_returns_three_tools():
    tools = build_patient_tools(_FakeSupabaseService(), doctor_id="doctor-1")
    names = {t.name for t in tools}
    assert names == {"lookup_patient_by_id", "lookup_patient_by_name", "refer_patient"}


def test_lookup_by_id_tool_delegates_with_doctor_id():
    fake_service = _FakeSupabaseService(record_result="patient record text")
    tools = build_patient_tools(fake_service, doctor_id="doctor-1")
    lookup_by_id = next(t for t in tools if t.name == "lookup_patient_by_id")

    result = lookup_by_id.invoke({"record_no": "REC-0001"})

    assert result == "patient record text"
    assert fake_service.calls == [("get_patient_full_record", {"doctor_id": "doctor-1", "record_no": "REC-0001"})]


def test_lookup_by_name_tool_delegates_with_father_name():
    fake_service = _FakeSupabaseService(record_result="patient record text")
    tools = build_patient_tools(fake_service, doctor_id="doctor-1")
    lookup_by_name = next(t for t in tools if t.name == "lookup_patient_by_name")

    result = lookup_by_name.invoke({"full_name": "Ahmad Karimi", "father_name": "Mohammad"})

    assert result == "patient record text"
    assert fake_service.calls == [
        (
            "get_patient_full_record",
            {"doctor_id": "doctor-1", "full_name": "Ahmad Karimi", "father_name": "Mohammad"},
        )
    ]


def test_refer_patient_tool_resolves_ids_then_delegates():
    fake_service = _FakeSupabaseService(patient_id="patient-1", to_doctor_id="doctor-2")
    tools = build_patient_tools(fake_service, doctor_id="doctor-1")
    refer_tool = next(t for t in tools if t.name == "refer_patient")

    result = refer_tool.invoke(
        {"patient_record_no": "REC-0001", "to_doctor_email": "colleague@watanhospital.af", "reason": "Specialist opinion"}
    )

    assert "Referral created" in result
    assert (
        "refer_patient",
        {"from_doctor_id": "doctor-1", "to_doctor_id": "doctor-2", "patient_id": "patient-1", "reason": "Specialist opinion"},
    ) in fake_service.calls


def test_refer_patient_tool_fails_gracefully_when_patient_not_found():
    fake_service = _FakeSupabaseService(patient_id=None)
    tools = build_patient_tools(fake_service, doctor_id="doctor-1")
    refer_tool = next(t for t in tools if t.name == "refer_patient")

    result = refer_tool.invoke(
        {"patient_record_no": "REC-9999", "to_doctor_email": "colleague@watanhospital.af"}
    )

    assert "No patient found" in result
    # Must not proceed to attempt the referral without a resolved patient.
    assert all(call[0] != "refer_patient" for call in fake_service.calls)


def test_refer_patient_tool_fails_gracefully_when_target_doctor_not_found():
    fake_service = _FakeSupabaseService(patient_id="patient-1", to_doctor_id=None)
    tools = build_patient_tools(fake_service, doctor_id="doctor-1")
    refer_tool = next(t for t in tools if t.name == "refer_patient")

    result = refer_tool.invoke(
        {"patient_record_no": "REC-0001", "to_doctor_email": "unknown@watanhospital.af"}
    )

    assert "No doctor found" in result
    assert all(call[0] != "refer_patient" for call in fake_service.calls)
