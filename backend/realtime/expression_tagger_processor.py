"""Pipecat ``FrameProcessor`` that tags Boxi's reply sentence-by-sentence (P14 Phase 4, form B).

Sits between ``CompanionBrainProcessor`` and the TTS service. The brain streams plain
``LLMTextFrame`` deltas; this processor re-aggregates them into sentences, sends each finished
sentence to the dedicated expression tagger (Gemini), and pushes the *tagged* sentence
downstream (as an ``AggregatedTextFrame`` so the TTS service synthesises it immediately
instead of re-buffering it behind its own sentence-boundary lookahead) so TTS speaks it
with Fish Audio tags.

Concurrent pre-tagging: each sentence's tagger call is kicked off (as an asyncio Task) the
instant the sentence is split off the stream — they run in parallel — while an ordered drain
loop awaits them in sentence order and pushes each as soon as it's ready. So while sentence 1
plays, sentences 2..N are already being tagged; by the time sentence 1's audio ends the next
tagged sentence is usually ready, keeping playback dense instead of stalling one tagger
round-trip per sentence boundary.

Form B / OQ decisions (see docs/HANDOFF.md "P14 Phase 4 拆解"):
- OQ1 = simplified variant: the brain no longer tags itself (P2). With ``tag_first_sentence``
  False (default), the first content sentence skips the tagger so first audio isn't delayed by
  a round-trip; every other sentence is tagged.
- OQ2 = "整段已说": each sentence is tagged with all already-streamed sentences of the current
  reply as ``prior_context`` (for tone continuity), capped by ``prior_context_char_cap``.
- OQ3 = Gemini (the tagger's default provider).

Hard requirement (inherited from the tagger): any tagger failure degrades to the plain
sentence — it must never break or stall the turn.
"""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from pipecat.frames.frames import (
    AggregatedTextFrame,
    AggregationType,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter
from backend.app.tts.expression_tagger import (
    DEFAULT_TAGGER_PROVIDER,
    _has_taggable_content,
    apply_expression_tags_to_sentence,
)

# Streaming-splitter sentence terminators. Derived from the offline tag_stats yardstick but
# WITH "…" removed: in conversational Chinese an ellipsis is almost always a *mid-utterance
# pause*, not an end of sentence (the brain writes "还是只是单纯地…羡慕那个时候的自己？" as one
# thought). Splitting on it fragments that single sentence into a grammatically-incomplete
# standalone Fish request ("……单纯地" with nothing after it), which is what makes Fish improvise
# filler audio over the broken fragment (real-machine repro, 2026-06-25). The tag_stats set keeps
# "…" — over-splitting only ever lowers its degradation false-positives — so the two are
# deliberately decoupled here for their different purposes.
from backend.app.tts.tag_stats import _TERMINATORS as _STATS_TERMINATORS

SENTENCE_TERMINATORS = _STATS_TERMINATORS - {"…"}

_DEFAULT_PRIOR_CONTEXT_CHAR_CAP = 800


def split_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """Split ``buffer`` into (complete sentences, trailing remainder).

    A sentence runs up to and including a *run* of consecutive terminator chars (e.g. "。\n" or
    "！？") so they stay attached to the sentence they end instead of each char cutting its own
    boundary — a naive per-char cut would strand a content-less fragment that still gets sent to
    Fish as its own flushed request. Note ``SENTENCE_TERMINATORS`` excludes "…" (see its comment),
    so a mid-utterance ellipsis does not split a sentence. The remainder is whatever follows the
    last terminator run (an in-progress sentence with no terminator yet). Pure + side-effect free
    so it can be unit-tested without a pipeline.
    """
    sentences: list[str] = []
    start = 0
    index = 0
    length = len(buffer)
    while index < length:
        if buffer[index] in SENTENCE_TERMINATORS:
            end = index
            while end < length and buffer[end] in SENTENCE_TERMINATORS:
                end += 1
            sentences.append(buffer[start:end])
            start = end
            index = end
        else:
            index += 1
    return sentences, buffer[start:]


def build_prior_context(spoken_sentences: list[str], char_cap: int) -> str:
    """Join already-spoken sentences for ``prior_context``, keeping the most recent within cap.

    "整段已说" (OQ2) with a length guard: if the full prefix fits in ``char_cap`` use all of it,
    otherwise fall back to the most recent sentences that fit. Pure + unit-testable.
    """
    if not spoken_sentences:
        return ""
    joined = "".join(spoken_sentences)
    if len(joined) <= char_cap:
        return joined
    kept: list[str] = []
    total = 0
    for sentence in reversed(spoken_sentences):
        kept.append(sentence)
        total += len(sentence)
        if total >= char_cap:
            break
    return "".join(reversed(kept))


_DRAIN_SENTINEL = object()


class ExpressionTaggerProcessor(FrameProcessor):
    """Re-aggregates brain deltas into sentences, tags them concurrently, releases them in order."""

    def __init__(
        self,
        *,
        store: MemoryStore,
        router: ProviderRouter,
        provider_name: str = DEFAULT_TAGGER_PROVIDER,
        prior_context_char_cap: int = _DEFAULT_PRIOR_CONTEXT_CHAR_CAP,
        tag_first_sentence: bool = False,
    ) -> None:
        super().__init__()
        self._store = store
        self._router = router
        self._provider_name = provider_name
        self._char_cap = prior_context_char_cap
        # Asymmetric / latency lever (OQ1 fallback): when False, the first content sentence
        # skips the tagger and goes straight to TTS so first audio isn't delayed by a tagger
        # round-trip (~1-2s). Set True to tag every sentence (uniform, but the opening costs
        # one tagger call of latency).
        self._tag_first_sentence = tag_first_sentence
        self._buffer = ""
        self._plain_so_far: list[str] = []
        self._collecting = False
        self._first_content_emitted = False
        # Bumped on every turn start AND every interruption. A scheduled sentence captures it; the
        # drainer drops any sentence whose turn_id no longer matches (interruption/new turn race).
        self._turn_id = 0
        self._mood = None
        # Concurrent pre-tagging: each sentence's tagger Task is started immediately and parked on
        # the queue; a single per-turn drainer awaits them in order and pushes them downstream.
        self._queue: asyncio.Queue | None = None
        self._drain_task: asyncio.Task | None = None
        self._inflight: list[asyncio.Task] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._begin_turn()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InterruptionFrame):
            # Invalidate any in-flight tagger calls + drainer and drop the partial sentence.
            await self._abort_turn()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMTextFrame) and self._collecting:
            # Replace the raw delta stream with tagged whole-sentence frames. Each finished
            # sentence is scheduled for tagging right away (concurrent); the drainer pushes them.
            self._buffer += frame.text
            sentences, self._buffer = split_complete_sentences(self._buffer)
            for sentence in sentences:
                self._schedule(sentence)
            return

        if isinstance(frame, LLMFullResponseEndFrame) and self._collecting:
            tail, self._buffer = self._buffer, ""
            self._collecting = False
            if tail.strip():
                self._schedule(tail)
            # Flush every queued sentence (in order) before letting the End frame past, so the
            # downstream sees Start → all tagged sentences → End.
            await self._finish_turn()
            await self.push_frame(frame, direction)
            return

        await self.push_frame(frame, direction)

    def _begin_turn(self) -> None:
        self._turn_id += 1
        self._buffer = ""
        self._plain_so_far = []
        self._collecting = True
        self._first_content_emitted = False
        self._inflight = []
        self._queue = asyncio.Queue()
        self._drain_task = asyncio.create_task(self._drain(self._queue))
        try:
            self._mood = self._store.get_mood_state()
        except Exception as error:  # pragma: no cover - defensive, must never break the turn
            logger.warning(f"ExpressionTaggerProcessor: failed to load mood ({error}); tagging without mood block")
            self._mood = None

    def _schedule(self, sentence: str) -> None:
        """Start tagging ``sentence`` concurrently and park it on the queue for ordered release."""
        if self._queue is None:
            return
        if not _has_taggable_content(sentence):
            # Pure punctuation/whitespace fragment (e.g. a stray terminator run that still slips
            # through the splitter) — nothing to say. Forwarding it would send Fish a content-less
            # request to flush, which is exactly the shape that makes it hallucinate filler audio
            # over the "finished" utterance (real-machine repro, 2026-06-25). Drop it instead.
            return
        turn_id = self._turn_id
        # Asymmetric latency lever: let the first content sentence out untagged (fast first audio).
        skip_first = not self._first_content_emitted and not self._tag_first_sentence
        self._first_content_emitted = True
        # prior_context is "everything streamed so far in this reply" — known at split time, so we
        # build it now (not when the tagger result lands) to keep it deterministic under concurrency.
        prior = build_prior_context(self._plain_so_far, self._char_cap)
        self._plain_so_far.append(sentence)
        task = asyncio.create_task(self._compute_tagged(sentence, prior, skip_first=skip_first))
        self._inflight.append(task)
        self._queue.put_nowait((turn_id, sentence, task))

    async def _compute_tagged(self, sentence: str, prior: str, *, skip_first: bool) -> str:
        """Return the tagged sentence (or the plain sentence on skip / no-mood / failure)."""
        if skip_first:
            logger.info(f"🏷️  tagger[skip-first] {sentence!r}")
            return sentence
        if self._mood is None:
            logger.info(f"🏷️  tagger[no-mood] {sentence!r}")
            return sentence
        if not _has_taggable_content(sentence):
            return sentence
        started = time.monotonic()
        tagged = await asyncio.to_thread(
            apply_expression_tags_to_sentence,
            sentence,
            self._mood,
            prior_context=prior,
            router=self._router,
            provider_name=self._provider_name,
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info(f"🏷️  tagger {elapsed_ms:.0f}ms | {sentence!r} -> {tagged!r}")
        return tagged

    async def _drain(self, queue: asyncio.Queue) -> None:
        """Await tagger Tasks in sentence order and push each tagged sentence downstream."""
        while True:
            item = await queue.get()
            if item is _DRAIN_SENTINEL:
                return
            turn_id, sentence, task = item
            try:
                tagged = await task
            except asyncio.CancelledError:
                raise
            except Exception as error:  # pragma: no cover - tagger already degrades internally
                logger.warning(f"ExpressionTaggerProcessor: tagging task failed ({error}); using plain sentence")
                tagged = sentence
            # Interrupted or a new turn started while we were tagging → this sentence is stale.
            if turn_id != self._turn_id:
                continue
            # Push as a *pre-aggregated* frame so TTS synthesises it immediately (tts_service.py
            # routes AggregatedTextFrame straight to _push_tts_frames). A plain LLMTextFrame would
            # re-enter the built-in SimpleTextAggregator, whose sentence-boundary lookahead holds
            # each sentence until the *next* sentence's first char arrives — i.e. until the next
            # tagger round-trip finishes — adding that latency to first audio. raw_text carries the
            # un-tagged sentence so TTS-internal context aggregation / word timestamps see clean text.
            text_frame = AggregatedTextFrame(tagged, AggregationType.SENTENCE, raw_text=sentence)
            text_frame.includes_inter_frame_spaces = True
            await self.push_frame(text_frame)

    async def _finish_turn(self) -> None:
        """Signal end-of-turn and wait for the drainer to flush every queued sentence."""
        if self._queue is None or self._drain_task is None:
            return
        self._queue.put_nowait(_DRAIN_SENTINEL)
        try:
            await self._drain_task
        except asyncio.CancelledError:  # pragma: no cover - only if aborted concurrently
            pass
        self._queue = None
        self._drain_task = None
        self._inflight = []

    async def _abort_turn(self) -> None:
        """Cancel the drainer + all in-flight tagger Tasks and drop any partial sentence."""
        self._turn_id += 1  # bump first so any push in flight sees the stale turn_id and drops
        self._buffer = ""
        self._collecting = False
        for task in self._inflight:
            task.cancel()
        if self._drain_task is not None:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        self._queue = None
        self._drain_task = None
        self._inflight = []
