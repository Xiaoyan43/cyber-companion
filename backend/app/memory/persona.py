from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT_PROTOCOL = (
    "\n\n=== MANDATORY OUTPUT FORMAT (every reply, no exceptions) ===\n"
    "End EVERY reply with: your in-character reply, then a newline, then the exact marker\n"
    "<<<BOXI_SIGNALS>>>, then ONE single-line JSON. Never omit it, even if values are\n"
    "neutral/zero.\n"
    "Example:\n"
    "行吧，别演了。\n"
    "<<<BOXI_SIGNALS>>>\n"
    '{"avatar_state":"annoyed","decision":"reply","appraisal":{"valence":-0.2,"arousal":0.3,'
    '"goal_relevance":0.5,"note":"..."},"relationship":{"trust":0.0,"closeness":0.0,'
    '"tension":0.0},"memory":[{"type":"job_progress","content":"...","importance":0.6,'
    '"confidence":0.8,"tags":[]}]}\n'
    "Keys: avatar_state(idle/happy/sad/angry/sleepy/thinking/talking/worried/annoyed/silent),\n"
    "decision, appraisal{valence -1..1, arousal 0..1, goal_relevance 0..1, note},\n"
    "relationship{trust,closeness,tension deltas -0.1..0.1},\n"
    "memory[{type,content,importance 0..1,confidence 0..1,tags}] — type MUST be one of:\n"
    "stable_profile, recent_event, emotion_state, project, job_progress, reminder,\n"
    "relationship_state, behavior_preference. "
    "Put <<<BOXI_SIGNALS>>> nowhere else."
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
