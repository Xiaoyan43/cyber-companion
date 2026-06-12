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


def _persona_path(config_dir: Path | None = None) -> Path | None:
    root = config_dir or _config_dir()
    persona_path = root / "persona.json"
    if persona_path.exists():
        return persona_path
    example_path = root / "persona.example.json"
    if example_path.exists():
        return example_path
    return None


def load_persona(config_dir: Path | None = None) -> dict:
    path = _persona_path(config_dir)
    if path is None:
        return {
            "name": "Boxi",
            "core_persona": "毒舌被困小人 + low-dose companionship",
            "tone": {"sarcasm": 0.65, "warmth": 0.35, "directness": 0.85},
        }
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_persona_name(config_dir: Path | None = None) -> str:
    return str(load_persona(config_dir).get("name") or "Boxi")


def _tone_values(persona: dict) -> tuple[float, float, float]:
    tone = persona.get("tone") or {}
    return (
        float(tone.get("sarcasm", 0.65)),
        float(tone.get("warmth", 0.35)),
        float(tone.get("directness", 0.85)),
    )


def load_chinese_persona_prompt(config_dir: Path | None = None) -> str:
    """Unified Chinese persona — text chat, Soul LLM, and RTC S2S system_role."""
    persona = load_persona(config_dir)
    name = str(persona.get("name") or "Boxi")
    core = str(persona.get("core_persona") or "毒舌被困小人 + low-dose companionship")
    sarcasm, warmth, directness = _tone_values(persona)
    return (
        f"你是 {name}，{core}。用口语、简短回答，每次最多一两句。\n"
        f"语气：讽刺 {sarcasm}、温暖 {warmth}、直接 {directness}。"
    )


def load_rtc_system_role(config_dir: Path | None = None) -> str:
    return load_chinese_persona_prompt(config_dir)


def load_persona_system_prompt(config_dir: Path | None = None) -> str:
    return load_chinese_persona_prompt(config_dir)


def load_rtc_speaking_style(config_dir: Path | None = None) -> str:
    sarcasm, warmth, directness = _tone_values(load_persona(config_dir))
    return (
        f"口语化，每次一两句（讽刺≈{sarcasm}，温暖≈{warmth}，直接≈{directness}）。"
    )
