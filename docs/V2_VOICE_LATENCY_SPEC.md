# Spec — V2 Voice latency + terseness tuning

Source: Session-29 DEBUG metrics. **Claude spec → Cursor builds → Claude reviews →
checkpoint.** Confined to `backend/realtime/**` (+ optional env knobs). **No soul edits**
(`backend/app/**` untouched) — the soul persona/context is shared with text chat; voice
tuning lives in the realtime layer.

## What the metrics showed (per exchange, "you stop → Boxi talks" ≈ 3s)
- **Turn-finalize ~1–1.5s** — Silero VAD `stop_secs` (~0.8s, default) + Doubao ASR
  `end_window_size_ms=800` + a Pipecat **smart_turn** analyzer, stacked.
- LLM TTFB **0.3s** (DeepSeek caches the prefix — *not* the bottleneck; context growth is
  irrelevant, confirmed 3×).
- TTS first audio **~1.3s**.
- **The "builds up" feeling = Boxi rambles:** replies are 3–4 sentences, each a **sequential
  ~1.5–2s Doubao TTS call** → 6–8s of talking, growing as it gets chattier.

Two fixes: (1) make Boxi **terse** (kills the buildup), (2) **tighten turn-finalize** (cuts
the start gap). LLM + TTS-first-chunk are near-inherent; don't chase them here.

## Task 1 — Terseness (biggest win)
Boxi should answer voice in **one short sentence** (occasionally two), not a paragraph.
- **Prompt (primary lever):** in `CompanionBrain`, *after* `build_provider_context(...)`,
  append a **voice-mode instruction** to the built messages (realtime-layer only — do NOT
  edit the soul persona): e.g. a system message
  「语音对话模式：用一句话、口语化、简短回答（必要时最多两句）。正文之后仍按协议输出
  `<<<BOXI_SIGNALS>>>` 行。」 Keep the signals trailer working (it rides *after* the spoken
  text and is stripped by `SignalStreamFilter`, so it doesn't delay first audio).
- **Token backstop:** pass a bounded `max_output_tokens` to `CompanionBrain(...)` in
  `run_voice.py` (≈ **200** — room for one short sentence **plus** the ~150-token trailer).
  Env-overridable: `CYBER_COMPANION_VOICE_MAX_TOKENS` (default 200). The cap is a backstop;
  the instruction is what actually shortens spoken output.
- Verify the trailer still fits (signals/memory keep flowing) — if it truncates often, nudge
  the cap up; do **not** drop the trailer.

## Task 2 — Tighten turn-finalize (start latency)
Pick **one** primary endpoint mechanism and tune it tight; don't stack three.
- **VAD `stop_secs`:** pass `VADParams(stop_secs≈0.4, ...)` to `SileroVADAnalyzer` in
  `SileroVADProcessor` (currently default ~0.8s). Env: `CYBER_COMPANION_VOICE_VAD_STOP_SECS`
  (default 0.4).
- **Doubao ASR `end_window_size_ms`:** 800 → **~300** in `DoubaoStreamingSTTService`. Env:
  `CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS` (default 300).
- **smart_turn:** find where Pipecat's smart-turn analyzer is enabled (transport params /
  default in the local transport) and **disable it** (rely on VAD `stop_secs`) **or** confirm
  it's not adding a wait — it's an extra end-of-turn ML step in the logs. Document the finding.
- **Caveat:** too-aggressive endpointing cuts the user off mid-pause. Keep all three values
  **env-overridable** so the user can dial back if it clips. Tune conservatively.

## Done criteria (manual, headphones, `CYBER_COMPANION_VOICE_STT=doubao_stream`)
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; V1
   untouched; realtime tests `importorskip`.
2. Re-run with `CYBER_COMPANION_VOICE_LOG_LEVEL=DEBUG`; compare to Session-29:
   - Boxi replies in **~1 sentence** (TTS finishes in ~1.5–2s, not 6–8s).
   - "you stop → bot started speaking" gap is **noticeably shorter** (target < ~2s).
   - Signals/memory still flow (a memory row written; relationship moves) — terseness didn't
     break the trailer.
3. Session log: before/after numbers (start gap, total Boxi talk-time), the smart_turn
   finding, and the final tuned values.
4. Diff confined to: `backend/realtime/**`, `docs/SESSION_LOG.md`, `docs/TODO.md` (+ optional
   `config/*` if a knob lands there). **No `backend/app/**` or `frontend/**`.**

## Boundaries
- Realtime-layer only; reuse the soul, don't edit it. The voice-mode instruction is appended
  in `backend/realtime/`, not in `memory/persona.py`.
- Keep the signals trailer + memory writes working (terseness must not truncate them away).
- All tuning values env-overridable; conservative defaults; no new cloud deps.
- This is tuning, not architecture — if a change needs a soul edit, stop and flag it.
