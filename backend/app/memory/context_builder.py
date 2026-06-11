from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.app.behavior.local_responses import behavior_tone_instruction
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import (
    ConversationSummaryRecord,
    MemoryRecord,
    MessageRecord,
    MoodStateRecord,
    RelationshipStateRecord,
)
from backend.app.memory.persona import OUTPUT_PROTOCOL, load_persona_system_prompt
from backend.app.memory.retrieval import is_expired, rank_memories, tokenize
from backend.app.memory.store import MemoryStore
from backend.app.providers.cost import estimate_token_count
from backend.app.providers.types import ChatMessage


@dataclass(frozen=True)
class BuiltContext:
    messages: list[ChatMessage]
    estimated_input_tokens: int
    included_memory_ids: list[int]
    included_message_ids: list[int]
    summary_used: str | None
    truncated: bool
    total_stored_messages: int


def _format_mood_block(mood: MoodStateRecord) -> str:
    return (
        "[Current mood]\n"
        f"mood={mood.mood}, energy={mood.energy:.2f}, annoyance={mood.annoyance:.2f}, "
        f"boredom={mood.boredom:.2f}, worry={mood.worry:.2f}, "
        f"loneliness={mood.loneliness:.2f}"
    )


def _format_relationship_block(rel: RelationshipStateRecord) -> str:
    return (
        "[Relationship]\n"
        f"trust={rel.trust:.2f}, closeness={rel.closeness:.2f}, "
        f"familiarity={rel.familiarity:.2f}, tension={rel.tension:.2f}"
    )


def _format_impression_block(store: MemoryStore) -> str | None:
    memories = store.list_memories(type="relationship_state", limit=1)
    if not memories:
        return None
    return f"[Impression]\n{memories[0].content}"


def _format_memories_block(memories: list[MemoryRecord]) -> str:
    if not memories:
        return "[Relevant memories]\n(none selected)"

    lines = ["[Relevant memories]"]
    for memory in memories:
        tag_text = ", ".join(memory.tags) if memory.tags else "no-tags"
        lines.append(f"- ({memory.type}) [{tag_text}] {memory.content}")
    return "\n".join(lines)


def _format_summary_block(summary: ConversationSummaryRecord | None) -> str | None:
    if summary is None:
        return None
    keywords = ", ".join(summary.keywords) if summary.keywords else "none"
    return f"[Recent conversation summary]\n{summary.summary}\nKeywords: {keywords}"


_TRUNCATION_SUFFIX = " …[truncated]"

_TRAILER_REMINDER = (
    "\n\n（系统提醒：本轮回复必须在正文后另起一行输出 <<<BOXI_SIGNALS>>> 及其单行 JSON，"
    "不可省略。）"
)


def _truncate_user_input_for_provider(user_input: str, max_tokens: int) -> str:
    if max_tokens <= 0 or estimate_token_count(user_input) <= max_tokens:
        return user_input

    max_chars = max_tokens * 3
    clipped = user_input[:max_chars].rstrip()
    return f"{clipped}{_TRUNCATION_SUFFIX}"


def _pack_sections(
    sections: list[str],
    *,
    max_input_tokens: int,
) -> tuple[list[str], bool]:
    selected: list[str] = []
    truncated = False
    used_tokens = 0

    for section in sections:
        section_tokens = estimate_token_count(section)
        if used_tokens + section_tokens > max_input_tokens:
            truncated = True
            break
        selected.append(section)
        used_tokens += section_tokens

    return selected, truncated


