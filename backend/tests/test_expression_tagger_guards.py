"""Code-level position/format guards (task 2): malformed-tag normalization + [break] guard.

These enforce tag legality only (format + obviously-wrong placement), never emotion
appropriateness. Every guard touches only ``[tags]``; original wording is never changed.
"""

from __future__ import annotations

import pytest

from backend.app.memory.database import MoodStateRecord
from backend.app.tts.expression_tagger import (
    _normalize_break_tags,
    _normalize_malformed_tags,
    _normalize_tag_placement,
    apply_expression_tags,
    apply_expression_tags_to_sentence,
)


def _mood(**overrides: float | str) -> MoodStateRecord:
    base = dict(
        updated_at="2026-06-25T00:00:00+00:00",
        mood="idle",
        energy=0.5,
        annoyance=0.0,
        boredom=0.0,
        worry=0.0,
        trust=0.5,
        loneliness=0.0,
    )
    base.update(overrides)
    return MoodStateRecord(**base)  # type: ignore[arg-type]


class _FakeRouter:
    """Returns a fixed tagger ``content`` so we can assert guards run on the way out."""

    def __init__(self, *, content: str) -> None:
        self._content = content

    def complete(self, request, *, provider_name=None):  # type: ignore[no-untyped-def]
        from backend.app.providers.types import ChatCompletionResult, CostEstimate, TokenUsage

        return ChatCompletionResult(
            provider="fake",
            model="fake-model",
            content=self._content,
            usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            cost=CostEstimate(input_usd=0.0, output_usd=0.0, total_usd=0.0, pricing_source="test"),
            mock=True,
        )


# --- P0 · malformed tag normalization --------------------------------------------------


def test_normalize_strips_inner_whitespace() -> None:
    assert _normalize_malformed_tags("[ sighing ] 我不知道") == "[sighing] 我不知道"


def test_normalize_collapses_internal_double_space() -> None:
    assert _normalize_malformed_tags("[soft  tone]你好") == "[soft tone]你好"


@pytest.mark.parametrize("empty_tag", ["[]你好", "[   ]你好", "[\t]你好"])
def test_normalize_drops_empty_tag(empty_tag: str) -> None:
    assert _normalize_malformed_tags(empty_tag) == "你好"


def test_normalize_leaves_well_formed_tags_untouched() -> None:
    assert _normalize_malformed_tags("[happy]晚上好[whispering]，想我了吗") == (
        "[happy]晚上好[whispering]，想我了吗"
    )


def test_normalize_fixes_multiple_malformed_tags() -> None:
    assert _normalize_malformed_tags("[ happy ]你好[ sad ]再见") == "[happy]你好[sad]再见"


def test_normalize_does_not_change_wording() -> None:
    # Only brackets are rewritten; the spoken text is identical.
    result = _normalize_malformed_tags("[ excited ]今天天气真好啊！")
    assert result.replace("[excited]", "") == "今天天气真好啊！"


# --- P1 · [break] redundancy + density -------------------------------------------------


def test_break_adjacent_to_trailing_punctuation_is_stripped() -> None:
    assert _normalize_break_tags("我想想[break]。") == "我想想。"


def test_break_adjacent_to_leading_punctuation_is_stripped() -> None:
    assert _normalize_break_tags("。[break]然后呢") == "。然后呢"


def test_long_break_adjacent_to_punctuation_is_stripped() -> None:
    assert _normalize_break_tags("好的[long-break]，再说") == "好的，再说"


def test_lone_mid_clause_break_is_preserved() -> None:
    # A single break inside a flowing clause (no punctuation neighbour) is a legal dramatic
    # pause — placement is the LLM's call, so we leave it alone.
    assert _normalize_break_tags("想让我[break]再卖个关子") == "想让我[break]再卖个关子"


def test_multiple_breaks_keep_only_the_first() -> None:
    assert _normalize_break_tags("我[break]想[break]说[break]点什么") == "我[break]想说点什么"


def test_redundant_break_does_not_consume_density_budget() -> None:
    # The first break is redundant (before "。") → dropped; the later mid-clause break is the
    # first *kept* one and survives the density cap.
    assert _normalize_break_tags("好的。[break]那[break]我们走") == "好的。那[break]我们走"


def test_break_guard_ignores_non_break_tags() -> None:
    assert _normalize_break_tags("[whispering]，你好[sighing]") == "[whispering]，你好[sighing]"


def test_break_guard_noop_when_no_breaks() -> None:
    assert _normalize_break_tags("[happy]晚上好啊") == "[happy]晚上好啊"


# --- composition order (malformed runs before break detection) -------------------------


def test_placement_normalizes_then_strips_malformed_break() -> None:
    # "[ break ]" must be normalized first so the break guard recognizes it as a pause tag.
    assert _normalize_tag_placement("好的[ break ]。") == "好的。"


def test_placement_is_idempotent_on_clean_text() -> None:
    clean = "[happy]晚上好啊，[whispering]想我了吗"
    assert _normalize_tag_placement(clean) == clean


# --- wiring · guards reach the public tagger return paths -------------------------------


def test_apply_expression_tags_runs_placement_guards() -> None:
    router = _FakeRouter(content="[ happy ]今天[break]，真开心！")

    result = apply_expression_tags("今天，真开心！", _mood(), router=router)  # type: ignore[arg-type]

    # malformed [ happy ] normalized; [break] sitting before "，" is redundant → stripped.
    assert result == "[happy]今天，真开心！"


def test_apply_expression_tags_to_sentence_runs_placement_guards() -> None:
    router = _FakeRouter(content="我想想[break]，[ soft  tone ]别急")

    result = apply_expression_tags_to_sentence(
        "我想想，别急", _mood(), router=router  # type: ignore[arg-type]
    )

    # redundant [break] before "，" stripped; malformed [ soft  tone ] normalized.
    assert result == "我想想，[soft tone]别急"
