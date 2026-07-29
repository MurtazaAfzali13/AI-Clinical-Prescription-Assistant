"""Builds the LangGraph StateGraph wiring Extractor -> Safety Checker."""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.extractor import extractor_node
from app.agents.safety_checker import safety_node
from app.agents.state import GraphState
from app.services.pinecone_service import PineconeService


def route_after_extraction(state: GraphState) -> str:
    """Skip the safety check entirely if extraction failed."""
    if state.get("extraction") is None:
        return END
    return "safety_checker"


def build_prescription_graph(llm, pinecone_service: PineconeService):
    """Compiles the Extractor -> Safety Checker pipeline.

    `llm` and `pinecone_service` are injected so the graph can be built
    with fakes/mocks in unit tests, and with real clients in production.
    """
    graph = StateGraph(GraphState)

    graph.add_node("extractor", partial(extractor_node, llm=llm))
    graph.add_node("safety_checker", partial(safety_node, pinecone_service=pinecone_service))

    graph.set_entry_point("extractor")
    graph.add_conditional_edges(
        "extractor",
        route_after_extraction,
        {"safety_checker": "safety_checker", END: END},
    )
    graph.add_edge("safety_checker", END)

    return graph.compile()
