from __future__ import annotations

import json

from backend.app.behavior.parser import JSON_BLOCK_PATTERN
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MemoryRecord, MessageRecord, utc_now_iso
from backend.app.memory.retrieval import tokenize
from backend.app.memory.schema import FACTUAL_MEMORY_TYPES
from backend.app.memory.store import MemoryStore
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import get_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatMessage

# SD-5 linker tuning.
_LINK_CANDIDATE_CAP = 40
_LINK_MIN_OVERLAP = 2
_LINK_MIN_RATIO = 0.25
_LINK_MAX_NEW_PER_PASS = 20


def _llm_json(
    *,
    system: str,
    user: str,
    max_output_tokens: int = 400,
) -> dict | None:
    # TODO(SD-later): gate reflection spend
    try:
        router = get_provider_router()
        result = router.complete(
            ChatCompletionRequest(
                messages=[
                    ChatMessage(role="system", content=system),
                    ChatMessage(role="user", content=user),
                ],
                max_output_tokens=max_output_tokens,
            ),
        )
        match = JSON_BLOCK_PATTERN.search(result.content)
        if not match:
            return None
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except (ProviderError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def _clamp_importance(value: float) -> float:
    return max(0.0, min(1.0, value))


def _factual_candidates(store: MemoryStore, cap: int) -> list[MemoryRecord]:
    # Factual user-fact memories only. The impression (relationship_state),
    # conversation summaries, and emotion_state are synthesized/internal and must
    # never be consolidated or mislinked.
    factual = [
        memory
        for memory in store.list_memories(limit=cap * 3)
        if memory.type in FACTUAL_MEMORY_TYPES
    ]
    return factual[:cap]


def consolidate_memories(store: MemoryStore, budget: BudgetConfig) -> None:
    del budget  # reserved for future budget gating
    candidates = _factual_candidates(store, _LINK_CANDIDATE_CAP)
    if not candidates:
        return

    lines = []
    for memory in candidates:
        lines.append(
            f"({memory.id}, {memory.type}, {memory.content!r}, "
            f"{memory.importance:.2f}, {memory.updated_at})"
        )
    user_prompt = "Stored memories:\n" + "\n".join(lines)

    payload = _llm_json(
        system=(
            "You maintain a companion's memory store. Given memories as "
            "(id, type, content, importance, updated_at), return JSON only: "
            '{"archive":[ids of stale/dead facts], "deprioritize":[{"id", "importance"}]}. '
            "Only archive clearly outdated job_progress/recent_event. "
            "deprioritize means LOWER importance only."
        ),
        user=user_prompt,
    )
    if not payload:
        return

    for memory_id in payload.get("archive") or []:
        try:
            mid = int(memory_id)
        except (TypeError, ValueError):
            continue
        if store.get_memory(mid) is None:
            continue
        store.update_memory(mid, expires_at=utc_now_iso())

    for item in payload.get("deprioritize") or []:
        if not isinstance(item, dict):
            continue
        try:
            mid = int(item.get("id"))
            new_importance = float(item.get("importance"))
        except (TypeError, ValueError):
            continue
        existing = store.get_memory(mid)
        if existing is None:
            continue
        clamped = _clamp_importance(min(existing.importance, new_importance))
        store.update_memory(mid, importance=clamped)


def link_related_memories(store: MemoryStore, budget: BudgetConfig) -> None:
    """Deterministically cross-link factual memories that share strong tokens.

    Runs in reflection (off the response path) after consolidation, with no LLM.
    Links are bidirectional + idempotent; only cross-type pairs with a real shared
    token are linked so retrieval can pull in related context (e.g. a ``project``
    and a ``job_progress`` that name the same company)."""
    del budget  # deterministic; no LLM, no budget gating
    candidates = _factual_candidates(store, _LINK_CANDIDATE_CAP)
    if len(candidates) < 2:
        return

    token_cache = {memory.id: tokenize(memory.content) for memory in candidates}
    # Lazily cache each memory's existing links so the per-pass cap counts only
    # genuinely new links (idempotent re-runs do not exhaust the budget).
    existing_links: dict[int, set[int]] = {}

    def _already_linked(left_id: int, right_id: int) -> bool:
        if left_id not in existing_links:
            existing_links[left_id] = set(store.get_linked_memory_ids(left_id))
        return right_id in existing_links[left_id]

    new_links = 0
    for index, left in enumerate(candidates):
        if new_links >= _LINK_MAX_NEW_PER_PASS:
            break
        left_tokens = token_cache[left.id]
        if not left_tokens:
            continue
        for right in candidates[index + 1 :]:
            if new_links >= _LINK_MAX_NEW_PER_PASS:
                break
            if left.type == right.type:
                continue
            right_tokens = token_cache[right.id]
            if not right_tokens:
                continue
            overlap = left_tokens & right_tokens
            if len(overlap) < _LINK_MIN_OVERLAP:
                continue
            smaller = min(len(left_tokens), len(right_tokens))
            if smaller == 0 or len(overlap) / smaller < _LINK_MIN_RATIO:
                continue
            if _already_linked(left.id, right.id):
                continue
            store.add_memory_link(left.id, right.id)
            existing_links[left.id].add(right.id)
            existing_links.setdefault(right.id, set()).add(left.id)
            new_links += 1


def form_impression(store: MemoryStore, budget: BudgetConfig) -> None:
    del budget
    relationship = store.get_relationship_state()
    rel_line = (
        f"trust={relationship.trust:.2f}, closeness={relationship.closeness:.2f}, "
        f"familiarity={relationship.familiarity:.2f}, tension={relationship.tension:.2f}"
    )

    memory_lines: list[str] = []
    for memory_type in ("stable_profile", "project", "job_progress"):
        for memory in store.list_memories(type=memory_type, limit=3):
            memory_lines.append(f"- ({memory.type}) {memory.content}")

    latest_summary = store.get_latest_conversation_summary()
    summary_text = latest_summary.summary if latest_summary else "(none)"

    user_prompt = (
        f"Relationship: {rel_line}\n"
        f"Relevant memories:\n"
        + ("\n".join(memory_lines) if memory_lines else "(none)")
        + f"\nLatest conversation summary: {summary_text}"
    )

    payload = _llm_json(
        system=(
            "In Boxi's voice, write a 2-4 sentence internal impression: who this person "
            "is to you and where you two stand. Honest, a little毒舌, not user-facing. "
            'Return JSON {"impression": "..."} only.'
        ),
        user=user_prompt,
        max_output_tokens=300,
    )
    if not payload:
        return
    impression = payload.get("impression")
    if not isinstance(impression, str) or not impression.strip():
        return
    impression = impression.strip()

    existing = store.list_memories(type="relationship_state", limit=1)
    metadata = {"writer": "reflection"}
    if existing:
        store.update_memory(
            existing[0].id,
            content=impression,
            metadata={**existing[0].metadata, **metadata},
        )
    else:
        store.create_memory(
            type="relationship_state",
            content=impression,
            importance=0.6,
            confidence=0.6,
            tags=["impression"],
            metadata=metadata,
        )


def _summary_batch_if_due(
    store: MemoryStore,
    budget: BudgetConfig,
) -> list[MessageRecord] | None:
    total = store.count_chat_messages()
    if total <= budget.max_raw_turns + 1:
        return None

    window_lower_bound_id = store.get_recent_chat_window_lower_bound_id(budget.max_raw_turns)
    if window_lower_bound_id is None:
        return None

    latest_summary = store.get_latest_conversation_summary()
    covered_until = latest_summary.range_end_message_id if latest_summary else 0
    older_messages = store.list_chat_messages_between(
        covered_until,
        window_lower_bound_id,
        budget.summary_batch_size,
    )
    if len(older_messages) < budget.summary_batch_size:
        return None
    return older_messages


def summarize_conversation_llm(store: MemoryStore, budget: BudgetConfig) -> None:
    if not budget.llm_summary:
        return

    batch = _summary_batch_if_due(store, budget)
    if not batch:
        return

    lines = []
    for message in batch:
        clipped = message.content.strip().replace("\n", " ")
        if len(clipped) > 120:
            clipped = clipped[:117] + "..."
        lines.append(f"{message.role}: {clipped}")

    payload = _llm_json(
        system=(
            "Summarize this conversation batch compactly for future context. "
            'Return JSON {"summary":"...","keywords":["..."]} only.'
        ),
        user="\n".join(lines),
        max_output_tokens=350,
    )
    if not payload:
        return

    summary = payload.get("summary")
    keywords = payload.get("keywords")
    if not isinstance(summary, str) or not summary.strip():
        return
    if not isinstance(keywords, list):
        keywords = []
    keyword_list = [str(k) for k in keywords if k][:12]

    store.create_conversation_summary(
        range_start_message_id=batch[0].id,
        range_end_message_id=batch[-1].id,
        summary=summary.strip(),
        keywords=keyword_list,
    )
