"""Isolated candidate memory backends (Soul Runtime Phase 5 spike).

Not wired into ``ports_from_store`` or production runtime. See
``docs/SOUL_RUNTIME_PHASE5_SPIKE.md``.
"""

from backend.app.memory.adapters.contract import (
    CandidateMemoryCapabilities,
    CandidateMemoryDTO,
    CandidateMemoryBackend,
    UnsupportedCandidateCapability,
    memory_record_to_candidate_dto,
)
from backend.app.memory.adapters.letta_candidate import LettaCandidateBackend
from backend.app.memory.adapters.mem0_candidate import Mem0CandidateBackend
from backend.app.memory.adapters.shadow import ShadowMemoryPort

__all__ = [
    "CandidateMemoryBackend",
    "CandidateMemoryCapabilities",
    "CandidateMemoryDTO",
    "LettaCandidateBackend",
    "Mem0CandidateBackend",
    "ShadowMemoryPort",
    "UnsupportedCandidateCapability",
    "memory_record_to_candidate_dto",
]
