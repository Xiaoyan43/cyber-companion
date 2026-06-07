from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus
from backend.app.tts.wav_utils import estimate_speech_duration_ms, generate_silent_wav


class MockTTSProvider(TextToSpeechProvider):
    name = "mock"
    cloud = False

    def __init__(self, model: str = "mock-tts") -> None:
        self._model = model

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        duration_ms = estimate_speech_duration_ms(request.text)
        audio_bytes = generate_silent_wav(duration_ms)
        return SynthesisResult(
            provider=self.name,
            model=self._model,
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            duration_ms=duration_ms,
            mock=True,
        )

    def status(self) -> TTSProviderStatus:
        return TTSProviderStatus(
            name=self.name,
            enabled=True,
            model=self._model,
            configured=True,
            api_key_present=False,
            placeholder=False,
            cloud=False,
        )
