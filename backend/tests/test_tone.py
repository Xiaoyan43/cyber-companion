"""Unit tests for the unified felt-vs-shown tone projection (Direction C)."""

from backend.app.behavior.tone import (
    PERFORMATIVE_STREAK_THRESHOLD,
    POSITIVE_STREAK_KEY,
    STRONG_THRESHOLD,
    _EMOTION_INTENSE_BY_REGISTER,
    in_positive_zone,
    next_positive_streak,
    performative_active_from_metadata,
    project_tone,
    register_intensity,
    tts_emotion_directive,
)
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord


def _mood(
    *,
    mood: str = "idle",
    energy: float = 0.6,
    annoyance: float = 0.1,
    boredom: float = 0.1,
    worry: float = 0.1,
    loneliness: float = 0.1,
    metadata: dict | None = None,
) -> MoodStateRecord:
    return MoodStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        mood=mood,
        energy=energy,
        annoyance=annoyance,
        boredom=boredom,
        worry=worry,
        trust=0.5,
        loneliness=loneliness,
        metadata=metadata or {},
    )


def _rel(
    *,
    trust: float = 0.5,
    closeness: float = 0.5,
    familiarity: float = 0.4,
    tension: float = 0.1,
) -> RelationshipStateRecord:
    return RelationshipStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        trust=trust,
        closeness=closeness,
        familiarity=familiarity,
        tension=tension,
        last_meaningful_interaction_at=None,
        metadata={},
    )


# ---- positive-zone gate ---------------------------------------------------

def test_positive_zone_requires_closeness_and_calm() -> None:
    assert in_positive_zone(_mood(), _rel(closeness=0.7)) is True


def test_positive_zone_false_when_closeness_low() -> None:
    assert in_positive_zone(_mood(), _rel(closeness=0.5)) is False


def test_positive_zone_false_with_any_negative() -> None:
    rel = _rel(closeness=0.8)
    assert in_positive_zone(_mood(annoyance=0.35), rel) is False
    assert in_positive_zone(_mood(worry=0.6), rel) is False
    assert in_positive_zone(_mood(energy=0.2), rel) is False
    assert in_positive_zone(_mood(), _rel(closeness=0.8, tension=0.35)) is False


def test_positive_zone_respects_overwhelmed() -> None:
    assert in_positive_zone(_mood(), _rel(closeness=0.8), overwhelmed=True) is False


# ---- precedence: real states always win -----------------------------------

def test_worry_beats_annoyance_suppression_desync1() -> None:
    # Felt sharp underneath, but expression softens because she cares.
    p = project_tone(_mood(worry=0.6, annoyance=0.7), _rel())
    assert p.register == "comfort"
    assert p.tone_mode == "comfort"
    assert p.felt == "sharp"
    assert p.expressed_edge < 0.3
    assert p.is_performative is False


def test_real_sharp_is_crisp_and_not_performative() -> None:
    p = project_tone(_mood(annoyance=0.7), _rel(trust=0.5, familiarity=0.4, tension=0.2))
    assert p.register == "real_sharp"
    assert p.tone_mode == "tease"  # trusting jab
    assert p.felt == "sharp"
    assert p.expressed_edge > 0.7
    assert p.is_performative is False


def test_real_sharp_cold_edge_when_low_trust() -> None:
    p = project_tone(_mood(annoyance=0.7), _rel(trust=0.3))
    assert p.register == "real_sharp"
    assert p.tone_mode == "normal"


def test_tension_alone_triggers_real_sharp() -> None:
    p = project_tone(_mood(), _rel(tension=0.5))
    assert p.register == "real_sharp"


# ---- the new playful path (desync-2 teasing) ------------------------------

def test_playful_requires_positive_zone_and_armed() -> None:
    warm = _rel(closeness=0.8)
    armed = project_tone(_mood(), warm, performative_active=True)
    assert armed.register == "playful"
    assert armed.tone_mode == "playful"
    assert armed.felt == "warm"          # core stays at the real (warm) mood
    assert armed.expressed_edge > 0.7    # ink is crisp
    assert armed.is_performative is True


