"""Patient-sharing endpoint: refer a patient you treat to a colleague by
email. This mirrors the `refer_patient` chat tool, but as a direct,
deterministic REST endpoint for the dedicated "Share patient" form -- no
LLM round-trip needed for something this structured.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.models.schemas import ReferPatientRequest, ReferPatientResponse
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/patients", tags=["patients"])


def get_supabase_service(settings: Settings = Depends(get_settings)) -> SupabaseService:
    return SupabaseService(settings=settings)


@router.post("/refer", response_model=ReferPatientResponse)
def refer_patient(
    payload: ReferPatientRequest,
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> ReferPatientResponse:
    patient_id = supabase_service.find_patient_id_by_record_no(payload.patient_record_no)
    if not patient_id:
        return ReferPatientResponse(
            success=False, message=f"No patient found with record number '{payload.patient_record_no}'."
        )

    to_doctor_id = supabase_service.find_doctor_id_by_email(payload.to_doctor_email)
    if not to_doctor_id:
        return ReferPatientResponse(
            success=False, message=f"No doctor found with email '{payload.to_doctor_email}'."
        )

    message = supabase_service.refer_patient(
        from_doctor_id=doctor.id, to_doctor_id=to_doctor_id, patient_id=patient_id, reason=payload.reason
    )
    success = "Referral created" in message
    return ReferPatientResponse(success=success, message=message)
