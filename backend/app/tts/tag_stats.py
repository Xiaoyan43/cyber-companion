"""Deterministic metrics for Fish Audio expression tags (P0, see docs/HANDOFF.md).

Pure string analysis — zero network, zero LLM — so the degradation patterns the
expression tagger keeps falling into can be measured instead of guessed at by ear:

- 重复贴同一标签  → ``max_repeat`` / ``distinct_ratio``
- 标签只堆开头      → ``opening_only`` / ``non_opening_tag_count``
- 标签密度          → ``tagged_sentence_ratio``

These metrics describe *only* the observable degradation patterns. Whether the
tags are emotionally *apt* is not something code can score — that always stays a
human judgement (blind listening). See the P0 dev script for that side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A tag is a single ``[...]`` with no nested brackets. Works for English ([happy])
# and Chinese ([叹气]) tags alike.
_TAG_RE = re.compile(r"\[[^\[\]]+\]")

# Sentence terminators across the languages Boxi speaks. ASCII '.' is included on
# purpose; over-splitting only ever *lowers* the chance ``opening_only`` fires, so
# it stays conservative for our degradation checks.
_TERMINATORS = set("。！？!?…\n.")

# Pure pause/rhythm markers — not expressive tags. Repeating [break] across a reply
# is legitimate prosody, NOT the "lazy same-emotion-tag" degradation, so they are
# excluded from the repeat/distinct degradation signals (but still shown in counts).
_RHYTHM_TAGS = {"break", "long-break"}


def extract_tags(text: str) -> list[str]:
    """Return normalized tag strings (lowercased, inner-trimmed) in order of appearance."""
    return [_normalize_tag(match.group(0)) for match in _TAG_RE.finditer(text)]


def _normalize_tag(raw: str) -> str:
    return raw[1:-1].strip().lower()


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Split into (start, end) char spans, dropping whitespace-only fragments."""
    spans: list[tuple[int, int]] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        if text[i] in _TERMINATORS:
            j = i
            while j < n and text[j] in _TERMINATORS:
                j += 1
            spans.append((start, j))
            start = j
            i = j
        else:
            i += 1
    if start < n:
        spans.append((start, n))
    return [(s, e) for (s, e) in spans if text[s:e].strip()]


def _span_index(spans: list[tuple[int, int]], offset: int) -> int:
    for idx, (s, e) in enumerate(spans):
        if s <= offset < e:
            return idx
    for idx in range(len(spans) - 1, -1, -1):
        if spans[idx][0] <= offset:
            return idx
    return 0


@dataclass(frozen=True)
class TagStats:
    total_tags: int  # all tags incl. rhythm markers (density)
    distinct_tags: int  # distinct expressive tags (rhythm markers excluded)
    distinct_ratio: float  # distinct/total over expressive tags; 1.0 = all unique, low = repetitive
    max_repeat: int  # occurrences of the most-repeated expressive tag (rhythm markers excluded)
    tag_counts: dict[str, int] = field(default_factory=dict)  # all tags, for display
    sentence_count: int = 0
    tagged_sentence_count: int = 0
    tagged_sentence_ratio: float = 0.0
    non_opening_tag_count: int = 0  # tags landing after the first sentence
    opening_only: bool = False  # multi-sentence text whose tags all sit in sentence 0

    def summary_line(self) -> str:
        return (
            f"tags={self.total_tags} distinct={self.distinct_tags} "
            f"distinct_ratio={self.distinct_ratio:.2f} max_repeat={self.max_repeat} "
            f"tagged_sent={self.tagged_sentence_count}/{self.sentence_count} "
            f"non_opening={self.non_opening_tag_count} opening_only={self.opening_only}"
        )


def compute_tag_stats(text: str) -> TagStats:
    """Compute the degradation metrics for one tagged reply."""
    spans = _sentence_spans(text)
    sentence_count = len(spans)

    matches = list(_TAG_RE.finditer(text))
    total = len(matches)

    counts: dict[str, int] = {}
    tagged_sentence_indices: set[int] = set()
    non_opening = 0
    for match in matches:
        normalized = _normalize_tag(match.group(0))
        counts[normalized] = counts.get(normalized, 0) + 1
        idx = _span_index(spans, match.start()) if spans else 0
        tagged_sentence_indices.add(idx)
        if idx >= 1:
            non_opening += 1

    # Degradation signals look only at expressive tags; rhythm markers are excluded.
    expressive = {tag: n for tag, n in counts.items() if tag not in _RHYTHM_TAGS}
    total_expressive = sum(expressive.values())
    distinct = len(expressive)
    max_repeat = max(expressive.values()) if expressive else 0
    distinct_ratio = (distinct / total_expressive) if total_expressive else 0.0
    tagged_sentence_count = len(tagged_sentence_indices)
    tagged_sentence_ratio = (tagged_sentence_count / sentence_count) if sentence_count else 0.0
    opening_only = total > 0 and sentence_count > 1 and non_opening == 0

    return TagStats(
        total_tags=total,
        distinct_tags=distinct,
        distinct_ratio=distinct_ratio,
        max_repeat=max_repeat,
        tag_counts=counts,
        sentence_count=sentence_count,
        tagged_sentence_count=tagged_sentence_count,
        tagged_sentence_ratio=tagged_sentence_ratio,
        non_opening_tag_count=non_opening,
        opening_only=opening_only,
    )
