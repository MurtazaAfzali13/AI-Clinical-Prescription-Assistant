"""Doctor analytics dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.models.schemas import DashboardStats
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_supabase_service(settings: Settings = Depends(get_settings)) -> SupabaseService:
    return SupabaseService(settings=settings)


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> DashboardStats:
    return supabase_service.get_dashboard_stats(doctor_id=doctor.id)
