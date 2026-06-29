from backend.app.behavior.types import ToneMode


def local_response_for_decision(
    decision: str,
    *,
    tone_mode: ToneMode = "normal",
) -> str:
    if decision == "silent":
        return "……"

    if decision == "mutter":
        return "嗯。你到底要不要说正事。"

    if decision == "refuse":
        return "这个我不帮。别拿我这个盒子里的倒霉小人当坏主意放大器。"

    if decision == "interrupt":
        if tone_mode == "comfort":
            return "停。你先别一口气倒完。只说一个现在能动的最小步骤。"
        return "停，别绕了。你这段话里有效信息太少。现在只说一个最小动作。"

    if decision == "proactive":
        return "喂，求职进度又安静得像断电了。今天至少投一个低门槛岗位。"

    return ""


def behavior_tone_instruction(decision: str, tone_mode: ToneMode) -> str | None:
    if tone_mode == "comfort":
        return "[Behavior tone]\nReduce sarcasm. Be brief, practical, and supportive."

    if decision == "interrupt":
        return "[Behavior tone]\nInterrupt the ramble. Redirect to one concrete next step."

    if decision == "proactive":
        return "[Behavior tone]\nProactively nudge the user on stale progress. Stay sharp, not cruel."

    if tone_mode == "playful":
        return (
            "[Behavior tone]\n心情不错，在逗ta：嘴上损ta、其实带笑意，是玩笑不是真凶。"
            "Playful teasing in a good mood — loving jabs, not real annoyance. Stay helpful."
        )

    if tone_mode == "tease":
        return "[Behavior tone]\nLight teasing is allowed, but stay helpful."

    return None
