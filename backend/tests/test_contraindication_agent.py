from app.agents.cdss_state import create_initial_cdss_state
from app.agents.contraindication_agent import contraindication_node
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction


class _FakePineconeService:
    def __init__(self, matches_by_namespace: dict[str, list[dict]]):
        self._matches_by_namespace = matches_by_namespace

    def query_namespace(self, query_text, namespace, top_k=5, filter=None):
        return self._matches_by_namespace.get(namespace, [])


def _extraction(current_medications=None) -> PrescriptionExtraction:
    return PrescriptionExtraction(
        patient=PatientInfo(),
        diagnosis="Back pain",
        medications=[Medication(name="Ibuprofen", dosage="400mg", frequency="twice a day")],
        current_medications=current_medications or [],
    )


def test_contraindication_node_flags_known_condition():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = _extraction(current_medications=["Warfarin"])

    pinecone_service = _FakePineconeService(
        {
            "contraindications": [
                {
                    "content": "Ibuprofen contraindicated with anticoagulant therapy.",
                    "metadata": {
                        "drug_name": "Ibuprofen",
                        "condition": "warfarin",
                        "severity": "high",
                        "explanation": "Increases bleeding risk.",
                    },
                    "score": 0.9,
                }
            ]
        }
    )

    result = contraindication_node(state, pinecone_service=pinecone_service)

    assert len(result["contraindication_warnings"]) == 1
    warning = result["contraindication_warnings"][0]
    assert warning.medication_name == "Ibuprofen"
    assert warning.severity == "high"
    assert warning.evidence is not None
    assert warning.evidence.source == "Pinecone: contraindications"


def test_contraindication_node_ignores_condition_patient_does_not_have():
    """The match exists in Pinecone, but the patient has no record of that
    condition -- must not be flagged (avoids false positives from generic
    semantic matches)."""
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = _extraction(current_medications=[])  # nothing on file

    pinecone_service = _FakePineconeService(
        {
            "contraindications": [
                {
                    "content": "Ibuprofen contraindicated with anticoagulant therapy.",
                    "metadata": {"drug_name": "Ibuprofen", "condition": "warfarin", "severity": "high"},
                    "score": 0.9,
                }
            ]
        }
    )

    result = contraindication_node(state, pinecone_service=pinecone_service)

    assert result["contraindication_warnings"] == []


def test_contraindication_node_ignores_cross_drug_semantic_false_match():
    """Mirrors the Safety Checker's guard: a Pinecone match for a
    DIFFERENT drug must never be attributed to the one being checked."""
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = _extraction(current_medications=["Warfarin"])

    pinecone_service = _FakePineconeService(
        {
            "contraindications": [
                {
                    "content": "Aspirin contraindicated with anticoagulant therapy.",
                    "metadata": {"drug_name": "Aspirin", "condition": "warfarin", "severity": "high"},
                    "score": 0.85,
                }
            ]
        }
    )

    result = contraindication_node(state, pinecone_service=pinecone_service)

    assert result["contraindication_warnings"] == []


def test_contraindication_node_no_extraction_returns_empty():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = None

    result = contraindication_node(state, pinecone_service=_FakePineconeService({}))

    assert result["contraindication_warnings"] == []
