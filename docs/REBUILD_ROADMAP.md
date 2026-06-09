# Rebuild Roadmap — toward the Companion in a Box

Driven by `docs/ARCHITECTURE_V2.md`. Each phase is independently verifiable.
Per phase: **Claude specs → Cursor builds → Claude reviews → checkpoint.** Keep
the soul (memory/behavior/persona/provider/file-gateway) throughout. Build
**hardware-ready** at every step (brain/surface split, audio abstraction, cloud
brains).

## Phase 0 — Foundation for the rebuild
- Adopt Pipecat (Level-4) + PixiJS (Level-3); record in `OPEN_SOURCE_REUSE.md`.
- Establish the brain/surface boundary in the repo layout.
- Keep V1 running so we don't lose a working app while rebuilding.
- **Done when:** the new structure exists and the old app still runs.

## Phase 1 — Pipecat voice skeleton (the hardest unknown first)
- Stand up a minimal Pipecat pipeline: mic → VAD → STT → DeepSeek (LLM slot) →
  TTS → speaker, with **interruption** working. Use whatever STT/TTS is fastest
  to wire first (even a placeholder) to prove the loop.
- **Done when:** you can speak, DeepSeek replies in voice, and you can interrupt
  it. (On laptop external speaker: half-duplex is acceptable here.)

## Phase 2 — Doubao streaming STT/TTS as Pipecat services
- Port the existing Doubao adapter logic into Pipecat custom services; use the
  **streaming** STT (removes post-release latency) and streaming TTS.
- **Done when:** Chinese voice in/out is fast and accurate through the pipeline.

## Phase 3 — Companion Brain (plug the soul into the LLM slot)
- Inside Pipecat's LLM step: run the behavior engine first (reply / silent /
  mutter / refuse / interrupt / proactive), inject retrieved memory + mood +
  persona, call DeepSeek, run M2 memory write, emit avatar_state + action tags.
- Proactive: Boxi can speak unprompted (idle/mood ticks).
- **Done when:** the real-time voice has Boxi's personality, can stay silent /
  refuse / nudge, and remembers across turns.

## Phase 4 — Turn-taking for external speaker
- Half-duplex turn-taking + VAD tuning so Boxi never hears itself; configurable
  toward full-duplex for the future hardware AEC.
- **Done when:** natural-feeling turns on a laptop with external speakers, no
  self-triggering.

## Phase 5 — 2.5D pixel room (PixiJS)
- Glass layer (the screen is the glass) + room layer + character layer. Character
  with 8–10 states bound to `avatar_state` from the brain. Replaces the CSS avatar.
- **Done when:** it visually reads as a little person living behind glass.

## Phase 6 — Room reactivity
- Day/night lighting, mood tint, progress cues, 4–6 fixed activity spots the
  character moves between.
- **Done when:** the room feels alive and reflects time/mood/progress.

## Phase 7 — Action-animation iteration (ongoing)
- Map the brain's action tags (and later, parsed stage directions) to a growing
  vocabulary of expressions/motions. Incremental — add states/actions over time.

## Phase 8 — Personal files (realism)
- Through the file permission gateway (allowed folders only), let Boxi reference
  the user's local material to deepen interaction.
- **Done when:** Boxi can use approved local context, safely.

## Phase 9 — The box (iPhone first; dedicated hardware optional)
- **Path A (now, recommended):** old iPhone (e.g. SE 2) as the surface — a
  fullscreen PWA (PixiJS room + mic/speaker + WebRTC to the brain), locked via iOS
  Guided Access on a charging dock, in a 3D-printed shell. Brain runs on the Mac
  (or a cheap headless box). **Validate iPhone AEC for full-duplex barge-in** —
  if it holds, real "interrupt any time" lands here.
- **Path B (optional, later):** dedicated Pi + screen + mic array + speaker, only
  if you want it standalone without the Mac/phone. Same surface, local audio.
- **Done when:** it lives on the desk as a real box you talk to and interrupt.

## Cross-cutting (every phase)
- Don't break the brain/surface split or the cloud-brains principle.
- Keep memory/behavior/persona/provider/file-gateway as the stable core.
- Verifiable checks per phase; checkpoint per slice; docs updated.
- Budget walls are off by user choice — no spend gating, but keep the config
  knobs so they can be re-enabled later.
