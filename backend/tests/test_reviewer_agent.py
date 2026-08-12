from app.agents.cdss_state import create_initial_cdss_state
from app.agents.reviewer_agent import reviewer_node
from app.models.cdss_schemas import ReflectionVerdict
from app.models.schemas import InteractionWarning, PatientInfo, Severity


def test_reviewer_fast_mode_no_warnings():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=False)
    state["warnings"] = []

    result = reviewer_node(state)

    review = result["review"]
    assert review.is_safe is True
    assert review.overall_severity == Severity.NONE
    assert review.used_copilot_mode is False
    assert "Fast mode" in review.summary


def test_reviewer_fast_mode_with_warning_derives_severity_directly():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=False)
    state["warnings"] = [
        InteractionWarning(medications=["Ibuprofen", "warfarin"], severity="critical", explanation="bleeding risk")
    ]

    result = reviewer_node(state)

    review = result["review"]
    assert review.is_safe is False
    assert review.overall_severity == Severity.CRITICAL
    # No Reflection ran in fast mode, so this must NOT be present.
    assert state.get("reflection") is None


def test_reviewer_copilot_mode_trusts_reflection_verdict():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["warnings"] = []
    state["reflection"] = ReflectionVerdict(
        is_safe=False, overall_severity=Severity.HIGH, summary="Contradiction resolved conservatively."
    )

    result = reviewer_node(state)

    review = result["review"]
    assert review.is_safe is False
    assert review.overall_severity == Severity.HIGH
    assert review.summary == "Contradiction resolved conservatively."
    assert review.used_copilot_mode is True


def test_reviewer_includes_all_specialist_outputs():
    from app.models.cdss_schemas import ContraindicationWarning, DoseCheckResult, GuidelineRecommendation, LabContext

    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["reflection"] = ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="ok")
    state["dose_results"] = [
        DoseCheckResult(medication_name="Amlodipine", is_within_range=True, explanation="fine")
    ]
    state["contraindication_warnings"] = [
        ContraindicationWarning(medication_name="Ibuprofen", condition="warfarin", severity=Severity.HIGH, explanation="x")
    ]
    state["guideline_recommendations"] = [
        GuidelineRecommendation(
            diagnosis="Hypertension",
            recommendation="Use ARBs",
            evidence={"source": "test", "confidence": 0.9},
        )
    ]
    state["lab_context"] = LabContext(weight_kg=70)

    result = reviewer_node(state)
    review = result["review"]

    assert len(review.dose_results) == 1
    assert len(review.contraindications) == 1
    assert len(review.guideline_recommendations) == 1
    assert review.lab_context is not None
    assert review.lab_context.weight_kg == 70
