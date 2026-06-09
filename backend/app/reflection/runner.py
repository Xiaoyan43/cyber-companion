from __future__ import annotations

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore


def _bump_last_reflected(store: MemoryStore) -> None:
    max_id = store.get_max_chat_message_id()
    if max_id > 0:
        store.set_meta("last_reflected_message_id", str(max_id))


def run_reflection_if_due(store: MemoryStore, budget: BudgetConfig) -> None:
    try:
        if not budget.enable_reflection:
            return
        if not store.claim_reflection(budget.reflection_every_n_turns):
            return
        try:
            from backend.app.reflection.jobs import (
                consolidate_memories,
                form_impression,
                link_related_memories,
                summarize_conversation_llm,
            )

            for job in (
                consolidate_memories,
                link_related_memories,
                form_impression,
                summarize_conversation_llm,
            ):
                try:
                    job(store, budget)
                except Exception:
                    pass
            _bump_last_reflected(store)
        finally:
            store.release_reflection()
    except Exception:
        pass
