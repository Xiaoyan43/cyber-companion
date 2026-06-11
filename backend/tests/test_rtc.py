"""Unit tests for RTC integration (no live Volcengine calls)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.rtc.config import RtcConfig, mode_ready, resolve_rtc_user_id
from backend.app.rtc.routes import router as rtc_router
from backend.app.rtc.signer import sign_rtc_openapi_request
from backend.app.rtc.token import AccessToken, mint_rtc_token
from backend.app.memory.persona import load_rtc_speaking_style, load_rtc_system_role
from backend.app.rtc.client import update_voice_chat
from backend.app.rtc.voice_chat import (
    build_memory_config,
    build_stop_voice_chat_body,
    build_update_voice_chat_body,
    build_voice_chat_body,
)


@pytest.fixture
def rtc_client() -> TestClient:
    app = FastAPI()
    app.include_router(rtc_router)
    return TestClient(app)


@pytest.fixture
def rtc_config() -> RtcConfig:
    return RtcConfig(
        rtc_app_id="0123456789abcdef01234567",
        rtc_app_key="test-app-key",
        access_key="AKTEST",
        secret_key="SKTEST",
        rt_app_id="1234567890",
        rt_access_token="rt-token",
        rt_speaker="zh_male_yunzhou_jupiter_bigtts",
        rt_model="1.2.1.1",
        soul_public_url="https://example.com/v1/chat/completions",
        soul_api_key="soul-key",
        welcome_pure="hi pure",
        welcome_hybrid="hi hybrid",
        bot_user_pure="BoxiBot",
        bot_user_hybrid="BoxiHybridBot",
        task_pure="BoxiTask01",
        task_hybrid="BoxiHybridTask01",
        default_user_id="boxi_user",
        viking_memory_api_key="",
        viking_memory_collection="",
        viking_memory_project="default",
        viking_memory_host="https://api-knowledgebase.mlp.cn-beijing.volces.com",
        viking_memory_assistant_id="",
        viking_memory_limit=3,
        viking_memory_transition_words="",
        viking_memory_types=(),
        enable_asr_twopass=False,
        enable_music=True,
    )


def test_mint_rtc_token_prefix(rtc_config: RtcConfig) -> None:
    token = mint_rtc_token(
        app_id=rtc_config.rtc_app_id,
        app_key=rtc_config.rtc_app_key,
        room_id="room-1",
        user_id="user-1",
    )
    assert token.startswith("001")
    assert rtc_config.rtc_app_id in token


def test_mint_rtc_token_matches_demo_wire_format() -> None:
    """Byte-compatible with rtc-aigc-demo Server/token.js serialize()."""
    import base64
    import struct

    token = AccessToken(
        app_id="0123456789abcdef01234567",
        app_key="test-app-key",
        room_id="room-1",
        user_id="user-1",
    )
    token.nonce = 12345
    token.issued_at = 1_700_000_000
    token.add_privilege(4, 0)
    token.add_privilege(0, 0)
    token.expire_time(1_700_086_400)

    expected = (
        "0010123456789abcdef01234567"
        "PAA5MAAAAPFTZYBCVWUGAHJvb20tMQYAdXNlci0xBQAAAAAAAAABAAAAAAACAAAAAAADAAAAAAAEAAAAAAAgABzD+VNbXlc31qkS9xkM7CYG7L3+oxaVXics9L8alau8"
    )
    assert token.serialize() == expected

    content = base64.b64decode(expected[3 + 24 :])
    msg_len = struct.unpack_from("<H", content, 0)[0]
    assert msg_len == 60
    sig_len = struct.unpack_from("<H", content, 2 + msg_len)[0]
    assert sig_len == 32


def test_build_voice_chat_pure_matches_demo_asr(rtc_config: RtcConfig) -> None:
    body = build_voice_chat_body(
        rtc_config,
        mode="pure",
        room_id="room-a",
        target_user_id="user-a",
    )
    asr = body["Config"]["S2SConfig"]["ProviderParams"]["asr"]["extra"]
    assert body["Config"]["S2SConfig"]["OutputMode"] == 0
    assert asr["end_smooth_window_ms"] == 1000
    assert asr["enable_asr_twopass"] is False
    assert (
        body["Config"]["S2SConfig"]["ProviderParams"]["tts"]["speaker"]
        == rtc_config.rt_speaker
    )
    dialog_extra = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]["extra"]
    assert dialog_extra["model"] == "1.2.1.1"
    assert dialog_extra["enable_music"] is True


def test_build_voice_chat_pure_music_opt_out(rtc_config: RtcConfig) -> None:
    without_music = RtcConfig(**{**rtc_config.__dict__, "enable_music": False})
    body = build_voice_chat_body(
        without_music,
        mode="pure",
        room_id="room-a",
        target_user_id="user-a",
    )
    extra = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]["extra"]
    assert "enable_music" not in extra


def test_build_voice_chat_pure_enables_tts_tag_parse(rtc_config: RtcConfig) -> None:
    body = build_voice_chat_body(
        rtc_config,
        mode="pure",
        room_id="room-a",
        target_user_id="user-a",
    )
    tts_context = body["Config"]["TTSConfig"]["Context"]
    assert tts_context == {"TagParse": True, "QuoteUserQuestion": True}


def test_build_voice_chat_hybrid_omits_tts_tag_parse(rtc_config: RtcConfig) -> None:
    body = build_voice_chat_body(
        rtc_config,
        mode="hybrid",
        room_id="room-b",
        target_user_id="user-b",
    )
    assert "TTSConfig" not in body["Config"]


def test_build_update_voice_chat_body_set_tts_context(rtc_config: RtcConfig) -> None:
    message = '{"Tag":{"additions":{"context_texts":["更冲、更不耐烦但别凶"]}}}'
    body = build_update_voice_chat_body(
        rtc_config,
        mode="pure",
        room_id="room-a",
        command="SetTTSContext",
        message=message,
    )
    assert body == {
        "AppId": rtc_config.rtc_app_id,
        "RoomId": "room-a",
        "TaskId": rtc_config.task_pure,
        "Command": "SetTTSContext",
        "Message": message,
    }


@patch("backend.app.rtc.client.httpx.post")
def test_update_voice_chat_calls_openapi(mock_post, rtc_config: RtcConfig) -> None:
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"Result": "ok"}
    message = '{"Tag":{"additions":{"context_texts":["语气放软、关切、稍慢"]}}}'
    result = update_voice_chat(
        rtc_config,
        mode="pure",
        room_id="room-a",
        command="SetTTSContext",
        message=message,
    )
    assert result == {"Result": "ok"}
    mock_post.assert_called_once()
    posted_body = mock_post.call_args.kwargs["content"]
    if isinstance(posted_body, bytes):
        posted_body = posted_body.decode("utf-8")
    assert rtc_config.rtc_app_id in posted_body
    assert "SetTTSContext" in posted_body
    assert "语气放软、关切、稍慢" in posted_body
    assert rtc_config.task_pure in posted_body
    assert mock_post.call_args.args[0].endswith("Action=UpdateVoiceChat&Version=2024-12-01")


def test_build_voice_chat_pure_asr_twopass_opt_in(
    rtc_config: RtcConfig,
    tmp_path: Path,
) -> None:
    from backend.app.memory.store import MemoryStore

    neutral_store = MemoryStore(db_path=tmp_path / "rtc_pure_twopass.db")
    neutral_store.update_mood_state(
        annoyance=0.1,
        worry=0.1,
        loneliness=0.1,
        boredom=0.1,
        energy=0.5,
    )
    neutral_store.update_relationship_state(trust=0.5, closeness=0.5, tension=0.1)

    with_twopass = RtcConfig(**{**rtc_config.__dict__, "enable_asr_twopass": True})
    with patch("backend.app.rtc.state_block.get_memory_store", return_value=neutral_store):
        body = build_voice_chat_body(
            with_twopass,
            mode="pure",
            room_id="room-a",
            target_user_id="user-a",
        )
    asr = body["Config"]["S2SConfig"]["ProviderParams"]["asr"]["extra"]
    assert asr["enable_asr_twopass"] is True
    dialog = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]
    assert dialog["system_role"] == load_rtc_system_role()
    assert dialog["speaking_style"] == load_rtc_speaking_style()
    assert "边界" not in dialog["system_role"]
    assert "LLMConfig" not in body["Config"]


def test_build_voice_chat_hybrid(rtc_config: RtcConfig) -> None:
    body = build_voice_chat_body(
        rtc_config,
        mode="hybrid",
        room_id="room-b",
        target_user_id="user-b",
    )
    assert body["Config"]["S2SConfig"]["OutputMode"] == 1
    llm = body["Config"]["LLMConfig"]
    assert llm["Mode"] == "CustomLLM"
    assert llm["Url"] == rtc_config.soul_public_url


@patch("backend.app.rtc.routes.start_voice_chat")
def test_rtc_agent_start(mock_start, rtc_client: TestClient, rtc_config: RtcConfig) -> None:
    mock_start.return_value = {"Result": "ok"}
    env = {
        "VOLC_RTC_APP_ID": rtc_config.rtc_app_id,
        "VOLC_RTC_APP_KEY": rtc_config.rtc_app_key,
        "VOLC_ACCESS_KEY": rtc_config.access_key,
        "VOLC_SECRET_KEY": rtc_config.secret_key,
        "DOUBAO_RT_APP_ID": rtc_config.rt_app_id,
        "DOUBAO_RT_ACCESS_TOKEN": rtc_config.rt_access_token,
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            response = rtc_client.post(
                "/rtc/agent/start",
                json={"mode": "pure", "room_id": "room-a", "user_id": "user-a"},
            )
            assert response.status_code == 200
            mock_start.assert_called_once()


def test_rtc_prepare_does_not_start_agent(rtc_client: TestClient, rtc_config: RtcConfig) -> None:
    env = {
        "VOLC_RTC_APP_ID": rtc_config.rtc_app_id,
        "VOLC_RTC_APP_KEY": rtc_config.rtc_app_key,
        "VOLC_ACCESS_KEY": rtc_config.access_key,
        "VOLC_SECRET_KEY": rtc_config.secret_key,
        "DOUBAO_RT_APP_ID": rtc_config.rt_app_id,
        "DOUBAO_RT_ACCESS_TOKEN": rtc_config.rt_access_token,
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            with patch("backend.app.rtc.routes.start_voice_chat") as mock_start:
                response = rtc_client.post("/rtc/prepare", json={"mode": "pure"})
                assert response.status_code == 200
                data = response.json()
                assert data["token"].startswith("001")
                mock_start.assert_not_called()


@patch("backend.app.rtc.routes.start_voice_chat")
def test_rtc_start_legacy(mock_start, rtc_client: TestClient, rtc_config: RtcConfig) -> None:
    mock_start.return_value = {"Result": "ok"}
    env = {
        "VOLC_RTC_APP_ID": rtc_config.rtc_app_id,
        "VOLC_RTC_APP_KEY": rtc_config.rtc_app_key,
        "VOLC_ACCESS_KEY": rtc_config.access_key,
        "VOLC_SECRET_KEY": rtc_config.secret_key,
        "DOUBAO_RT_APP_ID": rtc_config.rt_app_id,
        "DOUBAO_RT_ACCESS_TOKEN": rtc_config.rt_access_token,
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            response = rtc_client.post("/rtc/start", json={"mode": "pure"})
            assert response.status_code == 200
            assert response.json()["token"].startswith("001")
            mock_start.assert_called_once()


def test_build_voice_chat_includes_memory_config_when_configured(rtc_config: RtcConfig) -> None:
    with_memory = RtcConfig(
        **{
            **rtc_config.__dict__,
            "viking_memory_collection": "boxi_memory",
            "viking_memory_transition_words": "根据记录：",
            "viking_memory_types": ("recent_event",),
        }
    )
    body = build_voice_chat_body(
        with_memory,
        mode="pure",
        room_id="room-a",
        target_user_id="boxi_user",
    )
    memory = body["Config"]["MemoryConfig"]
    assert memory["Enable"] is True
    assert memory["Provider"] == "volc"
    params = memory["ProviderParams"]
    assert params["collection_name"] == "boxi_memory"
    assert params["project_name"] == "default"
    assert params["limit"] == 3
    assert params["filter"]["user_id"] == ["boxi_user"]
    assert params["filter"]["memory_type"] == ["recent_event"]
    assert params["transition_words"] == "根据记录："


def test_build_memory_config_defaults_runtime_types_to_profile(rtc_config: RtcConfig) -> None:
    with_memory = RtcConfig(
        **{**rtc_config.__dict__, "viking_memory_collection": "boxi_memory"}
    )
    memory = build_memory_config(with_memory, target_user_id="boxi_user")
    assert memory is not None
    assert memory["ProviderParams"]["filter"]["memory_type"] == ["profile_v1"]


def test_build_memory_config_disabled_without_collection(rtc_config: RtcConfig) -> None:
    assert build_memory_config(rtc_config, target_user_id="boxi_user") is None


def test_resolve_rtc_user_id_prefers_explicit(rtc_config: RtcConfig) -> None:
    assert resolve_rtc_user_id("custom-user", rtc_config) == "custom-user"
    assert resolve_rtc_user_id("", rtc_config) == "boxi_user"


def test_rtc_prepare_uses_stable_default_user_id(rtc_client: TestClient, rtc_config: RtcConfig) -> None:
    env = {
        "VOLC_RTC_APP_ID": rtc_config.rtc_app_id,
        "VOLC_RTC_APP_KEY": rtc_config.rtc_app_key,
        "VOLC_ACCESS_KEY": rtc_config.access_key,
        "VOLC_SECRET_KEY": rtc_config.secret_key,
        "DOUBAO_RT_APP_ID": rtc_config.rt_app_id,
        "DOUBAO_RT_ACCESS_TOKEN": rtc_config.rt_access_token,
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            response = rtc_client.post("/rtc/prepare", json={"mode": "pure"})
            assert response.status_code == 200
            assert response.json()["user_id"] == "boxi_user"


def test_rtc_status_reports_viking_memory_flag(rtc_client: TestClient, rtc_config: RtcConfig) -> None:
    env = {
        "VOLC_RTC_APP_ID": rtc_config.rtc_app_id,
        "VOLC_RTC_APP_KEY": rtc_config.rtc_app_key,
        "VOLC_ACCESS_KEY": rtc_config.access_key,
        "VOLC_SECRET_KEY": rtc_config.secret_key,
        "DOUBAO_RT_APP_ID": rtc_config.rt_app_id,
        "DOUBAO_RT_ACCESS_TOKEN": rtc_config.rt_access_token,
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            response = rtc_client.get("/rtc/status")
            assert response.status_code == 200
            data = response.json()
            assert data["viking_memory_enabled"] is False
            assert data["default_user_id"] == "boxi_user"


def test_mode_ready_hybrid_requires_soul(rtc_config: RtcConfig) -> None:
    assert mode_ready(rtc_config, "pure")
    assert mode_ready(rtc_config, "hybrid")
    incomplete = RtcConfig(**{**rtc_config.__dict__, "soul_public_url": ""})
    assert not mode_ready(incomplete, "hybrid")
