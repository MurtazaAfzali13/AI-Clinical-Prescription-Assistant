import pytest

from app.core.config import Settings
from app.core.exceptions import TranscriptionError
from app.services import transcription_service


class _FakeTranscriptionResult:
    def __init__(self, text: str):
        self.text = text


class _FakeAudioNamespace:
    def __init__(self, result=None, raise_error: Exception | None = None):
        self._result = result
        self._raise_error = raise_error
        self.last_call_kwargs = None

    class _Transcriptions:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.last_call_kwargs = kwargs
            if self._outer._raise_error:
                raise self._outer._raise_error
            return self._outer._result

    def __init__(self, result=None, raise_error=None):
        self._result = result
        self._raise_error = raise_error
        self.last_call_kwargs = None
        self.transcriptions = self._Transcriptions(self)


class _FakeOpenAIClient:
    def __init__(self, audio_namespace):
        self.audio = audio_namespace

    def __call__(self, *_args, **_kwargs):
        return self


def test_transcribe_audio_requires_api_key():
    settings = Settings(openrouter_api_key="")
    with pytest.raises(TranscriptionError, match="not configured"):
        transcription_service.transcribe_audio(settings, b"fake-audio-bytes", "note.webm")


def test_transcribe_audio_requires_nonempty_audio():
    settings = Settings(openrouter_api_key="key")
    with pytest.raises(TranscriptionError, match="No audio data"):
        transcription_service.transcribe_audio(settings, b"", "note.webm")


def test_transcribe_audio_rejects_oversized_file():
    settings = Settings(openrouter_api_key="key")
    too_big = b"x" * (transcription_service.MAX_AUDIO_BYTES + 1)
    with pytest.raises(TranscriptionError, match="too large"):
        transcription_service.transcribe_audio(settings, too_big, "note.webm")


def test_transcribe_audio_success(monkeypatch):
    settings = Settings(openrouter_api_key="key", stt_model_name="openai/whisper-1")
    fake_audio_ns = _FakeAudioNamespace(result=_FakeTranscriptionResult("Patient has a headache."))

    def _fake_openai_constructor(*_args, **_kwargs):
        return _FakeOpenAIClient(fake_audio_ns)

    monkeypatch.setattr(transcription_service, "OpenAI", _fake_openai_constructor)

    text = transcription_service.transcribe_audio(settings, b"fake-audio-bytes", "note.webm")

    assert text == "Patient has a headache."
    assert fake_audio_ns.last_call_kwargs["model"] == "openai/whisper-1"


def test_transcribe_audio_wraps_provider_errors(monkeypatch):
    settings = Settings(openrouter_api_key="key")
    fake_audio_ns = _FakeAudioNamespace(raise_error=RuntimeError("upstream boom"))

    def _fake_openai_constructor(*_args, **_kwargs):
        return _FakeOpenAIClient(fake_audio_ns)

    monkeypatch.setattr(transcription_service, "OpenAI", _fake_openai_constructor)

    with pytest.raises(TranscriptionError, match="upstream boom"):
        transcription_service.transcribe_audio(settings, b"fake-audio-bytes", "note.webm")


def test_transcribe_audio_rejects_empty_transcript(monkeypatch):
    settings = Settings(openrouter_api_key="key")
    fake_audio_ns = _FakeAudioNamespace(result=_FakeTranscriptionResult("   "))

    def _fake_openai_constructor(*_args, **_kwargs):
        return _FakeOpenAIClient(fake_audio_ns)

    monkeypatch.setattr(transcription_service, "OpenAI", _fake_openai_constructor)

    with pytest.raises(TranscriptionError, match="no text"):
        transcription_service.transcribe_audio(settings, b"fake-audio-bytes", "note.webm")
