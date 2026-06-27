import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.deepseek import (
    DeepSeekProvider,
    close_deepseek_http_client,
    get_shared_http_client,
)
from backend.app.providers.router import reset_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatMessage


@pytest.fixture(autouse=True)
def reset_router() -> None:
    close_deepseek_http_client()
    reset_provider_router()
    yield
    close_deepseek_http_client()
    reset_provider_router()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Seed providers from the committed example into an isolated config dir so these
    # tests are deterministic and ignore any live, deployment-specific
    # config/providers.json (e.g. an Ark endpoint switch with ARK_API_KEY).
    repo_config = Path(__file__).resolve().parents[2] / "config"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    shutil.copy(repo_config / "providers.example.json", config_dir / "providers.json")
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return TestClient(app)


def test_providers_status_lists_mock_and_deepseek(client: TestClient) -> None:
    response = client.get("/providers/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_provider"] == "mock"
    assert payload["force_mock"] is True
    names = {provider["name"] for provider in payload["providers"]}
    assert {"mock", "deepseek", "openai", "local"}.issubset(names)


def test_chat_complete_uses_mock_provider(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={
            "messages": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["mock"] is True
    assert "你好" in payload["content"]
    assert payload["usage"]["total_tokens"] > 0
    assert payload["cost"]["total_usd"] == 0.0


def test_chat_complete_omits_translation_when_target_language_unset(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )

    assert response.status_code == 200
    assert response.json()["translation"] is None


def test_chat_complete_returns_translation_when_target_language_set(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={
            "messages": [{"role": "user", "content": "你好"}],
            "target_language": "en",
        },
    )

    assert response.status_code == 200
    assert response.json()["translation"] is not None


def test_chat_complete_persists_translation_into_message_metadata(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={
            "messages": [{"role": "user", "content": "你好"}],
            "target_language": "en",
        },
    )
    assert response.status_code == 200
    translation = response.json()["translation"]
    assert translation is not None

    messages = client.get("/memory/messages").json()["messages"]
    assistant_message = next(m for m in reversed(messages) if m["role"] == "assistant")
    assert assistant_message["metadata"]["translation"] == translation


def test_chat_complete_missing_deepseek_key_returns_clear_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "")
    reset_provider_router()

    response = client.post(
        "/chat/complete",
        json={
            "provider": "deepseek",
            "messages": [{"role": "user", "content": "Explain the memory schema in one sentence."}],
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"]["provider"] == "deepseek"
    assert "DEEPSEEK_API_KEY" in payload["detail"]["error"]


def test_chat_complete_openai_placeholder_returns_clear_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "")
    reset_provider_router()

    response = client.post(
        "/chat/complete",
        json={
            "provider": "openai",
            "messages": [{"role": "user", "content": "Explain the memory schema in one sentence."}],
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"]["provider"] == "openai"
    assert "placeholder" in payload["detail"]["error"]


def test_deepseek_shared_http_client_reused() -> None:
    close_deepseek_http_client()
    first = get_shared_http_client()
    second = get_shared_http_client()
    assert first is second


def test_reset_provider_router_closes_deepseek_http_client() -> None:
    from backend.app.providers import router as provider_router

    close_deepseek_http_client()
    client = get_shared_http_client()

    provider_router.reset_provider_router()

    assert client.is_closed


def test_deepseek_complete_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "memory schema is sqlite-backed"}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
            }

        @property
        def text(self) -> str:
            return ""

        @property
        def reason_phrase(self) -> str:
            return "OK"

    class FakeClient:
        def post(
            self,
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, object],
        ) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    provider = DeepSeekProvider(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        http_client=FakeClient(),  # type: ignore[arg-type]
    )
    result = provider.complete(
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Explain memory.")],
            max_output_tokens=64,
        ),
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["stream"] is False
    assert result.provider == "deepseek"
    assert result.content == "memory schema is sqlite-backed"
    assert result.mock is False
    assert result.usage.total_tokens == 20


def test_claude_complete_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.claude import ClaudeProvider

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "（偏头看你）就那样呗。"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18,
                },
            }

        @property
        def text(self) -> str:
            return ""

        @property
        def reason_phrase(self) -> str:
            return "OK"

    class FakeClient:
        def post(
            self,
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, object],
        ) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    provider = ClaudeProvider(
        model="claude-sonnet-4-6",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        http_client=FakeClient(),  # type: ignore[arg-type]
    )
    result = provider.complete(
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="你在我不在的时候，是什么感觉")],
            max_output_tokens=128,
        ),
    )

    assert captured["url"] == "https://api.anthropic.com/v1/chat/completions"
    assert captured["headers"]["x-api-key"] == "test-anthropic-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in captured["headers"]
    assert captured["json"]["model"] == "claude-sonnet-4-6"
    assert captured["json"]["stream"] is False
    assert result.provider == "claude"
    assert result.content == "（偏头看你）就那样呗。"
    assert result.mock is False
    assert result.usage.total_tokens == 18


