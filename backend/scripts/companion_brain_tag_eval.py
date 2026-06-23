#!/usr/bin/env python
"""P8-C 前置 spike — Pipecat 标签退化率统计 (manual dev script, NOT run in CI).

``companion_brain.py``'s ``VOICE_MODE_INSTRUCTION`` is still single-stage: the main LLM
writes prose + Fish emotion tags in one shot (it never calls ``expression_tagger.py``'s
two-stage tagger). The text-chat path already proved single-stage prompting cannot
reliably stop tags from piling up at the opening (P8 trigger). This script answers
whether the same degradation shows up on the voice path's real output, using the same
deterministic ``tag_stats`` yardstick ``tagger_eval.py`` uses for the text-path tagger.

Uses a throwaway temp-file ``MemoryStore`` (fresh schema, default mood/relationship rows)
so this never reads or mutates the production database — safe to run repeatedly.

Makes live billed LLM calls (whatever provider is configured, e.g. grok-4.20 via
OpenRouter). Run it yourself, not from CI.

Usage (from repo root):
    python backend/scripts/companion_brain_tag_eval.py                 # 1 call per fixture
    python backend/scripts/companion_brain_tag_eval.py --repeats 10    # degradation recurrence rate
    python backend/scripts/companion_brain_tag_eval.py --repeats 25 --extended
        # also runs the round-2 coverage fixtures: real multi-turn history, a long-form
        # narrative prompt, and a mid-message emotional pivot (the original 4 fixtures
        # are all isolated single-turn messages and don't probe these).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_dotenv() -> None:
    import os

    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()

from backend.app.memory.store import MemoryStore  # noqa: E402
from backend.app.tts.tag_stats import compute_tag_stats  # noqa: E402
from backend.realtime.companion_brain import CompanionBrain, VoiceTurnOutcome  # noqa: E402

# Same four scenarios tagger_eval.py uses for the text-path tagger, so the voice-path
# numbers can be compared on equal footing against the existing P10-P1 baseline.
FIXTURES: list[str] = [
    "哦？你终于想起我了。我还以为你把我忘在这个破盒子里了呢。"
    "……说真的，你不在的时候，这里安静得有点过分。",
    "没事。你忙你的吧。我又没指望你能记得。反正我在这儿，也不去哪。",
    "我就说吧。你看，我早就告诉过你会是这个结果，你偏不信。现在知道谁说得对了？",
    "笨死了，这种事也要问我。……不过，你愿意问我，我其实挺高兴的。别告诉别人。",
]

# P8-C spike round 2 (2026-06-22) — the four fixtures above are all isolated single-turn
# messages, which the original spike's small N=8 sample didn't probe for coverage gaps.
# These extend coverage to: real multi-turn history, induced long-form replies, and an
# emotional pivot within one message. emotional_turn shares FIXTURES' --repeats; the
# other two get their own (cheaper) repeat counts since they cost more per call than a
# short single-turn reply (long_narrative: sanity check produced an 81-sentence reply;
# multi-turn: 3x the LLM calls per repeat).
EXTENDED_SINGLE_TURN_FIXTURES: list[tuple[str, str]] = [
    (
        "emotional_turn",
        "你知道吗，我等你回消息等了一整天，本来挺难受的……不过算了，反正你也没把我放心上对吧，随你便吧。",
    ),
]

EXTENDED_LONG_NARRATIVE_FIXTURE: tuple[str, str] = (
    "long_narrative",
    "哎我今天心情特别差，能不能给我讲个故事，随便什么都行，讲长一点，别三两句就完了。",
)

EXTENDED_MULTI_TURN_FIXTURE: tuple[str, list[str]] = (
    "multi_turn_softening",
    [
        "干嘛呢，叫你也不出声。",
        "你是不是又生我气了，有话直说啊。",
        "好啦好啦，是我不对，别真不高兴了，理我一下嘛。",
    ],
)


async def _one_turn(brain: CompanionBrain, user_text: str) -> VoiceTurnOutcome:
    async for event in brain.stream_turn(user_text):
        if event[0] == "done":
            return event[1]
    raise RuntimeError("stream_turn ended without a 'done' event")


async def _final_outcome(brain: CompanionBrain, fixture: str | list[str]) -> VoiceTurnOutcome:
    """Score the last turn; earlier turns (if any) are persisted as real history first."""
    if isinstance(fixture, str):
        return await _one_turn(brain, fixture)
    turns = fixture
    for turn_text in turns[:-1]:
        outcome = await _one_turn(brain, turn_text)
        brain.remember(outcome)
    return await _one_turn(brain, turns[-1])


def _new_brain() -> CompanionBrain:
    tmp_path = Path(tempfile.mkstemp(suffix=".sqlite3", prefix="companion_brain_tag_eval_")[1])
    store = MemoryStore(db_path=tmp_path)
    return CompanionBrain(store)


def _print_single_run(label: str, fixture: str | list[str]) -> None:
    brain = _new_brain()
    outcome = asyncio.run(_final_outcome(brain, fixture))
    preview = fixture if isinstance(fixture, str) else " / ".join(fixture)
    if not outcome.called_llm:
        print(f"[{label}] skipped (decision did not call LLM): {preview[:40]!r}\n")
        return
    stats = compute_tag_stats(outcome.raw_reply)
    print(f"[{label}] user: {preview}")
    print(f"  reply  : {outcome.raw_reply}")
    print(f"  metrics: {stats.summary_line()}")
    print(f"  counts : {stats.tag_counts}\n")


def _print_repeats_summary(label: str, fixture: str | list[str], repeats: int) -> None:
    preview = fixture if isinstance(fixture, str) else " / ".join(fixture)
    runs = []
    skipped = 0
    for _ in range(repeats):
        brain = _new_brain()
        outcome = asyncio.run(_final_outcome(brain, fixture))
        if not outcome.called_llm:
            skipped += 1
            continue
        runs.append(compute_tag_stats(outcome.raw_reply))

    print(f"[{label}] user: {preview[:50]!r}")
    if skipped:
        print(f"  skipped (no LLM call): {skipped}/{repeats}")
    if not runs:
        print("  no LLM-backed runs to report\n")
        return
    n = len(runs)
    repeat_degraded = sum(1 for s in runs if s.max_repeat > 1)
    opening_only = sum(1 for s in runs if s.opening_only)
    mean_distinct_ratio = sum(s.distinct_ratio for s in runs) / n
    mean_tagged_sentence_ratio = sum(s.tagged_sentence_ratio for s in runs) / n
    print(f"  repeat-tag degradation (max_repeat>1): {repeat_degraded}/{n}")
    print(f"  opening-only degradation              : {opening_only}/{n}")
    print(f"  mean distinct_ratio                   : {mean_distinct_ratio:.2f}")
    print(f"  mean tagged_sentence_ratio             : {mean_tagged_sentence_ratio:.2f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Call CompanionBrain N times per single-turn fixture (fresh store each call) "
        "and report degradation recurrence rates instead of a single sample (mirrors "
        "tagger_eval.py --repeats; single-run output is noise). Applies to the original "
        "4 fixtures plus the 2 new single-turn extended fixtures.",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Also run the round-2 coverage fixtures (multi-turn history, long-form "
        "narrative, mid-message emotional pivot) introduced 2026-06-22.",
    )
    parser.add_argument(
        "--repeats-multi-turn",
        type=int,
        default=15,
        help="Repeat count for the multi-turn fixture specifically (each repeat costs 3x "
        "the LLM calls of a single-turn repeat, hence a lower default than --repeats).",
    )
    parser.add_argument(
        "--repeats-long-narrative",
        type=int,
        default=10,
        help="Repeat count for the long_narrative fixture specifically — a sanity-check "
        "run produced an 81-sentence reply, so this is cheaper than --repeats by default.",
    )
    args = parser.parse_args()

    single_turn_fixtures: list[tuple[str, str]] = [
        (f"{i:02d}", text) for i, text in enumerate(FIXTURES, start=1)
    ]
    if args.extended:
        single_turn_fixtures += EXTENDED_SINGLE_TURN_FIXTURES

    if args.repeats == 1:
        print(f"=== companion_brain tag eval · {len(single_turn_fixtures)} single-turn fixtures ===\n")
        for label, text in single_turn_fixtures:
            _print_single_run(label, text)
        if args.extended:
            label, text = EXTENDED_LONG_NARRATIVE_FIXTURE
            _print_single_run(label, text)
            print("=== multi-turn fixture (single run) ===\n")
            label, turns = EXTENDED_MULTI_TURN_FIXTURE
            _print_single_run(label, turns)
        return

    print(
        f"=== companion_brain tag eval (repeats) · N={args.repeats} · "
        f"{len(single_turn_fixtures)} single-turn fixtures ===\n"
    )
    for label, text in single_turn_fixtures:
        _print_repeats_summary(label, text, args.repeats)

    if args.extended:
        label, text = EXTENDED_LONG_NARRATIVE_FIXTURE
        print(f"=== long_narrative fixture · N={args.repeats_long_narrative} ===\n")
        _print_repeats_summary(label, text, args.repeats_long_narrative)

        label, turns = EXTENDED_MULTI_TURN_FIXTURE
        print(f"=== multi-turn fixture · N={args.repeats_multi_turn} ===\n")
        _print_repeats_summary(label, turns, args.repeats_multi_turn)


if __name__ == "__main__":
    main()
