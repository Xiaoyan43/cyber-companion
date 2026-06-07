from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus


class TextToSpeechProvider(ABC):
    name: str
    cloud: bool = False

    @abstractmethod
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> TTSProviderStatus:
        raise NotImplementedError

    def is_configured(self) -> bool:
        status = self.status()
        return status.configured and (status.api_key_present or not status.cloud)
