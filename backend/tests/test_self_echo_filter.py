import pytest

pytest.importorskip("pipecat")

from backend.realtime.self_echo_filter import SelfEchoGate, is_self_echo


# --- is_self_echo (pure matching logic) ---------------------------------------------------


def test_exact_tail_echo_is_detected() -> None:
    # The real bug: Boxi's reply ends with "我都在。"; the mic captures that tail.
    bot = '你要是还想接着说，或者让我再讲一个跟“回不去的夏天”有关的故事，我都在。\n'
    assert is_self_echo("我都在。", bot) is True


def test_full_reply_echo_is_detected() -> None:
    bot = "挺残忍的，但也挺彻底。"
    assert is_self_echo("挺残忍的，但也挺彻底", bot) is True


def test_genuine_followup_sharing_a_mid_word_is_not_echo() -> None:
    # "接着说" appears in the middle of Boxi's reply but is NOT its tail → real user turn.
    bot = "你要是还想接着说，我都在。"
    assert is_self_echo("我想接着说", bot) is False


def test_user_longer_than_bot_is_not_echo() -> None:
    assert is_self_echo("我都在你身边一直陪着你", "我都在") is False


def test_too_short_is_not_echo() -> None:
    # A single-char overlap (user might genuinely say "嗯") must not be suppressed.
    assert is_self_echo("嗯", "今天天气真好嗯") is False


def test_fuzzy_tail_absorbs_minor_asr_error() -> None:
    # ASR mishears one char of the leaked tail; still a self-echo.
    bot = "搬了也抓不回那个味道了。"
    assert is_self_echo("那个味道了", bot) is True
    assert is_self_echo("那个味到了", bot) is True  # 道→到 ASR slip


def test_unrelated_user_text_is_not_echo() -> None:
    bot = "我都在。"
    assert is_self_echo("你再给我讲一个故事吗", bot) is False


# --- SelfEchoGate (capture + window + consume) --------------------------------------------


def _gate_with_clock(window_ms: int = 4000):
    clock = {"t": 1000.0}
    gate = SelfEchoGate(window_ms=window_ms, now=lambda: clock["t"])
    return gate, clock


def test_gate_captures_reply_and_suppresses_echo_within_window() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("你要是还想接着说，")
    gate.on_reply_delta("我都在。\n")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 1.5  # echo final arrives ~1.5s after Boxi stops
    assert gate.is_echo("我都在。") is True


def test_gate_does_not_suppress_past_window() -> None:
    gate, clock = _gate_with_clock(window_ms=4000)
    gate.on_reply_start()
    gate.on_reply_delta("我都在。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 5.0  # well past the 4s window → treat as a genuine user turn
    assert gate.is_echo("我都在。") is False


def test_gate_suppresses_exact_single_char_tail_in_brief_playback_window() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("先睡，乖。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 1.5
    assert gate.is_echo("乖。") is True


def test_gate_preserves_single_char_reply_after_brief_playback_window() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("先睡，乖。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 2.1
    assert gate.is_echo("乖。") is False


def test_gate_preserves_unrelated_single_char_reply_during_playback_window() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("先睡，乖。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 1.0
    assert gate.is_echo("好。") is False


def test_gate_without_bot_stopped_does_not_suppress() -> None:
    gate, _ = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("我都在。")
    gate.on_reply_end()
    # No on_bot_stopped() → window never opened.
    assert gate.is_echo("我都在。") is False


def test_gate_suppresses_at_most_one_echo_per_turn() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("我都在。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 1.0
    assert gate.is_echo("我都在。") is True
    gate.consume()
    # A genuine follow-up that happens to repeat the words is no longer eaten.
    assert gate.is_echo("我都在。") is False


def test_gate_new_reply_replaces_last_reply() -> None:
    gate, clock = _gate_with_clock()
    gate.on_reply_start()
    gate.on_reply_delta("第一句话。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    gate.on_reply_start()
    gate.on_reply_delta("第二句话。")
    gate.on_reply_end()
    gate.on_bot_stopped()

    clock["t"] += 1.0
    assert gate.is_echo("第二句话") is True
    gate.consume()
    assert gate.is_echo("第一句话") is False
