"""Viking AddSession proxy for RTC VM-3."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.rtc.config import RtcConfig
from backend.app.rtc.routes import router as rtc_router
from backend.app.rtc.viking_memory import (
    format_memories_for_system_role,
    merge_subtitle_turns,
)
from backend.app.rtc.voice_chat import build_voice_chat_body


@pytest.fixture
def rtc_client() -> TestClient:
    app = FastAPI()
    app.include_router(rtc_router)
    return TestClient(app)


@pytest.fixture
def viking_rtc_config() -> RtcConfig:
    return RtcConfig(
        rtc_app_id="0123456789abcdef01234567",
        rtc_app_key="test-app-key",
        access_key="AKTEST",
        secret_key="SKTEST",
        rt_app_id="1234567890",
        rt_access_token="rt-token",
        rt_speaker="zh_male_yunzhou_jupiter_bigtts",
        rt_model="1.2.1.1",
        rt_series="o",
        soul_public_url="https://example.com/v1/chat/completions",
        soul_api_key="soul-key",
        welcome_pure="hi pure",
        welcome_hybrid="hi hybrid",
        bot_user_pure="BoxiBot",
        bot_user_hybrid="BoxiHybridBot",
        task_pure="BoxiTask01",
        task_hybrid="BoxiHybridTask01",
        default_user_id="boxi_user",
        viking_memory_api_key="viking-test-key",
        viking_memory_collection="boxi_memory",
        viking_memory_project="default",
        viking_memory_host="https://api-knowledgebase.mlp.cn-beijing.volces.com",
        viking_memory_assistant_id="",
        viking_memory_limit=3,
        viking_memory_transition_words="",
        viking_memory_types=(),
        enable_asr_twopass=False,
        enable_music=True,
    )


def test_format_memories_for_system_role() -> None:
    block = format_memories_for_system_role(
        [
            {"memory_type": "event_v1", "memory_info": {"summary": "用户叫 Alex，在海岛市找工作"}},
            {
                "memory_type": "profile_v1",
                "memory_info": {
                    "user_profile": '{"基础信息": {"昵称": "Alex", "常驻城市": "海岛市"}}'
                },
            },
        ]
    )
    assert "Alex" in block
    assert "【用户档案】" in block
    assert "必须以【用户档案】为准" in block


def test_format_memories_skips_contradictory_events() -> None:
    block = format_memories_for_system_role(
        [
            {
                "memory_type": "profile_v1",
                "memory_info": {
                    "user_profile": '{"基础信息": {"昵称": "Alex", "常驻城市": "海岛市"}}'
                },
            },
            {
                "memory_type": "event_v1",
                "memory_info": {
                    "summary": "用户询问助手是否记得自己的名字，助手表示用户还未告知"
                },
            },
        ]
    )
    assert "Alex" in block
    assert "还未告知" not in block


def test_build_voice_chat_appends_memory_context(viking_rtc_config: RtcConfig) -> None:
    body = build_voice_chat_body(
        viking_rtc_config,
        mode="pure",
        room_id="room-a",
        target_user_id="boxi_user",
        memory_context="【长期记忆】\n- 用户叫 Alex",
    )
    system_role = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]["system_role"]
    assert "Alex" in system_role


def test_merge_subtitle_turns_combines_same_speaker() -> None:
    messages = merge_subtitle_turns(
        [
            {"speaker": "user", "text": "我叫"},
            {"speaker": "user", "text": "小王"},
            {"speaker": "boxi", "text": "行吧小王。"},
        ]
    )
    assert messages == [
        {"role": "user", "content": "我叫小王"},
        {"role": "assistant", "content": "行吧小王。"},
    ]


@patch("backend.app.rtc.routes.add_memory_session")
def test_rtc_memory_session(
    mock_add: MagicMock,
    rtc_client: TestClient,
    viking_rtc_config: RtcConfig,
) -> None:
    mock_add.return_value = {
        "session_id": "rtc_abc123",
        "message_count": 2,
        "response": {"code": 0},
    }
    with patch("backend.app.rtc.routes.load_rtc_config", return_value=viking_rtc_config):
        response = rtc_client.post(
            "/rtc/memory/session",
            json={
                "room_id": "room-1",
                "user_id": "boxi_user",
                "bot_user_id": "BoxiBot",
                "subtitles": [
                    {"speaker": "user", "text": "我副业叫 Acme"},
                    {"speaker": "boxi", "text": "记住了。"},
                ],
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["message_count"] == 2
    mock_add.assert_called_once()
    call_messages = mock_add.call_args.kwargs["messages"]
    assert call_messages[0]["content"] == "我副业叫 Acme"


def test_rtc_memory_session_requires_transcript(
    rtc_client: TestClient,
    viking_rtc_config: RtcConfig,
) -> None:
    with patch("backend.app.rtc.routes.load_rtc_config", return_value=viking_rtc_config):
        response = rtc_client.post(
            "/rtc/memory/session",
            json={"user_id": "boxi_user", "subtitles": []},
        )
    assert response.status_code == 400
