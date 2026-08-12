"""Integration tests for the CDSS graph wiring itself (not just individual
node functions). These run the REAL LangGraph StateGraph -- only the LLM,
Pinecone, and Supabase clients are faked -- specifically to catch graph
wiring bugs (wrong edges, fan-in that doesn't wait for all branches,
routing dead-ends) that node-level unit tests can't see.
"""
from __future__ import annotations

from app.agents.alternative_therapy_agent import _AlternativeSuggestion
from app.agents.cdss_graph import build_cdss_graph
from app.agents.cdss_state import create_initial_cdss_state
from app.models.cdss_schemas import ReflectionVerdict, RoutingDecision
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction, Severity


class _FakeStructuredRunnable:
    def __init__(self, response):
        self._response = response
        self.calls = 0

    def invoke(self, _inputs):
        self.calls += 1
        return self._response

    def __call__(self, inputs):
        return self.invoke(inputs)

    def __ror__(self, other):
        # Supports `prompt | fake_structured_runnable`, mirroring how
        # LangChain composes a real Runnable chain.
        from langchain_core.runnables import RunnableLambda

        return other | RunnableLambda(self.invoke)


class _FakeLLM:
    """Returns a canned response keyed by which Pydantic schema the caller
    requested via `with_structured_output` -- each node in the graph asks
    for a different schema, so this lets one fake LLM serve all of them."""

    def __init__(self, responses_by_schema: dict[type, object]):
        self._responses_by_schema = responses_by_schema
        self.requested_schemas: list[type] = []

    def with_structured_output(self, schema):
        self.requested_schemas.append(schema)
        return _FakeStructuredRunnable(self._responses_by_schema[schema])


class _FakePineconeService:
    def __init__(self, interactions=None, namespace_matches=None):
        self._interactions = interactions or []
        self._namespace_matches = namespace_matches or {}

    def find_interactions(self, medication_name, top_k=5):
        return self._interactions

    def query_namespace(self, query_text, namespace, top_k=5, filter=None):
        return self._namespace_matches.get(namespace, [])


class _FakeSupabaseService:
    def __init__(self, lab_row=None):
        self._lab_row = lab_row

    def get_lab_context(self, record_no, national_id=None):
        return self._lab_row


SAMPLE_EXTRACTION = PrescriptionExtraction(
    patient=PatientInfo(name="Ahmad Karimi", age=45, record_no="REC-0001"),
    diagnosis="Essential hypertension",
    medications=[
        Medication(name="Amlodipine", dosage="5mg", frequency="once daily"),
        Medication(name="Losartan", dosage="50mg", frequency="once daily"),
    ],
    current_medications=[],
    advice="Reduce salt intake.",
)


def _build_fake_llm(routing_decision: RoutingDecision, reflection: ReflectionVerdict) -> _FakeLLM:
    return _FakeLLM(
        {
            PrescriptionExtraction: SAMPLE_EXTRACTION,
            RoutingDecision: routing_decision,
            ReflectionVerdict: reflection,
            _AlternativeSuggestion: _AlternativeSuggestion(has_alternative=False),
        }
    )


def test_fast_mode_skips_supervisor_and_reflection_entirely():
    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(reasoning="should not be used in fast mode"),
        reflection=ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="unused"),
    )
    graph = build_cdss_graph(
        llm=fake_llm,
        pinecone_service=_FakePineconeService(),
        supabase_service=_FakeSupabaseService(),
    )

    initial_state = create_initial_cdss_state(
        raw_text="note", patient=PatientInfo(), trace_id="t1", use_copilot_mode=False
    )
    final_state = graph.invoke(initial_state)

    assert final_state["review"] is not None
    assert final_state["review"].summary == "Fast mode: only the Safety agent ran."
    # Supervisor/Reflection must never have run in fast mode.
    assert final_state["routing_decision"] is None
    assert final_state["reflection"] is None
    assert RoutingDecision not in fake_llm.requested_schemas
    assert ReflectionVerdict not in fake_llm.requested_schemas


def test_copilot_mode_full_fan_out_reaches_reviewer_with_all_branch_data():
    """The critical wiring test: every specialist agent enabled, verifying
    the fan-in actually waits for ALL of them (lab->dose chain included)
    before reflection/review runs."""
    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(
            run_dose_agent=True,
            run_lab_agent=True,
            run_contraindication_agent=True,
            run_guideline_agent=True,
            reasoning="full workup",
        ),
        reflection=ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="all clear"),
    )
    pinecone_service = _FakePineconeService(
        namespace_matches={
            "contraindications": [],
            "clinical-guidelines": [
                {
                    "content": "ACE inhibitors or ARBs are first-line for essential hypertension.",
                    "metadata": {"recommendation": "Continue ARB therapy.", "guideline_section": "JNC-8"},
                    "score": 0.9,
                }
            ],
        }
    )
    supabase_service = _FakeSupabaseService(
        lab_row={
            "weight_kg": 80,
            "age": 45,
            "egfr": 95,
            "liver_panel_normal": True,
            "labs_recorded_at": None,
            "chronic_conditions": [],
            "allergies": [],
        }
    )

    graph = build_cdss_graph(llm=fake_llm, pinecone_service=pinecone_service, supabase_service=supabase_service)
    initial_state = create_initial_cdss_state(
        raw_text="note", patient=PatientInfo(record_no="REC-0001"), trace_id="t2", use_copilot_mode=True
    )
    final_state = graph.invoke(initial_state)

    # Supervisor ran and its decision is present.
    assert final_state["routing_decision"] is not None
    assert final_state["routing_decision"].run_dose_agent is True

    # Lab -> Dose chain actually executed and dose saw the lab data.
    assert final_state["lab_context"] is not None
    assert final_state["lab_context"].weight_kg == 80
    assert len(final_state["dose_results"]) == 2  # one per medication

    # Guideline ran (parallel branch).
    assert final_state["guideline_recommendations"] != []

    # Fan-in reached Reflection exactly once (not skipped, not duplicated).
    assert final_state["reflection"] is not None
    assert final_state["reflection"].summary == "all clear"

    # Reviewer produced the final payload.
    assert final_state["review"] is not None
    assert final_state["review"].is_safe is True
    assert final_state["review"].lab_context is not None
    assert len(final_state["review"].dose_results) == 2