def build_provider_context(
    store: MemoryStore,
    *,
    user_input: str,
    budget: BudgetConfig | None = None,
    behavior: BehaviorDecision | None = None,
) -> BuiltContext:
    config = budget or BudgetConfig()
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    latest_summary = store.get_latest_conversation_summary()
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    active_memories = [
        memory
        for memory in store.list_memories(limit=200)
        if not is_expired(memory, now_iso)
    ]
    ranked_memories = rank_memories(active_memories, user_input)

    selected_memories: list[MemoryRecord] = []
    for memory in ranked_memories:
        if len(selected_memories) >= config.max_memories_per_turn:
            break
        selected_memories.append(memory)

    # SD-5: follow one hop of memory links so a selected memory drags in its related
    # context. Additive and capped — it never drops a would-be-selected memory.
    # active_memories already excludes expired, so linked-but-expired memories are
    # skipped. Linked extras ride the same _pack_sections token budget below.
    memory_by_id = {memory.id: memory for memory in active_memories}
    selected_ids = {memory.id for memory in selected_memories}
    link_extra_cap = max(2, config.max_memories_per_turn // 2)
    linked_extra: list[MemoryRecord] = []
    seen_extra: set[int] = set()
    for memory in selected_memories:
        if len(linked_extra) >= link_extra_cap:
            break
        for linked_id in store.get_linked_memory_ids(memory.id):
            if len(linked_extra) >= link_extra_cap:
                break
            if linked_id in selected_ids or linked_id in seen_extra:
                continue
            linked_memory = memory_by_id.get(linked_id)
            if linked_memory is None:
                continue
            linked_extra.append(linked_memory)
            seen_extra.add(linked_id)
    selected_memories.extend(linked_extra)

    # Only real conversation turns (source="chat") may be replayed to the
    # provider. SQL boundary queries avoid loading the full messages table.
    recent_raw = store.list_recent_chat_messages(config.max_raw_turns)

    system_sections = [
        load_persona_system_prompt(),
        _format_mood_block(mood),
        _format_relationship_block(relationship),
    ]
    impression_block = _format_impression_block(store)
    if impression_block:
        system_sections.append(impression_block)
    if behavior is not None:
        tone_instruction = behavior_tone_instruction(behavior.decision, behavior.tone_mode)
        if tone_instruction:
            system_sections.append(tone_instruction)
    summary_block = _format_summary_block(latest_summary)
    if summary_block:
        system_sections.append(summary_block)
    system_sections.append(_format_memories_block(selected_memories))

    provider_user_input = _truncate_user_input_for_provider(
        user_input,
        config.max_user_input_tokens,
    )
    provider_user_input_for_send = provider_user_input
    reserved_tokens = estimate_token_count(provider_user_input) + sum(
        estimate_token_count(f"{message.role}: {message.content}") for message in recent_raw
    )
    trailer_tokens = estimate_token_count(_TRAILER_REMINDER)
    protocol_tokens = estimate_token_count(OUTPUT_PROTOCOL)
    memory_budget = max(
        256,
        config.max_input_tokens_per_turn
        - reserved_tokens
        - protocol_tokens
        - trailer_tokens,
    )
    packed_sections, truncated = _pack_sections(system_sections, max_input_tokens=memory_budget)
    packed_sections.append(OUTPUT_PROTOCOL)
    packed_sections.append(_TRAILER_REMINDER.strip())

    provider_messages: list[ChatMessage] = [
        ChatMessage(role="system", content="\n\n".join(packed_sections))
    ]

    included_message_ids: list[int] = []
    for message in recent_raw:
        role = "assistant" if message.role == "assistant" else "user"
        if role not in {"user", "assistant"}:
            continue
        provider_messages.append(ChatMessage(role=role, content=message.content))
        included_message_ids.append(message.id)

    provider_messages.append(ChatMessage(role="user", content=provider_user_input_for_send))

    estimated_input_tokens = sum(
        estimate_token_count(message.content) for message in provider_messages
    )

    return BuiltContext(
        messages=provider_messages,
        estimated_input_tokens=estimated_input_tokens,
        included_memory_ids=[memory.id for memory in selected_memories],
        included_message_ids=included_message_ids,
        summary_used=latest_summary.summary if latest_summary else None,
        truncated=truncated,
        total_stored_messages=store.count_chat_messages(),
    )


def extract_latest_user_input(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    raise ValueError("At least one user message is required.")
