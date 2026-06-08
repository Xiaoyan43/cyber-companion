from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import reset_memory_store
from backend.app.providers.deepseek import DeepSeekProvider, close_deepseek_http_client
from backend.app.providers.mock import MockProvider
from backend.app.providers.router import reset_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatMessage, StreamChunk


def parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    return events


@pytest.fixture(autouse=True)
def reset_router() -> None:
    close_deepseek_http_client()
    reset_memory_store()
    reset_provider_router()
    yield
    close_deepseek_http_client()
    reset_memory_store()
    reset_provider_router()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return TestClient(app)


def test_chat_stream_emits_deltas_then_done(client: TestClient) -> None:
    before = client.get("/memory/messages").json()["messages"]
    response = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "你好流式"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)
    assert len(events) >= 2
    assert events[0]["type"] == "delta"
    assert events[-1]["type"] == "done"

    delta_text = "".join(event["text"] for event in events if event["type"] == "delta")
    assert "你好流式" in delta_text

    meta = events[-1]["meta"]
    assert meta["provider"] == "mock"
    assert meta["should_call_llm"] is True
    assert meta["usage"]["total_tokens"] > 0

    after = client.get("/memory/messages").json()["messages"]
    assert len(after) == len(before) + 2


def test_chat_stream_persists_turn_once_and_runs_auto_memory_write(client: TestClient) -> None:
    before = client.get("/memory/messages").json()["messages"]
    response = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "记住我今晚要改简历"}]},
    )
    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events[-1]["type"] == "done"

    messages = client.get("/memory/messages").json()["messages"]
    assert len(messages) == len(before) + 2

    memories = client.get("/memory/memories", params={"type": "reminder"}).json()["memories"]
    assert len(memories) == 1
    assert "今晚要改简历" in memories[0]["content"]


def test_chat_stream_budget_block_emits_local_done(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.main as main_module

    monkeypatch.setattr(
        main_module,
        "load_budget_config",
        lambda: BudgetConfig(daily_llm_turn_limit=1),
    )

    first = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "在吗朋友"}]},
    )
    assert parse_sse_events(first.text)[-1]["meta"]["should_call_llm"] is True

    second = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "再聊聊"}]},
    )
    events = parse_sse_events(second.text)
    assert [event["type"] for event in events] == ["delta", "done"]

    meta = events[-1]["meta"]
    assert meta["should_call_llm"] is False
    assert meta["provider"] == "local-budget"
    assert meta["cost"]["total_usd"] == 0.0


def test_chat_stream_mid_stream_error_does_not_persist_turn(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenMockProvider(MockProvider):
        def complete_stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
            yield ("delta", "半截")
            raise RuntimeError("stream blew up")

    import backend.app.providers.router as router_module

    original_build = router_module.build_providers

    def build_with_broken_mock(config):  # type: ignore[no-untyped-def]
        providers = original_build(config)
        providers["mock"] = BrokenMockProvider()
        return providers

    monkeypatch.setattr(router_module, "build_providers", build_with_broken_mock)
    reset_provider_router()

    before = client.get("/memory/messages").json()["messages"]
    response = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "会炸吗"}]},
    )
    events = parse_sse_events(response.text)
    assert events[0]["type"] == "delta"
    assert events[-1]["type"] == "error"

    after = client.get("/memory/messages").json()["messages"]
    assert len(after) == len(before)


def test_deepseek_complete_stream_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured: dict[str, object] = {}

    class FakeStreamResponse:
        status_code = 200

        def __enter__(self) -> "FakeStreamResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def iter_lines(self) -> list[str]:
            return [
                'data: {"choices":[{"delta":{"content":"hel"}}]}',
                'data: {"choices":[{"delta":{"content":"lo"}}]}',
                'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
                "data: [DONE]",
            ]

        def read(self) -> bytes:
            return b""

        @property
        def reason_phrase(self) -> str:
            return "OK"

    class FakeClient:
        def stream(
            self,
            method: str,
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, object],
        ) -> FakeStreamResponse:
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeStreamResponse()

    provider = DeepSeekProvider(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        http_client=FakeClient(),  # type: ignore[arg-type]
    )

    chunks = list(
        provider.complete_stream(
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="hi")],
                max_output_tokens=32,
            ),
        ),
    )

    assert captured["json"]["stream"] is True
    assert captured["json"]["stream_options"] == {"include_usage": True}
    assert chunks == [
        ("delta", "hel"),
        ("delta", "lo"),
        ("usage", chunks[-1][1]),
    ]
    assert chunks[-1][1].total_tokens == 7
