"""Tools that give the patient-records chat agent read access to the
patient database, via `SupabaseService`.

Each tool is bound to a specific `doctor_id` at build time (via closures),
so every lookup the LLM triggers is automatically attributed to the doctor
running the conversation -- this is what makes the audit log in
`patient_lookup_audit_log` meaningful.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.supabase_service import SupabaseService


class LookupByIdInput(BaseModel):
    record_no: str = Field(
        ..., description="The patient's record number (e.g. 'REC-0001') or national ID."
    )


class LookupByNameInput(BaseModel):
    full_name: str = Field(..., description="The patient's full name.")
    father_name: str | None = Field(
        default=None,
        description="The patient's father's name, used to disambiguate when multiple "
        "patients share the same full name.",
    )


class ReferPatientInput(BaseModel):
    patient_record_no: str = Field(
        ..., description="The record number or national ID of the patient being referred."
    )
    to_doctor_email: str = Field(..., description="The email of the doctor to refer the patient to.")
    reason: str | None = Field(default=None, description="The clinical reason for the referral.")


def build_patient_tools(supabase_service: SupabaseService, doctor_id: str) -> list[StructuredTool]:
    """Returns the patient-lookup and referral tools, bound to this doctor's identity."""

    def _lookup_by_id(record_no: str) -> str:
        return supabase_service.get_patient_full_record(doctor_id=doctor_id, record_no=record_no)

    def _lookup_by_name(full_name: str, father_name: str | None = None) -> str:
        return supabase_service.get_patient_full_record(
            doctor_id=doctor_id, full_name=full_name, father_name=father_name
        )

    def _refer_patient(patient_record_no: str, to_doctor_email: str, reason: str | None = None) -> str:
        patient_id = supabase_service.find_patient_id_by_record_no(patient_record_no)
        if not patient_id:
            return f"No patient found with record number '{patient_record_no}'."

        to_doctor_id = supabase_service.find_doctor_id_by_email(to_doctor_email)
        if not to_doctor_id:
            return f"No doctor found with email '{to_doctor_email}'."

        return supabase_service.refer_patient(
            from_doctor_id=doctor_id, to_doctor_id=to_doctor_id, patient_id=patient_id, reason=reason
        )

    lookup_by_id = StructuredTool.from_function(
        func=_lookup_by_id,
        name="lookup_patient_by_id",
        description=(
            "Look up a patient's full medical record (demographics, allergies, chronic "
            "conditions, and recent prescription history) using their record number or "
            "national ID. Prefer this over name lookup whenever an ID is available -- it's "
            "unambiguous."
        ),
        args_schema=LookupByIdInput,
    )
    lookup_by_name = StructuredTool.from_function(
        func=_lookup_by_name,
        name="lookup_patient_by_name",
        description=(
            "Look up a patient's full medical record using their full name, optionally "
            "narrowed by their father's name to disambiguate common names. If this returns "
            "multiple matches, ask the doctor for the exact record number instead of guessing."
        ),
        args_schema=LookupByNameInput,
    )
    refer_patient = StructuredTool.from_function(
        func=_refer_patient,
        name="refer_patient",
        description=(
            "Refer a patient you currently treat to another doctor by email, sharing access to "
            "the patient's record with them. Only works if you already have an active treatment "
            "relationship with the patient -- you can't refer a patient you don't treat."
        ),
        args_schema=ReferPatientInput,
    )
    return [lookup_by_id, lookup_by_name, refer_patient]
