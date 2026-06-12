# Spec — Visual Spike: the being (light core + ink) `[Claude spec → Cursor builds → Claude reviews]`

A **throwaway** spike to (1) choose the being's material and (2) prove that the
**felt-vs-shown desync** reads on screen. Not the product. ~1–2 days of Cursor,
deliberately disposable. The soul/voice stack is untouched.

## Locked direction context (the "why")

- **Final form = Direction C — "a being with a world":** a character you have a real
  relationship with (foreground, carries the soul) inside an elegant space that
  accumulates shared history (background, carries the taste). Keep Boxi's 毒舌 edge but
  add range + an arc (the *Her* lesson: range/interiority/growth, not solemnity).
- **Depth over latency.** The soul authors Boxi's words → voice goes **cascaded**
  (Doubao streaming STT → DeepSeek soul → Doubao streaming TTS), already built in V2
  Phases 1–3. **Pure E2E is retained** as the fast/present mode (its depth ceiling rises
  when VikingDB custom schemas land — revisit then). Hybrid is the only dead end.
- This spike is **only the being's material**, no soul wiring, no echo world yet.

## The invariant (the spine of the whole material)

> **The light core never lies — it is always the true inner feeling. The ink is always
> the outward performance.** Aligned states and both desyncs fall out of this one rule.

## Two material candidates (build BOTH, compare)

- **A — semi-figurative light-particles.** A luminous presence (readable gaze/posture,
  no literal face/body) made of capped GPU particles; "thinking" = disperse then regather.
- **B — light-in-ink (recommended).** Deep warm-gray / indigo field, rice-paper / aged-silk
  texture. An amorphous **light core** shines through translucent **ink**. Ink flows with
  expression: crisp knife-cut edges when sharp, soft diffuse shapes when tender. Maps the
  soul's two layers literally — core = inner state, ink = outward expression. Most distinctive;
  the spike most de-risks this one (the ink is the novel part).

## States to demo (manual buttons in the spike)

| Button | Core (felt) | Ink (shown) | Reads as |
|---|---|---|---|
| idle / neutral | dim, slow | calm, mid | present, waiting |
| real-sharp (aligned) | cool-white, fast flicker | crisp | genuinely annoyed |
| warm / tender (aligned) | amber, slow breath | soft, diffuse | genuinely warm |
| **desync 1 — suppression** | cool-white, fast flicker | **soft** | feels it, hides it (cares) |
| **desync 2 — teasing** | **amber, slow breath** | **crisp** | good mood, playing sharp |
| thinking → speaking | core shrinks & trembles | ink scatters, then regathers → flows into speech | she's considering |

The two desyncs are the showcase — they are the point.

## Material data contract (3 derived signals — no new tables)

The material reads a small soul projection; the spike fakes it via buttons, live wires it later:

- `felt` → **core**: color (cool-white ↔ amber), pulse rate, brightness. From `mood_state`.
- `expressed_edge` → **ink**: crisp (1) ↔ diffuse (0). From the behavior tone output.
- `is_performative` → **decoupler**: when true, ink is crisp but the core renders the *real*
  (warm) mood → teasing. The flag is what lets the two layers diverge.

All three are **derived from soul state already in SQLite** — rendering, not new state.

## Feasibility guardrails (this is what decides whether it ships)

- **Ink = a shader, NOT a fluid simulation.** Domain-warped fbm/curl noise over a signed-
  distance field; "crisp ↔ fluffy" = **one uniform** (the SDF smoothstep width). Light core =
  bloom/glow with colour+pulse uniforms. Paper/silk = static texture multiply. Single-pass,
  phone-friendly (the box = iPhone SE2 GPU).
- **Particles (A) = capped GPU count**, motion via a noise field. No physics.
- **Avoid early:** real fluid sim (Navier–Stokes), rigid-body physics, 3D scene navigation,
  uncapped particle counts. Approximate everything; the eye won't know.

## What the spike must NOT do

Real STT/LLM/TTS, real photos/memory, navigation, perf work, multiple scenes, the echo world.
Throwaway. (Mirrors the existing avatar-state debug panel — buttons fire each state.)

## Deliverable

One self-contained page: a material toggle (A/B) + a button per state above, so the user can
*feel* it and pick the material.

---

## Paired behavior slice — felt-vs-shown split `[Claude spec → Cursor builds → updates PERSONA_AND_BEHAVIOR]`

Required for **desync-2 (teasing) to be TRUE**, not a faked animation. Small change, high return.
**Per CLAUDE.md this touches the behavior contract → update `docs/PERSONA_AND_BEHAVIOR.md` on implement.**

1. **One shared tone projection.** Consolidate tone derivation (today split between the behavior
   engine and `state_block._kernel_speaking_modifier` / `_kernel_emotion_context_text`) into one
   helper that returns `(felt, expressed_edge, is_performative)` + the verbal tone instruction.
   RTC, cascaded voice, text chat, and the material all read this one projection (so every surface
   teases/suppresses identically — one personality).
2. **`performative_sharp` path (new).** Fires only in the positive zone: no worry/annoyance/tension
   **and** `relationship_state.closeness` high (**and** energy ok). (No "happy" field exists — define
   the positive zone from absence-of-negatives + closeness.) When it fires → `expressed_edge` sharp,
   `is_performative = True`, **core stays at real (warm) mood**.
3. **Distinct verbal register for performative.** NOT the real-annoyance instruction. Real anger →
   `更冲、更不耐烦但别凶`; performative → `嘴上损ta、其实在逗、带笑意`. Branches both ink and the
   spoken words / emotion-tag, or teasing won't land.
4. **Precedence:** real worry/annoyance/tension always win; performative is mutually exclusive with
   real-sharp. Suppression (desync-1) already exists today (`worry` beats `annoyance` → soft ink
   over an annoyed core) — keep it, it's honest.
5. **Live trigger (v1):** a short teasing **streak** (persist a few turns) over a per-turn coin-flip,
   so it reads as a mood not a glitch. Spike unaffected (manual buttons).

## Done criteria

- Spike: both materials, all 6 states, the two desyncs legible at a glance, thinking→speak flows
  (no hard cut), runs smooth on a laptop and plausibly on a phone (shader, not sim). User picks a material.
- Behavior slice: `(felt, expressed_edge, is_performative)` exposed from one shared helper; teasing
  fires only in the positive zone with its own playful register; real states unchanged;
  `PERSONA_AND_BEHAVIOR.md` updated; tests for the positive-zone gate + precedence.

## Boundaries

- Spike is throwaway — do not let it accrete product scope.
- No new memory tables / soul state — the material renders existing kernel + memory.
- Do not implement the echo world (ambient drift / memory traces) here — that's the post-spike staging.