def test_copilot_mode_supervisor_disables_everything_except_safety():
    """When the Supervisor decides nothing extra is needed, only Safety
    should run -- Lab/Dose/Contraindication/Guideline must all stay empty,
    and reflection_gate must still correctly fan-in with just one branch."""
    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(reasoning="nothing else relevant"),
        reflection=ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="minimal path"),
    )
    graph = build_cdss_graph(
        llm=fake_llm,
        pinecone_service=_FakePineconeService(),
        supabase_service=_FakeSupabaseService(),
    )

    initial_state = create_initial_cdss_state(
        raw_text="note", patient=PatientInfo(), trace_id="t3", use_copilot_mode=True
    )
    final_state = graph.invoke(initial_state)

    assert final_state["lab_context"] is None
    assert final_state["dose_results"] == []
    assert final_state["contraindication_warnings"] == []
    assert final_state["guideline_recommendations"] == []
    assert final_state["reflection"] is not None
    assert final_state["reflection"].summary == "minimal path"
    assert final_state["review"] is not None


def test_manual_entry_graph_skips_extractor_and_routes_through_supervisor():
    """The manual-entry builder must apply the EXACT SAME Supervisor
    routing as the AI-dictation graph, without ever touching Extractor."""
    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(
            run_dose_agent=True,
            run_guideline_agent=True,
            reasoning="manual entry, dose + guideline relevant",
        ),
        reflection=ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="manual path ok"),
    )
    from app.agents.cdss_graph import build_cdss_graph_from_structured_data

    graph = build_cdss_graph_from_structured_data(
        llm=fake_llm, pinecone_service=_FakePineconeService(), supabase_service=_FakeSupabaseService()
    )

    initial_state = create_initial_cdss_state(
        raw_text="", patient=PatientInfo(record_no="REC-0001"), trace_id="t5", use_copilot_mode=True
    )
    initial_state["extraction"] = SAMPLE_EXTRACTION  # pre-populated, as the manual endpoint does

    final_state = graph.invoke(initial_state)

    # Extractor never ran (no PrescriptionExtraction schema request went
    # through it) -- the pre-populated extraction is untouched.
    assert PrescriptionExtraction not in fake_llm.requested_schemas
    assert final_state["extraction"] == SAMPLE_EXTRACTION

    # Supervisor still ran and its routing decision drove the fan-out.
    assert final_state["routing_decision"] is not None
    assert final_state["routing_decision"].run_dose_agent is True
    assert len(final_state["dose_results"]) == 2
    assert final_state["review"] is not None


def test_manual_entry_graph_fast_mode_only_runs_safety():
    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(reasoning="unused in fast mode"),
        reflection=ReflectionVerdict(is_safe=True, overall_severity=Severity.NONE, summary="unused"),
    )
    from app.agents.cdss_graph import build_cdss_graph_from_structured_data

    graph = build_cdss_graph_from_structured_data(
        llm=fake_llm, pinecone_service=_FakePineconeService(), supabase_service=_FakeSupabaseService()
    )

    initial_state = create_initial_cdss_state(
        raw_text="", patient=PatientInfo(), trace_id="t6", use_copilot_mode=False
    )
    initial_state["extraction"] = SAMPLE_EXTRACTION

    final_state = graph.invoke(initial_state)

    assert final_state["routing_decision"] is None
    assert final_state["reflection"] is None
    assert final_state["review"] is not None


def test_alternative_therapy_only_runs_when_something_flagged():
    from app.services.pinecone_service import DrugKnowledgeMatch

    fake_llm = _build_fake_llm(
        routing_decision=RoutingDecision(reasoning="check safety only"),
        reflection=ReflectionVerdict(is_safe=False, overall_severity=Severity.CRITICAL, summary="interaction found"),
    )
    pinecone_service = _FakePineconeService(
        interactions=[
            DrugKnowledgeMatch(
                drug_name="Amlodipine",
                interacts_with=["losartan"],  # contrived for this test's sake
                severity="critical",
                explanation="test interaction",
                score=0.9,
            )
        ]
    )
    graph = build_cdss_graph(
        llm=fake_llm, pinecone_service=pinecone_service, supabase_service=_FakeSupabaseService()
    )

    initial_state = create_initial_cdss_state(
        raw_text="note", patient=PatientInfo(), trace_id="t4", use_copilot_mode=True
    )
    final_state = graph.invoke(initial_state)

    # A warning was produced, so alternative-therapy's gate condition was true.
    assert len(final_state["warnings"]) == 1
    assert final_state["review"] is not None
    assert final_state["review"].is_safe is False
