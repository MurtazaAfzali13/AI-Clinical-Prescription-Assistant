"""Patient-records chatbot endpoint.

POST /api/v1/chat -- a doctor asks a natural-language question about a
patient; the agent decides whether to call a lookup/referral tool and
returns a grounded answer. Access to any patient data is gated by the
treatment-relationship model enforced in SupabaseService.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.agents.patient_chat_agent import build_patient_chat_graph
from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_llm(settings: Settings = Depends(get_settings)) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


def get_supabase_service(settings: Settings = Depends(get_settings)) -> SupabaseService:
    return SupabaseService(settings=settings)


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    llm: ChatOpenAI = Depends(get_llm),
    supabase_service: SupabaseService = Depends(get_supabase_service),
    doctor: CurrentDoctor = Depends(get_current_doctor),
) -> ChatResponse:
    graph = build_patient_chat_graph(llm=llm, supabase_service=supabase_service, doctor_id=doctor.id)

    messages = []
    for turn in payload.history:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    messages.append(HumanMessage(content=payload.message))

    final_state = graph.invoke({"messages": messages})
    reply = final_state["messages"][-1].content
    return ChatResponse(reply=reply)
