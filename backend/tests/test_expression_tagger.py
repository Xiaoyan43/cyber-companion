from __future__ import annotations

import pytest

from backend.app.memory.database import MoodStateRecord
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, CostEstimate, TokenUsage
from backend.app.tts.expression_tagger import (
    DEFAULT_TAGGER_PROVIDER,
    TAGGER_INSTRUCTION_TEMPLATE,
    apply_expression_tags,
    apply_expression_tags_to_sentence,
)


def _mood(**overrides: float | str) -> MoodStateRecord:
    base = dict(
        updated_at="2026-06-20T00:00:00+00:00",
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
    def __init__(self, *, content: str | None = None, error: Exception | None = None) -> None:
        self._content = content
        self._error = error
        self.captured_request: ChatCompletionRequest | None = None
        self.captured_provider_name: str | None = None

    def complete(
        self,
        request: ChatCompletionRequest,
        *,
        provider_name: str | None = None,
    ) -> ChatCompletionResult:
        self.captured_request = request
        self.captured_provider_name = provider_name
        if self._error is not None:
            raise self._error
        return ChatCompletionResult(
            provider="fake",
            model="fake-model",
            content=self._content or "",
            usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            cost=CostEstimate(input_usd=0.0, output_usd=0.0, total_usd=0.0, pricing_source="test"),
            mock=True,
        )


def test_apply_expression_tags_returns_tagged_text_from_provider() -> None:
    router = _FakeRouter(content="你又这样[sighing]，真是拿你没办法。")

    result = apply_expression_tags("你又这样，真是拿你没办法。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "你又这样[sighing]，真是拿你没办法。"


def test_apply_expression_tags_falls_back_on_provider_error() -> None:
    router = _FakeRouter(error=ProviderError("boom", provider="deepseek"))

    result = apply_expression_tags("原文不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原文不变。"


def test_apply_expression_tags_falls_back_on_unexpected_error() -> None:
    router = _FakeRouter(error=RuntimeError("unexpected"))

    result = apply_expression_tags("原文不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原文不变。"


def test_apply_expression_tags_falls_back_on_empty_result() -> None:
    router = _FakeRouter(content="   ")

    result = apply_expression_tags("原文不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原文不变。"


def test_apply_expression_tags_falls_back_when_tagger_changes_wording() -> None:
    # Regression: tagger rewrote a word instead of only inserting tags ("你呢" → "我呢"),
    # which would make TTS speak something Boxi never wrote. Reject altered output.
    router = _FakeRouter(content="[curious] 我呢，最爱哪一部？")

    result = apply_expression_tags("你呢，最爱哪一部？", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "你呢，最爱哪一部？"


def test_apply_expression_tags_accepts_tags_only_insertion() -> None:
    # Whitespace around inserted tags is fine — only words/punctuation must be preserved.
    router = _FakeRouter(content="你呢， [curious] 最爱哪一部？")

    result = apply_expression_tags("你呢，最爱哪一部？", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "你呢， [curious] 最爱哪一部？"


def test_apply_expression_tags_skips_provider_call_when_input_blank() -> None:
    router = _FakeRouter(content="should not be used")

    result = apply_expression_tags("   ", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "   "
    assert router.captured_request is None


def test_apply_expression_tags_uses_default_provider_name() -> None:
    router = _FakeRouter(content="带标签的文本")

    apply_expression_tags("原文", _mood(), router=router)  # type: ignore[arg-type]

    assert router.captured_provider_name == DEFAULT_TAGGER_PROVIDER == "tagger"


def test_apply_expression_tags_allows_provider_override() -> None:
    router = _FakeRouter(content="带标签的文本")

    apply_expression_tags("原文", _mood(), router=router, provider_name="deepseek")  # type: ignore[arg-type]

    assert router.captured_provider_name == "deepseek"


def test_apply_expression_tags_passes_mood_and_text_into_prompt() -> None:
    router = _FakeRouter(content="带标签的文本")
    mood = _mood(mood="annoyed", annoyance=0.8)

    apply_expression_tags("用户刚才说的话", mood, router=router)  # type: ignore[arg-type]

    assert router.captured_request is not None
    system_message, user_message = router.captured_request.messages
    assert system_message.role == "system"
    assert "mood=annoyed" in system_message.content
    assert "annoyance=0.80" in system_message.content
    assert user_message.role == "user"
    assert user_message.content == "用户刚才说的话"


@pytest.mark.parametrize(
    "expected_phrase",
    [
        "不改变原文一个字",
        "每句话默认不加标签",  # Rule 3: per-sentence judgment; old "逐句重新判断" rewritten
        "[sighing]",
        "[whispering]",
        "音效/生理反应类",
    ],
)
def test_tagger_instruction_contains_core_rules(expected_phrase: str) -> None:
    assert expected_phrase in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_has_no_hard_tag_count_quota() -> None:
    assert "至少一次" not in TAGGER_INSTRUCTION_TEMPLATE
    assert "硬性要求" not in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_allows_freeform_fallback_when_no_exact_vocab_match() -> None:
    # Round-trip regression: a strict-vocab-only version caused near-total under-tagging
    # on emotionally loaded but vocab-mismatched content (teasing/commanding tone has no
    # exact word in the fixed list) — reopened controlled freeform fallback to fix it.
    assert "可在语义合理范围内自行扩展" in TAGGER_INSTRUCTION_TEMPLATE
    assert "不要因为没有完美对应词就放弃" in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_does_not_force_english_only_tags() -> None:
    # Regression: an earlier "tags must be English" rule contradicted
    # docs/FISH_AUDIO_REFERENCE.md §2, which documents that S2-Pro tags can match the
    # script language (Chinese tags are officially supported, not just an English seed list).
    assert "必须用英文方括号写" not in TAGGER_INSTRUCTION_TEMPLATE
    assert "跟正文语言保持一致" in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_keeps_official_physio_emotion_combo_example() -> None:
    # docs/FISH_AUDIO_REFERENCE.md §4.3 explicitly recommends pairing a physio tag with an
    # emotion tag back-to-back (e.g. [panting][tired]) — this was dropped during an earlier
    # rewrite of rule 5 and is restored here as an exception to the no-stacking rule.
    assert "[panting] [tired]" in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_prefers_mid_sentence_tone_start_for_b_tags() -> None:
    # B-class tone/emotion tags should mark the start of the emotional span, not lazily dye
    # the whole sentence from the first character.
    assert "语气/情绪/音调类标签也不要偷懒全放句首" in TAGGER_INSTRUCTION_TEMPLATE
    assert "转折词或情绪起点前" in TAGGER_INSTRUCTION_TEMPLATE
    assert "只有整句话从第一个字开始" in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_contains_mid_sentence_b_tag_examples() -> None:
    assert "我嘴上嫌你烦，[soft tone]不过还是给你留了灯" in TAGGER_INSTRUCTION_TEMPLATE
    assert "我今天去了那家店，[sad]后来才发现你不在" in TAGGER_INSTRUCTION_TEMPLATE


# --- dangling trailing tag guardrail (省略号幻觉) ----------------------------------------


def test_apply_expression_tags_strips_dangling_trailing_tag_after_ellipsis() -> None:
    # Fish hallucinates a sound for a tag with no text after it ("我不知道…[sighing]" — a sigh
    # over an empty span). Such tail tags must be stripped before reaching TTS.
    router = _FakeRouter(content="我不知道…[sighing]")

    result = apply_expression_tags("我不知道…", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "我不知道…"


def test_apply_expression_tags_strips_tag_stranded_before_trailing_ellipsis() -> None:
    # A tag sitting just before a trailing "……" also has an empty span.
    router = _FakeRouter(content="我不知道[sighing]……")

    result = apply_expression_tags("我不知道……", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "我不知道……"


def test_apply_expression_tags_keeps_tag_with_words_after_it() -> None:
    # A leading tag whose span still covers real words is legitimate — leave it alone.
    router = _FakeRouter(content="[sad]我不知道…我也不想这样。")

    result = apply_expression_tags("我不知道…我也不想这样。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "[sad]我不知道…我也不想这样。"


def test_apply_expression_tags_strips_only_trailing_dangling_tag_keeps_inner() -> None:
    # Strip the dangling tail tag, keep the inner one that still has words after it.
    router = _FakeRouter(content="[sad]我不知道[sighing]…")

    result = apply_expression_tags("我不知道…", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "[sad]我不知道…"


def test_apply_expression_tags_strips_multiple_trailing_dangling_tags() -> None:
    # A run of back-to-back tags at the tail (all with empty spans) is fully stripped.
    router = _FakeRouter(content="我不知道…[sad][sighing]")

    result = apply_expression_tags("我不知道…", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "我不知道…"


def test_apply_expression_tags_to_sentence_strips_dangling_trailing_tag() -> None:
    # Same guardrail on the streaming voice path (where the hallucination was heard live).
    router = _FakeRouter(content="我不知道…[sighing]")

    result = apply_expression_tags_to_sentence("我不知道…", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "我不知道…"


# --- streaming per-sentence variant (P14 Phase 4, form B) -------------------------------


def test_apply_expression_tags_to_sentence_returns_tagged_sentence() -> None:
    router = _FakeRouter(content="进来吧[laughing]，挤一挤还是能装下你的。")

    result = apply_expression_tags_to_sentence(
        "进来吧，挤一挤还是能装下你的。", _mood(), router=router  # type: ignore[arg-type]
    )

    assert result == "进来吧[laughing]，挤一挤还是能装下你的。"


def test_apply_expression_tags_to_sentence_falls_back_on_provider_error() -> None:
    router = _FakeRouter(error=ProviderError("boom", provider="tagger"))

    result = apply_expression_tags_to_sentence("原句不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原句不变。"


def test_apply_expression_tags_to_sentence_falls_back_on_unexpected_error() -> None:
    router = _FakeRouter(error=RuntimeError("unexpected"))

    result = apply_expression_tags_to_sentence("原句不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原句不变。"


def test_apply_expression_tags_to_sentence_falls_back_on_empty_result() -> None:
    router = _FakeRouter(content="   ")

    result = apply_expression_tags_to_sentence("原句不变。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "原句不变。"


def test_apply_expression_tags_to_sentence_falls_back_when_tagger_changes_wording() -> None:
    # Same fidelity guard as the whole-text path: a word substitution ("你呢" → "我呢") must
    # be rejected so TTS never speaks words Boxi didn't write.
    router = _FakeRouter(content="[curious] 我呢，最爱哪一部？")

    result = apply_expression_tags_to_sentence("你呢，最爱哪一部？", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "你呢，最爱哪一部？"


def test_apply_expression_tags_to_sentence_skips_provider_call_when_input_blank() -> None:
    router = _FakeRouter(content="should not be used")

    result = apply_expression_tags_to_sentence("   ", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "   "
    assert router.captured_request is None


@pytest.mark.parametrize("fragment", ["…", "……", "。！？", "...", "、"])
def test_apply_expression_tags_to_sentence_skips_punctuation_only_fragments(fragment: str) -> None:
    # Regression: a bare "…" (from splitting "……") sent to the tagger made it hallucinate
    # words to tag (e.g. "[sighing] 我不知道。"), which TTS would then speak. Punctuation-only
    # fragments must pass through untouched without an LLM call.
    router = _FakeRouter(content="should not be used")

    result = apply_expression_tags_to_sentence(fragment, _mood(), router=router)  # type: ignore[arg-type]

    assert result == fragment
    assert router.captured_request is None


def test_apply_expression_tags_to_sentence_uses_tagger_by_default() -> None:
    router = _FakeRouter(content="带标签的句子")

    apply_expression_tags_to_sentence("一句话", _mood(), router=router)  # type: ignore[arg-type]

    assert router.captured_provider_name == DEFAULT_TAGGER_PROVIDER == "tagger"


def test_apply_expression_tags_to_sentence_omits_prior_context_message_when_empty() -> None:
    router = _FakeRouter(content="带标签的句子")

    apply_expression_tags_to_sentence("一句话", _mood(), router=router)  # type: ignore[arg-type]

    assert router.captured_request is not None
    # No prior context → only the rules system prompt + the user sentence, no extra message.
    assert len(router.captured_request.messages) == 2
    system_message, user_message = router.captured_request.messages
    assert system_message.role == "system"
    assert user_message.role == "user"
    assert user_message.content == "一句话"


def test_apply_expression_tags_to_sentence_injects_prior_context_as_extra_system_message() -> None:
    router = _FakeRouter(content="带标签的句子")

    apply_expression_tags_to_sentence(
        "现在这一句。",
        _mood(),
        prior_context="刚才已经说过的前文。",
        router=router,  # type: ignore[arg-type]
    )

    assert router.captured_request is not None
    messages = router.captured_request.messages
    assert len(messages) == 3
    rules_prompt, prior_prompt, user_message = messages
    assert rules_prompt.role == "system"
    assert prior_prompt.role == "system"
    assert "刚才已经说过的前文。" in prior_prompt.content
    assert "不要重复输出" in prior_prompt.content
    assert user_message.role == "user"
    assert user_message.content == "现在这一句。"
