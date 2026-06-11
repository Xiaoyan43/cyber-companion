"""PS-3 / PS-4 — join-time kernel stance block for RTC."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.memory.store import MemoryStore
from backend.app.rtc.config import RtcConfig
from backend.app.rtc.routes import _load_rtc_memory_context, router as rtc_router
from backend.app.rtc.state_block import build_rtc_state_block, build_rtc_steering_directive
from backend.app.rtc.voice_chat import build_voice_chat_body


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "rtc_state_block.db")


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
    )


def _neutral_kernel(store: MemoryStore) -> None:
    store.update_mood_state(
        annoyance=0.1,
        worry=0.1,
        loneliness=0.1,
        boredom=0.1,
        energy=0.5,
    )
    store.update_relationship_state(trust=0.5, closeness=0.5, tension=0.1)


def test_fully_neutral_kernel_returns_empty_blocks(store: MemoryStore) -> None:
    _neutral_kernel(store)
    assert build_rtc_state_block(store) == ""
    assert build_rtc_steering_directive(store) == ""


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("annoyance", "有点烦躁"),
        ("worry", "有点担心ta"),
        ("loneliness", "有点想找人说话"),
        ("boredom", "有点无聊"),
    ],
)
def test_state_block_mood_branches(
    store: MemoryStore,
    field: str,
    label: str,
) -> None:
    _neutral_kernel(store)
    store.update_mood_state(**{field: 0.6})
    block = build_rtc_state_block(store)
    assert "【你此刻的状态】" in block
    assert f"情绪：{label}" in block


def test_state_block_low_energy_mood_line(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_mood_state(energy=0.2)
    block = build_rtc_state_block(store)
    assert "情绪：没什么精神" in block


@pytest.mark.parametrize(
    ("trust", "closeness", "tension", "expected_fragment"),
    [
        (0.2, 0.2, 0.1, "信任低、亲近低"),
        (0.5, 0.2, 0.1, "信任中、亲近低"),
        (0.8, 0.8, 0.1, "信任高、亲近高"),
        (0.5, 0.5, 0.5, "信任中、亲近中、有点别扭"),
    ],
)
def test_state_block_relationship_buckets(
    store: MemoryStore,
    trust: float,
    closeness: float,
    tension: float,
    expected_fragment: str,
) -> None:
    _neutral_kernel(store)
    store.update_relationship_state(trust=trust, closeness=closeness, tension=tension)
    block = build_rtc_state_block(store)
    assert expected_fragment in block


def test_steering_worry_comfort_directive(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_mood_state(worry=0.6)
    assert build_rtc_steering_directive(store) == "用户最近不太好，收一收毒舌，话短一点、稳一点。"


def test_steering_annoyance_terse_directive(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_mood_state(annoyance=0.6)
    assert (
        build_rtc_steering_directive(store)
        == "你对最近的互动有点不耐烦，可以更冲、更短，但别真羞辱用户。"
    )


def test_steering_tension_terse_directive(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_relationship_state(tension=0.5)
    assert (
        build_rtc_steering_directive(store)
        == "你对最近的互动有点不耐烦，可以更冲、更短，但别真羞辱用户。"
    )


def test_steering_high_closeness_warmer_directive(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_relationship_state(closeness=0.75, tension=0.1)
    assert build_rtc_steering_directive(store) == "你和ta挺熟了，可以更随意、更贴一点，毒舌底色别丢。"


def test_steering_worry_beats_annoyance(store: MemoryStore) -> None:
    _neutral_kernel(store)
    store.update_mood_state(worry=0.6, annoyance=0.7)
    assert build_rtc_steering_directive(store) == "用户最近不太好，收一收毒舌，话短一点、稳一点。"


def test_merged_context_prepends_state_before_sqlite(
    store: MemoryStore,
    rtc_config: RtcConfig,
) -> None:
    store.update_mood_state(annoyance=0.6)
    store.update_relationship_state(trust=0.8, closeness=0.8, tension=0.1)
    store.create_message(role="user", content="我明天要去面试。")

    with patch("backend.app.rtc.routes.get_memory_store", return_value=store):
        merged = _load_rtc_memory_context(rtc_config, "boxi_user")

    state_pos = merged.find("【你此刻的状态】")
    sqlite_pos = merged.find("近期对话原文")
    assert state_pos != -1
    assert sqlite_pos != -1
    assert state_pos < sqlite_pos
    assert "有点烦躁" in merged
    assert "可以更冲、更短" in merged


def test_build_voice_chat_system_role_includes_state_block(
    store: MemoryStore,
    rtc_config: RtcConfig,
) -> None:
    store.update_mood_state(worry=0.6)
    store.update_relationship_state(trust=0.5, closeness=0.5, tension=0.1)

    state_block = build_rtc_state_block(store)
    steering = build_rtc_steering_directive(store)
    memory_context = "\n\n".join(part for part in (state_block, steering) if part)

    body = build_voice_chat_body(
        rtc_config,
        mode="pure",
        room_id="room-a",
        target_user_id="boxi_user",
        memory_context=memory_context,
    )
    system_role = body["Config"]["S2SConfig"]["ProviderParams"]["dialog"]["system_role"]
    assert "【你此刻的状态】" in system_role
    assert "有点担心ta" in system_role
    assert "收一收毒舌" in system_role


@patch("backend.app.rtc.routes.start_voice_chat")
def test_rtc_agent_start_injects_state_block(
    mock_start,
    rtc_config: RtcConfig,
    store: MemoryStore,
) -> None:
    store.update_mood_state(annoyance=0.6)
    mock_start.return_value = {"Result": "ok"}

    app = FastAPI()
    app.include_router(rtc_router)
    client = TestClient(app)

    with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
        with patch("backend.app.rtc.routes.get_memory_store", return_value=store):
            response = client.post(
                "/rtc/agent/start",
                json={"mode": "pure", "room_id": "room-1", "user_id": "boxi_user"},
            )

    assert response.status_code == 200
    memory_context = mock_start.call_args.kwargs["memory_context"]
    assert "【你此刻的状态】" in memory_context
    assert "有点烦躁" in memory_context
