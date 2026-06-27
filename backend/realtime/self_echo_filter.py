"""Self-echo suppression — drop user transcripts that are actually Boxi hearing herself.

Root cause (half-duplex + external speakers, no AEC): the half-duplex gate unmutes on
``BotStoppedSpeakingFrame``, but the speaker is still physically playing the buffered tail
of Boxi's last sentence (the ~200ms output buffer + device latency lead ``BotStopped`` over
real playback — see ``run_voice._BufferedLocalAudioOutputTransport``). With external speakers
and no echo cancellation the mic captures that tail; Doubao streaming ASR then finalizes it
~800ms later (its end-of-speech window), past the half-duplex resume guard, so the final
transcript escapes and the brain replies to Boxi's own words.

This is a **content-level backstop**: if a user final transcript matches the tail of Boxi's
last reply within a short window after she stopped speaking, drop it. It is keyed to a tail
(suffix) match — only the tail leaks past the gate — which keeps it from eating a genuine
fast follow-up that merely shares a word with Boxi's reply. When the project later moves to
barge-in / WebRTC (browser AEC), this stays useful as a residual-echo backstop.

Two processors share one ``SelfEchoGate`` (mirrors ``HalfDuplexMute``): a capture processor
placed *after* the brain records Boxi's reply text (``LLMTextFrame`` deltas) plus the
bot-stopped timestamp; a filter processor placed *before* the brain drops matching user finals.
"""

from __future__ import annotations

import re
import time
from difflib import SequenceMatcher
from typing import Callable

from loguru import logger

from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

_NON_WORD_RE = re.compile(r"[^\w]", re.UNICODE)
_DEFAULT_SINGLE_CHAR_ECHO_WINDOW_MS = 2000


def _normalize(text: str) -> str:
    """Strip whitespace + punctuation (CJK + ASCII) so echo matching ignores formatting."""
    return _NON_WORD_RE.sub("", text)


def is_self_echo(user_text: str, bot_text: str, *, min_chars: int = 2, ratio: float = 0.8) -> bool:
    """True if ``user_text`` looks like a tail of ``bot_text`` (Boxi hearing herself).

    Only the *tail* of Boxi's reply leaks past the half-duplex gate, so we require the user
    text to be a suffix (exact, or fuzzy ≥ ``ratio`` to absorb minor ASR errors) of the bot
    text — not just any substring. A genuine user reply that reuses a word from the middle of
    Boxi's sentence is therefore not suppressed.
    """
    u = _normalize(user_text)
    b = _normalize(bot_text)
    if len(u) < min_chars or len(b) < min_chars:
        return False
    if len(u) > len(b):
        return False  # user said more than Boxi did — cannot be a tail echo
    if b.endswith(u):
        return True
    tail = b[-len(u):]
    return SequenceMatcher(None, u, tail).ratio() >= ratio


def _is_exact_single_char_tail(user_text: str, bot_text: str) -> bool:
    """Match the narrow one-character tail leak seen after local speaker playback."""
    u = _normalize(user_text)
    b = _normalize(bot_text)
    return len(u) == 1 and bool(b) and b.endswith(u)


class SelfEchoGate:
    """Shared state for the capture/filter processor pair: Boxi's last reply + when it ended."""

    def __init__(
        self,
        *,
        window_ms: int,
        min_chars: int = 2,
        ratio: float = 0.8,
        single_char_window_ms: int = _DEFAULT_SINGLE_CHAR_ECHO_WINDOW_MS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._window_secs = window_ms / 1000.0
        self._single_char_window_secs = single_char_window_ms / 1000.0
        self._min_chars = min_chars
        self._ratio = ratio
        self._now = now or time.monotonic
        self._last_reply: str = ""
        self._reply_buffer: list[str] = []
        self._collecting = False
        self._bot_stopped_at: float | None = None

    # --- capture side (placed after the brain) ---
    def on_reply_start(self) -> None:
        self._reply_buffer = []
        self._collecting = True

    def on_reply_delta(self, text: str) -> None:
        if self._collecting:
            self._reply_buffer.append(text)

    def on_reply_end(self) -> None:
        if not self._collecting:
            return
        self._collecting = False
        text = "".join(self._reply_buffer).strip()
        self._reply_buffer = []
        if text:
            self._last_reply = text

    def on_bot_stopped(self) -> None:
        # Window starts when Boxi (almost) finishes speaking — that is when the tail leaks.
        self._bot_stopped_at = self._now()

    # --- filter side (placed before the brain) ---
    def is_echo(self, user_text: str) -> bool:
        if self._bot_stopped_at is None or not self._last_reply:
            return False
        elapsed = self._now() - self._bot_stopped_at
        if elapsed > self._window_secs:
            return False
        # Keep the general matcher at min_chars=2 so real one-character replies such as
        # "嗯"/"好" are normally preserved. The only exception is the exact final character
        # of Boxi's reply during the brief physical playback-tail window. This covers the
        # observed "先睡，乖。" -> ASR "乖。" loop without widening fuzzy matching.
        if elapsed <= self._single_char_window_secs and _is_exact_single_char_tail(
            user_text, self._last_reply
        ):
            return True
        return is_self_echo(
            user_text, self._last_reply, min_chars=self._min_chars, ratio=self._ratio
        )

    def consume(self) -> None:
        # Suppress at most one echo per Boxi turn; a genuine follow-up afterward is safe.
        self._bot_stopped_at = None


class SelfEchoCaptureProcessor(FrameProcessor):
    """Records Boxi's reply text + bot-stopped time into the gate (placed after the brain)."""

    def __init__(self, gate: SelfEchoGate) -> None:
        super().__init__()
        self._gate = gate

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self._gate.on_reply_start()
        elif isinstance(frame, LLMTextFrame):
            self._gate.on_reply_delta(frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame):
            self._gate.on_reply_end()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._gate.on_bot_stopped()
        await self.push_frame(frame, direction)


class SelfEchoFilterProcessor(FrameProcessor):
    """Drops user final transcripts that echo Boxi's last reply (placed before the brain)."""

    def __init__(self, gate: SelfEchoGate) -> None:
        super().__init__()
        self._gate = gate

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text and self._gate.is_echo(text):
                self._gate.consume()
                logger.info(f"🔇 self-echo suppressed (Boxi heard herself): {text!r}")
                return
        await self.push_frame(frame, direction)
