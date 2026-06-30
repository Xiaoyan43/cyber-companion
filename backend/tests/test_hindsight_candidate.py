"""Hindsight candidate adapter contract tests (offline, no SDK/network)."""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.memory.adapters.contract import (
    CandidateMemoryDTO,
    UnsupportedCandidateCapability,
)
from backend.app.memory.adapters.hindsight_candidate import HindsightCandidateBackend


class _FakeHindsightClient:
    def __init__(self) -> None:
        self.retain_calls: list[dict[str, object]] = []
        self.recall_calls: list[dict[str, object]] = []
        self.list_calls: list[dict[str, object]] = []
        self._by_bank: dict[str, list[dict[str, Any]]] = {}
        self._next_id = 1
        self._next_op = 1

    def retain(
        self,
        *,
        bank_id: str,
        content: str,
        context: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        self.retain_calls.append(
            {"bank_id": bank_id, "content": content, "context": context, "tags": tags}
        )
        memory_id = f"hs-{self._next_id}"
        self._next_id += 1
        operation_id = f"op-{self._next_op}"
        self._next_op += 1
        entry = {"id": memory_id, "text": content, "type": "unknown", "tags": tags or []}
        self._by_bank.setdefault(bank_id, []).append(entry)
        return {"success": True, "bank_id": bank_id, "items_count": 1, "operation_id": operation_id}

    def recall(self, *, bank_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        self.recall_calls.append({"bank_id": bank_id, "query": query, "limit": limit})
        matches = [
            item
            for item in self._by_bank.get(bank_id, [])
            if query.lower() in str(item.get("text", "")).lower()
        ]
        return {"results": matches[:limit]}

    def list_memories(self, *, bank_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        self.list_calls.append({"bank_id": bank_id, "limit": limit, "offset": offset})
        items = self._by_bank.get(bank_id, [])[offset : offset + limit]
        return {"items": items, "total": len(self._by_bank.get(bank_id, []))}


def test_hindsight_write_returns_operation_id_and_scopes_by_bank() -> None:
    client = _FakeHindsightClient()
    bank_a = HindsightCandidateBackend(client, bank_id="boxi-bank-a")
    bank_b = HindsightCandidateBackend(client, bank_id="boxi-bank-b")

    op_id = bank_a.write(
        CandidateMemoryDTO(type="stable_profile", content="我叫小明", importance=0.9, confidence=0.85)
    )
    assert op_id == "op-1"
    assert client.retain_calls[0]["bank_id"] == "boxi-bank-a"

    bank_b.write(CandidateMemoryDTO(type="project", content="在做赛博伴侣", importance=0.7, confidence=0.6))

    assert len(bank_a.list_all()) == 1
    assert len(bank_b.list_all()) == 1
    assert bank_a.list_all()[0].content == "我叫小明"
    assert bank_b.list_all()[0].content == "在做赛博伴侣"


def test_hindsight_search_scopes_to_bank_id() -> None:
    client = _FakeHindsightClient()
    backend = HindsightCandidateBackend(client, bank_id="boxi-bank-a")
    backend.write(CandidateMemoryDTO(type="project", content="赛博伴侣项目", importance=0.8, confidence=0.7))

    hits = backend.search("赛博", limit=5)

    assert len(hits) == 1
    assert hits[0].content == "赛博伴侣项目"
    assert client.recall_calls == [{"bank_id": "boxi-bank-a", "query": "赛博", "limit": 5}]


def test_hindsight_delete_is_explicitly_unsupported() -> None:
    backend = HindsightCandidateBackend(_FakeHindsightClient(), bank_id="boxi-bank-a")
    with pytest.raises(UnsupportedCandidateCapability) as exc:
        backend.delete("hs-1")
    assert exc.value.backend == "hindsight"
    assert exc.value.capability == "delete"


def test_hindsight_capabilities_match_real_sdk_limits() -> None:
    backend = HindsightCandidateBackend(_FakeHindsightClient(), bank_id="boxi-bank-a")
    caps = backend.capabilities
    assert caps.scoped_write
    assert caps.scoped_search
    assert not caps.delete
    assert caps.export_list
    assert caps.semantic_search