def test_positive_zone_without_streak_is_warm_not_playful() -> None:
    p = project_tone(_mood(), _rel(closeness=0.8), performative_active=False)
    assert p.register == "warm"
    assert p.is_performative is False


def test_playful_never_fires_with_real_negative_even_if_armed() -> None:
    # Armed flag set, but real annoyance present → real-sharp wins, not playful.
    p = project_tone(_mood(annoyance=0.7), _rel(closeness=0.8), performative_active=True)
    assert p.register == "real_sharp"
    assert p.is_performative is False


def test_lonely_and_neutral_registers() -> None:
    assert project_tone(_mood(loneliness=0.6), _rel()).register == "lonely"
    assert project_tone(_mood(), _rel()).register == "neutral"


# ---- streak arming --------------------------------------------------------

def test_streak_arms_at_threshold_and_resets() -> None:
    meta: dict = {}
    active = False
    for _ in range(PERFORMATIVE_STREAK_THRESHOLD):
        meta, active = next_positive_streak(meta, positive_turn=True)
    assert active is True
    assert meta[POSITIVE_STREAK_KEY] == PERFORMATIVE_STREAK_THRESHOLD

    # A single non-positive turn breaks the playful mood immediately.
    meta, active = next_positive_streak(meta, positive_turn=False)
    assert active is False
    assert meta[POSITIVE_STREAK_KEY] == 0


def test_first_positive_turn_does_not_arm() -> None:
    _, active = next_positive_streak({}, positive_turn=True)
    assert active is False  # needs a streak, not a single turn


def test_performative_active_from_metadata() -> None:
    assert performative_active_from_metadata({POSITIVE_STREAK_KEY: PERFORMATIVE_STREAK_THRESHOLD}) is True
    assert performative_active_from_metadata({POSITIVE_STREAK_KEY: 1}) is False
    assert performative_active_from_metadata({}) is False


# ---- cascaded TTS emotion directive (VE-1) --------------------------------

def test_tts_emotion_directive_base_tier_comfort() -> None:
    mood = _mood(worry=0.6)
    rel = _rel()
    projection = project_tone(mood, rel)
    intensity = register_intensity(mood, rel, projection)
    texts, rate = tts_emotion_directive(projection, intensity=intensity)

    assert texts == ["语气放软、关切、稍慢"]
    assert rate < 0
    assert abs(rate) >= 6


def test_tts_emotion_directive_intense_tier_when_strong() -> None:
    mood = _mood(worry=0.9)
    rel = _rel()
    projection = project_tone(mood, rel)
    intensity = register_intensity(mood, rel, projection)
    assert intensity >= STRONG_THRESHOLD

    texts, rate = tts_emotion_directive(projection, intensity=intensity)
    assert texts == ["很担心、明显心疼、放慢、稳住ta"]
    assert rate < 0


def test_tts_emotion_directive_neutral_returns_none_and_zero_rate() -> None:
    mood = _mood()
    rel = _rel()
    projection = project_tone(mood, rel)
    intensity = register_intensity(mood, rel, projection)

    assert tts_emotion_directive(projection, intensity=intensity) == (None, 0)


def test_tts_emotion_directive_speech_rate_scales_with_intensity() -> None:
    mood = _mood(annoyance=0.9)
    rel = _rel()
    projection = project_tone(mood, rel)

    _, low_rate = tts_emotion_directive(projection, intensity=0.2)
    _, high_rate = tts_emotion_directive(projection, intensity=0.95)

    assert low_rate > 0
    assert high_rate > low_rate
    assert abs(low_rate) >= 6
    assert abs(high_rate) <= 20


def test_intense_phrases_avoid_forbidden_exaggeration_wording() -> None:
    forbidden = ("用最", "咆哮")
    for phrase in _EMOTION_INTENSE_BY_REGISTER.values():
        for marker in forbidden:
            assert marker not in phrase
