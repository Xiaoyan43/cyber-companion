"""Strip markdown, emoji, and stage-direction brackets before cloud TTS synthesis."""

from __future__ import annotations

import re

_QUOTED_SPAN_PATTERN = re.compile(r'"[^"]*"|「[^」]*」|\'[^\']*\'')
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)
_FENCED_CODE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_AUTOLINK_PATTERN = re.compile(r"<https?://[^>]+>")
_BOLD_PATTERN = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_ITALIC_PATTERN = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)")
_STRIKE_PATTERN = re.compile(r"~~([^~]+)~~")
_HEADER_PATTERN = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def _strip_stage_directions(text: str) -> str:
    """Remove bracketed stage cues; preserve quoted dialogue (aligned with speechText.ts)."""
    placeholders: list[str] = []

    def _protect(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\x00Q{len(placeholders) - 1}\x00"

    protected = _QUOTED_SPAN_PATTERN.sub(_protect, text)
    stripped = re.sub(r"（[^）]*）", "", protected)
    stripped = re.sub(r"【[^】]*】", "", stripped)
    stripped = re.sub(r"\([^)]*\)", "", stripped)
    return re.sub(
        r"\x00Q(\d+)\x00",
        lambda match: placeholders[int(match.group(1))],
        stripped,
    )


def _strip_markdown(text: str) -> str:
    text = _FENCED_CODE_PATTERN.sub("", text)
    text = _INLINE_CODE_PATTERN.sub(r"\1", text)
    text = _IMAGE_PATTERN.sub(r"\1", text)
    text = _LINK_PATTERN.sub(r"\1", text)
    text = _AUTOLINK_PATTERN.sub("", text)
    text = _BOLD_PATTERN.sub(lambda match: match.group(1) or match.group(2) or "", text)
    text = _ITALIC_PATTERN.sub(lambda match: match.group(1) or match.group(2) or "", text)
    text = _STRIKE_PATTERN.sub(r"\1", text)
    text = _HEADER_PATTERN.sub("", text)
    return text


def _normalize_speech_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([，。！？…；、])", r"\1", text)
    # Dedup accidental repeats, but KEEP the ellipsis（……）— Boxi 的拖尾省略号是有意的韵味。
    text = re.sub(r"([，。！？；、]){2,}", r"\1", text)
    return text.strip()


def clean_text_for_tts(text: str) -> str:
    """Prepare reply text for TTS only; stored/subtitle text stays untouched."""
    cleaned = text.strip()
    if not cleaned:
        return ""
    cleaned = _strip_stage_directions(cleaned)
    cleaned = _EMOJI_PATTERN.sub("", cleaned)
    cleaned = _strip_markdown(cleaned)
    return _normalize_speech_text(cleaned)
