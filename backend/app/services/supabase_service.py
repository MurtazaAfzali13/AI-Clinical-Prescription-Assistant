"""Thin wrapper around the Supabase client for persisting prescriptions.

Persistence is best-effort and non-blocking: if Supabase isn't configured
(no URL/key in settings, e.g. in local dev or tests) the service quietly
no-ops instead of failing the request, since the Extractor/Safety pipeline
must keep working without a database.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.schemas import DailyCount, DashboardStats, DiagnosisBreakdown, PrescriptionResponse, RecentPrescriptionSummary

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
                if patient_id:
                    # Writing a prescription IS the clinical encounter that
                    # establishes (or re-activates) this doctor's treatment
                    # relationship with the patient -- this is what the
                    # patient-lookup chatbot's access check relies on.
                    self._ensure_treatment_relationship(client, doctor_id, patient_id)

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

    def _ensure_treatment_relationship(
        self, client, doctor_id: str, patient_id: str, referred_by: str | None = None
    ) -> None:
        """Creates (or re-activates) an 'active' treatment relationship
        between this doctor and this patient. Idempotent: upserts on the
        (doctor_id, patient_id) unique constraint, so calling this on every
        prescription is safe and cheap."""
        try:
            client.table("treatment_relationships").upsert(
                {
                    "doctor_id": doctor_id,
                    "patient_id": patient_id,
                    "status": "active",
                    "referred_by": referred_by,
                    "ended_at": None,
                },
                on_conflict="doctor_id,patient_id",
            ).execute()
        except Exception as exc:  # noqa: BLE001 - must never break prescription saving
            logger.error("treatment_relationship_upsert_failed", extra={"extra_fields": {"error": str(exc)}})

    def has_treatment_relationship(self, doctor_id: str, patient_id: str) -> bool:
        """True if this doctor currently has an active or referred
        treatment relationship with this patient -- the access-control
        check the patient-lookup chatbot must pass before revealing any
        clinical data."""
        client = self._ensure_client()
        if client is None:
            return False
        try:
            result = (
                client.table("treatment_relationships")
                .select("id")
                .eq("doctor_id", doctor_id)
                .eq("patient_id", patient_id)
                .in_("status", ["active", "referred"])
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as exc:  # noqa: BLE001
            logger.error("treatment_relationship_check_failed", extra={"extra_fields": {"error": str(exc)}})
            return False

    def find_patient_id_by_record_no(self, record_no: str) -> str | None:
        """Resolves a patient's internal UUID from their record number or
        national ID. Used internally by the refer-patient tool -- the
        referring doctor already knows this record number because they
        treat the patient, and `refer_patient` still enforces the
        relationship check before anything is shared."""
        client = self._ensure_client()
        if client is None:
            return None
        try:
            result = (
                client.table("patients")
                .select("id")
                .or_(f"record_no.eq.{record_no},national_id.eq.{record_no}")
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0]["id"] if rows else None
        except Exception as exc:  # noqa: BLE001
            logger.error("find_patient_id_failed", extra={"extra_fields": {"error": str(exc)}})
            return None

    def find_doctor_id_by_email(self, email: str) -> str | None:
        """Resolves a doctor's ID from their email, for the refer-patient tool."""
        client = self._ensure_client()
        if client is None:
            return None
        try:
            result = client.table("doctors").select("id").eq("email", email).limit(1).execute()
            rows = result.data or []
            return rows[0]["id"] if rows else None
        except Exception as exc:  # noqa: BLE001
            logger.error("find_doctor_id_failed", extra={"extra_fields": {"error": str(exc)}})
            return None

    def refer_patient(
        self, from_doctor_id: str, to_doctor_id: str, patient_id: str, reason: str | None = None
    ) -> str:
        """Shares treatment access with another doctor (a referral).
        Requires the referring doctor to already hold an active
        relationship with the patient -- you can't refer a patient you
        don't treat."""
        client = self._ensure_client()
        if client is None:
            return "Referral is unavailable: Supabase is not configured in this environment."

        if not self.has_treatment_relationship(from_doctor_id, patient_id):
            return "You don't have an active treatment relationship with this patient, so you can't refer them."

        try:
            client.table("treatment_relationships").upsert(
                {
                    "doctor_id": to_doctor_id,
                    "patient_id": patient_id,
                    "status": "referred",
                    "referred_by": from_doctor_id,
                    "reason": reason,
                    "ended_at": None,
                },
                on_conflict="doctor_id,patient_id",
            ).execute()
            return "Referral created: the receiving doctor now has access to this patient's record."
        except Exception as exc:  # noqa: BLE001
            logger.error("refer_patient_failed", extra={"extra_fields": {"error": str(exc)}})
            return f"Referral failed due to a system error: {exc}"

    def end_treatment_relationship(self, doctor_id: str, patient_id: str) -> None:
        """Marks a treatment relationship as ended (kept for audit history,
        no longer grants access)."""
        client = self._ensure_client()
        if client is None:
            return
        try:
            client.table("treatment_relationships").update(
                {"status": "ended", "ended_at": datetime.now(timezone.utc).isoformat()}
            ).eq("doctor_id", doctor_id).eq("patient_id", patient_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("end_treatment_relationship_failed", extra={"extra_fields": {"error": str(exc)}})

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

    def get_patient_full_record(
        self,
        doctor_id: str,
        record_no: str | None = None,
        full_name: str | None = None,
        father_name: str | None = None,
    ) -> str:
        """Looks up a patient by record number/national ID, or by full name
        (optionally narrowed by father's name), and returns a plain-text
        summary of their demographics, allergies, chronic conditions, and
        recent prescription history -- formatted for an LLM tool result.

        Every lookup attempt is recorded in `patient_lookup_audit_log`,
        since this reads sensitive medical records (PHI) directly.
        """
        client = self._ensure_client()
        if client is None:
            return "Patient lookup is unavailable: Supabase is not configured in this environment."

        if not record_no and not full_name:
            return "Please provide either a record number/national ID, or a patient's full name."

        try:
            query = client.table("patients").select("*")
            if record_no:
                query = query.or_(f"record_no.eq.{record_no},national_id.eq.{record_no}")
            else:
                query = query.ilike("full_name", f"%{full_name}%")
                if father_name:
                    query = query.ilike("father_name", f"%{father_name}%")

            result = query.limit(5).execute()
            all_rows = result.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("patient_lookup_failed", extra={"extra_fields": {"error": str(exc)}})
            return f"Patient lookup failed due to a system error: {exc}"

        # Filter to patients this doctor actually has a treatment
        # relationship with BEFORE any disambiguation logic runs -- this
        # matters because otherwise the "multiple matches" branch below
        # would leak the existence, name, and record number of patients
        # outside this doctor's care just from a name search.
        rows = [row for row in all_rows if self.has_treatment_relationship(doctor_id, row["id"])]

        self._log_patient_lookup(
            doctor_id=doctor_id,
            query_text=record_no or f"{full_name} / father: {father_name}",
            patient_id=rows[0]["id"] if len(rows) == 1 else None,
            found=bool(rows),
        )

        if not rows:
            # Deliberately identical wording whether zero patients matched the
            # search at all, or some matched but this doctor has no treatment
            # relationship with them -- distinguishing the two would leak
            # whether a specific patient exists to a doctor who isn't
            # authorized to know that.
            return (
                "No matching patient found within your active treatment relationships. "
                "Double-check the record number/name, or note that you may need to see this "
                "patient for a new visit, or request a referral from their treating doctor."
            )

        if len(rows) > 1:
            candidates = "; ".join(
                f"{row['full_name']} (father: {row.get('father_name') or 'unknown'}, record no: {row['record_no']})"
                for row in rows
            )
            return (
                f"Multiple patients matched this search: {candidates}. "
                "Ask the doctor to specify the exact record number to disambiguate."
            )

        patient = rows[0]
        prescriptions = self._fetch_prescriptions(client, patient["id"])
        return self._format_patient_record(patient, prescriptions)

    def _fetch_prescriptions(self, client, patient_id: str, limit: int = 10) -> list[dict]:
        try:
            result = (
                client.table("prescriptions")
                .select("*")
                .eq("patient_id", patient_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("fetch_prescriptions_failed", extra={"extra_fields": {"error": str(exc)}})
            return []

    @staticmethod
    def _format_patient_record(patient: dict, prescriptions: list[dict]) -> str:
        lines = [
            f"Patient: {patient['full_name']} (father: {patient.get('father_name') or 'unknown'})",
            f"Record No: {patient['record_no']} | National ID: {patient.get('national_id') or 'N/A'} "
            f"| Age: {patient.get('age', 'N/A')} | Gender: {patient.get('gender') or 'N/A'}",
        ]
        if patient.get("allergies"):
            lines.append(f"Allergies: {', '.join(patient['allergies'])}")
        if patient.get("chronic_conditions"):
            lines.append(f"Chronic conditions: {', '.join(patient['chronic_conditions'])}")

        lines.append("")
        lines.append("Recent prescriptions:")
        if not prescriptions:
            lines.append("- No prescription history on file.")
        for p in prescriptions:
            meds = ", ".join(m.get("name", "?") for m in (p.get("medications") or []))
            status_note = f" [{p['status']}]" if p.get("status") and p["status"] != "draft" else ""
            created = str(p.get("created_at", ""))[:10]
            lines.append(f"- {created}: Dx: {p.get('diagnosis', '?')}; Meds: {meds or 'none'}{status_note}")

        return "\n".join(lines)

    def _log_patient_lookup(
        self, doctor_id: str, query_text: str, patient_id: str | None, found: bool
    ) -> None:
        client = self._ensure_client()
        if client is None:
            return
        try:
            client.table("patient_lookup_audit_log").insert(
                {
                    "doctor_id": doctor_id,
                    "patient_id": patient_id,
                    "query_text": query_text,
                    "found": found,
                }
            ).execute()
        except Exception as exc:  # noqa: BLE001 - auditing must never break the lookup itself
            logger.error("audit_log_failed", extra={"extra_fields": {"error": str(exc)}})

    def get_dashboard_stats(self, doctor_id: str, days: int = 14) -> DashboardStats:
        """Aggregates this doctor's recent activity for the analytics
        dashboard: today's volume, a daily trend series, a top-diagnoses
        breakdown, and a short list of recent prescriptions.

        Everything is computed in Python from a single bounded fetch rather
        than multiple aggregate SQL queries, since the data volumes here
        (one doctor's recent prescriptions) are small and this keeps the
        Supabase-facing surface simple and easy to mock in tests.
        """
        client = self._ensure_client()
        if client is None:
            return DashboardStats()

        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            result = (
                client.table("prescriptions")
                .select("*")
                .eq("doctor_id", doctor_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )
            prescriptions = result.data or []

            active_result = (
                client.table("treatment_relationships")
                .select("id")
                .eq("doctor_id", doctor_id)
                .eq("status", "active")
                .execute()
            )
            active_patients = len(active_result.data or [])
        except Exception as exc:  # noqa: BLE001
            logger.error("dashboard_stats_failed", extra={"extra_fields": {"error": str(exc)}})
            return DashboardStats()

        today_str = datetime.now(timezone.utc).date().isoformat()
        today_rows = [p for p in prescriptions if str(p.get("created_at", ""))[:10] == today_str]
        today_patient_ids = {p["patient_id"] for p in today_rows if p.get("patient_id")}
        today_warnings = sum(len(p.get("warnings") or []) for p in today_rows)

        day_counts: Counter[str] = Counter()
        for p in prescriptions:
            day_counts[str(p.get("created_at", ""))[:10]] += 1
        daily_series = [
            DailyCount(date=day, count=day_counts.get(day, 0))
            for day in self._last_n_days(days)
        ]

        diagnosis_counts = Counter(p.get("diagnosis", "Unspecified").strip() for p in prescriptions if p.get("diagnosis"))
        top_diagnoses = [
            DiagnosisBreakdown(label=label, count=count) for label, count in diagnosis_counts.most_common(5)
        ]

        patient_ids = {p["patient_id"] for p in prescriptions[:5] if p.get("patient_id")}
        names_by_id = self._fetch_patient_names(client, patient_ids)
        recent_prescriptions = [
            RecentPrescriptionSummary(
                patient_name=names_by_id.get(p.get("patient_id"), "Unknown"),
                diagnosis=p.get("diagnosis", "-"),
                created_at=str(p.get("created_at", "")),
                status=p.get("status", "draft"),
                is_safe=p.get("is_safe", True),
            )
            for p in prescriptions[:5]
        ]

        return DashboardStats(
            today_patients=len(today_patient_ids),
            today_prescriptions=len(today_rows),
            active_patients=active_patients,
            safety_warnings_today=today_warnings,
            daily_series=daily_series,
            top_diagnoses=top_diagnoses,
            recent_prescriptions=recent_prescriptions,
        )

    @staticmethod
    def _last_n_days(n: int) -> list[str]:
        today = datetime.now(timezone.utc).date()
        return [(today - timedelta(days=offset)).isoformat() for offset in range(n - 1, -1, -1)]

    @staticmethod
    def _fetch_patient_names(client, patient_ids: set[str]) -> dict[str, str]:
        if not patient_ids:
            return {}
        try:
            result = client.table("patients").select("id,full_name").in_("id", list(patient_ids)).execute()
            return {row["id"]: row["full_name"] for row in (result.data or [])}
        except Exception as exc:  # noqa: BLE001
            logger.error("fetch_patient_names_failed", extra={"extra_fields": {"error": str(exc)}})
            return {}
