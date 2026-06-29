from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult


class SpeechToTextProvider(ABC):
    name: str
    cloud: bool = False

    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> STTProviderStatus:
        raise NotImplementedError

    def is_configured(self) -> bool:
        status = self.status()
        return status.configured and (status.api_key_present or not status.cloud)
