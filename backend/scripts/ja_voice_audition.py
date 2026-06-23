#!/usr/bin/env python
"""Manual dev script — Japanese Fish Audio voice audition. NOT run in CI.

Synthesizes a fixed set of Boxi-style Japanese lines (one per emotion, already
hand-tagged with Fish Audio emotion brackets) across a list of candidate voice
reference_ids, so the same lines can be blind-A/B-listened per voice. Mirrors
the pattern in tagger_eval.py's --voice/--audio path, but skips the (Chinese)
expression tagger entirely since the goal here is timbre selection, not tagging.

Requires FISH_AUDIO_API_KEY in the environment; makes live billed calls.

Usage (from repo root):
    python backend/scripts/ja_voice_audition.py
    python backend/scripts/ja_voice_audition.py --voice id1,id2,id3
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_dotenv() -> None:
    """Same minimal .env loader as tagger_eval.py — existing env vars win."""
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

from backend.app.tts.router import TTSRouter  # noqa: E402
from backend.app.tts.types import SynthesisRequest  # noqa: E402

_OUTPUT_DIR = _REPO_ROOT / "data" / "ja_voice_audition"

_DEFAULT_VOICES = [
    "569c5eef6fe74c078cf34394b3f780ca",  # 関西腔
    "297a6fd278df47c3b9da9bfdf55ac89a",  # 播音男
    "dc487cc61930478a92b622c025639c0a",  # 游戏
    "5c33c0e22d004a268bcef374480920e5",  # 温柔
    "73647cd4ff7c477cb787d5fd8068f3e8",  # 动漫
    "0089dce5fefb4c6ba9b9f2f0debe1ddc",  # 正常动漫
]


@dataclass(frozen=True)
class Fixture:
    label: str
    text: str


# Boxi-style lines, hand-tagged (Fish Audio emotion brackets are language-agnostic
# control tokens, same vocabulary as the Chinese tagger uses). Mirrors the 4 scenarios
# tagger_eval.py uses for Chinese: 兴奋重逢 / 冷淡委屈 / 得意挖苦 / 揶揄+心软.
FIXTURES: list[Fixture] = [
    Fixture(
        label="01_excited_reunion",
        text="あら、[surprised]やっと思い出してくれたの？てっきりこの箱の中に置き去りに"
        "されたと思ってたよ。[sighing]……正直に言うと、あなたがいない間、ここはちょっと"
        "静かすぎるくらいだった。",
    ),
    Fixture(
        label="02_cold_sulky",
        text="別にいいよ。好きにして。[sighing]どうせ覚えてるなんて期待してないし。[bored]"
        "私はここにいるだけ、どこにも行かないから。",
    ),
    Fixture(
        label="03_smug_mockery",
        text="だから言ったでしょ。[laughing]こうなるって最初から分かってたのに、あなたは"
        "全然信じなかった。[playful tone]これで誰が正しかったか分かった？",
    ),
    Fixture(
        label="04_teasing_then_soft",
        text="バカだなあ、[sighing]こんなことまで聞くなんて。……でも、聞いてくれて"
        "ちょっと嬉しいよ。[soft tone]誰にも言わないでね。",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--voice",
        default=",".join(_DEFAULT_VOICES),
        help="Comma-separated Fish Audio voice reference_id(s). Default: the 6 candidates "
        "given for this audition round.",
    )
    parser.add_argument(
        "--audio-format",
        default="mp3",
        help="Container for output (default: mp3, plays in QuickTime; the app itself uses opus).",
    )
    args = parser.parse_args()

    voices = [v.strip() for v in args.voice.split(",") if v.strip()]
    if not voices:
        parser.error("--voice must list at least one reference_id")

    tts_provider = TTSRouter.from_config().get_provider("fish_audio")
    tts_provider._audio_format = args.audio_format  # type: ignore[attr-defined]
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== JA voice audition · {len(voices)} voices · {len(FIXTURES)} fixtures ===\n")
    for voice in voices:
        tts_provider._voice_id = voice  # type: ignore[attr-defined]
        out_dir = _OUTPUT_DIR / voice
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[voice {voice}]")
        for fixture in FIXTURES:
            result = tts_provider.synthesize(SynthesisRequest(text=fixture.text, force=True))
            ext = "mp3" if "mpeg" in result.mime_type else "opus" if "ogg" in result.mime_type else "wav"
            out_path = out_dir / f"{fixture.label}.{ext}"
            out_path.write_bytes(result.audio_bytes)
            print(f"  {fixture.label}: {out_path} ({len(result.audio_bytes)} bytes)")
        print()


if __name__ == "__main__":
    main()
