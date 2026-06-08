from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.store import reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.stt.exceptions import STTError
from backend.app.stt.faster_whisper import (
    FasterWhisperProvider,
    decode_audio_bytes,
    reset_faster_whisper_cache,
)
from backend.app.stt.mock import MockSTTProvider
from backend.app.stt.registry import build_stt_provider
from backend.app.stt.router import STTRouter, reset_stt_router
from backend.app.stt.types import TranscriptionRequest
from backend.app.stt.config import STTProviderConfigEntry


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    reset_stt_router()
    reset_faster_whisper_cache()
    yield
    reset_provider_router()
    reset_memory_store()
    reset_stt_router()
    reset_faster_whisper_cache()


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


def test_registry_builds_faster_whisper_provider() -> None:
    entry = STTProviderConfigEntry(
        name="faster_whisper",
        enabled=True,
        model="base",
        cloud=False,
    )
    provider = build_stt_provider(entry)

    assert isinstance(provider, FasterWhisperProvider)
    assert provider.name == "faster_whisper"
    assert provider.cloud is False


def test_faster_whisper_provider_status_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.stt.faster_whisper.shutil.which", lambda _: "/usr/bin/ffmpeg")
    provider = FasterWhisperProvider(model="base")
    status = provider.status()

    assert status.name == "faster_whisper"
    assert status.enabled is True
    assert status.model == "base"
    assert status.placeholder is False
    assert status.cloud is False
    assert status.api_key_present is False


def test_faster_whisper_decode_rejects_empty_audio() -> None:
    with pytest.raises(STTError) as error:
        decode_audio_bytes(b"")

    assert error.value.status_code == 400
    assert "empty" in error.value.message.lower()


def test_faster_whisper_decode_rejects_garbled_audio() -> None:
    with pytest.raises(STTError) as error:
        decode_audio_bytes(b"not-a-real-audio-file")

    assert error.value.status_code == 400
    assert error.value.provider == "faster_whisper"


@dataclass
class _FakeSegment:
    text: str


class _FakeWhisperModel:
    def __init__(self, *, text: str = "你好世界", language: str = "zh") -> None:
        self._text = text
        self._language = language
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio: np.ndarray, *, language: str | None = None) -> tuple[list[_FakeSegment], object]:
        self.calls.append({"audio": audio, "language": language})
        return [_FakeSegment(self._text)], SimpleNamespace(language=self._language)


def test_faster_whisper_transcribe_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_audio = np.zeros(16_000, dtype=np.float32)
    fake_model = _FakeWhisperModel(text="  你好世界  ", language="zh")

    monkeypatch.setattr(
        "backend.app.stt.faster_whisper.decode_audio_bytes",
        lambda _payload: fake_audio,
    )
    monkeypatch.setattr(
        "backend.app.stt.faster_whisper._get_whisper_model",
        lambda _size: fake_model,
    )

    provider = FasterWhisperProvider(model="base")
    result = provider.transcribe(
        TranscriptionRequest(
            audio_bytes=b"ignored",
            mime_type="audio/webm",
            language="zh",
        ),
    )

    assert fake_model.calls == [{"audio": fake_audio, "language": "zh"}]
    assert result.mock is False
    assert result.provider == "faster_whisper"
    assert result.model == "base"
    assert result.text == "你好世界"
    assert result.language == "zh"


def test_faster_whisper_transcribe_no_speech_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = _FakeWhisperModel(text="   ")

    monkeypatch.setattr(
        "backend.app.stt.faster_whisper.decode_audio_bytes",
        lambda _payload: np.zeros(8_000, dtype=np.float32),
    )
    monkeypatch.setattr(
        "backend.app.stt.faster_whisper._get_whisper_model",
        lambda _size: fake_model,
    )

    provider = FasterWhisperProvider()

    with pytest.raises(STTError) as error:
        provider.transcribe(
            TranscriptionRequest(audio_bytes=b"clip", mime_type="audio/webm"),
        )

    assert error.value.status_code == 400
    assert "No speech detected" in error.value.message


def test_stt_config_defaults_to_faster_whisper_without_force_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.stt.config import load_stt_config

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.delenv("CYBER_COMPANION_STT_MODE", raising=False)

    config = load_stt_config(repo_root / "config")
    assert config.default_provider == "faster_whisper"
    assert config.force_mock is False


def test_force_mock_overrides_faster_whisper_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from backend.app.stt.router import get_stt_router

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_STT_MODE", "mock")
    reset_stt_router()

    stt_router = get_stt_router()
    assert stt_router.config.force_mock is True
    assert stt_router.resolve_provider_name() == "mock"

