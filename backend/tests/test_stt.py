from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.store import reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.stt.mock import MockSTTProvider
from backend.app.stt.router import STTRouter, reset_stt_router
from backend.app.stt.types import TranscriptionRequest


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    reset_stt_router()
    yield
    reset_provider_router()
    reset_memory_store()
    reset_stt_router()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    monkeypatch.setenv("CYBER_COMPANION_STT_MODE", "mock")
    return TestClient(app)


def test_stt_status_route(client: TestClient) -> None:
    response = client.get("/stt/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["force_mock"] is True
    assert payload["allow_cloud_stt"] is False
    assert any(provider["name"] == "mock" for provider in payload["providers"])


def test_stt_transcribe_mock(client: TestClient) -> None:
    response = client.post(
        "/stt/transcribe",
        files={"audio": ("clip.webm", BytesIO(b"fake-audio-bytes"), "audio/webm")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert "mock 语音转写" in payload["text"]
    assert payload["mock"] is True


def test_stt_transcribe_rejects_empty_audio(client: TestClient) -> None:
    response = client.post(
        "/stt/transcribe",
        files={"audio": ("clip.webm", BytesIO(b""), "audio/webm")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "Audio payload is empty."


def test_cloud_provider_blocked_without_budget_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.memory.budget import BudgetConfig
    from backend.app.stt.config import STTConfig, STTProviderConfigEntry
    from backend.app.stt.openai_whisper import OpenAIWhisperProvider

    config = STTConfig(
        enabled=True,
        default_provider="openai_whisper",
        force_mock=False,
        providers={
            "openai_whisper": STTProviderConfigEntry(
                name="openai_whisper",
                enabled=True,
                model="whisper-1",
                api_key_env="OPENAI_API_KEY",
                placeholder=False,
                cloud=True,
            )
        },
    )
    router = STTRouter(
        config,
        {"openai_whisper": OpenAIWhisperProvider(enabled=True, placeholder=False)},
        BudgetConfig(allow_cloud_stt=False),
    )

    with pytest.raises(Exception) as error:
        router.transcribe(
            TranscriptionRequest(audio_bytes=b"abc", mime_type="audio/webm"),
            provider_name="openai_whisper",
        )

    assert "Cloud STT is disabled" in str(error.value)


def test_mock_provider_transcribe() -> None:
    provider = MockSTTProvider()
    result = provider.transcribe(
        TranscriptionRequest(audio_bytes=b"12345", mime_type="audio/webm"),
    )

    assert result.mock is True
    assert "5 bytes" in result.text
