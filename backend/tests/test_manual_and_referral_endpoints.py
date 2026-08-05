from fastapi.testclient import TestClient

from app.api.routes import patients as patients_routes
from app.api.routes import prescription as prescription_routes
from app.core.config import Settings
from app.main import app
from app.services.pinecone_service import DrugKnowledgeMatch
from app.services.supabase_service import SupabaseService

client = TestClient(app)


class _FakePineconeService:
    def __init__(self, matches_by_drug: dict[str, list[DrugKnowledgeMatch]]):
        self._matches_by_drug = matches_by_drug

    def find_interactions(self, medication_name: str, top_k: int = 5):
        return self._matches_by_drug.get(medication_name, [])


def _noop_supabase_service() -> SupabaseService:
    return SupabaseService(settings=Settings(supabase_url="", supabase_service_key=""))


def teardown_function(_):
    app.dependency_overrides.clear()


def test_manual_prescription_requires_at_least_one_medication():
    app.dependency_overrides[prescription_routes.get_pinecone_service] = lambda: _FakePineconeService({})
    app.dependency_overrides[prescription_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/prescriptions/manual",
        json={"patient": {}, "diagnosis": "Headache", "medications": []},
    )

    assert response.status_code == 422


def test_manual_prescription_safe_case():
    app.dependency_overrides[prescription_routes.get_pinecone_service] = lambda: _FakePineconeService({})
    app.dependency_overrides[prescription_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/prescriptions/manual",
        json={
            "patient": {"name": "Ahmad Karimi", "age": 45, "record_no": "REC-0001"},
            "diagnosis": "Essential hypertension",
            "medications": [
                {"name": "Amlodipine", "dosage": "5mg", "frequency": "once daily"},
                {"name": "Losartan", "dosage": "50mg", "frequency": "once daily"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_safe"] is True
    assert body["warnings"] == []
    assert body["extraction"]["diagnosis"] == "Essential hypertension"
    assert len(body["extraction"]["medications"]) == 2
    # No Extractor agent involved: no LLM call, so no extraction_error path.


def test_manual_prescription_flags_interaction():
    app.dependency_overrides[prescription_routes.get_pinecone_service] = lambda: _FakePineconeService(
        {
            "Ibuprofen": [
                DrugKnowledgeMatch(
                    drug_name="Ibuprofen",
                    interacts_with=["warfarin"],
                    severity="critical",
                    explanation="Increases bleeding risk.",
                    score=0.95,
                )
            ]
        }
    )
    app.dependency_overrides[prescription_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/prescriptions/manual",
        json={
            "patient": {},
            "diagnosis": "Back pain",
            "medications": [{"name": "Ibuprofen", "dosage": "400mg", "frequency": "twice a day"}],
            "current_medications": ["Warfarin"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_safe"] is False
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["severity"] == "critical"


def test_refer_patient_endpoint_not_found_patient():
    app.dependency_overrides[patients_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/patients/refer",
        json={"patient_record_no": "REC-9999", "to_doctor_email": "colleague@watanhospital.af"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "No patient found" in body["message"]
