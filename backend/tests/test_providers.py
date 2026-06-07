import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.router import reset_provider_router


@pytest.fixture(autouse=True)
def reset_router() -> None:
    reset_provider_router()
    yield
    reset_provider_router()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
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
