from fastapi.testclient import TestClient

from app.agents.alternative_therapy_agent import _AlternativeSuggestion
from app.api.routes import cdss as cdss_routes
from app.core.config import Settings
from app.main import app
from app.models.cdss_schemas import ReflectionVerdict
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction, Severity
from app.services.supabase_service import SupabaseService

client = TestClient(app)

SAMPLE_EXTRACTION = PrescriptionExtraction(
    patient=PatientInfo(name="Ahmad Karimi", age=45, record_no="REC-0001"),
    diagnosis="Essential hypertension",
    medications=[Medication(name="Amlodipine", dosage="5mg", frequency="once daily")],
    current_medications=[],
    advice="Reduce salt intake.",
)


class _FakeStructuredRunnable:
    def __init__(self, response):
        self._response = response

    def invoke(self, _inputs):
        return self._response

    def __call__(self, inputs):
        return self.invoke(inputs)

    def __ror__(self, other):
        from langchain_core.runnables import RunnableLambda

        return other | RunnableLambda(self.invoke)


class _FakeLLM:
    def __init__(self, responses_by_schema):
        self._responses_by_schema = responses_by_schema

    def with_structured_output(self, schema):
        return _FakeStructuredRunnable(self._responses_by_schema[schema])


class _FakePineconeService:
    def find_interactions(self, medication_name, top_k=5):
        return []

    def query_namespace(self, query_text, namespace, top_k=5, filter=None):
        return []


def _noop_supabase_service() -> SupabaseService:
    return SupabaseService(settings=Settings(supabase_url="", supabase_service_key=""))


def teardown_function(_):
    app.dependency_overrides.clear()


def _fake_llm():
    from app.models.cdss_schemas import RoutingDecision

    return _FakeLLM(
        {
            PrescriptionExtraction: SAMPLE_EXTRACTION,
            RoutingDecision: RoutingDecision(reasoning="minimal"),
            ReflectionVerdict: ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="ok"),
            _AlternativeSuggestion: _AlternativeSuggestion(has_alternative=False),
        }
    )


def test_cdss_prescription_fast_mode():
    app.dependency_overrides[cdss_routes.get_llm] = _fake_llm
    app.dependency_overrides[cdss_routes.get_pinecone_service] = lambda: _FakePineconeService()
    app.dependency_overrides[cdss_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/cdss/prescriptions",
        json={"raw_text": "Patient has hypertension, prescribe Amlodipine 5mg daily.", "use_copilot_mode": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["used_copilot_mode"] is False
    assert body["review"]["is_safe"] is True
    assert "trace_id" in body


def test_cdss_prescription_copilot_mode():
    app.dependency_overrides[cdss_routes.get_llm] = _fake_llm
    app.dependency_overrides[cdss_routes.get_pinecone_service] = lambda: _FakePineconeService()
    app.dependency_overrides[cdss_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/cdss/prescriptions",
        json={"raw_text": "Patient has hypertension, prescribe Amlodipine 5mg daily.", "use_copilot_mode": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["used_copilot_mode"] is True
    assert body["review"]["summary"] == "ok"


def test_cdss_manual_prescription_fast_mode_never_calls_extractor():
    """The original bug this whole endpoint fixes: manual entry must
    never invoke the Extractor LLM at all -- confirmed here by using an
    LLM fake that would raise if PrescriptionExtraction is ever requested."""
    from app.models.cdss_schemas import RoutingDecision

    class _ExplodingIfExtractorCalled(_FakeLLM):
        def with_structured_output(self, schema):
            if schema is PrescriptionExtraction:
                raise AssertionError("Extractor must never run for manual entry")
            return super().with_structured_output(schema)

    fake_llm = _ExplodingIfExtractorCalled(
        {
            RoutingDecision: RoutingDecision(reasoning="unused"),
            ReflectionVerdict: ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="unused"),
            _AlternativeSuggestion: _AlternativeSuggestion(has_alternative=False),
        }
    )
    app.dependency_overrides[cdss_routes.get_llm] = lambda: fake_llm
    app.dependency_overrides[cdss_routes.get_pinecone_service] = lambda: _FakePineconeService()
    app.dependency_overrides[cdss_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/cdss/prescriptions/manual",
        json={
            "diagnosis": "Essential hypertension",
            "medications": [{"name": "Amlodipine", "dosage": "5mg", "frequency": "once daily"}],
            "use_copilot_mode": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["used_copilot_mode"] is False
    assert body["extraction"]["diagnosis"] == "Essential hypertension"


def test_cdss_manual_prescription_copilot_mode_reaches_supervisor():
    """Manual entry + Copilot Mode must actually reach the Supervisor and
    apply its routing -- this is the fix the user's question surfaced."""
    app.dependency_overrides[cdss_routes.get_llm] = _fake_llm
    app.dependency_overrides[cdss_routes.get_pinecone_service] = lambda: _FakePineconeService()
    app.dependency_overrides[cdss_routes.get_supabase_service] = _noop_supabase_service

    response = client.post(
        "/api/v1/cdss/prescriptions/manual",
        json={
            "diagnosis": "Essential hypertension",
            "medications": [{"name": "Amlodipine", "dosage": "5mg", "frequency": "once daily"}],
            "use_copilot_mode": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["used_copilot_mode"] is True
    assert body["review"]["summary"] == "ok"  # came from Reflection, proving Supervisor->fan-out->Reflection ran
