from app.agents.safety_checker import safety_node
from app.agents.state import create_initial_state
from app.models.schemas import PatientInfo
from app.services.pinecone_service import DrugKnowledgeMatch


class _FakePineconeService:
    def __init__(self, matches_by_drug: dict[str, list[DrugKnowledgeMatch]]):
        self._matches_by_drug = matches_by_drug

    def find_interactions(self, medication_name: str, top_k: int = 5):
        return self._matches_by_drug.get(medication_name, [])


def test_safety_node_flags_high_severity_interaction(sample_extraction):
    state = create_initial_state("raw", PatientInfo(), "trace-1")
    state["extraction"] = sample_extraction

    pinecone_service = _FakePineconeService(
        {
            "Acetaminophen": [
                DrugKnowledgeMatch(
                    drug_name="Acetaminophen",
                    interacts_with=["warfarin"],
                    severity="high",
                    explanation="Increases bleeding risk.",
                    score=0.92,
                )
            ]
        }
    )

    result = safety_node(state, pinecone_service=pinecone_service)

    assert result["is_safe"] is False
    assert len(result["warnings"]) == 1
    assert result["warnings"][0].severity == "high"
    assert "warfarin" in result["warnings"][0].medications


def test_safety_node_flags_interaction_with_current_medication():
    """Reproduces the reported gap: a drug the patient is 'currently on'
    (not newly prescribed) must still be checked against what's prescribed now."""
    from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction

    extraction = PrescriptionExtraction(
        patient=PatientInfo(name="Ahmad Karimi", age=45, record_no="REC-0001"),
        diagnosis="Headache",
        medications=[Medication(name="Ibuprofen", dosage="400mg", frequency="twice a day")],
        current_medications=["Warfarin"],
        advice="Rest and monitor.",
    )

    state = create_initial_state("raw", PatientInfo(), "trace-1")
    state["extraction"] = extraction

    pinecone_service = _FakePineconeService(
        {
            "Ibuprofen": [
                DrugKnowledgeMatch(
                    drug_name="Ibuprofen",
                    interacts_with=["warfarin"],
                    severity="critical",
                    explanation="NSAIDs combined with warfarin significantly increase bleeding risk.",
                    score=0.95,
                )
            ]
        }
    )

    result = safety_node(state, pinecone_service=pinecone_service)

    assert result["is_safe"] is False
    assert len(result["warnings"]) == 1
    assert result["warnings"][0].severity == "critical"
    assert "warfarin" in result["warnings"][0].medications


def test_safety_node_ignores_cross_drug_semantic_false_matches():
    """Reproduces the exact reported bug: querying 'Ibuprofen' returns
    near-duplicate records for Acetaminophen and Amoxicillin too (because
    the seed sentences are worded almost identically), which must NOT be
    attached to Ibuprofen's warning."""
    from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction

    extraction = PrescriptionExtraction(
        patient=PatientInfo(name="Ahmad Karimi", age=45, record_no="REC-0001"),
        diagnosis="Headache",
        medications=[Medication(name="Ibuprofen", dosage="400mg", frequency="twice a day")],
        current_medications=["Warfarin"],
        advice="Rest and monitor.",
    )

    state = create_initial_state("raw", PatientInfo(), "trace-1")
    state["extraction"] = extraction

    pinecone_service = _FakePineconeService(
        {
            "Ibuprofen": [
                DrugKnowledgeMatch(
                    drug_name="Ibuprofen",
                    interacts_with=["warfarin"],
                    severity="critical",
                    explanation="NSAIDs combined with warfarin significantly increase bleeding risk.",
                    score=0.95,
                ),
                # These two should NOT produce warnings: they're a different
                # drug's record that Pinecone returned due to semantic
                # similarity, not an actual match for Ibuprofen.
                DrugKnowledgeMatch(
                    drug_name="Acetaminophen",
                    interacts_with=["warfarin"],
                    severity="high",
                    explanation="Regular acetaminophen use can potentiate warfarin's anticoagulant effect.",
                    score=0.80,
                ),
                DrugKnowledgeMatch(
                    drug_name="Amoxicillin",
                    interacts_with=["warfarin"],
                    severity="moderate",
                    explanation="Amoxicillin may enhance the anticoagulant effect of warfarin.",
                    score=0.75,
                ),
            ]
        }
    )

    result = safety_node(state, pinecone_service=pinecone_service)

    assert len(result["warnings"]) == 1, "Only the true Ibuprofen match should produce a warning"
    assert result["warnings"][0].severity == "critical"
    assert "bleeding risk" in result["warnings"][0].explanation


def test_safety_node_no_interactions_is_safe(sample_extraction):
    state = create_initial_state("raw", PatientInfo(), "trace-1")
    state["extraction"] = sample_extraction

    pinecone_service = _FakePineconeService({})
    result = safety_node(state, pinecone_service=pinecone_service)

    assert result["is_safe"] is True
    assert result["warnings"] == []


def test_safety_node_no_extraction_is_unsafe():
    state = create_initial_state("raw", PatientInfo(), "trace-1")
    state["extraction"] = None

    result = safety_node(state, pinecone_service=_FakePineconeService({}))

    assert result["is_safe"] is False
    assert result["warnings"] == []
