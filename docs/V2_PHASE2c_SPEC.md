# Spec — V2 Phase 2c: Doubao end-to-end realtime voice (Dialog S2S, OutputMode 0/1)

Source: user request (fundamental latency fix) + Doubao 端到端实时语音大模型 docs
(6561/1739229, /1739228, /1597646; product page realtime-voice-model).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Reuse-first. **Additive —
keep the current STT→brain→TTS pipeline as a fallback toggle; do not delete it.**

## Why
Measured 3–3.4s = ~1s STT-finalize + ~1.8s DeepSeek-to-first-sentence + ~0.9s TTS. The
end-to-end model fuses ASR+LLM+TTS in one streaming WebSocket → kills the STT/TTS overhead
and is natively interruptible. The **~1.8s LLM floor only disappears in pure mode** (Doubao's
brain); hybrid mode keeps our soul but the external-LLM round-trip remains.

## The two modes (build BOTH, choose via config)
- **`OutputMode 0` — pure end-to-end.** Doubao's fused model is the brain → **sub-second**,
  interruptible. Soul kept via: persona (`system_role`/`bot_name`/`speaking_style`) + our
  retrieved memory injected as context (short-term-memory / 自定义指令) + memory/relationship
  **extracted from the returned transcripts** off-path. Drops DeepSeek + behavior engine +
  signals trailer.
- **`OutputMode 1` — hybrid orchestration.** Doubao does fast ASR/TTS; **our soul/DeepSeek is
  the orchestrated LLM** via `LLMConfig` (bring-your-own-LLM). Full soul; latency ~2s.

## Ground rule on protocol (read first)
Implement against the **official Doubao Dialog / realtime API docs + official sample/SDK**
(doc series 6561; the Dialog WebSocket S2S, *not* the RTC SDK — RTC is heavier and not needed
for our local-audio setup). The framing/`OutputMode`/`LLMConfig` field names here are
orientation — **the docs win**; reuse Volcengine's sample (like we did for `sauc` streaming
ASR). Record what you reused in `docs/OPEN_SOURCE_REUSE.md`.

## What we know
- Auth: **App ID + Access Token** (provided; env only — `DOUBAO_RT_APP_ID`,
  `DOUBAO_RT_ACCESS_TOKEN`; never committed). WebSocket Dialog endpoint per docs.
- Audio: bidirectional streaming PCM in/out; the model handles endpointing + barge-in.
- Returns **text transcripts** (实时字幕/对话记录) for user + bot → feed our memory extraction.

## Tasks (staged — Task 1 proves the latency win)
1. **Pure mode skeleton (`OutputMode 0`).** New `backend/realtime/doubao_realtime_service.py`
   — a Pipecat processor that opens the Dialog WebSocket, streams mic PCM up, plays returned
   audio down, injects Boxi **persona** (`system_role` from `load_persona_system_prompt`).
   Wire a new pipeline path in `run_voice.py` (`CYBER_COMPANION_VOICE_MODE=realtime`,
   replacing the STT+brain+TTS chain with this single service). **Measure latency** vs the
   3.4s baseline. This is the hard unknown — land it first.
2. **Memory in/out (still pure mode).** Inject our retrieved compact memory as context
   (short-term-memory / custom-instruction field). On each completed turn, take the
   user+bot **transcripts** and run the soul's `record_turn_memories` + kernel updates
   **off the audio path** (reuse `CompanionBrain.remember`-style logic, transcript-driven).
3. **Hybrid mode (`OutputMode 1`).** Configure `LLMConfig` so the Dialog model orchestrates
   **our soul** as the LLM. If that requires an OpenAI-compatible endpoint, expose the soul
   (compact context + DeepSeek) as a minimal local endpoint the model calls; else use the
   docs' native bring-your-own-LLM hook. Full behavior/persona/memory via the soul.
4. **Toggle + fallback + measure.** `CYBER_COMPANION_VOICE_MODE` ∈ `{pipeline (default),
   realtime}`; `CYBER_COMPANION_VOICE_OUTPUT_MODE` ∈ `{0,1}`. Keep the current
   pipeline (STT/brain/TTS) fully working as default. Session log: real latency for pure vs
   hybrid vs current, and a soul-quality note (does memory/persona survive each mode).

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; V1 untouched;
   realtime tests `importorskip`.
2. `CYBER_COMPANION_VOICE_MODE=realtime` (pure): speak → **sub-second, interruptible** Doubao
   voice reply; persona is Boxi; transcripts logged; a memory row written off-path.
3. Hybrid mode: reply goes through the soul (DeepSeek + memory + behavior); latency measured.
4. Current pipeline still works as the default fallback.
5. Diff confined to `backend/realtime/**`, `backend/requirements-realtime.txt`,
   `docs/SESSION_LOG.md`, `docs/TODO.md`, `docs/OPEN_SOURCE_REUSE.md`. **No `backend/app/**`**
   (soul reused, not edited) **or `frontend/**`**.

## Boundaries
- Additive: the current STT→brain→TTS pipeline stays the default and is not deleted.
- Reuse Volcengine's official Dialog sample/SDK; verify every field against the live docs.
- Keys (App ID + Access Token) via env only; never committed.
- Soul reused, not edited. If a soul change is truly needed for hybrid, stop and flag it `[Claude]`.
- This is the hardest integration yet — if a stage stalls, report the specific blocker
  (auth? framing? OutputMode? LLMConfig?) rather than thrashing. Land Task 1 first.
