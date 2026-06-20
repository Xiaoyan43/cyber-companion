from __future__ import annotations

import pytest

from backend.app.memory.database import MoodStateRecord
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, CostEstimate, TokenUsage
from backend.app.tts.expression_tagger import (
    DEFAULT_TAGGER_PROVIDER,
    TAGGER_INSTRUCTION_TEMPLATE,
    apply_expression_tags,
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


def test_apply_expression_tags_skips_provider_call_when_input_blank() -> None:
    router = _FakeRouter(content="should not be used")

    result = apply_expression_tags("   ", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "   "
    assert router.captured_request is None


def test_apply_expression_tags_uses_default_provider_name() -> None:
    router = _FakeRouter(content="带标签的文本")

    apply_expression_tags("原文", _mood(), router=router)  # type: ignore[arg-type]

    assert router.captured_provider_name == DEFAULT_TAGGER_PROVIDER == "deepseek"


def test_apply_expression_tags_allows_provider_override() -> None:
    router = _FakeRouter(content="带标签的文本")

    apply_expression_tags("原文", _mood(), router=router, provider_name="gemini")  # type: ignore[arg-type]

    assert router.captured_provider_name == "gemini"


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
        "逐句重新判断",
        "[sigh]",
        "[whispering]",
        "音效/生理反应类",
    ],
)
def test_tagger_instruction_contains_core_rules(expected_phrase: str) -> None:
    assert expected_phrase in TAGGER_INSTRUCTION_TEMPLATE


def test_tagger_instruction_has_no_hard_tag_count_quota() -> None:
    assert "至少一次" not in TAGGER_INSTRUCTION_TEMPLATE
    assert "硬性要求" not in TAGGER_INSTRUCTION_TEMPLATE
