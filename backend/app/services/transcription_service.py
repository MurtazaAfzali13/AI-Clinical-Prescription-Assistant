"""Voice-to-text transcription via OpenRouter's audio/transcriptions endpoint.

OpenRouter exposes a dedicated Whisper-compatible endpoint
(`/api/v1/audio/transcriptions`) that accepts the same Bearer key used for
chat completions -- no separate OpenAI account is needed. The official
`openai` Python client works against it directly by pointing `base_url` at
OpenRouter, so we reuse that client rather than hand-rolling HTTP calls.
"""
from __future__ import annotations

from openai import OpenAI

from app.core.config import Settings
from app.core.exceptions import TranscriptionError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Whisper/OpenRouter's transcription endpoint caps uploads at 25 MB.
MAX_AUDIO_BYTES = 25 * 1024 * 1024


def transcribe_audio(settings: Settings, audio_bytes: bytes, filename: str) -> str:
    """Sends a recorded audio clip to Whisper (via OpenRouter) and returns
    the transcribed text."""
    if not settings.openrouter_api_key:
        raise TranscriptionError("OPENROUTER_API_KEY is not configured; voice input is unavailable.")

    if not audio_bytes:
        raise TranscriptionError("No audio data received.")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise TranscriptionError("Audio clip is too large (25 MB limit). Please record a shorter note.")

    client = OpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)

    try:
        result = client.audio.transcriptions.create(
            model=settings.stt_model_name,
            file=(filename, audio_bytes),
        )
    except Exception as exc:  # noqa: BLE001 - normalise all provider/network errors
        logger.error("transcription_failed", extra={"extra_fields": {"error": str(exc)}})
        raise TranscriptionError(f"Transcription failed: {exc}") from exc

    text = getattr(result, "text", "") or ""
    if not text.strip():
        raise TranscriptionError("Transcription returned no text; the recording may be silent or too short.")

    return text.strip()
