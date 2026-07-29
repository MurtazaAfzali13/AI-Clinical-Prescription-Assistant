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
