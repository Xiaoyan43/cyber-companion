"""Doubao streaming TTS as a Pipecat TTSService (PCM 24 kHz)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Iterator

from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts

from backend.app.tts.doubao import DoubaoTTSProvider
from backend.app.tts.exceptions import TTSConfigError, TTSError
from backend.app.tts.text_cleanup import clean_text_for_tts
from backend.app.tts.types import SynthesisRequest

SAMPLE_RATE = 24_000


def _sync_next(iterator: Iterator[bytes]) -> bytes | None:
    try:
        return next(iterator)
    except StopIteration:
        return None


async def _async_pcm_chunks(iterator: Iterator[bytes]) -> AsyncIterator[bytes]:
    while True:
        chunk = await asyncio.to_thread(_sync_next, iterator)
        if chunk is None:
            return
        yield chunk


class DoubaoTTSService(TTSService):
    """Pipecat TTS backed by Doubao V3 unidirectional HTTP streaming."""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=SAMPLE_RATE,
            settings=TTSSettings(model=None, voice=None, language=None),
            **kwargs,
        )
        self._provider = DoubaoTTSProvider(enabled=True, audio_format="pcm")
        if not self._provider.is_configured():
            raise RuntimeError(
                "Doubao TTS is not configured. Set DOUBAO_TTS_API_KEY and DOUBAO_TTS_VOICE_TYPE."
            )
        self._current_context_id: str | None = None
        self._context_sentences: list[str] = []

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"{self}: Generating Doubao TTS [{text}]")

        if context_id != self._current_context_id:
            self._current_context_id = context_id
            self._context_sentences = []

        try:
            await self.start_tts_usage_metrics(text)
            stream = self._provider.synthesize_stream(
                SynthesisRequest(text=text, context_texts=self._context_sentences or None)
            )
            async for frame in self._stream_audio_frames_from_iterator(
                _async_pcm_chunks(stream),
                in_sample_rate=SAMPLE_RATE,
                context_id=context_id,
            ):
                await self.stop_ttfb_metrics()
                yield frame
            self._context_sentences.append(clean_text_for_tts(text))
        except (TTSConfigError, TTSError) as error:
            logger.error(f"{self} Doubao TTS error: {error}")
            yield ErrorFrame(error=f"Doubao TTS failed: {error}")
        except Exception as error:
            logger.error(f"{self} exception: {error}")
            yield ErrorFrame(error=f"Doubao TTS failed: {error}")
        finally:
            logger.debug(f"{self}: Finished Doubao TTS [{text}]")
            await self.stop_ttfb_metrics()
