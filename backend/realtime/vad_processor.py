"""Silero VAD passthrough — keeps endpointing without Pipecat LLMContext."""

from __future__ import annotations

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
from backend.realtime.voice_config import load_vad_stop_secs
from pipecat.audio.vad.vad_controller import VADController
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    StartFrame,
    UserSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class SileroVADProcessor(FrameProcessor):
    """Minimal VAD step extracted from ``LLMUserAggregator`` — passthrough all frames."""

    def __init__(self, *, vad_analyzer: VADAnalyzer | None = None, stop_secs: float | None = None) -> None:
        super().__init__()
        resolved_stop_secs = stop_secs if stop_secs is not None else load_vad_stop_secs()
        analyzer = vad_analyzer or SileroVADAnalyzer(
            params=VADParams(stop_secs=resolved_stop_secs),
        )
        logger.debug(f"SileroVADProcessor stop_secs={resolved_stop_secs}")
        self._vad_controller = VADController(analyzer)
        self._vad_controller.add_event_handler("on_speech_started", self._on_vad_speech_started)
        self._vad_controller.add_event_handler("on_speech_stopped", self._on_vad_speech_stopped)
        self._vad_controller.add_event_handler("on_speech_activity", self._on_vad_speech_activity)
        self._vad_controller.add_event_handler("on_push_frame", self._on_push_frame)
        self._vad_controller.add_event_handler("on_broadcast_frame", self._on_broadcast_frame)

    async def cleanup(self) -> None:
        await super().cleanup()
        await self._vad_controller.cleanup()

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self._vad_controller.process_frame(frame)

        if isinstance(frame, StartFrame):
            await self.push_frame(frame, direction)
            await self._vad_controller.setup(self.task_manager)
        elif isinstance(frame, (EndFrame, CancelFrame)):
            await self.push_frame(frame, direction)
            if isinstance(frame, EndFrame):
                await self._vad_controller.cleanup()
        else:
            await self.push_frame(frame, direction)

    async def _queued_broadcast_frame(self, frame_cls: type[Frame], **kwargs) -> None:
        await self.queue_frame(frame_cls(**kwargs))
        await self.push_frame(frame_cls(**kwargs), FrameDirection.UPSTREAM)

    async def _on_push_frame(
        self,
        _controller: VADController,
        frame: Frame,
        direction: FrameDirection = FrameDirection.DOWNSTREAM,
    ) -> None:
        await self.queue_frame(frame, direction)

    async def _on_broadcast_frame(self, _controller: VADController, frame_cls: type[Frame], **kwargs) -> None:
        await self._queued_broadcast_frame(frame_cls, **kwargs)

    async def _on_vad_speech_started(self, controller: VADController) -> None:
        await self._queued_broadcast_frame(
            VADUserStartedSpeakingFrame,
            start_secs=controller._vad_analyzer.params.start_secs,
        )

    async def _on_vad_speech_stopped(self, controller: VADController) -> None:
        await self._queued_broadcast_frame(
            VADUserStoppedSpeakingFrame,
            stop_secs=controller._vad_analyzer.params.stop_secs,
        )

    async def _on_vad_speech_activity(self, _controller: VADController) -> None:
        await self._queued_broadcast_frame(UserSpeakingFrame)
