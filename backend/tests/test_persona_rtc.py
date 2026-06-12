"""RTC / S2S persona loaders — Chinese dialog fields from persona.json."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.memory.persona import (
    load_chinese_persona_prompt,
    load_persona_name,
    load_persona_system_prompt,
    load_rtc_character_manifest,
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


def test_load_rtc_character_manifest_from_persona_json(tmp_path: Path) -> None:
    manifest = "SC测试人设：毒舌小人，请用括号补充动作。"
    persona = {
        "name": "Boxi",
        "rtc_character_manifest": manifest,
    }
    (tmp_path / "persona.json").write_text(json.dumps(persona, ensure_ascii=False), encoding="utf-8")

    loaded = load_rtc_character_manifest(tmp_path)
    assert loaded == manifest
    assert "被困在透明盒子" not in loaded


def test_load_rtc_character_manifest_falls_back_to_default(tmp_path: Path) -> None:
    persona = {"name": "Boxi", "core_persona": "测试"}
    (tmp_path / "persona.json").write_text(json.dumps(persona, ensure_ascii=False), encoding="utf-8")

    loaded = load_rtc_character_manifest(tmp_path)
    assert "被困在透明盒子里的毒舌小人" in loaded
    assert "请始终以 Boxi 的身份出演" in loaded


def test_load_rtc_character_manifest_reads_example_file() -> None:
    from backend.app.memory.persona import _config_dir

    loaded = load_rtc_character_manifest(_config_dir())
    assert "回应规则" in loaded
    assert "括号()" in loaded
