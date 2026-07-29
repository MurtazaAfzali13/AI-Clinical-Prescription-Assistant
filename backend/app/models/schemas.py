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
    advice: str | None = None


class PrescriptionRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Free-text doctor note in English")
    patient: PatientInfo = Field(default_factory=PatientInfo)


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
