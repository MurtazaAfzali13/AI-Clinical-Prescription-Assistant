"""Thin wrapper around the Supabase client for persisting prescriptions.

Persistence is best-effort and non-blocking: if Supabase isn't configured
(no URL/key in settings, e.g. in local dev or tests) the service quietly
no-ops instead of failing the request, since the Extractor/Safety pipeline
must keep working without a database.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.schemas import PrescriptionResponse

logger = get_logger(__name__)


class SupabaseService:
    def __init__(self, settings: Settings, client: Any = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.supabase_url and self._settings.supabase_service_key)

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.is_configured:
            return None
        from supabase import create_client

        self._client = create_client(self._settings.supabase_url, self._settings.supabase_service_key)
        return self._client

    def save_prescription(
        self, doctor_id: str, response: PrescriptionResponse, patient_record_no: str | None
    ) -> None:
        client = self._ensure_client()
        if client is None:
            logger.info("supabase_not_configured_skip_persist")
            return

        try:
            patient_id = None
            if patient_record_no:
                patient_id = self._upsert_patient(client, response, patient_record_no)

            client.table("prescriptions").upsert(
                {
                    "trace_id": response.trace_id,
                    "doctor_id": doctor_id,
                    "patient_id": patient_id,
                    "raw_text": "",  # populated by caller if desired
                    "diagnosis": response.extraction.diagnosis,
                    "medications": [m.model_dump() for m in response.extraction.medications],
                    "advice": response.extraction.advice,
                    "warnings": [w.model_dump() for w in response.warnings],
                    "is_safe": response.is_safe,
                    "status": "draft",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="trace_id",
            ).execute()
        except Exception as exc:  # noqa: BLE001 - persistence must never break the pipeline
            logger.error("supabase_persist_failed", extra={"extra_fields": {"error": str(exc)}})

    def _upsert_patient(self, client, response: PrescriptionResponse, record_no: str) -> str | None:
        patient = response.extraction.patient
        result = (
            client.table("patients")
            .upsert(
                {
                    "record_no": record_no,
                    "full_name": patient.name or "Unknown",
                    "age": patient.age,
                },
                on_conflict="record_no",
            )
            .execute()
        )
        rows = result.data or []
        return rows[0]["id"] if rows else None

    def record_override(self, prescription_trace_id: str, doctor_id: str, reason: str) -> None:
        client = self._ensure_client()
        if client is None:
            logger.info("supabase_not_configured_skip_override")
            return
        try:
            presc = (
                client.table("prescriptions")
                .select("id")
                .eq("trace_id", prescription_trace_id)
                .limit(1)
                .execute()
            )
            rows = presc.data or []
            if not rows:
                logger.error("override_prescription_not_found", extra={"extra_fields": {"trace_id": prescription_trace_id}})
                return
            prescription_id = rows[0]["id"]

            client.table("prescription_overrides").insert(
                {"prescription_id": prescription_id, "doctor_id": doctor_id, "reason": reason}
            ).execute()
            client.table("prescriptions").update({"status": "overridden"}).eq("id", prescription_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("supabase_override_failed", extra={"extra_fields": {"error": str(exc)}})
