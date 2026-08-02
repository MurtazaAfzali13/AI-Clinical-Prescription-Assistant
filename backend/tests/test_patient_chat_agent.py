from langchain_core.messages import AIMessage, HumanMessage

from app.agents.patient_chat_agent import build_patient_chat_graph
from app.core.config import Settings
from app.services.supabase_service import SupabaseService


class _FakeToolCallingLLM:
    """Simulates a chat model that first decides to call a tool, then
    produces a final answer once it sees the tool's result."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.call_count = 0

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def or_(self, *_a, **_k):
        return self

    def ilike(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, *_a, **_k):
        return self

    def execute(self):
        class _Result:
            def __init__(self, data):
                self.data = data

        return _Result(self._rows)


class _FakeSupabaseClient:
    def __init__(self, patients, prescriptions, treatment_relationships=None):
        self._patients = patients
        self._prescriptions = prescriptions
        self._treatment_relationships = treatment_relationships or []

    def table(self, name):
        if name == "patients":
            return _FakeQuery(self._patients)
        if name == "prescriptions":
            return _FakeQuery(self._prescriptions)
        if name == "treatment_relationships":
            return _FakeQuery(self._treatment_relationships)
        if name == "patient_lookup_audit_log":
            return _FakeQuery([])
        raise AssertionError(f"Unexpected table: {name}")


def test_patient_chat_graph_calls_tool_then_answers():
    tool_call_message = AIMessage(
        content="",
        tool_calls=[
            {"name": "lookup_patient_by_id", "args": {"record_no": "REC-0001"}, "id": "call_1"}
        ],
    )
    final_message = AIMessage(content="Ahmad Karimi is on Ibuprofen; the prior interaction was overridden.")

    fake_llm = _FakeToolCallingLLM([tool_call_message, final_message])

    settings = Settings(supabase_url="https://x.supabase.co", supabase_service_key="key")
    fake_client = _FakeSupabaseClient(
        patients=[
            {
                "id": "patient-1",
                "record_no": "REC-0001",
                "full_name": "Ahmad Karimi",
                "father_name": "Mohammad",
                "age": 45,
            }
        ],
        prescriptions=[
            {"created_at": "2026-07-29T10:00:00+00:00", "diagnosis": "Headache", "medications": [{"name": "Ibuprofen"}], "status": "overridden"}
        ],
        treatment_relationships=[{"id": "tr-1", "doctor_id": "doctor-1", "patient_id": "patient-1", "status": "active"}],
    )
    supabase_service = SupabaseService(settings=settings, client=fake_client)

    graph = build_patient_chat_graph(llm=fake_llm, supabase_service=supabase_service, doctor_id="doctor-1")
    final_state = graph.invoke({"messages": [HumanMessage(content="Show me patient REC-0001")]})

    last_message = final_state["messages"][-1]
    assert last_message.content == "Ahmad Karimi is on Ibuprofen; the prior interaction was overridden."
    assert fake_llm.call_count == 2  # one tool-call turn, one final-answer turn

    # Confirm the tool actually ran and produced a real ToolMessage grounded
    # in the fake database, not just an echo.
    tool_messages = [m for m in final_state["messages"] if type(m).__name__ == "ToolMessage"]
    assert len(tool_messages) == 1
    assert "Ahmad Karimi" in tool_messages[0].content
    assert "Ibuprofen" in tool_messages[0].content


def test_patient_chat_graph_answers_directly_without_tool_call():
    """If the LLM decides no lookup is needed (e.g. a greeting), the graph
    should end after a single turn with no tool call."""
    final_message = AIMessage(content="Hi! Ask me about any patient by name or record number.")
    fake_llm = _FakeToolCallingLLM([final_message])

    settings = Settings(supabase_url="", supabase_service_key="")
    supabase_service = SupabaseService(settings=settings)

    graph = build_patient_chat_graph(llm=fake_llm, supabase_service=supabase_service, doctor_id="doctor-1")
    final_state = graph.invoke({"messages": [HumanMessage(content="hello")]})

    assert final_state["messages"][-1].content == "Hi! Ask me about any patient by name or record number."
    assert fake_llm.call_count == 1
