from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.tts.config import TTSConfig, TTSProviderConfigEntry
from backend.app.tts.mock import MockTTSProvider
from backend.app.tts.openai_tts import OpenAITTSProvider
from backend.app.tts.policy import evaluate_speech_policy
from backend.app.tts.router import TTSRouter, reset_tts_router
from backend.app.tts.types import SynthesisRequest


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    reset_tts_router()
    yield
    reset_provider_router()
    reset_memory_store()
    reset_tts_router()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    monkeypatch.setenv("CYBER_COMPANION_TTS_MODE", "mock")
    return TestClient(app)


def test_tts_status_route(client: TestClient) -> None:
    response = client.get("/tts/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["force_mock"] is True
    assert payload["allow_cloud_tts"] is False
    assert payload["max_speech_chars"] == 120
    assert any(provider["name"] == "mock" for provider in payload["providers"])


def test_tts_evaluate_skips_long_reply(client: TestClient) -> None:
    response = client.post(
        "/tts/evaluate",
        json={
            "text": "x" * 200,
            "decision": "reply",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["should_speak"] is False
    assert payload["reason"] == "text too long for selective TTS"


def test_tts_evaluate_allows_short_proactive(client: TestClient) -> None:
    response = client.post(
        "/tts/evaluate",
        json={
            "text": "喂，你那个项目还做不做？",
            "decision": "proactive",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["should_speak"] is True


def test_tts_synthesize_mock(client: TestClient) -> None:
    response = client.post(
        "/tts/synthesize",
        json={
            "text": "短句测试。",
            "decision": "reply",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["spoken"] is True
    assert payload["provider"] == "mock"
    assert payload["mock"] is True
    assert payload["audio_base64"]
    assert payload["duration_ms"] >= 1400


def test_tts_synthesize_skips_silent_decision(client: TestClient) -> None:
    response = client.post(
        "/tts/synthesize",
        json={
            "text": "……",
            "decision": "silent",
            "avatar_state": "silent",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["spoken"] is False
    assert "silent" in payload["reason"]


def test_tts_synthesize_rejects_empty_text(client: TestClient) -> None:
    response = client.post(
        "/tts/synthesize",
        json={"text": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "Text payload is empty."


def test_cloud_provider_blocked_without_budget_flag() -> None:
    config = TTSConfig(
        enabled=True,
        default_provider="openai_tts",
        force_mock=False,
        max_speech_chars=120,
        speak_decisions=("reply",),
        providers={
            "openai_tts": TTSProviderConfigEntry(
                name="openai_tts",
                enabled=True,
                model="tts-1",
                api_key_env="OPENAI_API_KEY",
                placeholder=False,
                cloud=True,
            )
        },
    )
    router = TTSRouter(
        config,
        {"openai_tts": OpenAITTSProvider(enabled=True, placeholder=False)},
        BudgetConfig(allow_cloud_tts=False),
    )

    with pytest.raises(Exception) as error:
        router.synthesize(
            SynthesisRequest(text="短句", decision="reply", force=True),
            provider_name="openai_tts",
        )

    assert "Cloud TTS is disabled" in str(error.value)


def test_mock_provider_synthesize() -> None:
    provider = MockTTSProvider()
    result = provider.synthesize(SynthesisRequest(text="你好", decision="reply"))

    assert result.mock is True
    assert result.mime_type == "audio/wav"
    assert len(result.audio_bytes) > 44


def test_policy_skips_observe_and_mutter() -> None:
    assert evaluate_speech_policy("嗯", decision="mutter").should_speak is False
    assert evaluate_speech_policy("看着", decision="observe").should_speak is False
