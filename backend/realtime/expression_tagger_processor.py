"""Pipecat ``FrameProcessor`` that tags Boxi's reply sentence-by-sentence (P14 Phase 4, form B).

Sits between ``CompanionBrainProcessor`` and the TTS service. The brain streams plain
``LLMTextFrame`` deltas; this processor re-aggregates them into sentences, sends each finished
sentence to the dedicated expression tagger (Gemini), and pushes the *tagged* sentence
downstream so TTS speaks it with Fish Audio tags.

Form B / OQ decisions (see docs/HANDOFF.md "P14 Phase 4 拆解"):
- OQ1 = simplified variant: *every* sentence (including the first) goes through the tagger;
  the brain no longer tags itself (P2). The only un-hidden latency is the tagger call before
  the very first sentence; later sentences' tagger calls overlap with earlier playback.
- OQ2 = "整段已说": each sentence is tagged with all already-spoken sentences of the current
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

# Reuse the exact terminator set the offline tag_stats yardstick splits on, so streaming
# segmentation and the degradation metrics agree on what counts as a sentence boundary.
from backend.app.tts.tag_stats import _TERMINATORS as SENTENCE_TERMINATORS

_DEFAULT_PRIOR_CONTEXT_CHAR_CAP = 800


def split_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """Split ``buffer`` into (complete sentences, trailing remainder).

    A sentence runs up to and including a terminator char. The remainder is whatever follows
    the last terminator (an in-progress sentence with no terminator yet). Pure + side-effect
    free so it can be unit-tested without a pipeline.
    """
    sentences: list[str] = []
    start = 0
    for index, char in enumerate(buffer):
        if char in SENTENCE_TERMINATORS:
            sentences.append(buffer[start : index + 1])
            start = index + 1
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


class ExpressionTaggerProcessor(FrameProcessor):
    """Re-aggregates brain deltas into sentences and tags each one before it reaches TTS."""

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
        # round-trip (~1-2s). Later sentences are tagged, overlapping with playback. Set True
        # to tag every sentence (uniform, but the opening costs one tagger call of latency).
        self._tag_first_sentence = tag_first_sentence
        self._buffer = ""
        self._spoken: list[str] = []
        self._collecting = False
        self._first_content_emitted = False
        # Bumped on every turn start AND every interruption. A tagger call captures it before
        # awaiting and drops its (now-stale) result if it changed during the await.
        self._turn_id = 0
        self._mood = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._begin_turn()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InterruptionFrame):
            # Invalidate any in-flight tagger call and drop the partial sentence.
            self._turn_id += 1
            self._buffer = ""
            self._collecting = False
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMTextFrame) and self._collecting:
            # Replace the raw delta stream with tagged whole-sentence frames.
            self._buffer += frame.text
            sentences, self._buffer = split_complete_sentences(self._buffer)
            for sentence in sentences:
                await self._tag_and_push(sentence)
            return

        if isinstance(frame, LLMFullResponseEndFrame) and self._collecting:
            tail, self._buffer = self._buffer, ""
            self._collecting = False
            if tail.strip():
                await self._tag_and_push(tail)
            await self.push_frame(frame, direction)
            return

        await self.push_frame(frame, direction)

    def _begin_turn(self) -> None:
        self._turn_id += 1
        self._buffer = ""
        self._spoken = []
        self._collecting = True
        self._first_content_emitted = False
        try:
            self._mood = self._store.get_mood_state()
        except Exception as error:  # pragma: no cover - defensive, must never break the turn
            logger.warning(f"ExpressionTaggerProcessor: failed to load mood ({error}); tagging without mood block")
            self._mood = None

    async def _tag_and_push(self, sentence: str) -> None:
        turn_id = self._turn_id
        is_content = _has_taggable_content(sentence)
        # Asymmetric latency lever: let the first content sentence out untagged (fast first
        # audio); tag the rest. With tag_first_sentence=True every content sentence is tagged.
        skip_first = is_content and not self._first_content_emitted and not self._tag_first_sentence
        if is_content:
            self._first_content_emitted = True

        if skip_first:
            tagged = sentence
            logger.info(f"🏷️  tagger[skip-first] {sentence!r}")
        elif self._mood is None:
            tagged = sentence
            logger.info(f"🏷️  tagger[no-mood] {sentence!r}")
        else:
            prior = build_prior_context(self._spoken, self._char_cap)
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

        # Interrupted or a new turn started while we were tagging → this sentence is stale.
        if turn_id != self._turn_id:
            return

        if sentence.strip():
            self._spoken.append(sentence)

        # Push the tagged sentence as a *pre-aggregated* frame so the TTS service treats it as a
        # finished sentence and synthesises it immediately (tts_service.py routes AggregatedTextFrame
        # straight to _push_tts_frames). A plain LLMTextFrame would instead re-enter the built-in
        # SimpleTextAggregator, whose sentence-boundary lookahead holds each sentence until the *next*
        # sentence's first char arrives — i.e. until the next tagger round-trip finishes — adding that
        # latency to first audio. raw_text carries the un-tagged sentence so TTS-internal context
        # aggregation / word timestamps see clean text without the [tags].
        text_frame = AggregatedTextFrame(tagged, AggregationType.SENTENCE, raw_text=sentence)
        text_frame.includes_inter_frame_spaces = True
        await self.push_frame(text_frame)
