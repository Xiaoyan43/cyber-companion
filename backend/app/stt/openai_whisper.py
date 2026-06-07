from __future__ import annotations

import os

from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.exceptions import STTConfigError
from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult


class OpenAIWhisperProvider(SpeechToTextProvider):
    name = "openai_whisper"
    cloud = True

    def __init__(
        self,
        *,
        model: str = "whisper-1",
        api_key_env: str = "OPENAI_API_KEY",
        enabled: bool = False,
        placeholder: bool = True,
    ) -> None:
        self._model = model
        self._api_key_env = api_key_env
        self._enabled = enabled
        self._placeholder = placeholder

    def _api_key(self) -> str | None:
        value = os.getenv(self._api_key_env, "").strip()
        return value or None

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self._placeholder:
            raise STTConfigError(
                "OpenAI Whisper adapter is a placeholder in this MVP pass. "
                "Use mock STT or implement the cloud adapter explicitly."
            )

        api_key = self._api_key()
        if not api_key:
            raise STTConfigError(
                f"OpenAI Whisper is selected but `{self._api_key_env}` is not configured."
            )

        raise STTConfigError("Cloud Whisper transcription is not wired in this MVP pass.")

    def status(self) -> STTProviderStatus:
        api_key_present = self._api_key() is not None
        return STTProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=not self._placeholder and api_key_present,
            api_key_present=api_key_present,
            placeholder=self._placeholder,
            cloud=True,
        )
