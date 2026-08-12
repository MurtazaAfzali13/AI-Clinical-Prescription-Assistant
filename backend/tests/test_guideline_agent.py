from app.agents.cdss_state import create_initial_cdss_state
from app.agents.guideline_agent import guideline_node
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction


class _FakePineconeService:
    def __init__(self, matches_by_namespace: dict[str, list[dict]]):
        self._matches_by_namespace = matches_by_namespace

    def query_namespace(self, query_text, namespace, top_k=5, filter=None):
        return self._matches_by_namespace.get(namespace, [])


def test_guideline_node_returns_recommendations():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = PrescriptionExtraction(
        patient=PatientInfo(),
        diagnosis="Essential hypertension",
        medications=[Medication(name="Amlodipine", dosage="5mg", frequency="once daily")],
    )

    pinecone_service = _FakePineconeService(
        {
            "clinical-guidelines": [
                {
                    "content": "ACE inhibitors or ARBs are first-line for essential hypertension.",
                    "metadata": {"recommendation": "Continue ARB therapy.", "guideline_section": "JNC-8"},
                    "score": 0.91,
                }
            ]
        }
    )

    result = guideline_node(state, pinecone_service=pinecone_service)

    assert len(result["guideline_recommendations"]) == 1
    rec = result["guideline_recommendations"][0]
    assert rec.diagnosis == "Essential hypertension"
    assert rec.evidence.guideline_section == "JNC-8"


def test_guideline_node_no_extraction_returns_empty():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = None

    result = guideline_node(state, pinecone_service=_FakePineconeService({}))

    assert result["guideline_recommendations"] == []


def test_guideline_node_no_matches_returns_empty():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = PrescriptionExtraction(
        patient=PatientInfo(), diagnosis="Rare condition", medications=[]
    )

    result = guideline_node(state, pinecone_service=_FakePineconeService({}))

    assert result["guideline_recommendations"] == []
