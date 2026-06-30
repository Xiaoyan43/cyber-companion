from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import InterruptionFrame, TranscriptionFrame
from pipecat.tests.utils import SleepFrame, run_test

from backend.realtime.companion_brain_processor import CompanionBrainProcessor


class _FakeResult:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeOutcome:
    def __init__(self, raw_reply: str) -> None:
        self.raw_reply = raw_reply
        self.truncated = False
        self.result = _FakeResult(raw_reply)
        self.reply_signals = None
        self.final_decision = "reply"
        self.avatar_state = "talking"
        self.called_llm = False


class _FakeBrain:
    """Stub CompanionBrain — first turn streams slowly so it can be cut off mid-reply,
    second turn finishes immediately. Records the ``interrupted_partial`` it was called
    with each time."""

    def __init__(self) -> None:
        self.calls: list[str | None] = []

    async def stream_turn(self, user_text, *, interrupted_partial=None):
        self.calls.append(interrupted_partial)
        if len(self.calls) == 1:
            yield ("delta", "先睡，")
            await asyncio.sleep(0.2)
            yield ("delta", "乖。")
            yield ("done", _FakeOutcome("先睡，乖。"))
        else:
            yield ("delta", "嗯。")
            yield ("done", _FakeOutcome("嗯。"))

    def remember(self, outcome) -> None:
        return None


def _transcription(text: str) -> TranscriptionFrame:
    return TranscriptionFrame(text, "user", "2026-07-01T00:00:00Z")


def test_interrupted_partial_carried_into_next_turn() -> None:
    async def run() -> None:
        brain = _FakeBrain()
        processor = CompanionBrainProcessor(brain)
        await run_test(
            processor,
            frames_to_send=[
                _transcription("先睡吧"),
                SleepFrame(sleep=0.05),
                InterruptionFrame(),
                _transcription("我还没说完"),
                SleepFrame(sleep=0.1),
            ],
        )

        assert len(brain.calls) == 2
        assert brain.calls[0] is None  # first turn: nothing to reference yet
        assert brain.calls[1] == "先睡，"  # only what had actually streamed before the cut

    asyncio.run(run())


def test_no_interruption_means_no_hint_carried() -> None:
    async def run() -> None:
        brain = _FakeBrain()
        processor = CompanionBrainProcessor(brain)
        await run_test(
            processor,
            frames_to_send=[
                _transcription("先睡吧"),
                SleepFrame(sleep=0.3),
                _transcription("早安"),
                SleepFrame(sleep=0.1),
            ],
        )

        assert len(brain.calls) == 2
        assert brain.calls[0] is None
        assert brain.calls[1] is None  # turn 1 finished naturally, never interrupted

    asyncio.run(run())
