"""Pydantic models for the Clinical Decision Support System (CDSS) layer.

These are additive to app/models/schemas.py -- the original Extractor ->
Safety -> print pipeline (and its API contracts) are untouched. Everything
here backs the opt-in "Copilot Mode" pipeline (Supervisor + specialist
agents + Reflection + Reviewer).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction, Severity


class EvidenceObject(BaseModel):
    """Every clinically-significant claim from a specialist agent must be
    traceable to a source -- this is the anti-hallucination backbone of
    the CDSS. An agent that can't populate this for a claim shouldn't make
    the claim."""

    source: str = Field(..., description="Where this evidence came from, e.g. 'Pinecone: clinical-guidelines'")
    url: str | None = Field(default=None, description="Link to the source document, if available")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Retrieval/model confidence, 0-1")
    guideline_section: str | None = Field(default=None, description="e.g. 'JNC-8 Section 4.2'")


class RoutingDecision(BaseModel):
    """The Supervisor's output: which specialist agents are actually
    worth running for this specific prescription. Safety (DDI) is not a
    field here because it always runs regardless of routing -- it's the
    non-negotiable baseline check, not an optional specialist."""

    run_dose_agent: bool = False
    run_lab_agent: bool = False
    run_contraindication_agent: bool = False
    run_guideline_agent: bool = False
    reasoning: str = Field(..., description="Brief explanation of why these flags were chosen")


class LabContext(BaseModel):
    """Patient clinical context pulled from Supabase (not computed by an
    LLM) -- weight, renal/hepatic function, etc., used by the Dose and
    Contraindication agents."""

    weight_kg: float | None = None
    age: int | None = None
    egfr: float | None = Field(default=None, description="Estimated glomerular filtration rate (renal function)")
    liver_panel_normal: bool | None = Field(
        default=None, description="None = unknown/not on file, NOT assumed normal"
    )
    labs_recorded_at: str | None = None
    chronic_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class DoseCheckResult(BaseModel):
    """Output of the deterministic dose calculator -- never LLM math."""

    medication_name: str
    prescribed_dose_mg: float | None = None
    recommended_min_mg: float | None = None
    recommended_max_mg: float | None = None
    is_within_range: bool | None = Field(default=None, description="None if we had insufficient data to check")
    renal_adjustment_applied: bool = False
    explanation: str


class ContraindicationWarning(BaseModel):
    medication_name: str
    condition: str
    severity: Severity
    explanation: str
    evidence: EvidenceObject | None = None


class GuidelineRecommendation(BaseModel):
    diagnosis: str
    recommendation: str
    evidence: EvidenceObject


class AlternativeTherapy(BaseModel):
    original_medication: str
    suggested_alternative: str
    rationale: str
    evidence: EvidenceObject | None = None


class ReflectionVerdict(BaseModel):
    """The Reflection agent's unified verdict after resolving any
    contradictions between specialist agents (e.g. Dose says the amount is
    fine, but Lab/eGFR says renal function is impaired)."""

    is_safe: bool
    overall_severity: Severity
    summary: str = Field(..., description="Plain-language synthesis for the reviewing physician")
    contradictions_resolved: list[str] = Field(
        default_factory=list, description="Any conflicts between agents and how they were resolved"
    )


class CDSSReview(BaseModel):
    """Final payload the Reviewer agent assembles for the frontend."""

    is_safe: bool
    overall_severity: Severity
    summary: str
    safety_warnings: list["EvidenceBackedWarning"] = Field(default_factory=list)
    dose_results: list[DoseCheckResult] = Field(default_factory=list)
    contraindications: list[ContraindicationWarning] = Field(default_factory=list)
    guideline_recommendations: list[GuidelineRecommendation] = Field(default_factory=list)
    alternative_therapies: list[AlternativeTherapy] = Field(default_factory=list)
    lab_context: LabContext | None = None
    used_copilot_mode: bool = False


class EvidenceBackedWarning(BaseModel):
    """A drug-drug interaction warning, upgraded with an EvidenceObject
    when running in Copilot Mode (Fast Mode's plain InteractionWarning has
    no evidence field, by design, to keep it cheap)."""

    medications: list[str]
    severity: Severity
    explanation: str
    evidence: EvidenceObject | None = None


CDSSReview.model_rebuild()


class CDSSManualPrescriptionRequest(BaseModel):
    """Manual entry variant of CDSSPrescriptionRequest -- the doctor
    already typed structured diagnosis + medications (no raw text), so
    this skips the Extractor agent entirely but still applies the exact
    same Supervisor routing as AI dictation when `use_copilot_mode=True`."""

    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnosis: str = Field(..., min_length=1)
    medications: list[Medication] = Field(..., min_length=1)
    current_medications: list[str] = Field(default_factory=list)
    advice: str | None = None
    use_copilot_mode: bool = False


class CDSSPrescriptionRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    patient: PatientInfo = Field(default_factory=PatientInfo)
    use_copilot_mode: bool = False


class CDSSPrescriptionResponse(BaseModel):
    review: CDSSReview
    extraction: PrescriptionExtraction | None = None
    trace_id: str
