from __future__ import annotations

from backend.app.providers.exceptions import ProviderError
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, CostEstimate, TokenUsage
from backend.app.tts.translator import DEFAULT_TRANSLATOR_PROVIDER, translate_to_chinese


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


def test_translate_to_chinese_returns_translated_text() -> None:
    router = _FakeRouter(content="你好，今天过得怎么样？")

    result = translate_to_chinese("Hello, how was your day?", router=router)  # type: ignore[arg-type]

    assert result == "你好，今天过得怎么样？"


def test_translate_to_chinese_falls_back_to_none_on_provider_error() -> None:
    router = _FakeRouter(error=ProviderError("boom", provider="gemini"))

    result = translate_to_chinese("Hello", router=router)  # type: ignore[arg-type]

    assert result is None


def test_translate_to_chinese_falls_back_to_none_on_unexpected_error() -> None:
    router = _FakeRouter(error=RuntimeError("unexpected"))

    result = translate_to_chinese("Hello", router=router)  # type: ignore[arg-type]

    assert result is None


def test_translate_to_chinese_falls_back_to_none_on_empty_result() -> None:
    router = _FakeRouter(content="   ")

    result = translate_to_chinese("Hello", router=router)  # type: ignore[arg-type]

    assert result is None


def test_translate_to_chinese_skips_provider_call_when_input_blank() -> None:
    router = _FakeRouter(content="should not be used")

    result = translate_to_chinese("   ", router=router)  # type: ignore[arg-type]

    assert result is None
    assert router.captured_request is None


def test_translate_to_chinese_uses_default_provider_name() -> None:
    router = _FakeRouter(content="你好")

    translate_to_chinese("Hello", router=router)  # type: ignore[arg-type]

    assert router.captured_provider_name == DEFAULT_TRANSLATOR_PROVIDER == "gemini"


def test_translate_to_chinese_allows_provider_override() -> None:
    router = _FakeRouter(content="你好")

    translate_to_chinese("Hello", router=router, provider_name="deepseek")  # type: ignore[arg-type]

    assert router.captured_provider_name == "deepseek"


def test_translate_to_chinese_passes_text_into_prompt() -> None:
    router = _FakeRouter(content="你好")

    translate_to_chinese("Hello there", router=router)  # type: ignore[arg-type]

    assert router.captured_request is not None
    system_message, user_message = router.captured_request.messages
    assert system_message.role == "system"
    assert user_message.role == "user"
    assert user_message.content == "Hello there"
