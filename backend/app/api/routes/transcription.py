"""Voice-to-text endpoint: a doctor records an encounter note by voice,
and this transcribes it to English text ready to feed into the Extractor
agent -- exactly like typing it, just faster.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from app.core.auth import CurrentDoctor, get_current_doctor
from app.core.config import Settings, get_settings
from app.models.schemas import TranscriptionResponse
from app.services.transcription_service import transcribe_audio

router = APIRouter(prefix="/transcribe", tags=["transcription"])


@router.post("", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile,
    settings: Settings = Depends(get_settings),
    _doctor: CurrentDoctor = Depends(get_current_doctor),
) -> TranscriptionResponse:
    audio_bytes = await audio.read()
    text = transcribe_audio(settings, audio_bytes, filename=audio.filename or "recording.webm")
    return TranscriptionResponse(text=text)
