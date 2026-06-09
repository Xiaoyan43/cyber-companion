# Spec — V2 Half-duplex (drop the headphones)

Source: `docs/ARCHITECTURE_V2.md` (Echo & turn-taking). **Claude spec → Cursor builds →
Claude reviews → checkpoint.** Confined to `backend/realtime/**` (+ env knob). No soul edits.

## Why
On laptop speakers, Boxi hears its own TTS through the mic → VAD fires → it interrupts
itself after ~1 word. Today the only workaround is headphones. **Half-duplex** = Boxi
**stops listening while it speaks**, resumes after — so the speaker echo never reaches the
turn logic, and you can use speakers.

**Explicit trade-off:** half-duplex **disables barge-in** (you can't interrupt Boxi mid-reply,
because the mic is muted while it talks). That's the right laptop default — the architecture
already says reliable barge-in on laptop external speakers isn't achievable in software;
true interrupt-any-time is the iPhone/hardware-AEC phase. Make it a **toggle** so headphone
users can switch back to full-duplex.

## Task 0 — Reuse-first check (do first, record finding)
Check whether the installed Pipecat (1.3.0) ships a built-in **`STTMuteFilter`** /
`STTMuteConfig` (or equivalent) with a strategy that **mutes STT/VAD while the bot is
speaking** (Pipecat has mute strategies like `MUTE_UNTIL_FIRST_BOT_COMPLETE`, function-call,
custom, etc.). If a "mute while bot speaks" strategy exists → **use it directly** in the
pipeline; do not hand-roll. Only build a custom processor if Pipecat lacks it.

## Task 1 — Half-duplex gating
- **Preferred (reuse):** insert Pipecat's `STTMuteFilter` configured to mute during bot
  speech, placed so it suppresses user audio/STT between `BotStartedSpeakingFrame` and
  `BotStoppedSpeakingFrame` (both already in the logs).
- **Fallback (custom, only if no built-in):** a small `FrameProcessor` in `backend/realtime/`
  that, on `BotStartedSpeakingFrame`, drops incoming audio / `Interim`/`Transcription` /
  VAD-start frames until `BotStoppedSpeakingFrame`. Mirror how the existing services consume
  frames; verify frame-type names against the installed Pipecat.
- Add a tiny **resume guard** if needed (e.g. ignore a trailing partial that arrives right as
  the bot stops) so the first post-reply utterance isn't half-eaten.

## Task 2 — Toggle + wiring
- Env knob in `voice_config.py`: `CYBER_COMPANION_VOICE_HALF_DUPLEX` (default **on**).
  `off` → current full-duplex behavior (barge-in, needs headphones).
- Wire into `run_voice.py`'s pipeline build; log the active mode in the "Voice brain ready"
  line (like the other knobs).

## Task 3 — Pre-warm jieba (folded-in freebie)
At voice startup (before the first turn), call `retrieval.tokenize("预热")` once so the ~1s
jieba model load doesn't land on the user's first utterance. One call, in `run_voice.py`
startup (or the brain's `__init__`). Realtime layer only.

## Done criteria (manual)
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; V1 untouched;
   realtime tests `importorskip`.
2. **On laptop speakers, no headphones:** Boxi speaks a full reply **without cutting itself
   off**; after it finishes, it listens again and you can take your turn. With
   `CYBER_COMPANION_VOICE_HALF_DUPLEX=off` + headphones, barge-in still works as before.
3. First-turn latency no longer pays the jieba cold-load (turn 1 ≈ later turns).
4. Session log: reuse finding (Pipecat built-in used or custom), the toggle, before/after
   (self-interrupt gone on speakers).
5. Diff confined to: `backend/realtime/**`, `docs/SESSION_LOG.md`, `docs/TODO.md`. No
   `backend/app/**` / `frontend/**`.

## Boundaries
- Realtime layer only; reuse Pipecat's mute filter if present.
- Half-duplex disables barge-in by design — document it; keep the toggle.
- Keys env-only; no new cloud deps; conservative default (half-duplex on).
- Full-duplex barge-in stays a later hardware-phase win (iPhone AEC), not this slice.
