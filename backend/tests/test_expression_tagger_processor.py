from __future__ import annotations

import pytest

pytest.importorskip("pipecat")

from backend.realtime.expression_tagger_processor import (
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
