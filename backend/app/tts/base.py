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

    def stream_mime_type(self) -> str:
        """MIME type of the bytes yielded by synthesize_stream(). Override when the
        provider streams a different container/codec than the audio/mpeg default."""
        return "audio/mpeg"

    def is_configured(self) -> bool:
        status = self.status()
        return status.configured and (status.api_key_present or not status.cloud)
