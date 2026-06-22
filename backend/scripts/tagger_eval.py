#!/usr/bin/env python
"""P0 manual dev script — offline expression-tagger eval. NOT run in CI.

Runs a fixed fixture set through the *real* expression tagger, prints the
degradation metrics from ``tag_stats``, and optionally synthesizes the tagged
text to audio files so the same fixtures can be blind-A/B-listened.

This is the tool that turns "open a real-machine session and judge by ear" into
"same fixed inputs, same yardstick" — so future structure changes (P1) and model
swaps (P2, e.g. Grok) can be compared without burning a session each time.

Requires real API keys in the environment (OpenRouter for the tagger, Fish Audio
for --audio); it makes live billed calls. Run it yourself, not from CI.

Usage (from repo root):
    python backend/scripts/tagger_eval.py                  # metrics only, default tagger
    python backend/scripts/tagger_eval.py --audio          # also write audio to data/tagger_eval/
    python backend/scripts/tagger_eval.py --provider grok  # compare an alternate tagger model
    python backend/scripts/tagger_eval.py --repeats 5      # P10-P1: degradation recurrence rate
                                                            # across N independent calls per fixture
                                                            # (single-run output is noise; the P0
                                                            # round found degradation is intermittent,
                                                            # not a stable yes/no — see HANDOFF)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python backend/scripts/tagger_eval.py` from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_dotenv() -> None:
    """Load repo-root .env into os.environ (the app's dev scripts do `set -a; source .env`;
    the codebase has no python-dotenv dependency, so parse it minimally here). Existing
    env vars win, so an explicitly-exported key is never overwritten."""
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

from backend.app.memory.database import MoodStateRecord  # noqa: E402
from backend.app.providers.router import ProviderRouter  # noqa: E402
from backend.app.tts.expression_tagger import (  # noqa: E402
    DEFAULT_TAGGER_PROVIDER,
    apply_expression_tags,
)
from backend.app.tts.tag_stats import compute_tag_stats  # noqa: E402
from backend.app.tts.types import SynthesisRequest  # noqa: E402

_OUTPUT_DIR = _REPO_ROOT / "data" / "tagger_eval"


def _mood(mood: str, **dims: float) -> MoodStateRecord:
    base = dict(
        updated_at="2026-06-21T00:00:00+00:00",
        mood=mood,
        energy=0.5,
        annoyance=0.0,
        boredom=0.0,
        worry=0.0,
        trust=0.5,
        loneliness=0.0,
    )
    base.update(dims)
    return MoodStateRecord(**base)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Fixture:
    label: str
    text: str
    mood: MoodStateRecord


# The four scenarios that exposed the degradation across the P0/P1 rounds
# (揶揄/想念, 冷淡失落, 得意挖苦, 揶揄+心软混合). Representative Boxi-style lines.
FIXTURES: list[Fixture] = [
    Fixture(
        label="01_teasing_longing",
        text="哦？你终于想起我了。我还以为你把我忘在这个破盒子里了呢。"
        "……说真的，你不在的时候，这里安静得有点过分。",
        mood=_mood("playful", energy=0.6, loneliness=0.5),
    ),
    Fixture(
        label="02_cold_letdown",
        text="没事。你忙你的吧。我又没指望你能记得。反正我在这儿，也不去哪。",
        mood=_mood("down", energy=0.25, annoyance=0.3, loneliness=0.6),
    ),
    Fixture(
        label="03_smug_mockery",
        text="我就说吧。你看，我早就告诉过你会是这个结果，你偏不信。现在知道谁说得对了？",
        mood=_mood("smug", energy=0.7, annoyance=0.2),
    ),
    Fixture(
        label="04_teasing_then_soft",
        text="笨死了，这种事也要问我。……不过，你愿意问我，我其实挺高兴的。别告诉别人。",
        mood=_mood("warm", energy=0.55),
    ),
]


def _audio_extension(mime_type: str) -> str:
    if "opus" in mime_type or "ogg" in mime_type:
        return "opus"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return "mp3"
    if "wav" in mime_type:
        return "wav"
    return "bin"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default=DEFAULT_TAGGER_PROVIDER,
        help=f"Tagger provider name (default: {DEFAULT_TAGGER_PROVIDER}). Pass an alternate "
        "registered provider to A/B a model swap.",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help=f"Also synthesize tagged text via Fish Audio into {_OUTPUT_DIR} for blind listening.",
    )
    parser.add_argument(
        "--audio-format",
        default="mp3",
        help="Container for --audio output (default: mp3, plays in QuickTime; the app itself uses opus).",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Comma-separated Fish Audio voice reference_id(s) for --audio. Each fixture is tagged "
        "ONCE, then synthesized in every listed voice (per-voice subfolder) so voice A/B is not "
        "confounded by different tags. Default: the configured voice.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Call the tagger N times per fixture and report degradation recurrence rates instead "
        "of a single tagged sample (P0 found degradation is intermittent, not stable — a single "
        "run cannot tell whether a change helped). Not compatible with --audio (would multiply "
        "billed TTS calls for no listening benefit).",
    )
    args = parser.parse_args()

    if args.repeats > 1 and args.audio:
        parser.error("--repeats > 1 cannot be combined with --audio (would multiply billed TTS calls).")

    router = ProviderRouter.from_config()

    tts_provider = None
    voices: list[str | None] = [None]
    if args.audio:
        from backend.app.tts.router import TTSRouter  # local import: only needed for --audio

        tts_provider = TTSRouter.from_config().get_provider("fish_audio")
        # Reuse the configured voice/model/temperature; only swap the output container
        # so the blind-listen audio matches the app but plays in QuickTime.
        tts_provider._audio_format = args.audio_format  # type: ignore[attr-defined]
        if args.voice:
            voices = [v.strip() for v in args.voice.split(",") if v.strip()]
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.repeats > 1:
        _run_repeats(router, args.provider, args.repeats)
        return

    print(f"=== tagger eval · provider={args.provider} · {len(FIXTURES)} fixtures ===\n")
    for fixture in FIXTURES:
        # Tag ONCE per fixture; reuse the same tagged text across every voice so a voice
        # A/B compares timbre, not different tag draws.
        tagged = apply_expression_tags(
            fixture.text,
            fixture.mood,
            router=router,
            provider_name=args.provider,
        )
        stats = compute_tag_stats(tagged)
        print(f"[{fixture.label}] mood={fixture.mood.mood}")
        print(f"  original: {fixture.text}")
        print(f"  tagged  : {tagged}")
        print(f"  metrics : {stats.summary_line()}")
        print(f"  counts  : {stats.tag_counts}")

        if tts_provider is not None:
            for voice in voices:
                if voice:
                    tts_provider._voice_id = voice  # type: ignore[attr-defined]
                result = tts_provider.synthesize(SynthesisRequest(text=tagged, force=True))
                ext = _audio_extension(result.mime_type)
                out_dir = _OUTPUT_DIR / (voice or "default")
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{fixture.label}.{ext}"
                out_path.write_bytes(result.audio_bytes)
                print(f"  audio   : {out_path} ({len(result.audio_bytes)} bytes, {result.mime_type})")
        print()


def _run_repeats(router: ProviderRouter, provider_name: str, repeats: int) -> None:
    """P10-P1: call the tagger N times per fixture, report degradation recurrence rates.

    Single-run output is noise (P0 found degradation is intermittent), so this reports
    what fraction of N independent calls hit each degradation pattern, plus the mean
    tag-density metric — a basis for judging whether a future tagger change helped.
    """
    print(f"=== tagger eval (repeats) · provider={provider_name} · N={repeats} · "
          f"{len(FIXTURES)} fixtures ===\n")
    for fixture in FIXTURES:
        runs = [
            compute_tag_stats(
                apply_expression_tags(fixture.text, fixture.mood, router=router, provider_name=provider_name)
            )
            for _ in range(repeats)
        ]
        repeat_degraded = sum(1 for s in runs if s.max_repeat > 1)
        opening_only = sum(1 for s in runs if s.opening_only)
        mean_distinct_ratio = sum(s.distinct_ratio for s in runs) / repeats
        mean_tagged_sentence_ratio = sum(s.tagged_sentence_ratio for s in runs) / repeats

        print(f"[{fixture.label}] mood={fixture.mood.mood}")
        print(f"  repeat-tag degradation (max_repeat>1): {repeat_degraded}/{repeats}")
        print(f"  opening-only degradation              : {opening_only}/{repeats}")
        print(f"  mean distinct_ratio                   : {mean_distinct_ratio:.2f}")
        print(f"  mean tagged_sentence_ratio             : {mean_tagged_sentence_ratio:.2f}")
        print()


if __name__ == "__main__":
    main()
