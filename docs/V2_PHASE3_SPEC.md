# Spec — V2 Phase 3: Companion Brain (plug the soul into the LLM slot)

Source: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md` (Phase 3).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** This is the milestone
where voice-Boxi stops being a dumb DeepSeek and becomes **the soul** (memory + persona +
behavior). It also bounds the LLM context (good hygiene) — but see the latency caveat.

## Latency caveat (read first)
A Session-29 probe showed **DeepSeek TTFB is flat (~0.4s) up to ~2,600 input chars**, so
unbounded context is **not** the proven cause of the "builds up over the conversation"
latency. Phase 3's compact context is correct regardless, but **do not assume it fixes the
latency** — the per-stage metrics run (LLM/TTS TTFB over several turns) is the real
diagnostic and may point elsewhere (TTS synth, audio backpressure). Treat the latency fix as
a separate, metrics-driven follow-up.

## Goal
Replace the raw `OpenAILLMService` + Pipecat `LLMContext` aggregators in `run_voice.py` with a
**Companion Brain** in the LLM slot that, per finalized user utterance:
1. builds **compact context** via the soul (`build_provider_context`: persona + mood +
   relationship + relevant memories + last few turns) — *not* the full transcript;
2. runs the **behavior engine** to decide `reply / silent / mutter / refuse / interrupt /
   proactive` (Boxi does **not** always answer);
3. calls DeepSeek with that context, **streams** the reply to TTS;
4. strips the `<<<BOXI_SIGNALS>>>` trailer from spoken text (reuse SD-1's `SignalStreamFilter`);
5. off the spoken path, writes memories (`record_turn_memories`) + applies kernel/mood
   updates — exactly like `/chat/complete` does today.

The `CompanionBrain` stub from Phase 0 (`backend/realtime/companion_brain.py`) is what gets
filled in. **Mirror `backend/app/main.py:/chat/complete`** — same soul calls, same order;
the only new thing is doing it inside a Pipecat frame processor instead of an HTTP handler.

## Integration approach
Add a custom Pipecat `FrameProcessor` (e.g. `CompanionBrainProcessor`) that sits where
`OpenAILLMService` + the `LLMContextAggregatorPair` are now:
- Consumes the final `TranscriptionFrame` (user utterance) from the STT service.
- Drives the soul (context → behavior → provider stream → signal-strip) and emits
  `TextFrame`/`LLMTextFrame` (installed-version names) downstream to TTS, **sentence by
  sentence** so TTS starts early.
- The soul owns conversation state (SQLite messages + compact context), so we **drop
  Pipecat's `LLMContext` accumulation entirely** — that's the context-bounding.
- **Verify the exact FrameProcessor / frame-type API against the installed Pipecat** (don't
  trust symbol names here); follow a Pipecat custom-processor example.

## Tasks (staged — Task 1 lands the core)
1. **Core brain (reply path):** `CompanionBrainProcessor` + fill `CompanionBrain.respond` —
   `build_provider_context` → `get_provider_router().complete/stream` (DeepSeek) →
   `SignalStreamFilter` strips trailer → emit clean text frames to TTS. Persona comes from
   `load_persona_system_prompt` (replaces the hardcoded `BOXI_VOICE_PROMPT`). Context is
   compact + bounded. **Voice-Boxi now remembers + sounds like Boxi.**
2. **Behavior gate:** fill `CompanionBrain.decide` via `evaluate_behavior(BehaviorEvent(...))`.
   `silent` → emit nothing (no TTS); `mutter/refuse/proactive` → local lines (no LLM);
   `reply/interrupt` → Task-1 path. Map the decision's `avatar_state` out (log/no-op now;
   real room binding is Phase 5).
3. **Memory write + subjectivity (off the spoken path):** after the reply, fill
   `CompanionBrain.remember` → `record_turn_memories(signals=...)` + kernel/mood updates,
   run so they **never block** audio (background task / after frames are emitted). Persist the
   user + assistant turns to SQLite like `/chat/complete`.
4. **Wire `run_voice.py`:** swap the LLM section for `CompanionBrainProcessor`; keep STT
   (`doubao_stream`/flash toggle), VAD, TTS, transport, and the OpenBLAS fix unchanged.

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; V1 untouched;
   realtime tests `importorskip`.
2. Manual (headphones, `CYBER_COMPANION_VOICE_STT=doubao_stream`): tell Boxi a fact, keep
   talking, later it **recalls** that fact; replies are in 毒舌 persona; sometimes it stays
   silent/refuses (behavior engine live); a memory row is written (check `/memory/memories`
   via the V1 API against the same data dir).
3. Context is compact (soul-built), **not** the full transcript — confirm via a debug dump of
   the provider messages on one turn.
4. Diff confined to: `backend/realtime/**`, `docs/SESSION_LOG.md`, `docs/TODO.md`. **No
   `backend/app/**` changes** — the soul is imported and reused, not modified. (If a genuine
   soul change is needed, stop and flag it — that's a `[Claude]` restricted-layer call.)

## Boundaries
- Reuse the soul exactly as `/chat/complete` does; do not fork or edit `backend/app/**`.
- Soul's extra LLM work (memory/kernel/reflection) stays **off the audio path** (background),
  per the latency-smart rule.
- Keys env-only; DeepSeek for the LLM; no full-history replay.
- Don't claim the latency fix — that's metrics-driven and tracked separately.
