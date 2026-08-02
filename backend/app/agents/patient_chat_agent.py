"""Patient Records Chat Agent.

A small tool-calling ReAct loop (agent -> tools -> agent -> ... -> END)
that lets a doctor ask natural-language questions about a patient
("show me Ahmad Karimi's file", "what is patient REC-0001 currently on?")
and get back an answer grounded in a real database lookup -- the LLM is
never allowed to just make up patient data; it must call a tool.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.services.supabase_service import SupabaseService
from app.tools.patient_tools import build_patient_tools

SYSTEM_PROMPT = """You are a clinical records assistant for Watan Hospital doctors. \
You have tools to look up a patient's full medical record -- demographics, allergies, \
chronic conditions, and prescription history -- by record number/national ID, or by \
full name and (optionally) father's name. You can also refer a patient to another \
doctor by email, sharing your access with them.

Rules:
- Always call a tool before answering any question about a specific patient. Never \
guess, infer, or fabricate patient data from memory.
- Access is controlled by treatment relationships: a doctor can only see patients they \
actively treat (or have been referred). If a lookup says no patient was found, this may \
mean the patient doesn't exist in the system, OR that the doctor simply isn't authorized \
to view them -- these cases are intentionally indistinguishable, so never speculate about \
which one it is. Just relay that no accessible match was found, and suggest either seeing \
the patient for a new visit or requesting a referral from their treating doctor.
- If a lookup returns multiple matching patients, ask the doctor to provide the exact \
record number rather than picking one yourself.
- Referrals require the referring doctor to already have an active relationship with the \
patient; if that's not the case, relay the tool's explanation plainly.
- Answer in clear, concise English, organized so a doctor can scan it quickly.
"""


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_patient_chat_graph(llm, supabase_service: SupabaseService, doctor_id: str):
    """Compiles the tool-calling chat graph for a single doctor's session."""
    tools = build_patient_tools(supabase_service, doctor_id)
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: ChatState) -> ChatState:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
