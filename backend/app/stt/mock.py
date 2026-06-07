from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult


class MockSTTProvider(SpeechToTextProvider):
    name = "mock"
    cloud = False

    def __init__(self, model: str = "mock-stt") -> None:
        self._model = model

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        byte_count = len(request.audio_bytes)
        return TranscriptionResult(
            provider=self.name,
            model=self._model,
            text=f"这是一条 mock 语音转写（{byte_count} bytes）。",
            mock=True,
            language=request.language,
        )

    def status(self) -> STTProviderStatus:
        return STTProviderStatus(
            name=self.name,
            enabled=True,
            model=self._model,
            configured=True,
            api_key_present=False,
            placeholder=False,
            cloud=False,
        )
