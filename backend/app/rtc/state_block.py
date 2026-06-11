"""Join-time kernel stance block for pure-E2E RTC (PS-3 / PS-4)."""

from __future__ import annotations

import logging

from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord
from backend.app.memory.store import MemoryStore, get_memory_store

logger = logging.getLogger(__name__)

_MOOD_THRESHOLD = 0.5
_TENSION_AWKWARD_THRESHOLD = 0.4
_LOW_ENERGY_THRESHOLD = 0.3
_BUCKET_LOW = 0.34
_BUCKET_HIGH = 0.67

_MOOD_LINES: tuple[tuple[str, float, str], ...] = (
    ("annoyance", _MOOD_THRESHOLD, "有点烦躁"),
    ("worry", _MOOD_THRESHOLD, "有点担心ta"),
    ("loneliness", _MOOD_THRESHOLD, "有点想找人说话"),
    ("boredom", _MOOD_THRESHOLD, "有点无聊"),
)

# Spoken WelcomeMessage lines — deliberately distinct per branch for E2E weight experiments.
_WELCOME_LINES: tuple[tuple[str, float, str], ...] = (
    ("annoyance", _MOOD_THRESHOLD, "又响了。有话快说，别磨蹭。"),
    ("worry", _MOOD_THRESHOLD, "在呢。你最近还好吗？"),
    ("loneliness", _MOOD_THRESHOLD, "终于来人了。说吧，我听着。"),
    ("boredom", _MOOD_THRESHOLD, "无聊死了。你赶紧说点有意思的。"),
)
_LOW_ENERGY_WELCOME = "困……干嘛非现在把我喊醒。"
_HIGH_CLOSENESS_WELCOME = "哟，又是你啊。想聊啥？"


def _bucket_label(value: float) -> str:
    if value < _BUCKET_LOW:
        return "低"
    if value < _BUCKET_HIGH:
        return "中"
    return "高"


def _is_mid(value: float) -> bool:
    return _BUCKET_LOW <= value < _BUCKET_HIGH


def _mood_line(mood: MoodStateRecord) -> str | None:
    for field, threshold, label in _MOOD_LINES:
        if getattr(mood, field) >= threshold:
            return label
    if mood.energy <= _LOW_ENERGY_THRESHOLD:
        return "没什么精神"
    return None


def _relationship_line(relationship: RelationshipStateRecord) -> str:
    line = (
        f"和这个用户：信任{_bucket_label(relationship.trust)}、"
        f"亲近{_bucket_label(relationship.closeness)}"
    )
    if relationship.tension >= _TENSION_AWKWARD_THRESHOLD:
        line += "、有点别扭"
    return line


def _is_fully_neutral(mood: MoodStateRecord, relationship: RelationshipStateRecord) -> bool:
    if _mood_line(mood) is not None:
        return False
    return (
        _is_mid(relationship.trust)
        and _is_mid(relationship.closeness)
        and relationship.tension < _TENSION_AWKWARD_THRESHOLD
    )


def build_rtc_state_block(store: MemoryStore | None = None) -> str:
    """Discretized Chinese stance block from the kernel. '' when fully neutral."""
    try:
        resolved = store if store is not None else get_memory_store()
        mood = resolved.get_mood_state()
        relationship = resolved.get_relationship_state()
        if _is_fully_neutral(mood, relationship):
            return ""

        lines = ["【你此刻的状态】"]
        mood_line = _mood_line(mood)
        if mood_line:
            lines.append(f"情绪：{mood_line}")
        lines.append(_relationship_line(relationship))
        return "\n".join(lines)
    except Exception:
        logger.exception("build_rtc_state_block failed")
        return ""


def build_rtc_welcome_message(
    store: MemoryStore | None = None,
    *,
    default: str,
) -> str:
    """Kernel-derived spoken opening for StartVoiceChat. Falls back to *default* when neutral."""
    try:
        resolved = store if store is not None else get_memory_store()
        mood = resolved.get_mood_state()
        relationship = resolved.get_relationship_state()

        for field, threshold, line in _WELCOME_LINES:
            if getattr(mood, field) >= threshold:
                return line
        if mood.energy <= _LOW_ENERGY_THRESHOLD:
            return _LOW_ENERGY_WELCOME
        if relationship.closeness >= _BUCKET_HIGH and relationship.tension < 0.3:
            return _HIGH_CLOSENESS_WELCOME
        if _is_fully_neutral(mood, relationship):
            return default
        return default
    except Exception:
        logger.exception("build_rtc_welcome_message failed")
        return default


def build_rtc_steering_directive(store: MemoryStore | None = None) -> str:
    """One Chinese stance directive from the kernel buckets. '' for the default persona."""
    try:
        resolved = store if store is not None else get_memory_store()
        mood = resolved.get_mood_state()
        relationship = resolved.get_relationship_state()

        if mood.worry >= _MOOD_THRESHOLD:
            return "用户最近不太好，收一收毒舌，话短一点、稳一点。"
        if mood.annoyance >= _MOOD_THRESHOLD or relationship.tension >= _TENSION_AWKWARD_THRESHOLD:
            return "你对最近的互动有点不耐烦，可以更冲、更短，但别真羞辱用户。"
        if relationship.closeness >= _BUCKET_HIGH and relationship.tension < 0.3:
            return "你和ta挺熟了，可以更随意、更贴一点，毒舌底色别丢。"
        return ""
    except Exception:
        logger.exception("build_rtc_steering_directive failed")
        return ""
