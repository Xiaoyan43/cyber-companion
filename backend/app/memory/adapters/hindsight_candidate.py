"""Hindsight candidate backend (Phase 5 spike — not production).

Uses injected client only; no SDK import or network I/O in this module. The
injected client is expected to expose plain ``dict`` responses (matching
``HindsightClientProtocol`` below) — callers wiring up the *real*
``hindsight-client`` SDK (which returns typed Pydantic response objects, e.g.
``RetainResponse``/``RecallResponse``) must wrap it in a thin adapter that
calls ``.model_dump()`` before handing results to this backend. See
``backend/scripts/memory_backend_ab.py`` for that adapter.

Hindsight's HTTP API (https://hindsight.vectorize.io/api-reference) scopes
memories under a ``bank_id`` and runs ``retain`` through fact extraction: one
``retain`` call can split into multiple stored facts. ``operation_id`` is only
populated when ``retain_async=True`` — verified against a real running server
(0.8.3): a synchronous retain (the default, and what this candidate uses)
returns ``operation_id=None`` and ``operation_ids=None``, with no per-call id
at all, just ``success``/``items_count``/``usage``. ``write()`` therefore
returns a non-unique placeholder (``"sync:<bank_id>"``) when no operation id
is present — it cannot be used to look up or delete the specific fact(s)
just written. Combined with delete being unsupported (below), this candidate
has no per-record identity at all in its default sync mode; only
``list_all``/``search`` see realized facts after extraction settles.

**Delete is explicitly unsupported** (verified against the real
``hindsight-client`` 0.8.3 SDK source, not just docs): the client only exposes
``clear_bank_memories`` (whole-bank wipe, optionally type-filtered) and
``update_memory``; there is no per-memory-id delete. Mirrors Letta's
"explicitly unsupported" pattern for capabilities the real backend can't do.
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.app.memory.adapters.contract import (
    CandidateMemoryCapabilities,
    CandidateMemoryDTO,
    UnsupportedCandidateCapability,
    _require_capability,
)


class HindsightClientProtocol(Protocol):
    """Minimal Hindsight client surface for bank-scoped memory write/search/list.

    Shaped as plain dicts (not the real SDK's Pydantic response objects) —
    see module docstring.
    """

    def retain(
        self,
        *,
        bank_id: str,
        content: str,
        context: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]: ...

    def recall(
        self,
        *,
        bank_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]: ...

    def list_memories(
        self,
        *,
        bank_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]: ...


def _result_to_dto(item: dict[str, Any]) -> CandidateMemoryDTO:
    metadata = dict(item.get("metadata") or {})
    mem_type = str(item.get("type") or metadata.get("memory_type") or "unknown")
    tags_raw = item.get("tags") or metadata.get("tags") or []
    tags = tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, list) else ()
    return CandidateMemoryDTO(
        id=str(item.get("id") or ""),
        type=mem_type,
        content=str(item.get("text") or item.get("content") or ""),
        tags=tags,
        importance=float(metadata.get("importance", 0.5)),
        confidence=float(metadata.get("confidence", 0.5)),
        source_message_id=_optional_int(metadata.get("source_message_id")),
        metadata=metadata,
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _unwrap_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return []


def _unwrap_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


class HindsightCandidateBackend:
    backend_name = "hindsight"

    def __init__(self, client: HindsightClientProtocol, *, bank_id: str) -> None:
        self._client = client
        self._bank_id = bank_id

    @property
    def namespace(self) -> str:
        return self._bank_id

    @property
    def capabilities(self) -> CandidateMemoryCapabilities:
        return CandidateMemoryCapabilities(
            scoped_write=True,
            scoped_search=True,
            delete=False,
            export_list=True,
            semantic_search=True,
        )

    def write(self, record: CandidateMemoryDTO) -> str:
        _require_capability(self, "scoped_write", supported=self.capabilities.scoped_write)
        metadata = {
            "memory_type": record.type,
            "type": record.type,
            "importance": record.importance,
            "confidence": record.confidence,
            "source_message_id": record.source_message_id,
            **record.metadata,
        }
        payload = self._client.retain(
            bank_id=self._bank_id,
            content=record.content,
            context=str(metadata),
            tags=list(record.tags),
        )
        operation_id = payload.get("operation_id")
        if operation_id is not None:
            return str(operation_id)
        if not payload.get("success", True):
            raise ValueError("hindsight retain response reported failure")
        return f"sync:{self._bank_id}"

    def search(self, query: str, *, limit: int = 10) -> list[CandidateMemoryDTO]:
        _require_capability(self, "scoped_search", supported=self.capabilities.scoped_search)
        payload = self._client.recall(bank_id=self._bank_id, query=query, limit=limit)
        return [_result_to_dto(item) for item in _unwrap_results(payload)]

    def delete(self, memory_id: str) -> None:
        _require_capability(self, "delete", supported=self.capabilities.delete)
        raise UnsupportedCandidateCapability(self.backend_name, "delete")

    def list_all(self, *, limit: int = 100) -> list[CandidateMemoryDTO]:
        _require_capability(self, "export_list", supported=self.capabilities.export_list)
        payload = self._client.list_memories(bank_id=self._bank_id, limit=limit)
        return [_result_to_dto(item) for item in _unwrap_items(payload)]
