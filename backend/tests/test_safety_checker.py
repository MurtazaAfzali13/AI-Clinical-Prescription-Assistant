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
