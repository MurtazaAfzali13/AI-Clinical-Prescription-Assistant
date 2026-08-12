"""Builds the full CDSS StateGraph.

Two modes share the same graph, selected per-request via
`state["use_copilot_mode"]`:

  Fast Mode (False):
    Extractor -> Safety Checker -> Reviewer -> END
    (identical cost/latency profile to the original pipeline)

  Copilot Mode (True):
    Extractor -> Supervisor -> fan-out(Safety, Lab[->Dose], Contraindication,
    Guideline) -> reflection_gate (fan-in) -> Alternative Therapy
    (conditional, only if something was flagged) -> Reflection -> Reviewer -> END

`reflection_gate` is a trivial pass-through node whose only job is to be a
single join point: LangGraph waits for every *activated* incoming edge
before running a node with multiple predecessors, so this correctly waits
for exactly the specialist agents the Supervisor actually turned on -- not
a hardcoded set.

Lab and Dose are chained (not parallel with each other) because Dose reads
the Lab agent's output (weight/eGFR) for renal-adjusted limits; running
them as true siblings would mean Dose never sees fresh lab data in the same
superstep. Safety, Contraindication, and Guideline have no such dependency
and run as genuine parallel branches.

Node/state-key naming note: LangGraph forbids a node name that collides
with a state channel key, so the Reflection node is named "reflection_node"
(the state field is "reflection") and the Reviewer node is "reviewer" (the
state field is "review").
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.alternative_therapy_agent import alternative_therapy_node, should_run_alternative_agent
from app.agents.cdss_state import CDSSState
from app.agents.context_lab_agent import lab_node
from app.agents.contraindication_agent import contraindication_node
from app.agents.dose_agent import dose_node
from app.agents.extractor import extractor_node
from app.agents.guideline_agent import guideline_node
from app.agents.reflection_agent import reflection_node
from app.agents.reviewer_agent import reviewer_node
from app.agents.safety_checker import safety_node
from app.agents.supervisor import supervisor_node
from app.services.pinecone_service import PineconeService
from app.services.supabase_service import SupabaseService


def _route_after_extraction(state: CDSSState) -> str:
    if state.get("extraction") is None:
        return END
    if not state.get("use_copilot_mode"):
        return "safety_checker"
    return "supervisor"


def _fan_out_after_supervisor(state: CDSSState) -> list[str]:
    """Returns every node the Supervisor's routing decision activates.
    Safety (drug-drug interaction) always runs -- it's the non-negotiable
    baseline check, not something the Supervisor can turn off."""
    decision = state.get("routing_decision")
    targets = ["safety_checker"]

    if decision is not None:
        # Dose needs weight/eGFR from Lab, so route through Lab whenever
        # either Lab OR Dose is wanted.
        if decision.run_lab_agent or decision.run_dose_agent:
            targets.append("lab_node")
        if decision.run_contraindication_agent:
            targets.append("contraindication_node")
        if decision.run_guideline_agent:
            targets.append("guideline_node")

    return targets


def _route_after_lab(state: CDSSState) -> str:
    decision = state.get("routing_decision")
    if decision is not None and decision.run_dose_agent:
        return "dose_node"
    return "reflection_gate"


def _route_after_safety(state: CDSSState) -> str:
    """Fast Mode ends right after Safety; Copilot Mode joins the fan-in."""
    if not state.get("use_copilot_mode"):
        return "reviewer"
    return "reflection_gate"


def _route_after_reflection_gate(state: CDSSState) -> str:
    if should_run_alternative_agent(state):
        return "alternative_therapy"
    return "reflection_node"


def _identity(state: CDSSState) -> dict:
    """True no-op: exists purely to be a single fan-in join point for the
    Supervisor's dynamically-activated branches. LangGraph requires every
    node to write at least one declared channel, so this writes `trace_id`
    back unchanged -- a harmless, idempotent no-op write, since this node
    runs alone (after fan-in completes, not concurrently with siblings)."""
    return {"trace_id": state.get("trace_id", "")}


def _entry_route_from_structured_data(state: CDSSState) -> str:
    """Entry-point routing for manually-authored prescriptions: the
    doctor already supplied structured diagnosis + medications (no raw
    text to extract), so this skips Extractor entirely and goes straight
    to Supervisor (Copilot Mode) or Safety (Fast Mode)."""
    if not state.get("use_copilot_mode"):
        return "safety_checker"
    return "supervisor"


def _register_shared_nodes_and_edges(
    graph: StateGraph, llm, pinecone_service: PineconeService, supabase_service: SupabaseService
) -> None:
    """Registers every node/edge common to BOTH graph variants (the
    Extractor-first graph used by AI dictation, and the
    structured-data-first graph used by manual entry). Keeping this in one
    place means the Supervisor's fan-out/fan-in logic can never drift
    between the two entry paths -- a manually-entered prescription in
    Copilot Mode gets exactly the same specialist-agent routing as an
    AI-dictated one."""
    graph.add_node("supervisor", partial(supervisor_node, llm=llm))
    graph.add_node("safety_checker", partial(safety_node, pinecone_service=pinecone_service))
    graph.add_node("lab_node", partial(lab_node, supabase_service=supabase_service))
    graph.add_node("dose_node", dose_node)
    graph.add_node("contraindication_node", partial(contraindication_node, pinecone_service=pinecone_service))
    graph.add_node("guideline_node", partial(guideline_node, pinecone_service=pinecone_service))
    graph.add_node("reflection_gate", _identity)
    graph.add_node(
        "alternative_therapy", partial(alternative_therapy_node, llm=llm, pinecone_service=pinecone_service)
    )
    graph.add_node("reflection_node", partial(reflection_node, llm=llm))
    graph.add_node("reviewer", reviewer_node)

    graph.add_conditional_edges(
        "supervisor",
        _fan_out_after_supervisor,
        {
            "safety_checker": "safety_checker",
            "lab_node": "lab_node",
            "contraindication_node": "contraindication_node",
            "guideline_node": "guideline_node",
        },
    )
    graph.add_conditional_edges(
        "safety_checker", _route_after_safety, {"reviewer": "reviewer", "reflection_gate": "reflection_gate"}
    )
    graph.add_conditional_edges(
        "lab_node", _route_after_lab, {"dose_node": "dose_node", "reflection_gate": "reflection_gate"}
    )
    graph.add_edge("dose_node", "reflection_gate")
    graph.add_edge("contraindication_node", "reflection_gate")
    graph.add_edge("guideline_node", "reflection_gate")

    graph.add_conditional_edges(
        "reflection_gate",
        _route_after_reflection_gate,
        {"alternative_therapy": "alternative_therapy", "reflection_node": "reflection_node"},
    )
    graph.add_edge("alternative_therapy", "reflection_node")
    graph.add_edge("reflection_node", "reviewer")
    graph.add_edge("reviewer", END)


def build_cdss_graph(llm, pinecone_service: PineconeService, supabase_service: SupabaseService):
    """Compiles the AI-dictation graph: Extractor -> (Fast Mode | Copilot
    Mode). `llm`, `pinecone_service`, and `supabase_service` are injected
    so the graph can be built with fakes/mocks in unit tests, and with
    real clients in production."""
    graph = StateGraph(CDSSState)
    graph.add_node("extractor", partial(extractor_node, llm=llm))
    _register_shared_nodes_and_edges(graph, llm, pinecone_service, supabase_service)

    graph.set_entry_point("extractor")
    graph.add_conditional_edges(
        "extractor",
        _route_after_extraction,
        {"safety_checker": "safety_checker", "supervisor": "supervisor", END: END},
    )

    return graph.compile()


def build_cdss_graph_from_structured_data(llm, pinecone_service: PineconeService, supabase_service: SupabaseService):
    """Compiles the manual-entry graph: skips Extractor (the caller must
    pre-populate `state["extraction"]` before invoking), entering directly
    at Supervisor (Copilot Mode) or Safety (Fast Mode). Every specialist
    agent, and the Supervisor's routing logic, is IDENTICAL to the
    AI-dictation graph -- a manually-typed prescription gets the same
    Dose/Lab/Contraindication/Guideline workup as a dictated one."""
    graph = StateGraph(CDSSState)
    _register_shared_nodes_and_edges(graph, llm, pinecone_service, supabase_service)

    graph.set_conditional_entry_point(
        _entry_route_from_structured_data,
        {"safety_checker": "safety_checker", "supervisor": "supervisor"},
    )

    return graph.compile()

if __name__ == "__main__":
    # 1. ساخت متغیرهای غیرواقعی (Mock) فقط برای کامپایل شدن گراف
    dummy_llm = None
    dummy_pinecone = None
    dummy_supabase = None

    # 2. کامپایل کردن گراف اصلی
    graph = build_cdss_graph(
        llm=dummy_llm, 
        pinecone_service=dummy_pinecone, 
        supabase_service=dummy_supabase
    )
    
    # 3. دریافت ساختار قابل رسم گراف
    drawable_graph = graph.get_graph()

    print("=== 1. چاپ گراف در محیط متنی (ASCII) ===")
    drawable_graph.print_ascii()
    print("\n" + "="*50 + "\n")

    print("=== 2. تولید کد Mermaid (برای استفاده در سایت‌های رسم گراف) ===")
    mermaid_code = drawable_graph.draw_mermaid()
    print(mermaid_code)
    print("\n" + "="*50 + "\n")

    print("=== 3. ذخیره گراف به صورت عکس PNG ===")
    try:
        png_data = drawable_graph.draw_mermaid_png()
        
        output_path = "cdss_graph_diagram.png"
        with open(output_path, "wb") as f:
            f.write(png_data)
        print(f"✅ گراف با موفقیت به صورت عکس در فایل '{output_path}' ذخیره شد.")
    except Exception as e:
        print(f"❌ خطا در تولید عکس (احتمالاً به دلیل عدم دسترسی به اینترنت یا نصب نبودن httpx): {e}")
