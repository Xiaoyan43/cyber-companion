"""Placeholder local TTS via macOS ``say`` for the V2 voice skeleton."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import wave
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path

from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts

DEFAULT_VOICE = "Tingting"
SAMPLE_RATE = 22050
CHUNK_SAMPLES = 2205  # ~100ms at 22050 Hz


class MacSayTTSService(TTSService):
    """Audible placeholder TTS using the built-in macOS ``say`` command."""

    def __init__(self, *, voice: str | None = None, **kwargs) -> None:
        resolved_voice = voice or os.getenv("CYBER_COMPANION_SAY_VOICE", DEFAULT_VOICE)
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=SAMPLE_RATE,
            settings=TTSSettings(model=None, voice=resolved_voice, language=None),
            **kwargs,
        )
        self._voice = resolved_voice
        self._say_path = shutil.which("say")
        if not self._say_path:
            raise RuntimeError("macOS `say` is not available on this system.")

    def _synthesize_to_wav(self, text: str, path: Path) -> None:
        completed = subprocess.run(
            [
                self._say_path,
                "-v",
                self._voice,
                "-o",
                str(path),
                "--file-format=WAVE",
                "--data-format=LEI16@22050",
                text,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or "macOS `say` failed").strip())

    @staticmethod
    def _pcm_chunks(wav_path: Path) -> list[bytes]:
        with wave.open(str(wav_path), "rb") as wav_file:
            if wav_file.getnchannels() != 1:
                raise RuntimeError("Expected mono WAV from `say`.")
            if wav_file.getsampwidth() != 2:
                raise RuntimeError("Expected 16-bit PCM from `say`.")
            if wav_file.getframerate() != SAMPLE_RATE:
                raise RuntimeError(
                    f"Expected {SAMPLE_RATE} Hz from `say`, got {wav_file.getframerate()}."
                )
            frames = wav_file.readframes(wav_file.getnframes())

        chunk_bytes = CHUNK_SAMPLES * 2
        return [frames[index : index + chunk_bytes] for index in range(0, len(frames), chunk_bytes)]

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"{self}: Generating TTS [{text}]")

        async def chunk_iterator() -> AsyncIterator[bytes]:
            tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)
            tmp_path = Path(tmp_path_str)
            try:
                await asyncio.to_thread(self._synthesize_to_wav, text, tmp_path)
                for chunk in self._pcm_chunks(tmp_path):
                    yield chunk
            finally:
                tmp_path.unlink(missing_ok=True)

        try:
            await self.start_tts_usage_metrics(text)
            async for frame in self._stream_audio_frames_from_iterator(
                chunk_iterator(),
                in_sample_rate=SAMPLE_RATE,
                context_id=context_id,
            ):
                await self.stop_ttfb_metrics()
                yield frame
        except Exception as error:
            logger.error(f"{self} exception: {error}")
            yield ErrorFrame(error=f"macOS say TTS failed: {error}")
        finally:
            logger.debug(f"{self}: Finished TTS [{text}]")
            await self.stop_ttfb_metrics()
