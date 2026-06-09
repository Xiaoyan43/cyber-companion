"""Doubao flash (one-shot) STT as a Pipecat SegmentedSTTService.

Streaming WebSocket ASR is deferred to Phase 2b; this shim reuses the existing
``DoubaoASRProvider`` so cloud STT replaces local Whisper CPU load now.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

from backend.app.stt.doubao import DoubaoASRProvider
from backend.app.stt.exceptions import STTConfigError, STTError
from backend.app.stt.types import TranscriptionRequest

INPUT_SAMPLE_RATE = 16_000


class DoubaoFlashSTTService(SegmentedSTTService):
    """Cloud flash ASR on VAD speech segments (WAV in, transcript out)."""

    def __init__(self, *, language: str | None = "zh-CN", **kwargs) -> None:
        super().__init__(
            sample_rate=INPUT_SAMPLE_RATE,
            settings=STTSettings(model="bigmodel", language=language),
            **kwargs,
        )
        self._provider = DoubaoASRProvider(enabled=True)
        if not self._provider.is_configured():
            raise RuntimeError(
                "Doubao ASR is not configured. Set DOUBAO_API_KEY."
            )

    def can_generate_metrics(self) -> bool:
        return True

    @traced_stt
    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        """Transcribe a VAD segment (WAV bytes from SegmentedSTTService)."""
        await self.start_processing_metrics()

        language = self._settings.language
        if isinstance(language, Language):
            language = language.value

        request = TranscriptionRequest(
            audio_bytes=audio,
            mime_type="audio/wav",
            language=language if isinstance(language, str) else "zh-CN",
        )

        try:
            result = await asyncio.to_thread(self._provider.transcribe, request)
        except STTConfigError as error:
            await self.stop_processing_metrics()
            yield ErrorFrame(error=f"Doubao ASR config error: {error}")
            return
        except STTError as error:
            await self.stop_processing_metrics()
            message = str(error)
            if "No speech detected" in message:
                logger.debug(f"{self}: silent segment, skipping")
                return
            yield ErrorFrame(error=f"Doubao ASR failed: {error}")
            return
        except Exception as error:
            await self.stop_processing_metrics()
            yield ErrorFrame(error=f"Doubao ASR failed: {error}")
            return

        await self.stop_processing_metrics()

        text = result.text.strip()
        if not text:
            return

        logger.debug(f"Transcription: [{text}]")
        yield TranscriptionFrame(
            text,
            self._user_id,
            time_now_iso8601(),
            Language.ZH if result.language and result.language.startswith("zh") else None,
            result=result,
        )
