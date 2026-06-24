from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("pipecat")

import backend.realtime.expression_tagger_processor as proc_mod
from backend.realtime.expression_tagger_processor import (
    ExpressionTaggerProcessor,
    build_prior_context,
    split_complete_sentences,
)


# --- split_complete_sentences -----------------------------------------------------------


def test_split_returns_no_sentences_when_no_terminator() -> None:
    sentences, remainder = split_complete_sentences("还没说完的半句")

    assert sentences == []
    assert remainder == "还没说完的半句"


def test_split_extracts_complete_sentences_and_keeps_remainder() -> None:
    sentences, remainder = split_complete_sentences("第一句。第二句！还在写")

    assert sentences == ["第一句。", "第二句！"]
    assert remainder == "还在写"


def test_split_consumes_everything_when_buffer_ends_on_terminator() -> None:
    sentences, remainder = split_complete_sentences("说完了？")

    assert sentences == ["说完了？"]
    assert remainder == ""


def test_split_handles_mixed_and_ascii_terminators() -> None:
    # _TERMINATORS includes 。！？!?…\n. — newline and ascii period both end a sentence.
    sentences, remainder = split_complete_sentences("ok.\n下一句…尾巴")

    assert sentences == ["ok.", "\n", "下一句…"]
    assert remainder == "尾巴"


# --- build_prior_context ----------------------------------------------------------------


def test_prior_context_empty_when_nothing_spoken() -> None:
    assert build_prior_context([], char_cap=800) == ""


def test_prior_context_returns_full_prefix_within_cap() -> None:
    spoken = ["第一句。", "第二句。"]

    assert build_prior_context(spoken, char_cap=800) == "第一句。第二句。"


def test_prior_context_keeps_most_recent_sentences_when_over_cap() -> None:
    spoken = ["AAAA。", "BBBB。", "CCCC。"]  # each 5 chars, 15 total

    # cap=6 → walking back from the end, "CCCC。" (5) then "BBBB。" (10 ≥ 6) → keep last two.
    result = build_prior_context(spoken, char_cap=6)

    assert result == "BBBB。CCCC。"
    assert "AAAA。" not in result


def test_prior_context_keeps_only_last_sentence_when_one_already_exceeds_cap() -> None:
    spoken = ["短。", "这是一句很长很长很长的话。"]

    result = build_prior_context(spoken, char_cap=3)

    assert result == "这是一句很长很长很长的话。"


# --- concurrent pre-tagging: ordered release --------------------------------------------


class _FakeStore:
    def get_mood_state(self):  # noqa: ANN201 - mood is opaque to the fake tagger below
        return object()


def test_drainer_releases_sentences_in_order_despite_out_of_order_tagging() -> None:
    """Tagger calls finish out of order (s1 slowest, s3 fastest) but must be pushed s1→s2→s3."""
    sentences = ["第一句。", "第二句。", "第三句。"]
    # Earlier sentences sleep LONGER so their tagger Tasks complete last — if release order
    # followed completion order it would come out reversed.
    delays = {"第一句。": 0.06, "第二句。": 0.03, "第三句。": 0.0}

    def fake_tagger(sentence, mood, *, prior_context, router, provider_name):  # noqa: ANN001, ANN202
        time.sleep(delays[sentence])  # runs in the to_thread executor, so concurrency is real
        return f"[t] {sentence}"

    async def run() -> list[str]:
        pushed: list[str] = []
        processor = ExpressionTaggerProcessor(
            store=_FakeStore(),
            router=object(),
            tag_first_sentence=True,  # tag every sentence so all three race
        )

        async def capture(frame, direction=None):  # noqa: ANN001, ANN202
            pushed.append(frame.text)

        processor.push_frame = capture  # type: ignore[assignment]

        processor._begin_turn()
        for sentence in sentences:
            processor._schedule(sentence)
        await processor._finish_turn()
        return pushed

    monkey = pytest.MonkeyPatch()
    monkey.setattr(proc_mod, "apply_expression_tags_to_sentence", fake_tagger)
    try:
        pushed = asyncio.run(run())
    finally:
        monkey.undo()

    assert pushed == ["[t] 第一句。", "[t] 第二句。", "[t] 第三句。"]


def test_abort_turn_drops_inflight_sentences() -> None:
    """An interruption mid-turn must cancel in-flight tagging and push nothing for that turn."""
    def slow_tagger(sentence, mood, *, prior_context, router, provider_name):  # noqa: ANN001, ANN202
        time.sleep(0.2)
        return f"[t] {sentence}"

    async def run() -> list[str]:
        pushed: list[str] = []
        processor = ExpressionTaggerProcessor(
            store=_FakeStore(), router=object(), tag_first_sentence=True
        )

        async def capture(frame, direction=None):  # noqa: ANN001, ANN202
            pushed.append(frame.text)

        processor.push_frame = capture  # type: ignore[assignment]

        processor._begin_turn()
        processor._schedule("会被打断的一句。")
        await asyncio.sleep(0)  # let the tagging Task start
        await processor._abort_turn()  # interruption before tagging finishes
        await asyncio.sleep(0.25)  # past the tagger sleep — nothing should have been pushed
        return pushed

    monkey = pytest.MonkeyPatch()
    monkey.setattr(proc_mod, "apply_expression_tags_to_sentence", slow_tagger)
    try:
        pushed = asyncio.run(run())
    finally:
        monkey.undo()

    assert pushed == []
