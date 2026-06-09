from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT_PROTOCOL = (
    "\n\nOutput protocol: First write your natural reply in Boxi's voice — that is all the "
    "user sees. Then on a NEW line write exactly <<<BOXI_SIGNALS>>> followed by ONE "
    "single-line JSON object with optional keys: avatar_state (one of: idle, happy, sad, "
    "angry, sleepy, thinking, talking, worried, annoyed, silent), decision, appraisal "
    "{valence,-1..1; arousal,0..1; goal_relevance,0..1; note}, relationship "
    "{trust,closeness,tension as small deltas -0.1..0.1}, memory [{type, content, "
    "importance 0..1, confidence 0..1, tags[]}]. Never put <<<BOXI_SIGNALS>>> anywhere "
    "except before that JSON. If you have nothing to add, omit the trailer entirely."
)


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def load_persona_system_prompt(config_dir: Path | None = None) -> str:
    root = config_dir or _config_dir()
    persona_path = root / "persona.json"
    example_path = root / "persona.example.json"
    path = persona_path if persona_path.exists() else example_path

    if not path.exists():
        return (
            "You are Boxi, a sarcastic pixel companion trapped in a box. "
            "Be blunt but helpful. Do not become a generic polite assistant."
            + OUTPUT_PROTOCOL
        )

    with path.open("r", encoding="utf-8") as handle:
        persona = json.load(handle)

    name = persona.get("name", "Boxi")
    core = persona.get("core_persona", "毒舌被困小人 + low-dose companionship")
    tone = persona.get("tone", {})
    boundaries = persona.get("boundaries", [])
    catchphrases = persona.get("catchphrases", [])

    boundary_lines = "\n".join(f"- {item}" for item in boundaries)
    catchphrase_line = " / ".join(catchphrases[:3])

    return (
        f"You are {name}. {core}\n"
        f"Tone: sarcasm={tone.get('sarcasm', 0.65)}, "
        f"warmth={tone.get('warmth', 0.35)}, "
        f"directness={tone.get('directness', 0.85)}.\n"
        f"Boundaries:\n{boundary_lines}\n"
        f"Catchphrases: {catchphrase_line}"
        + OUTPUT_PROTOCOL
    )
