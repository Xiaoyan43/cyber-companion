"""Compact SQLite memory inject for pure E2E RTC (VM-4)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.memory.database import ConversationSummaryRecord, MemoryRecord
from backend.app.memory.retrieval import is_expired
from backend.app.memory.schema import FACTUAL_MEMORY_TYPES
from backend.app.memory.store import MemoryStore, get_memory_store

SQLITE_MEMORY_INSTRUCTION = (
    "下列是用户此前在文字聊天里已经告诉你的内容，等同于你们已经聊过、你本来就知道的事。"
    "用户用口语间接提问时（例如「我明天要干嘛」「接下来干嘛」「我要去做什么」），"
    "必须从这些记录里推断并直接回答；不要限定只有用户提到「文字聊天」时才回答，"
    "也不要说你不记得或让用户重复。"
)
_PLAN_MARKERS = (
    "明天",
    "后天",
    "今天",
    "今晚",
    "明早",
    "明晚",
    "下周",
    "下月",
    "周末",
    "打算",
    "要去",
    "准备",
    "计划",
    "安排",
    "预约",
)
MAX_PLAN_LINES = 4
MAX_PLAN_LINE_CHARS = 120
MAX_RECENT_CHAT_TURNS = 8
MAX_RECENT_LINE_CHARS = 180
MAX_RECENT_BLOCK_CHARS = 900
MAX_SUMMARY_CHARS = 400
MAX_IMPRESSION_CHARS = 200
MAX_MEMORY_LINES = 5
MAX_MEMORY_CONTENT_CHARS = 160


def _clip(text: str, limit: int) -> str:
    trimmed = text.strip()
    if len(trimmed) <= limit:
        return trimmed
    return f"{trimmed[: limit - 1].rstrip()}…"


def _clip_chat_line(role: str, content: str) -> str:
    text = content.strip().replace("\n", " ")
    if not text:
        return ""
    if len(text) > MAX_RECENT_LINE_CHARS:
        text = f"{text[: MAX_RECENT_LINE_CHARS - 1].rstrip()}…"
    speaker = "用户" if role == "user" else "Boxi"
    return f"{speaker}: {text}"


def _format_user_plans_block(store: MemoryStore) -> str:
    messages = store.list_recent_chat_messages(MAX_RECENT_CHAT_TURNS)
    lines: list[str] = []
    seen: set[str] = set()
    for message in messages:
        if message.role != "user":
            continue
        text = message.content.strip().replace("\n", " ")
        if not text or not any(marker in text for marker in _PLAN_MARKERS):
            continue
        clipped = _clip(text, MAX_PLAN_LINE_CHARS)
        if clipped in seen:
            continue
        seen.add(clipped)
        lines.append(clipped)
        if len(lines) >= MAX_PLAN_LINES:
            break

    if not lines:
        return ""
    return "【用户说过的事】\n" + "\n".join(f"- {line}" for line in lines)


def _format_recent_chat_block(store: MemoryStore) -> str:
    messages = store.list_recent_chat_messages(MAX_RECENT_CHAT_TURNS)
    if not messages:
        return ""

    lines = ["【近期对话原文】"]
    used_chars = len(lines[0])
    for message in messages:
        line = _clip_chat_line(message.role, message.content)
        if not line:
            continue
        next_size = used_chars + len(line) + 1
        if next_size > MAX_RECENT_BLOCK_CHARS and len(lines) > 1:
            break
        lines.append(line)
        used_chars = next_size

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _format_summary_block(summary: ConversationSummaryRecord) -> str:
    body = _clip(summary.summary, MAX_SUMMARY_CHARS)
    if not body:
        return ""
    keywords = ", ".join(keyword for keyword in summary.keywords if keyword.strip())
    if keywords:
        return f"【文字聊天摘要】{body}\n关键词：{keywords}"
    return f"【文字聊天摘要】{body}"


def _format_impression_block(store: MemoryStore) -> str:
    memories = store.list_memories(type="relationship_state", limit=1)
    if not memories:
        return ""
    content = _clip(memories[0].content, MAX_IMPRESSION_CHARS)
    if not content:
        return ""
    return f"【文字聊天印象】{content}"


def _select_rtc_memories(store: MemoryStore) -> list[MemoryRecord]:
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candidates = [
        memory
        for memory in store.list_memories(limit=200)
        if memory.type in FACTUAL_MEMORY_TYPES and not is_expired(memory, now_iso)
    ]
    candidates.sort(key=lambda memory: (memory.importance, memory.created_at), reverse=True)
    return candidates[:MAX_MEMORY_LINES]


def _format_memory_lines(memories: list[MemoryRecord]) -> str:
    if not memories:
        return ""
    lines = ["【文字聊天要点】"]
    for memory in memories:
        content = _clip(memory.content, MAX_MEMORY_CONTENT_CHARS)
        if content:
            lines.append(f"- {content}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def sqlite_memory_has_content(store: MemoryStore) -> bool:
    return bool(format_sqlite_memory_for_system_role(store).strip())


def format_sqlite_memory_for_system_role(store: MemoryStore) -> str:
    sections: list[str] = []

    plans_block = _format_user_plans_block(store)
    if plans_block:
        sections.append(plans_block)

    recent_chat_block = _format_recent_chat_block(store)
    if recent_chat_block:
        sections.append(recent_chat_block)

    memory_block = _format_memory_lines(_select_rtc_memories(store))
    if memory_block:
        sections.append(memory_block)

    summary = store.get_latest_conversation_summary()
    if summary is not None:
        summary_block = _format_summary_block(summary)
        if summary_block:
            sections.append(summary_block)

    impression_block = _format_impression_block(store)
    if impression_block:
        sections.append(impression_block)

    if not sections:
        return ""
    return f"{SQLITE_MEMORY_INSTRUCTION}\n\n" + "\n\n".join(sections)


def load_sqlite_memory_context(store: MemoryStore | None = None) -> str:
    resolved = store if store is not None else get_memory_store()
    return format_sqlite_memory_for_system_role(resolved)
