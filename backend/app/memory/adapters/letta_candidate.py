"""Letta candidate backend (Phase 5 spike — not production).

Wraps Letta **memory blocks** CRUD only. Does not call ``agents.create``,
``messages.create``, or any reply-generation API. Semantic retrieval is
explicitly unsupported — blocks are label/value documents, not ranked facts.
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.app.memory.adapters.contract import (
    CandidateMemoryCapabilities,
    CandidateMemoryDTO,
    UnsupportedCandidateCapability,
    _require_capability,
)


class LettaBlocksClientProtocol(Protocol):
    """Minimal Letta client surface for memory-block CRUD."""

    def list_blocks(self, *, agent_id: str | None = None) -> list[dict[str, Any]]: ...

    def create_block(
        self,
        *,
        label: str,
        value: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def update_block(
        self,
        block_id: str,
        *,
        label: str | None = None,
        value: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def delete_block(self, block_id: str) -> None: ...


def _block_to_dto(block: dict[str, Any]) -> CandidateMemoryDTO:
    metadata = dict(block.get("metadata") or {})
    mem_type = str(metadata.get("memory_type") or metadata.get("type") or block.get("label") or "block")
    tags_raw = metadata.get("tags") or []
    tags = tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, list) else ()
    return CandidateMemoryDTO(
        id=str(block.get("id") or ""),
        type=mem_type,
        content=str(block.get("value") or block.get("content") or ""),
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


class LettaCandidateBackend:
    backend_name = "letta"

    def __init__(
        self,
        client: LettaBlocksClientProtocol,
        *,
        namespace: str,
        block_label_prefix: str = "boxi_mem",
    ) -> None:
        self._client = client
        self._namespace = namespace
        self._block_label_prefix = block_label_prefix

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def capabilities(self) -> CandidateMemoryCapabilities:
        return CandidateMemoryCapabilities(
            scoped_write=True,
            scoped_search=False,
            delete=True,
            export_list=True,
            semantic_search=False,
        )

    def _block_label(self, record: CandidateMemoryDTO) -> str:
        return f"{self._block_label_prefix}:{self._namespace}:{record.type}"

    def _scoped_blocks(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prefix = f"{self._block_label_prefix}:{self._namespace}:"
        scoped: list[dict[str, Any]] = []
        for block in blocks:
            label = str(block.get("label") or "")
            metadata = block.get("metadata") or {}
            ns = metadata.get("namespace") if isinstance(metadata, dict) else None
            if label.startswith(prefix) or ns == self._namespace:
                scoped.append(block)
        return scoped

    def write(self, record: CandidateMemoryDTO) -> str:
        _require_capability(self, "scoped_write", supported=self.capabilities.scoped_write)
        metadata = {
            "namespace": self._namespace,
            "memory_type": record.type,
            "type": record.type,
            "tags": list(record.tags),
            "importance": record.importance,
            "confidence": record.confidence,
            "source_message_id": record.source_message_id,
            **record.metadata,
        }
        label = self._block_label(record)
        existing = [
            block
            for block in self._scoped_blocks(self._client.list_blocks())
            if str(block.get("label") or "") == label
        ]
        if existing:
            block_id = str(existing[0]["id"])
            updated = self._client.update_block(
                block_id,
                label=label,
                value=record.content,
                metadata=metadata,
            )
            return str(updated.get("id") or block_id)
        created = self._client.create_block(
            label=label,
            value=record.content,
            metadata=metadata,
        )
        block_id = created.get("id")
        if block_id is None:
            raise ValueError("letta create_block response missing id")
        return str(block_id)

    def search(self, query: str, *, limit: int = 10) -> list[CandidateMemoryDTO]:
        _require_capability(self, "scoped_search", supported=self.capabilities.scoped_search)
        raise UnsupportedCandidateCapability(self.backend_name, "scoped_search")

    def delete(self, memory_id: str) -> None:
        _require_capability(self, "delete", supported=self.capabilities.delete)
        self._client.delete_block(memory_id)

    def list_all(self, *, limit: int = 100) -> list[CandidateMemoryDTO]:
        _require_capability(self, "export_list", supported=self.capabilities.export_list)
        blocks = self._scoped_blocks(self._client.list_blocks())[:limit]
        return [_block_to_dto(block) for block in blocks]
