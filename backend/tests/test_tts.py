import base64
import json
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.tts.config import TTSConfig, TTSProviderConfigEntry
from backend.app.tts.doubao import (
    CANCAN_BIGMODEL_SPEAKER,
    TTS_HTTP_ENDPOINT,
    DoubaoTTSProvider,
    close_doubao_http_client,
    get_shared_http_client,
    resolve_resource_id,
)
from backend.app.tts.exceptions import TTSConfigError, TTSError
from backend.app.tts.mac_say import MacSayTTSProvider
from backend.app.tts.mock import MockTTSProvider
from backend.app.tts.openai_tts import OpenAITTSProvider
from backend.app.tts.policy import evaluate_speech_policy
from backend.app.tts.registry import build_tts_provider
from backend.app.tts.router import TTSRouter, reset_tts_router
from backend.app.tts.text_cleanup import clean_text_for_tts
from backend.app.tts.types import SynthesisRequest
from backend.app.tts.wav_utils import generate_silent_wav, parse_wav_duration_ms


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    close_doubao_http_client()
    reset_tts_router()
    yield
    reset_provider_router()
    reset_memory_store()
    close_doubao_http_client()
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
    assert payload["allow_cloud_tts"] is True
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


def test_tts_stream_mock_fallback(client: TestClient) -> None:
    response = client.get(
        "/tts/stream",
        params={
            "text": "短句测试。",
            "decision": "reply",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["cache-control"] == "no-store"
    assert len(response.content) > 44


def test_tts_stream_policy_skip_returns_204(client: TestClient) -> None:
    response = client.get(
        "/tts/stream",
        params={
            "text": "……",
            "decision": "silent",
            "avatar_state": "silent",
        },
    )

    assert response.status_code == 204
    assert response.content == b""


def test_tts_stream_rejects_empty_text(client: TestClient) -> None:
    response = client.get(
        "/tts/stream",
        params={"text": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "Text payload is empty."


def test_router_stream_synthesize_fallback_for_mock() -> None:
    config = TTSConfig(
        enabled=True,
        default_provider="mock",
        force_mock=True,
        max_speech_chars=120,
        speak_decisions=("reply",),
        providers={
            "mock": TTSProviderConfigEntry(
                name="mock",
                enabled=True,
                model="mock-tts",
            )
        },
    )
    router = TTSRouter(
        config,
        {"mock": MockTTSProvider()},
        BudgetConfig(allow_cloud_tts=True),
    )

    policy, chunks = router.stream_synthesize(
        SynthesisRequest(text="你好", decision="reply"),
    )

    assert policy.should_speak is True
    assert chunks is not None
    audio_parts = list(chunks)
    assert len(audio_parts) == 1
    assert len(audio_parts[0]) > 44


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


def test_parse_wav_duration_ms() -> None:
    wav = generate_silent_wav(800)
    assert parse_wav_duration_ms(wav) == 800


def test_registry_builds_mac_say_provider() -> None:
    entry = TTSProviderConfigEntry(
        name="mac_say",
        enabled=True,
        model="mac-say",
        voice="Tingting",
        cloud=False,
    )
    provider = build_tts_provider(entry)

    assert isinstance(provider, MacSayTTSProvider)
    assert provider.name == "mac_say"
    assert provider.cloud is False


def test_mac_say_provider_status_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.tts.mac_say.shutil.which", lambda _: "/usr/bin/say")
    provider = MacSayTTSProvider(voice="Tingting")
    status = provider.status()

    assert status.name == "mac_say"
    assert status.enabled is True
    assert status.model == "mac-say-Tingting"
    assert status.configured is True
    assert status.placeholder is False
    assert status.cloud is False
    assert status.api_key_present is False


def test_mac_say_unavailable_raises_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.tts.mac_say.shutil.which", lambda _: None)
    provider = MacSayTTSProvider()

    with pytest.raises(TTSError) as error:
        provider.synthesize(SynthesisRequest(text="你好"))

    assert "not available" in str(error.value)
    assert error.value.provider == "mac_say"


def test_mac_say_synthesize_mocked_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    wav = generate_silent_wav(600)
    captured_cmd: list[str] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_cmd.extend(cmd)
        assert kwargs.get("shell") is not True
        out_index = cmd.index("-o") + 1
        Path(cmd[out_index]).write_bytes(wav)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("backend.app.tts.mac_say.shutil.which", lambda _: "/usr/bin/say")
    monkeypatch.setattr("backend.app.tts.mac_say.subprocess.run", fake_run)

    provider = MacSayTTSProvider(voice="Tingting")
    result = provider.synthesize(SynthesisRequest(text="你好"))

    assert captured_cmd[-1] == "你好"
    assert "--file-format=WAVE" in captured_cmd
    assert "--data-format=LEI16@22050" in captured_cmd
    assert result.mock is False
    assert result.provider == "mac_say"
    assert result.model == "mac-say-Tingting"
    assert result.mime_type == "audio/wav"
    assert result.audio_bytes == wav
    assert result.duration_ms == 600


def test_tts_config_defaults_to_doubao_without_force_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.tts.config import load_tts_config

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.delenv("CYBER_COMPANION_TTS_MODE", raising=False)

    config = load_tts_config(repo_root / "config")
    assert config.default_provider == "doubao"
    assert config.force_mock is False


def test_force_mock_overrides_doubao_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from backend.app.tts.router import get_tts_router

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_TTS_MODE", "mock")
    reset_tts_router()

    tts_router = get_tts_router()
    assert tts_router.config.force_mock is True
    assert tts_router.resolve_provider_name() == "mock"


def _set_doubao_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOUBAO_TTS_API_KEY", "api-key-abc")
    monkeypatch.setenv("DOUBAO_TTS_VOICE_TYPE", CANCAN_BIGMODEL_SPEAKER)
    monkeypatch.setenv("DOUBAO_TTS_RESOURCE_ID", "seed-tts-2.0")
    monkeypatch.delenv("DOUBAO_TTS_ACCESS_TOKEN", raising=False)


def test_registry_builds_doubao_provider() -> None:
    entry = TTSProviderConfigEntry(
        name="doubao",
        enabled=False,
        model="doubao-tts",
        cloud=True,
    )
    provider = build_tts_provider(entry)

    assert isinstance(provider, DoubaoTTSProvider)
    assert provider.name == "doubao"
    assert provider.cloud is True


def test_doubao_provider_status_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    provider = DoubaoTTSProvider(enabled=False)
    status = provider.status()

    assert status.name == "doubao"
    assert status.enabled is False
    assert status.model == CANCAN_BIGMODEL_SPEAKER
    assert status.configured is True
    assert status.api_key_present is True
    assert status.placeholder is False
    assert status.cloud is True


def test_doubao_unconfigured_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOUBAO_TTS_API_KEY", raising=False)
    monkeypatch.delenv("DOUBAO_TTS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DOUBAO_TTS_VOICE_TYPE", raising=False)

    provider = DoubaoTTSProvider()
    assert provider.is_configured() is False

    with pytest.raises(TTSConfigError) as error:
        provider.synthesize(SynthesisRequest(text="你好"))

    assert "DOUBAO_TTS_API_KEY" in str(error.value)


def test_resolve_resource_id_for_cancan_bigmodel() -> None:
    assert resolve_resource_id(CANCAN_BIGMODEL_SPEAKER) == "seed-tts-2.0"
    assert resolve_resource_id("zh_female_shuangkuaisisi_moon_bigtts") == "seed-tts-1.0"


def test_doubao_rejects_legacy_bv_streaming_speaker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOUBAO_TTS_API_KEY", "api-key-abc")
    monkeypatch.setenv("DOUBAO_TTS_VOICE_TYPE", "BV700_streaming")
    provider = DoubaoTTSProvider()

    with pytest.raises(TTSError) as error:
        provider.synthesize(SynthesisRequest(text="你好"))

    assert "legacy small-model" in str(error.value).lower()


def test_doubao_accepts_legacy_access_token_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOUBAO_TTS_API_KEY", raising=False)
    monkeypatch.setenv("DOUBAO_TTS_ACCESS_TOKEN", "legacy-token")
    monkeypatch.setenv("DOUBAO_TTS_VOICE_TYPE", "BV700_streaming")

    provider = DoubaoTTSProvider()
    assert provider.is_configured() is True


def _fake_stream_client(lines: list[str], captured: dict[str, object]) -> object:
    class FakeStreamResponse:
        status_code = 200

        def __init__(self, stream_lines: list[str]) -> None:
            self._lines = stream_lines

        def iter_lines(self) -> list[str]:
            return self._lines

        def __enter__(self) -> "FakeStreamResponse":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    class FakeClient:
        def stream(
            self,
            method: str,
            url: str,
            *,
            json: dict,
            headers: dict[str, str],
            timeout: float,
        ) -> FakeStreamResponse:
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeStreamResponse(lines)

    return FakeClient()


def test_doubao_shared_http_client_reused() -> None:
    close_doubao_http_client()
    first = get_shared_http_client(30.0)
    second = get_shared_http_client(30.0)
    assert first is second


def test_reset_tts_router_closes_doubao_http_client() -> None:
    from backend.app.tts import router as tts_router

    close_doubao_http_client()
    client = get_shared_http_client(30.0)

    tts_router.reset_tts_router()

    assert client.is_closed


def test_doubao_synthesize_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    audio1 = b"mp3-chunk-1"
    audio2 = b"mp3-chunk-2"
    captured: dict[str, object] = {}
    lines = [
        json.dumps({"code": 0, "message": "", "data": base64.b64encode(audio1).decode("ascii")}),
        json.dumps({"code": 0, "message": "", "data": base64.b64encode(audio2).decode("ascii")}),
        json.dumps({"code": 20_000_000, "message": "OK", "data": None}),
    ]

    provider = DoubaoTTSProvider(http_client=_fake_stream_client(lines, captured))  # type: ignore[arg-type]
    chunks = list(provider.synthesize_stream(SynthesisRequest(text="流式测试。")))

    assert chunks == [audio1, audio2]
    assert captured["url"] == TTS_HTTP_ENDPOINT
    assert captured["json"]["req_params"]["audio_params"]["format"] == "mp3"


def test_doubao_synthesize_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    audio = b"mp3-audio-bytes"
    captured: dict[str, object] = {}
    lines = [
        json.dumps({"code": 0, "message": "", "data": base64.b64encode(audio).decode("ascii")}),
        json.dumps({"code": 20_000_000, "message": "OK", "data": None}),
    ]

    provider = DoubaoTTSProvider(http_client=_fake_stream_client(lines, captured))  # type: ignore[arg-type]
    result = provider.synthesize(SynthesisRequest(text="你好，Boxi。"))

    assert captured["url"] == TTS_HTTP_ENDPOINT
    headers = captured["headers"]
    assert headers["X-Api-Key"] == "api-key-abc"
    assert headers["X-Api-Resource-Id"] == "seed-tts-2.0"
    assert headers["X-Api-Request-Id"]
    assert headers["Content-Type"] == "application/json"

    body = captured["json"]
    assert body["user"]["uid"] == "cyber-companion"
    assert body["req_params"]["text"] == "你好，Boxi。"
    assert body["req_params"]["speaker"] == CANCAN_BIGMODEL_SPEAKER
    assert body["req_params"]["audio_params"]["format"] == "mp3"

    assert result.mock is False
    assert result.provider == "doubao"
    assert result.model == CANCAN_BIGMODEL_SPEAKER
    assert result.mime_type == "audio/mpeg"
    assert result.audio_bytes == audio


def test_doubao_auth_failure_raises_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    captured: dict[str, object] = {}
    lines = [
        json.dumps(
            {
                "code": 45_000_000,
                "message": "speaker permission denied: get resource id: access denied",
            }
        ),
    ]

    provider = DoubaoTTSProvider(http_client=_fake_stream_client(lines, captured))  # type: ignore[arg-type]

    with pytest.raises(TTSError) as error:
        provider.synthesize(SynthesisRequest(text="你好"))

    assert error.value.provider == "doubao"
    assert "permission denied" in str(error.value).lower()
    assert error.value.status_code == 503


def test_doubao_network_error_raises_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)

    class FakeClient:
        def stream(self, *args: object, **kwargs: object) -> None:
            raise httpx.ConnectError("connection refused", request=httpx.Request("POST", TTS_HTTP_ENDPOINT))

    provider = DoubaoTTSProvider(http_client=FakeClient())  # type: ignore[arg-type]

    with pytest.raises(TTSError) as error:
        provider.synthesize(SynthesisRequest(text="你好"))

    assert error.value.provider == "doubao"
    assert "network error" in str(error.value).lower()


def test_doubao_cloud_provider_blocked_without_budget_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    config = TTSConfig(
        enabled=True,
        default_provider="doubao",
        force_mock=False,
        max_speech_chars=120,
        speak_decisions=("reply",),
        providers={
            "doubao": TTSProviderConfigEntry(
                name="doubao",
                enabled=True,
                model="doubao-tts",
                cloud=True,
            )
        },
    )
    router = TTSRouter(
        config,
        {"doubao": DoubaoTTSProvider(enabled=True)},
        BudgetConfig(allow_cloud_tts=False),
    )

    with pytest.raises(Exception) as error:
        router.synthesize(
            SynthesisRequest(text="短句", decision="reply", force=True),
            provider_name="doubao",
        )

    assert "Cloud TTS is disabled" in str(error.value)


def test_clean_text_for_tts_strips_markdown_emoji_and_stage_directions() -> None:
    raw = "（叹气）**你好** 😀（翻白眼）"
    cleaned = clean_text_for_tts(raw)
    assert "你好" in cleaned
    assert "**" not in cleaned
    assert "😀" not in cleaned
    assert "叹气" not in cleaned
    assert "翻白眼" not in cleaned


def test_clean_text_for_tts_preserves_ellipsis() -> None:
    # Boxi 的拖尾省略号是有意的韵味，不该被标点去重压成单个。
    assert clean_text_for_tts("行吧……随你") == "行吧……随你"
    assert clean_text_for_tts("好。。。") == "好。"  # 真·重复句号仍归一


def test_doubao_payload_includes_emotion_directive(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    captured: dict[str, object] = {}
    lines = [
        json.dumps({"code": 0, "message": "", "data": base64.b64encode(b"audio").decode("ascii")}),
        json.dumps({"code": 20_000_000, "message": "OK", "data": None}),
    ]
    provider = DoubaoTTSProvider(http_client=_fake_stream_client(lines, captured))  # type: ignore[arg-type]
    provider.synthesize(
        SynthesisRequest(
            text="（小声）短句。",
            context_texts=["更冲、更不耐烦但别凶"],
            speech_rate=12,
        )
    )

    req = captured["json"]["req_params"]
    assert req["text"] == "短句。"
    assert req["additions"]["context_texts"] == ["更冲、更不耐烦但别凶"]
    assert req["audio_params"]["speech_rate"] == 12


def test_doubao_payload_backward_compatible_without_emotion(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_doubao_env(monkeypatch)
    captured: dict[str, object] = {}
    lines = [
        json.dumps({"code": 0, "message": "", "data": base64.b64encode(b"audio").decode("ascii")}),
        json.dumps({"code": 20_000_000, "message": "OK", "data": None}),
    ]
    provider = DoubaoTTSProvider(http_client=_fake_stream_client(lines, captured))  # type: ignore[arg-type]
    provider.synthesize(SynthesisRequest(text="你好，Boxi。"))

    req = captured["json"]["req_params"]
    assert req["text"] == "你好，Boxi。"
    assert "additions" not in req
    assert "speech_rate" not in req["audio_params"]


def test_tts_synthesize_neutral_kernel_omits_emotion_on_doubao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_TTS_MODE", "doubao")
    _set_doubao_env(monkeypatch)
    reset_tts_router()

    captured: dict[str, object] = {}
    original_build = DoubaoTTSProvider._build_request_payload

    def _capture_build(self, text, creds, *, context_texts=None, speech_rate=0):
        captured["context_texts"] = context_texts
        captured["speech_rate"] = speech_rate
        return original_build(self, text, creds, context_texts=context_texts, speech_rate=speech_rate)

    monkeypatch.setattr(DoubaoTTSProvider, "_build_request_payload", _capture_build)
    monkeypatch.setattr(
        DoubaoTTSProvider,
        "_stream_synthesis",
        lambda self, payload, headers: b"audio",
    )

    client = TestClient(app)
    response = client.post(
        "/tts/synthesize",
        json={"text": "短句测试。", "decision": "reply", "force": True},
    )

    assert response.status_code == 200
    assert captured["context_texts"] is None
    assert captured["speech_rate"] == 0
