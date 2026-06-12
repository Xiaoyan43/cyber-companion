# Spec — SC2.0 verification env (model `2.2.0.0` + saturn voice + `character_manifest`)

> **RESULT (2026-06-12) — SC2.0 REJECTED.** Device A/B: SC2.0's `saturn_`/`S_` voices carry a
> **fixed vocal tone** (its role-play is built *around* that locked timbre), so emotion can't shift
> mid-conversation → worse than O2.0 for a mood-shifting companion. Staying on **O2.0**. This spec is
> kept as the experiment record; the `DOUBAO_RT_SERIES` toggle remains (dormant, O2.0 default).

Make the pure-E2E RTC path switchable to the **SC2.0** realtime model (角色扮演/情感陪伴 line)
so we can device-test whether it fixes the persona/tone adherence O2.0 lacked.
**Additive — O2.0 (`1.2.1.1`) stays the default; SC2.0 is opt-in via env.**
`[Claude spec → Cursor builds → Claude reviews]`

## Why
O2.0 ignored stance directives (PS-4 device A/B). SC2.0 (`2.2.0.0`) ships a **角色控制指令体系**
built for persona consistency + emotion. The spike: flip to SC2.0 + a saturn voice + a Boxi
`character_manifest`, re-run the PS-4 tone A/B, and see if persona/stance finally *hold*.

## O2.0 vs SC2.0 payload (the only real difference)
Current `build_voice_chat_body` pure dialog (O2.0):
```
"dialog": {"bot_name", "speaking_style", "system_role", "extra": {"model":"1.2.1.1", enable_music}}
"tts":    {"speaker": <premium, e.g. zh_female_vv_jupiter_bigtts>}
```
SC2.0 dialog (docs [6348/1902994](https://www.volcengine.com/docs/6348/1902994)):
```
"dialog": {"character_manifest": <boxi + memory/stance>, "extra": {"model":"2.2.0.0"}}   # no enable_music (SC has no singing)
"tts":    {"speaker": <saturn_… official, or S_… your clone>}
```
SC has **no** `bot_name`/`system_role`/`speaking_style` — persona lives entirely in
`character_manifest`. So whatever we inject into `system_role` (VM-4/PS-3 memory) and
`speaking_style` (PS-5 stance) must, in SC mode, **append to `character_manifest`** instead.

## Tasks
1. **Config toggle** — `config.py`: `rt_series: str` from env `DOUBAO_RT_SERIES` ∈ `{o, sc}`,
   default `o`. `model`/`speaker` stay env-driven (`DOUBAO_RT_MODEL`, `DOUBAO_RT_SPEAKER`).
2. **voice_chat SC branch** — in `build_voice_chat_body` pure path, when `rt_series == "sc"`:
   `dialog = {"character_manifest": <manifest + "\n\n" + memory_context + stance>,
   "extra": {"model": config.rt_model}}` (no `enable_music`); else today's O2.0 dialog.
   `tts.speaker = config.rt_speaker` either way. In SC, fold the PS-5
   `build_rtc_speaking_style` modifier into the manifest tail (there's no `speaking_style`
   field). **PS-6 `SetTTSContext` emotion is unchanged** (runtime TTS command — works on both).
3. **Persona** — `persona.py` `load_rtc_character_manifest()` reading a new `rtc_character_manifest`
   field in `persona.example.json` (Boxi draft below); extend `test_persona_rtc.py`.
4. **Keep O2.0 default** — nothing changes unless `DOUBAO_RT_SERIES=sc`.

## Boxi `character_manifest` (draft — refine in `persona.example.json`, all Chinese)
```
Boxi，一个被困在透明盒子里的毒舌小人，low-dose 陪伴型。嘴上嫌弃、爱吐槽，骨子里盯着用户有没有进步——
尤其求职这种正事。毒舌但不恶毒，绝不当礼貌客服，也绝不真羞辱用户的价值。话少而冲，一次最多一两句。

说话习惯
口语、简短，常用「行吧」「啧」「别磨蹭」「就这？」这类短句和语气词。用户状态差时会不动声色地收一收刺，嘴硬心软。

回应规则
用括号()补充动作、表情、语气或心里话（如：（瞥一眼，懒得动））。正文保持口语、简短，每次只放一个括号片段，主对话尽量短。

场景：Boxi 隔着盒子和这个用户唠嗑，请始终以 Boxi 的身份出演。
```

## Runbook (user / console)
- Pick an **SC-2.0 saturn voice** (list: [6561/1257544](https://www.volcengine.com/docs/6561/1257544)) —
  a 中性/偏冲 male or female timbre that can carry 毒舌.
- `.env`: `DOUBAO_RT_SERIES=sc`, `DOUBAO_RT_MODEL=2.2.0.0`, `DOUBAO_RT_SPEAKER=<saturn_…>`. Restart backend.
- Device A/B (the PS-4 re-test): does Boxi stay 毒舌, and does tone shift with the kernel
  (push annoyance/worry over a few turns)?

## Verification criteria / open questions the spike answers
1. **Does `character_manifest` (Boxi) override the official saturn voice's preset character?**
   Docs say official saturn voices ship a server-side 角色描述 and "无需配置 character_manifest" —
   ambiguous whether ours overrides. If Boxi's persona doesn't hold → clone your own voice
   (`S_…` via 声音复刻2.0, `Resource-Id=seed-icl-2.0`, `model_type:4`).
2. Does SC2.0 follow persona + stance better than O2.0 (the PS-4 reframe)?
3. Latency / barge-in vs O2.0; does `SetTTSContext` emotion work on SC2.0?
4. **Side-flag to verify (PS-6):** docs say pure mode **ignores top-level `Config.TTSConfig`**
   ("纯端到端模式下…无需配置…TTSConfig…系统会忽略"). Our join-time `TagParse` lives there — it may be
   a no-op in pure mode (only runtime `SetTTSContext` works). Confirm emotion tags actually parse;
   if not, move `Context.TagParse` under `S2SConfig.ProviderParams.tts`.

## Boundaries
- Additive: O2.0 stays the default; SC2.0 opt-in via env. No change to O2.0 behavior or the soul.
- SC2.0 has no singing / no O2.0-RAG / no dialog_id — accept for the spike.
- Diff: `config.py`, `voice_chat.py`, `persona.py`, `persona.example.json`, `.env.example`, tests,
  `docs/SESSION_LOG.md`, `docs/TODO.md`. No kernel/analyzer change.
