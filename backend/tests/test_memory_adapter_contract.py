"""Phase 5 candidate memory adapter contract tests (offline, no SDK/network)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.behavior.parser import SIGNALS_SENTINEL
from backend.app.memory.adapters.contract import (
    CandidateMemoryDTO,
    UnsupportedCandidateCapability,
    memory_record_to_candidate_dto,
)
from backend.app.memory.adapters.letta_candidate import LettaCandidateBackend
from backend.app.memory.adapters.mem0_candidate import Mem0CandidateBackend
from backend.app.memory.adapters.shadow import ShadowMemoryPort
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MemoryRecord
from backend.app.memory.store import MemoryStore
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.mock import MockProvider
from backend.app.providers.router import get_provider_router, reset_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, TokenUsage
from backend.app.soul import PerceivedEvent, SoulTurnRuntime
from backend.app.soul.adapters import SQLiteMemoryPort, ports_from_store


class _FakeMem0Client:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, object]] = []
        self.search_calls: list[dict[str, object]] = []
        self.delete_calls: list[str] = []
        self.get_all_calls: list[dict[str, object]] = []
        self._by_user: dict[str, list[dict[str, object]]] = {}
        self._next_id = 1

    def add(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.add_calls.append(
            {"messages": messages, "user_id": user_id, "metadata": metadata}
        )
        memory_id = f"mem0-{self._next_id}"
        self._next_id += 1
        entry = {
            "id": memory_id,
            "memory": messages[0]["content"] if messages else "",
            "metadata": metadata or {},
        }
        self._by_user.setdefault(user_id, []).append(entry)
        return {"results": [entry]}

    def search(
        self,
        query: str,
        *,
        filters: dict[str, str],
        limit: int = 10,
    ) -> dict[str, object]:
        self.search_calls.append(
            {"query": query, "filters": filters, "limit": limit}
        )
        user_id = filters.get("user_id", "")
        matches = [
            item
            for item in self._by_user.get(user_id, [])
            if query.lower() in str(item.get("memory", "")).lower()
        ]
        return {"results": matches[:limit]}

    def delete(self, memory_id: str) -> None:
        self.delete_calls.append(memory_id)
        for entries in self._by_user.values():
            entries[:] = [item for item in entries if item.get("id") != memory_id]

    def get_all(self, *, user_id: str, limit: int = 100) -> dict[str, object]:
        self.get_all_calls.append({"user_id": user_id, "limit": limit})
        return {"results": self._by_user.get(user_id, [])[:limit]}


class _FakeLettaBlocksClient:
    def __init__(self) -> None:
        self.blocks: list[dict[str, object]] = []
        self._next_id = 1
        self.forbidden_calls: list[str] = []

    def list_blocks(self, *, agent_id: str | None = None) -> list[dict[str, object]]:
        return list(self.blocks)

    def create_block(
        self,
        *,
        label: str,
        value: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        block_id = f"letta-{self._next_id}"
        self._next_id += 1
        block = {"id": block_id, "label": label, "value": value, "metadata": metadata or {}}
        self.blocks.append(block)
        return block

    def update_block(
        self,
        block_id: str,
        *,
        label: str | None = None,
        value: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        for block in self.blocks:
            if block["id"] == block_id:
                if label is not None:
                    block["label"] = label
                if value is not None:
                    block["value"] = value
                if metadata is not None:
                    block["metadata"] = metadata
                return block
        raise KeyError(block_id)

    def delete_block(self, block_id: str) -> None:
        self.blocks = [block for block in self.blocks if block["id"] != block_id]

    def create_agent(self, *_args, **_kwargs) -> None:
        self.forbidden_calls.append("create_agent")
        raise AssertionError("Letta candidate must not call create_agent")

    def messages_create(self, *_args, **_kwargs) -> None:
        self.forbidden_calls.append("messages_create")
        raise AssertionError("Letta candidate must not call messages_create")


class _BrokenCandidate:
    backend_name = "broken"

    def __init__(self) -> None:
        self.write_attempts = 0

    @property
    def namespace(self) -> str:
        return "broken-ns"

    @property
    def capabilities(self):
        from backend.app.memory.adapters.contract import CandidateMemoryCapabilities

        return CandidateMemoryCapabilities(
            scoped_write=True,
            scoped_search=False,
            delete=False,
            export_list=False,
            semantic_search=False,
        )

    def write(self, record: CandidateMemoryDTO) -> str:
        self.write_attempts += 1
        raise RuntimeError("candidate unavailable")

    def search(self, query: str, *, limit: int = 10) -> list[CandidateMemoryDTO]:
        raise UnsupportedCandidateCapability(self.backend_name, "scoped_search")

    def delete(self, memory_id: str) -> None:
        raise UnsupportedCandidateCapability(self.backend_name, "delete")

    def list_all(self, *, limit: int = 100) -> list[CandidateMemoryDTO]:
        raise UnsupportedCandidateCapability(self.backend_name, "export_list")


@pytest.fixture(autouse=True)
def _router_env(monkeypatch: pytest.MonkeyPatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    reset_provider_router()
    yield
    reset_provider_router()


def test_mem0_maps_fields_and_isolates_namespace() -> None:
    client = _FakeMem0Client()
    user_a = Mem0CandidateBackend(client, user_id="boxi-user-a")
    user_b = Mem0CandidateBackend(client, user_id="boxi-user-b")

    dto = CandidateMemoryDTO(
        type="stable_profile",
        content="我叫小明",
        tags=("profile",),
        importance=0.9,
        confidence=0.85,
        source_message_id=42,
        metadata={"origin": "signal"},
    )
    memory_id = user_a.write(dto)
    assert memory_id == "mem0-1"
    assert client.add_calls[0]["user_id"] == "boxi-user-a"
    metadata = client.add_calls[0]["metadata"]
    assert metadata["memory_type"] == "stable_profile"
    assert metadata["tags"] == ["profile"]
    assert metadata["importance"] == 0.9
    assert metadata["confidence"] == 0.85
    assert metadata["source_message_id"] == 42
    assert metadata["origin"] == "signal"

    user_b.write(
        CandidateMemoryDTO(type="project", content="在做赛博伴侣", importance=0.7, confidence=0.6)
    )
    assert user_a.list_all() != user_b.list_all()
    assert len(user_a.list_all()) == 1
    assert len(user_b.list_all()) == 1
    assert user_a.list_all()[0].content == "我叫小明"
    assert user_b.list_all()[0].content == "在做赛博伴侣"


def test_mem0_search_uses_filters_user_id() -> None:
    client = _FakeMem0Client()
    backend = Mem0CandidateBackend(client, user_id="boxi-user-a")
    backend.write(CandidateMemoryDTO(type="project", content="赛博伴侣项目", importance=0.8, confidence=0.7))
    hits = backend.search("赛博", limit=5)

    assert len(hits) == 1
    assert hits[0].type == "project"
    assert hits[0].content == "赛博伴侣项目"
    assert client.search_calls == [
        {"query": "赛博", "filters": {"user_id": "boxi-user-a"}, "limit": 5}
    ]


def test_letta_blocks_crud_without_agent_or_message_api() -> None:
    client = _FakeLettaBlocksClient()
    backend = LettaCandidateBackend(client, namespace="boxi-ns")

    block_id = backend.write(
        CandidateMemoryDTO(
            type="stable_profile",
            content="我叫小明",
            tags=("profile",),
            importance=0.9,
            confidence=0.8,
            source_message_id=7,
        )
    )
    assert block_id == "letta-1"
    assert client.forbidden_calls == []
    assert client.blocks[0]["label"] == "boxi_mem:boxi-ns:stable_profile"
    assert client.blocks[0]["metadata"]["namespace"] == "boxi-ns"
    assert client.blocks[0]["metadata"]["source_message_id"] == 7

    listed = backend.list_all()
    assert len(listed) == 1
    assert listed[0].content == "我叫小明"
    assert listed[0].type == "stable_profile"

    backend.delete(block_id)
    assert backend.list_all() == []


def test_letta_search_is_explicitly_unsupported() -> None:
    client = _FakeLettaBlocksClient()
    backend = LettaCandidateBackend(client, namespace="boxi-ns")
    with pytest.raises(UnsupportedCandidateCapability) as exc:
        backend.search("小明")
    assert exc.value.backend == "letta"
    assert exc.value.capability == "scoped_search"
    assert client.forbidden_calls == []


def test_memory_record_to_candidate_dto_roundtrip_fields() -> None:
    record = MemoryRecord(
        id=11,
        created_at="2000-01-01T00:00:00+00:00",
        updated_at="2000-01-01T00:00:00+00:00",
        type="project",
        content="在做赛博伴侣",
        tags=["dev"],
        importance=0.75,
        confidence=0.65,
        expires_at=None,
        source_message_id=3,
        metadata={"writer": "signal"},
    )
    dto = memory_record_to_candidate_dto(record)
    assert dto.id == "11"
    assert dto.type == "project"
    assert dto.tags == ("dev",)
    assert dto.source_message_id == 3
    assert dto.metadata == {"writer": "signal"}


def _kernel_snapshot(store: MemoryStore) -> dict[str, object]:
    mood = store.get_mood_state()
    rel = store.get_relationship_state()
    return {
        "mood": mood.mood,
        "energy": round(mood.energy, 6),
        "trust": round(rel.trust, 6),
        "closeness": round(rel.closeness, 6),
    }


def _memory_snapshot(store: MemoryStore) -> list[tuple]:
    return sorted(
        (
            memory.type,
            memory.content,
            round(memory.importance, 6),
            round(memory.confidence, 6),
            memory.source_message_id,
        )
        for memory in store.list_memories(limit=200)
    )


class _FixedReplyProvider(MockProvider):
    _RAW = (
        "记下了。\n"
        f"{SIGNALS_SENTINEL}\n"
        + json.dumps(
            {
                "avatar_state": "talking",
                "decision": "reply",
                "memory": [
                    {
                        "type": "stable_profile",
                        "content": "用户在做赛博伴侣项目",
                        "importance": 0.8,
                        "confidence": 0.9,
                    }
                ],
            },
            ensure_ascii=False,
        )
    )

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        usage = TokenUsage(input_tokens=32, output_tokens=8, total_tokens=40)
        return ChatCompletionResult(
            provider=self.name,
            model="mock-boxi",
            content=self._RAW,
            usage=usage,
            cost=estimate_cost("mock-boxi", usage),
            mock=True,
        )


def test_shadow_port_preserves_sqlite_turn_side_effects(tmp_path: Path) -> None:
    store_plain = MemoryStore(db_path=tmp_path / "plain.db")
    store_shadow = MemoryStore(db_path=tmp_path / "shadow.db")
    router = get_provider_router()
    router.providers["mock"] = _FixedReplyProvider()
    budget = BudgetConfig()
    user_input = "我想跟你认真聊聊我最近在忙的事"

    SoulTurnRuntime(store=store_plain, router=router, budget=budget).run_turn(
        PerceivedEvent(event_type="user_message", user_input=user_input, surface="text")
    )

    candidate = _BrokenCandidate()
    diagnostics: list[tuple[str, dict[str, object]]] = []
    canonical = SQLiteMemoryPort(store_shadow)
    shadow = ShadowMemoryPort(
        canonical,
        candidate,
        diagnostics=lambda event, payload: diagnostics.append((event, payload)),
    )
    SoulTurnRuntime(
        ports=replace(ports_from_store(store_shadow), memory=shadow),
        router=router,
        budget=budget,
    ).run_turn(
        PerceivedEvent(event_type="user_message", user_input=user_input, surface="text")
    )

    assert _kernel_snapshot(store_plain) == _kernel_snapshot(store_shadow)
    assert _memory_snapshot(store_plain) == _memory_snapshot(store_shadow)
    assert store_plain.count_chat_messages() == store_shadow.count_chat_messages()
    assert (
        store_plain.count_llm_turns_since("2000-01-01 00:00:00")
        == store_shadow.count_llm_turns_since("2000-01-01 00:00:00")
    )
    assert candidate.write_attempts == 1
    assert any(event == "candidate_mirror_failed" for event, _payload in diagnostics)
    assert all("content" not in payload for _event, payload in diagnostics)


def test_shadow_port_canonical_commit_succeeds_when_candidate_raises(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "commit.db")
    candidate = _BrokenCandidate()
    shadow = ShadowMemoryPort(SQLiteMemoryPort(store), candidate)
    usage = estimate_usage(["记住 我叫小明"], "记下了。")
    result = ChatCompletionResult(
        provider="local-test",
        model="local-test",
        content="记下了。",
        usage=usage,
        cost=estimate_cost("mock-boxi", usage),
        mock=True,
    )
    saved_ids = shadow.persist_turn(
        user_input="记住 我叫小明",
        result=result,
        decision="reply",
        avatar_state="talking",
        should_call_llm=False,
    )
    records = shadow.record_turn_memories(
        user_input="记住 我叫小明",
        signals=None,
        source_message_id=saved_ids[0],
        budget=BudgetConfig(),
    )

    assert saved_ids == [1, 2]
    assert store.count_chat_messages() == 2
    assert len(records) >= 1
    assert sorted(memory.content for memory in store.list_memories()) == [
        "User profile: 小明",
        "我叫小明",
    ]