def test_claude_missing_key_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.claude import ClaudeProvider

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ClaudeProvider(model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY")

    from backend.app.providers.exceptions import ProviderNotConfiguredError

    with pytest.raises(ProviderNotConfiguredError, match="ANTHROPIC_API_KEY"):
        provider.complete(
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="test")],
                max_output_tokens=64,
            )
        )


def test_openrouter_complete_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.openrouter import OpenRouterProvider

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "（偏头看你）就那样呗。"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            }

        @property
        def text(self) -> str:
            return ""

        @property
        def reason_phrase(self) -> str:
            return "OK"

    class FakeClient:
        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    provider = OpenRouterProvider(
        model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        http_client=FakeClient(),  # type: ignore[arg-type]
    )
    result = provider.complete(
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="你在我不在的时候，是什么感觉")],
            max_output_tokens=128,
        ),
    )

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-openrouter-key"
    assert captured["json"]["model"] == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    assert result.provider == "openrouter"
    assert result.content == "（偏头看你）就那样呗。"
    assert result.usage.total_tokens == 18


def test_openrouter_missing_key_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.openrouter import OpenRouterProvider
    from backend.app.providers.exceptions import ProviderNotConfiguredError

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = OpenRouterProvider(
        model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        api_key_env="OPENROUTER_API_KEY",
    )

    with pytest.raises(ProviderNotConfiguredError, match="OPENROUTER_API_KEY"):
        provider.complete(
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="test")],
                max_output_tokens=64,
            )
        )


def test_tagger_provider_prefers_neutral_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.config import ProviderConfigEntry
    from backend.app.providers.registry import build_provider

    monkeypatch.setenv("OPENROUTER_TAGGER_API_KEY", "neutral-key")
    monkeypatch.setenv("OPENROUTER_GEMINI_API_KEY", "legacy-key")
    provider = build_provider(
        ProviderConfigEntry(
            name="tagger",
            enabled=True,
            model="anthropic/claude-haiku-4.5",
            api_key_env="OPENROUTER_TAGGER_API_KEY",
        )
    )

    assert provider.api_key == "neutral-key"  # type: ignore[attr-defined]


def test_tagger_provider_accepts_legacy_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.config import ProviderConfigEntry
    from backend.app.providers.registry import build_provider

    monkeypatch.delenv("OPENROUTER_TAGGER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_GEMINI_API_KEY", "legacy-key")
    provider = build_provider(
        ProviderConfigEntry(
            name="tagger",
            enabled=True,
            model="anthropic/claude-haiku-4.5",
            api_key_env="OPENROUTER_TAGGER_API_KEY",
        )
    )

    assert provider.api_key == "legacy-key"  # type: ignore[attr-defined]


def test_legacy_gemini_provider_alias_still_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.providers.config import ProviderConfigEntry
    from backend.app.providers.registry import build_provider

    monkeypatch.setenv("OPENROUTER_GEMINI_API_KEY", "legacy-key")
    provider = build_provider(
        ProviderConfigEntry(
            name="gemini",
            enabled=True,
            model="google/gemini-2.5-flash-lite",
            api_key_env="OPENROUTER_GEMINI_API_KEY",
        )
    )

    assert provider.api_key == "legacy-key"  # type: ignore[attr-defined]


def test_chat_complete_unknown_provider_returns_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "")
    reset_provider_router()

    response = client.post(
        "/chat/complete",
        json={
            "provider": "unknown-vendor",
            "messages": [{"role": "user", "content": "Explain the memory schema in one sentence."}],
        },
    )

    assert response.status_code == 500
    assert "Unknown provider" in response.json()["detail"]["error"]
