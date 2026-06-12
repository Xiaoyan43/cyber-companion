"""RTC / S2S persona loaders — Chinese dialog fields from persona.json."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.memory.persona import (
    load_chinese_persona_prompt,
    load_persona_name,
    load_persona_system_prompt,
    load_rtc_speaking_style,
    load_rtc_system_role,
)


def test_chinese_persona_prompt_unified_across_loaders(tmp_path: Path) -> None:
    persona = {
        "name": "小盒",
        "core_persona": "测试人设",
        "tone": {"sarcasm": 0.8, "warmth": 0.2, "directness": 0.9},
    }
    (tmp_path / "persona.json").write_text(json.dumps(persona, ensure_ascii=False), encoding="utf-8")

    expected = load_chinese_persona_prompt(tmp_path)
    assert load_rtc_system_role(tmp_path) == expected
    assert load_persona_system_prompt(tmp_path) == expected
    assert "你是 小盒，测试人设" in expected
    assert "边界" not in expected
    assert "务实" not in expected
    assert load_persona_name(tmp_path) == "小盒"


def test_load_rtc_speaking_style_uses_tone(tmp_path: Path) -> None:
    persona = {
        "name": "Boxi",
        "tone": {"sarcasm": 0.5, "warmth": 0.5, "directness": 0.7},
    }
    (tmp_path / "persona.json").write_text(json.dumps(persona, ensure_ascii=False), encoding="utf-8")

    style = load_rtc_speaking_style(tmp_path)
    assert "讽刺≈0.5" in style
    assert "温暖≈0.5" in style
    assert "口语化" in style
    assert "客服" not in style
