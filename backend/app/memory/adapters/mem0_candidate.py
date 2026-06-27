"""Mem0 candidate backend (Phase 5 spike — not production).

Uses injected client only; no SDK import or network I/O in this module.
Mem0 ``search`` must use ``filters={"user_id": ...}`` (current API shape).
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.app.memory.adapters.contract import (
    CandidateMemoryCapabilities,
    CandidateMemoryDTO,
    _require_capability,
)


class Mem0ClientProtocol(Protocol):
    def add(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def search(
        self,
        query: str,
        *,
        filters: dict[str, str],
        limit: int = 10,
    ) -> dict[str, Any]: ...

    def delete(self, memory_id: str) -> None: ...

    def get_all(
        self,
        *,
        user_id: str,
        limit: int = 100,
    ) -> dict[str, Any]: ...


def _mem0_result_to_dto(raw: dict[str, Any]) -> CandidateMemoryDTO:
    metadata = dict(raw.get("metadata") or {})
    mem_type = str(metadata.get("memory_type") or metadata.get("type") or "unknown")
    tags_raw = metadata.get("tags") or []
    tags = tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, list) else ()
    return CandidateMemoryDTO(
        id=str(raw.get("id") or raw.get("memory_id") or ""),
        type=mem_type,
        content=str(raw.get("memory") or raw.get("content") or ""),
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
    if isinstance(payload.get("memories"), list):
        return [item for item in payload["memories"] if isinstance(item, dict)]
    return []


class Mem0CandidateBackend:
    backend_name = "mem0"

    def __init__(self, client: Mem0ClientProtocol, *, user_id: str) -> None:
        self._client = client
        self._user_id = user_id

    @property
    def namespace(self) -> str:
        return self._user_id

    @property
    def capabilities(self) -> CandidateMemoryCapabilities:
        return CandidateMemoryCapabilities(
            scoped_write=True,
            scoped_search=True,
            delete=True,
            export_list=True,
            semantic_search=True,
        )

    def write(self, record: CandidateMemoryDTO) -> str:
        _require_capability(self, "scoped_write", supported=self.capabilities.scoped_write)
        metadata = {
            "memory_type": record.type,
            "type": record.type,
            "tags": list(record.tags),
            "importance": record.importance,
            "confidence": record.confidence,
            "source_message_id": record.source_message_id,
            **record.metadata,
        }
        payload = self._client.add(
            messages=[{"role": "user", "content": record.content}],
            user_id=self._user_id,
            metadata=metadata,
        )
        memory_id = payload.get("id") or payload.get("memory_id")
        if memory_id is None and isinstance(payload.get("results"), list):
            first = payload["results"][0] if payload["results"] else {}
            if isinstance(first, dict):
                memory_id = first.get("id") or first.get("memory_id")
        if memory_id is None:
            raise ValueError("mem0 add response missing memory id")
        return str(memory_id)

    def search(self, query: str, *, limit: int = 10) -> list[CandidateMemoryDTO]:
        _require_capability(self, "scoped_search", supported=self.capabilities.scoped_search)
        payload = self._client.search(
            query,
            filters={"user_id": self._user_id},
            limit=limit,
        )
        return [_mem0_result_to_dto(item) for item in _unwrap_results(payload)]

    def delete(self, memory_id: str) -> None:
        _require_capability(self, "delete", supported=self.capabilities.delete)
        self._client.delete(memory_id)

    def list_all(self, *, limit: int = 100) -> list[CandidateMemoryDTO]:
        _require_capability(self, "export_list", supported=self.capabilities.export_list)
        payload = self._client.get_all(user_id=self._user_id, limit=limit)
        return [_mem0_result_to_dto(item) for item in _unwrap_results(payload)]
