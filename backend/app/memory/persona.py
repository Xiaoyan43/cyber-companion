from __future__ import annotations

import json
import os
from pathlib import Path


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
    )
