"""Pydantic models shared across the API and the LangGraph agents."""
from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Medication(BaseModel):
    name: str = Field(..., description="Generic or brand drug name")
    dosage: str = Field(..., description="e.g. '500mg'")
    frequency: str = Field(..., description="e.g. 'twice a day'")
    duration: str | None = Field(default=None, description="e.g. '5 days'")


class InteractionWarning(BaseModel):
    medications: list[str]
    severity: Severity
    explanation: str


class PatientInfo(BaseModel):
    name: str | None = None
    age: int | None = None
    record_no: str | None = None


class PrescriptionExtraction(BaseModel):
    """Structured output produced by the Extractor agent from raw
    free-text doctor notes."""

    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnosis: str
    medications: list[Medication] = Field(default_factory=list)
    current_medications: list[str] = Field(
        default_factory=list,
        description="Medications the patient is already taking (not newly prescribed here), "
        "e.g. mentioned as 'currently on X' or 'already takes X'. Used for interaction "
        "checking against the newly prescribed medications.",
    )
    advice: str | None = None


class PrescriptionRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Free-text doctor note in English")
    patient: PatientInfo = Field(default_factory=PatientInfo)


class ManualPrescriptionRequest(BaseModel):
    """Direct, doctor-authored prescription that skips the Extractor agent
    entirely -- the doctor types the diagnosis and medications themselves.
    Still passes through the Safety Checker agent before printing."""

    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnosis: str = Field(..., min_length=1)
    medications: list[Medication] = Field(..., min_length=1, description="At least one medication is required")
    current_medications: list[str] = Field(default_factory=list)
    advice: str | None = None


class PrescriptionResponse(BaseModel):
    extraction: PrescriptionExtraction
    warnings: list[InteractionWarning] = Field(default_factory=list)
    is_safe: bool
    trace_id: str


class OverrideRequest(BaseModel):
    trace_id: str
    reason: str = Field(..., min_length=5, description="Clinical justification for overriding the safety warning")


class OverrideResponse(BaseModel):
    trace_id: str
    status: str = "overridden"


class PrintablePrescription(BaseModel):
    """Final, doctor-approved payload sent to the frontend print engine."""

    patient_name: str
    age: int | None = None
    date: date
    record_no: str
    diagnosis: str
    advice: str
    medications: list[Medication]
    doctor_signature_name: str


class ChatTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


class TranscriptionResponse(BaseModel):
    text: str


class DailyCount(BaseModel):
    date: str  # ISO date, "YYYY-MM-DD"
    count: int


class DiagnosisBreakdown(BaseModel):
    label: str
    count: int


class RecentPrescriptionSummary(BaseModel):
    patient_name: str
    diagnosis: str
    created_at: str
    status: str
    is_safe: bool


class DashboardStats(BaseModel):
    """Aggregated stats for the doctor's analytics dashboard."""

    today_patients: int = 0
    today_prescriptions: int = 0
    active_patients: int = 0
    safety_warnings_today: int = 0
    daily_series: list[DailyCount] = Field(default_factory=list)
    top_diagnoses: list[DiagnosisBreakdown] = Field(default_factory=list)
    recent_prescriptions: list[RecentPrescriptionSummary] = Field(default_factory=list)


class ReferPatientRequest(BaseModel):
    patient_record_no: str = Field(..., min_length=1)
    to_doctor_email: str = Field(..., min_length=3)
    reason: str | None = None


class ReferPatientResponse(BaseModel):
    success: bool
    message: str
