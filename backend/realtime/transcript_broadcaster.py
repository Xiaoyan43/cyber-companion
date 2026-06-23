"""Pass-through Pipecat taps that broadcast user/Boxi transcript text to WebSocket subscribers.

Two tap points are needed because the user's text and Boxi's text live in different parts of
the pipeline: ``CompanionBrainProcessor`` consumes (swallows) ``TranscriptionFrame`` rather than
forwarding it, so the user tap must sit *before* the brain; ``LLMTextFrame`` deltas are only
produced *after* the brain, so the Boxi tap must sit *after* it. Both taps share one
``TranscriptBroadcaster`` so a single set of WebSocket subscribers sees both roles.
"""

from __future__ import annotations

import asyncio
import time

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TranscriptBroadcaster:
    """Holds WebSocket subscriber queues and fans out transcript events to all of them."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def emit(self, role: str, text: str) -> None:
        event = {"role": role, "text": text, "ts": time.time()}
        for queue in self._subscribers:
            queue.put_nowait(event)


class _UserTranscriptTap(FrameProcessor):
    """Emits the user's finalized STT text without altering the frame stream."""

    def __init__(self, broadcaster: TranscriptBroadcaster) -> None:
        super().__init__()
        self._broadcaster = broadcaster

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                self._broadcaster.emit("user", text)
        await self.push_frame(frame, direction)


class _BoxiTranscriptTap(FrameProcessor):
    """Aggregates streamed ``LLMTextFrame`` deltas into one event per finished reply."""

    def __init__(self, broadcaster: TranscriptBroadcaster) -> None:
        super().__init__()
        self._broadcaster = broadcaster
        self._buffer: list[str] = []
        self._collecting = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self._buffer = []
            self._collecting = True
        elif isinstance(frame, LLMTextFrame) and self._collecting:
            self._buffer.append(frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame) and self._collecting:
            self._collecting = False
            text = "".join(self._buffer).strip()
            self._buffer = []
            if text:
                self._broadcaster.emit("boxi", text)
        await self.push_frame(frame, direction)


_broadcaster: TranscriptBroadcaster | None = None


def get_transcript_broadcaster() -> TranscriptBroadcaster:
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = TranscriptBroadcaster()
    return _broadcaster


def user_transcript_tap(broadcaster: TranscriptBroadcaster) -> FrameProcessor:
    return _UserTranscriptTap(broadcaster)


def boxi_transcript_tap(broadcaster: TranscriptBroadcaster) -> FrameProcessor:
    return _BoxiTranscriptTap(broadcaster)
