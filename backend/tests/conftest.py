"""Shared pytest hooks for backend/tests."""

from __future__ import annotations

import pytest

# docs/SOUL_RUNTIME_ARCH.md §5 — invariant suite file selection (351 tests).
_INVARIANT_EXACT = frozenset(
    {
        "test_tone.py",
        "test_mood.py",
        "test_behavior.py",
        "test_reflection.py",
        "test_relationship_state.py",
        "test_rtc_state_block.py",
        "test_context_builder.py",
    }
)

_INVARIANT_PREFIXES = (
    "test_memory",
    "test_expression_tagger",
    "test_proactive",
)


def _is_invariant_module(filename: str) -> bool:
    if filename in _INVARIANT_EXACT:
        return True
    return any(filename.startswith(prefix) for prefix in _INVARIANT_PREFIXES)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _is_invariant_module(item.path.name):
            item.add_marker(pytest.mark.invariant)
