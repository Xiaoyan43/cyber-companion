from __future__ import annotations

import io
import shutil
import threading
from typing import TYPE_CHECKING

import numpy as np

from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.exceptions import STTError
from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

TARGET_SAMPLE_RATE = 16_000

_model_cache: dict[str, WhisperModel] = {}
_cache_lock = threading.Lock()


def reset_faster_whisper_cache() -> None:
    with _cache_lock:
        _model_cache.clear()


def _get_whisper_model(model_size: str) -> WhisperModel:
    with _cache_lock:
        if model_size not in _model_cache:
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise STTError(
                    "faster-whisper is not installed. Install it into the project venv.",
                    provider="faster_whisper",
                    status_code=503,
                ) from error

            _model_cache[model_size] = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
            )
        return _model_cache[model_size]


def decode_audio_bytes(audio_bytes: bytes) -> np.ndarray:
    try:
        import av
    except ImportError as error:
        raise STTError(
            "PyAV is not installed. Install av into the project venv.",
            provider="faster_whisper",
            status_code=503,
        ) from error

    if not audio_bytes:
        raise STTError("Audio payload is empty.", provider="faster_whisper", status_code=400)

    try:
        container = av.open(io.BytesIO(audio_bytes))
    except av.error.FFmpegError as error:
        raise STTError(
            f"Could not decode audio: {error}",
            provider="faster_whisper",
            status_code=400,
        ) from error

    if not container.streams.audio:
        container.close()
        raise STTError(
            "Audio file contains no audio stream.",
            provider="faster_whisper",
            status_code=400,
        )

    resampler = av.AudioResampler(
        format="flt",
        layout="mono",
        rate=TARGET_SAMPLE_RATE,
    )

    samples: list[np.ndarray] = []
    try:
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                array = resampled.to_ndarray()
                if array.ndim > 1:
                    array = array[0]
                samples.append(array.astype(np.float32, copy=False))
    except av.error.FFmpegError as error:
        raise STTError(
            f"Audio decode failed: {error}",
            provider="faster_whisper",
            status_code=400,
        ) from error
    finally:
        container.close()

    if not samples:
        raise STTError(
            "No audio samples could be decoded from the recording.",
            provider="faster_whisper",
            status_code=400,
        )

    audio = np.concatenate(samples)
    if audio.size == 0:
        raise STTError(
            "Decoded audio is empty.",
            provider="faster_whisper",
            status_code=400,
        )

    return audio


class FasterWhisperProvider(SpeechToTextProvider):
    name = "faster_whisper"
    cloud = False

    def __init__(
        self,
        *,
        model: str = "base",
        enabled: bool = True,
    ) -> None:
        self._model_size = model
        self._enabled = enabled

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        audio = decode_audio_bytes(request.audio_bytes)
        whisper_model = _get_whisper_model(self._model_size)

        try:
            segments, info = whisper_model.transcribe(
                audio,
                language=request.language or None,
            )
        except Exception as error:
            raise STTError(
                f"Transcription failed: {error}",
                provider=self.name,
            ) from error

        text = "".join(segment.text for segment in segments).strip()
        if not text:
            raise STTError(
                "No speech detected in the recording.",
                provider=self.name,
                status_code=400,
            )

        detected_language = getattr(info, "language", None) or request.language

        return TranscriptionResult(
            provider=self.name,
            model=self._model_size,
            text=text,
            mock=False,
            language=detected_language,
        )

    def status(self) -> STTProviderStatus:
        return STTProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model_size,
            configured=self._dependencies_available(),
            api_key_present=False,
            placeholder=False,
            cloud=False,
        )

    def _dependencies_available(self) -> bool:
        try:
            import av  # noqa: F401
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return shutil.which("ffmpeg") is not None
