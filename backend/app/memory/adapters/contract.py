"""Narrow normalized contract for Phase 5 memory backend candidates.

Deliberately smaller than ``MemoryPort`` (which still bundles behavior, budget,
context assembly, and chat persistence). Candidates only model durable fact
records: scoped write/search/delete/export with explicit capability flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.app.memory.database import MemoryRecord


class UnsupportedCandidateCapability(RuntimeError):
    """Raised when a backend declares a capability as unsupported."""

    def __init__(self, backend: str, capability: str) -> None:
        self.backend = backend
        self.capability = capability
        super().__init__(f"{backend} does not support capability: {capability}")


@dataclass(frozen=True)
class CandidateMemoryDTO:
    """Normalized memory fact for candidate backends."""

    type: str
    content: str
    tags: tuple[str, ...] = ()
    importance: float = 0.5
    confidence: float = 0.5
    source_message_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None


@dataclass(frozen=True)
class CandidateMemoryCapabilities:
    scoped_write: bool
    scoped_search: bool
    delete: bool
    export_list: bool
    semantic_search: bool


class CandidateMemoryBackend(Protocol):
    @property
    def backend_name(self) -> str: ...

    @property
    def namespace(self) -> str: ...

    @property
    def capabilities(self) -> CandidateMemoryCapabilities: ...

    def write(self, record: CandidateMemoryDTO) -> str: ...

    def search(self, query: str, *, limit: int = 10) -> list[CandidateMemoryDTO]: ...

    def delete(self, memory_id: str) -> None: ...

    def list_all(self, *, limit: int = 100) -> list[CandidateMemoryDTO]: ...


def memory_record_to_candidate_dto(record: MemoryRecord) -> CandidateMemoryDTO:
    return CandidateMemoryDTO(
        type=record.type,
        content=record.content,
        tags=tuple(record.tags),
        importance=record.importance,
        confidence=record.confidence,
        source_message_id=record.source_message_id,
        metadata=dict(record.metadata),
        id=str(record.id),
    )


def _require_capability(
    backend: CandidateMemoryBackend,
    capability: str,
    *,
    supported: bool,
) -> None:
    if not supported:
        raise UnsupportedCandidateCapability(backend.backend_name, capability)
