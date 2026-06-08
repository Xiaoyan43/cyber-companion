from __future__ import annotations

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MessageRecord
from backend.app.memory.retrieval import tokenize
from backend.app.memory.store import MemoryStore


def build_rule_based_summary(messages: list[MessageRecord]) -> tuple[str, list[str]]:
    snippets: list[str] = []
    keywords: set[str] = set()

    for message in messages:
        clipped = message.content.strip().replace("\n", " ")
        if len(clipped) > 120:
            clipped = clipped[:117] + "..."
        snippets.append(f"{message.role}: {clipped}")
        keywords.update(tokenize(message.content))

    summary = "Earlier conversation recap: " + " | ".join(snippets)
    return summary, sorted(keywords)[:12]


def maybe_update_conversation_summary(
    store: MemoryStore,
    *,
    budget: BudgetConfig | None = None,
) -> bool:
    config = budget or BudgetConfig()
    # Summaries recap the real conversation only; idle/proactive behavior-tick
    # lines are excluded so they neither enter summaries nor advance the batch
    # threshold.
    all_messages = [
        message
        for message in store.list_messages(limit=10_000)
        if message.source == "chat"
    ]
    if len(all_messages) <= config.max_raw_turns + 1:
        return False

    latest_summary = store.get_latest_conversation_summary()
    covered_until = latest_summary.range_end_message_id if latest_summary else 0
    cutoff_index = max(0, len(all_messages) - config.max_raw_turns)
    older_messages = [
        message
        for message in all_messages[:cutoff_index]
        if message.id > covered_until
    ]

    if len(older_messages) < config.summary_batch_size:
        return False

    batch = older_messages[: config.summary_batch_size]
    summary_text, keywords = build_rule_based_summary(batch)
    store.create_conversation_summary(
        range_start_message_id=batch[0].id,
        range_end_message_id=batch[-1].id,
        summary=summary_text,
        keywords=keywords,
    )
    return True
