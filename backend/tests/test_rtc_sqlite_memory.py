"""VM-4 — SQLite summary/facts inject into RTC system_role."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.memory.store import MemoryStore
from backend.app.rtc.config import RtcConfig
from backend.app.rtc.routes import router as rtc_router
from backend.app.rtc.sqlite_memory import format_sqlite_memory_for_system_role, sqlite_memory_has_content
from backend.app.rtc.voice_chat import build_voice_chat_body


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "rtc_sqlite.db")


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


def _seed_messages(store: MemoryStore, count: int) -> None:
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"turn-{index + 1}")


def test_format_sqlite_memory_includes_summary_and_facts(store: MemoryStore) -> None:
    _seed_messages(store, 4)
    store.create_conversation_summary(
        range_start_message_id=1,
        range_end_message_id=4,
        summary="用户说明天要去 Acme 面试后端岗位。",
        keywords=["面试", "Acme"],
    )
    store.create_memory(
        type="job_progress",
        content="已投递 Acme 后端工程师岗位。",
        importance=0.9,
    )
    store.create_memory(
        type="relationship_state",
        content="用户最近压力大，但愿意继续聊求职。",
        importance=0.5,
    )

    block = format_sqlite_memory_for_system_role(store)

    assert "近期对话原文" in block
    assert "turn-4" in block
    assert "文字聊天摘要" in block
    assert "Acme" in block
    assert "文字聊天印象" in block
    assert "文字聊天要点" in block
    assert "已投递 Acme" in block


def test_format_sqlite_memory_empty_store_returns_empty(store: MemoryStore) -> None:
    assert format_sqlite_memory_for_system_role(store) == ""


def test_format_sqlite_memory_includes_recent_chat_without_summary(store: MemoryStore) -> None:
    store.create_message(role="user", content="我下周要去 Stripe 面试后端。")
    store.create_message(role="assistant", content="行吧，又去面试。")

    block = format_sqlite_memory_for_system_role(store)

    assert "用户说过的事" in block
    assert "Stripe" in block
    assert "近期对话原文" in block
    assert "又去面试" in block
    assert "文字聊天摘要" not in block
    assert "间接提问" in block


def test_format_sqlite_memory_extracts_tomorrow_plan_for_implicit_questions(
    store: MemoryStore,
) -> None:
    store.create_message(role="user", content="我明天要去吃盖浇饭。")
    store.create_message(role="assistant", content="行，别噎着。")

    block = format_sqlite_memory_for_system_role(store)

    assert "【用户说过的事】" in block
    assert "盖浇饭" in block
    assert "明天" in block


def test_build_voice_chat_merges_sqlite_and_viking_blocks(
    store: MemoryStore,
    rtc_config: RtcConfig,
) -> None:
    _seed_messages(store, 2)
    store.create_conversation_summary(
        range_start_message_id=1,
        range_end_message_id=2,
        summary="用户偏好简短回复。",
        keywords=["偏好"],
    )
    sqlite_block = format_sqlite_memory_for_system_role(store)
    viking_block = "【长期记忆】\n- 用户叫 Alex"
    body = build_voice_chat_body(
        rtc_config,
        mode="pure",
        room_id="room-a",
        target_user_id="boxi_user",
        memory_context=f"{sqlite_block}\n\n{viking_block}",
    )
    system_role = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]["system_role"]
    assert "用户偏好简短回复" in system_role
    assert "Alex" in system_role


@patch("backend.app.rtc.routes.start_voice_chat")
def test_rtc_agent_start_injects_sqlite_context(
    mock_start: MagicMock,
    rtc_client: TestClient,
    rtc_config: RtcConfig,
    store: MemoryStore,
) -> None:
    _seed_messages(store, 2)
    store.create_conversation_summary(
        range_start_message_id=1,
        range_end_message_id=2,
        summary="用户正在准备产品经理面试。",
        keywords=["面试"],
    )
    mock_start.return_value = {"Result": "ok"}

    with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
        with patch("backend.app.rtc.routes.get_memory_store", return_value=store):
            response = rtc_client.post(
                "/rtc/agent/start",
                json={"mode": "pure", "room_id": "room-1", "user_id": "boxi_user"},
            )

    assert response.status_code == 200
    mock_start.assert_called_once()
    memory_context = mock_start.call_args.kwargs["memory_context"]
    assert "产品经理面试" in memory_context


@patch("backend.app.rtc.routes.load_rtc_config")
def test_rtc_status_reports_sqlite_memory_ready(
    mock_load_config: MagicMock,
    rtc_client: TestClient,
    rtc_config: RtcConfig,
    store: MemoryStore,
) -> None:
    mock_load_config.return_value = rtc_config
    store.create_message(role="user", content="记得我说要去吃火锅吗？")

    with patch("backend.app.rtc.routes.get_memory_store", return_value=store):
        response = rtc_client.get("/rtc/status")

    assert response.status_code == 200
    assert response.json()["sqlite_memory_ready"] is True
    assert sqlite_memory_has_content(store) is True
