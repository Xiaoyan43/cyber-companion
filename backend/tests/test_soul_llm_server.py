from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.behavior.parser import SIGNALS_SENTINEL
from backend.app.memory.store import get_memory_store, reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.providers.types import ChatCompletionRequest, ProviderStatus, TokenUsage
from backend.realtime.companion_brain import CompanionBrain
from backend.realtime.soul_llm_server import (
    app,
    create_app,
    extract_latest_user_text,
)
from backend.realtime.soul_llm_server import ChatMessagePayload as SoulChatMessage


pytest.importorskip("fastapi")


def parse_openai_sse(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.split("\n\n"):
        block = block.strip()
        if block == "data: [DONE]":
            continue
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    return events


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_memory_store()
    reset_provider_router()
    yield
    reset_memory_store()
    reset_provider_router()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    monkeypatch.setenv("SOUL_LLM_API_KEY", "test-soul-key")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return TestClient(create_app())


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-soul-key"}


def test_extract_latest_user_text_ignores_earlier_turns() -> None:
    messages = [
        SoulChatMessage(role="user", content="旧话"),
        SoulChatMessage(role="assistant", content="旧答"),
        SoulChatMessage(role="user", content="最新一句"),
    ]
    assert extract_latest_user_text(messages) == "最新一句"


def test_chat_completions_stream_openai_shape(client: TestClient) -> None:
    store = get_memory_store()
    before = len(store.list_messages())

    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers(),
        json={
            "model": "boxi-soul",
            "stream": True,
            "messages": [
                {"role": "user", "content": "你好 soul"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in response.text

    events = parse_openai_sse(response.text)
    assert events
    assert events[0]["object"] == "chat.completion.chunk"
    assert events[-1]["choices"][0]["finish_reason"] == "stop"

    delta_text = "".join(
        str(choice["delta"].get("content", ""))
        for event in events
        for choice in event["choices"]
        if choice.get("delta")
    )
    assert "你好 soul" in delta_text
    assert SIGNALS_SENTINEL not in delta_text

    after = len(store.list_messages())
    assert after == before + 2


def test_chat_completions_non_stream_openai_shape(client: TestClient) -> None:
    store = get_memory_store()
    before = len(store.list_messages())

    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers(),
        json={
            "model": "boxi-soul",
            "stream": False,
            "messages": [{"role": "user", "content": "非流式你好"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    content = payload["choices"][0]["message"]["content"]
    assert "非流式你好" in content
    assert SIGNALS_SENTINEL not in content
    assert payload["usage"]["total_tokens"] > 0

    after = len(store.list_messages())
    assert after == before + 2


def test_chat_completions_stream_strips_signal_trailer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = get_memory_store()
    brain = CompanionBrain(store)
    brain._provider_name = "mock"

    class _TrailerProvider:
        def status(self) -> ProviderStatus:
            return ProviderStatus(
                name="mock",
                model="mock-boxi",
                enabled=True,
                configured=True,
                api_key_present=False,
            )

        def complete_stream(self, request: ChatCompletionRequest, provider_name=None):
            visible = "记住了。"
            trailer = (
                f'\n{SIGNALS_SENTINEL}\n{{"avatar_state":"talking","decision":"reply",'
                f'"memory":[{{"type":"profile","content":"用户叫小明"}}]}}'
            )
            yield ("delta", visible + trailer)
            yield ("usage", TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15))

    brain._router.providers["mock"] = _TrailerProvider()  # type: ignore[assignment]

    import backend.realtime.soul_llm_server as soul_module

    def _store_with_brain():
        return store

    monkeypatch.setattr(soul_module, "get_memory_store", _store_with_brain)

    def _brain_factory(*args, **kwargs):
        return brain

    monkeypatch.setattr(soul_module, "CompanionBrain", _brain_factory)

    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers(),
        json={
            "stream": True,
            "messages": [{"role": "user", "content": "我叫小明"}],
        },
    )

    assert response.status_code == 200
    events = parse_openai_sse(response.text)
    delta_text = "".join(
        str(choice["delta"].get("content", ""))
        for event in events
        for choice in event["choices"]
        if choice.get("delta")
    )
    assert "记住了。" in delta_text
    assert SIGNALS_SENTINEL not in delta_text


def test_auth_rejects_missing_bearer(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 401


def test_module_app_is_created() -> None:
    assert app is not None
