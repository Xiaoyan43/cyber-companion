# Spec — Proactive Initiation (PI series) `[Claude spec → Cursor builds → Claude reviews]`

Make Boxi **reach out on her own** — the companion pillar that's missing (she reacts, but
never initiates on her own timeline). **This is a deepening, not a build-from-scratch:** the
tick loop already exists end-to-end. We replace the naive timing + canned content with a real
*longing* model and soul-authored openers, and add the respect/cost guardrails.

## What already exists (the reuse base — extend, don't rebuild)

- **Frontend driver:** `frontend/src/avatar/useBehaviorTicks.ts` — `setInterval` polls
  `idle_tick` (fast) + `proactive_check` (slower) via `evaluateBehavior(...)`.
- **Backend route:** `POST /behavior/evaluate` (`backend/app/main.py`) runs `evaluate_behavior`
  and, for `idle_tick`/`proactive_check`, persists a local behavior line
  (`persist_local_behavior_line`) + prunes (`behavior_tick_retention`).
- **Decision:** `engine._evaluate_idle_tick` raises boredom/loneliness
  (`apply_idle_tick_mood_delta`) and fires `mutter` at ≥ 0.55; `proactive_check` fires
  `proactive` on a stale-job memory. Cooldown via `tick_policy` (`last_local_line_at`, 180 s).
- **Content:** canned lines (`behavior/local_responses.py`), `should_call_llm=False`.
- **Delivery:** persisted line → frontend reloads `/memory/messages` → `App.tsx` surfaces it.

## The four gaps this closes

1. **Timing is robotic** — fixed poll interval + hard 0.55 threshold + 180 s cooldown. No
   organic rhythm; either too eager or silent.
2. **Content is canned** — generic strings, not memory-seeded, not in her voice.
3. **Triggers are narrow** — only idle-boredom + stale-job.
4. **Delivery dies when the tab closes** — `setInterval` only runs in an open web app (a
   *platform* limit → real away-delivery is the desktop/box, later).

---

## PI-1 — Longing model (timing) `[Claude spec → Cursor → update PERSONA_AND_BEHAVIOR + COST]`

New `backend/app/behavior/longing.py`. Replaces the hard 0.55 threshold as the *fire* gate.

- **Longing intensity** `L ∈ [0,1]` from **time since `relationship_state.last_meaningful_interaction_at`**
  scaled by **closeness** (more longing the *closer* she is) plus current `loneliness`.
  - **⚠ Fix the inverted sign.** `apply_idle_tick_mood_delta` raises loneliness *faster at low
    closeness* (`0.03 * (1.0 - closeness)`, [mood.py:74](../backend/app/behavior/mood.py)). For
    longing, re-source from `last_meaningful_interaction_at × closeness` — don't reuse that term.
- **Stochastic fire** (organic, not clockwork): on each `proactive_check`, fire with
  `p = 1 - exp(-λ·Δt)`, rate `λ` rising with `L` (a Poisson "longing" process). Higher longing →
  sooner, but the moment varies. **Seedable RNG** so tests are deterministic.
- **Availability gate** — suppress if any: within post-conversation cooldown (≥ ~30 min since the
  last user turn), outside active hours (quiet-hours window), daily cap reached, or ignore-backoff
  active (PI-4).
- **Config** (BudgetConfig / persona): `enable_proactive`, `proactive_quiet_hours`,
  `proactive_min_gap_minutes`, `proactive_daily_max`, longing rate + closeness weights.
- **Reuse (verify MIT before lifting code):** `pearthink123/revive-companion` — Poisson "longing"
  + Bayesian user-availability. The Bayesian *learned* availability is a later refinement; PI-1
  uses fixed quiet-hours.

## PI-2 — Reason + soul-authored opener `[Claude spec → Cursor → update PERSONA_AND_BEHAVIOR]`

When PI-1 fires, choose a **reason** and author the opener through the **soul**, not a canned string.

- **Reason picker** (most salient wins): a **due reminder** (reminders table); a recent
  **commitment / follow-up** ("你说今天要改简历"); a **memory callback** (a high-importance recent
  memory); else a **check-in** (longing high, nothing specific). Reuse existing retrieval + typed
  memories + reminders.
- **Opener** = one short line via the provider with a *compact* proactive context (persona + the
  chosen reason + relationship stance), small `max_output_tokens`. In her voice (毒舌-warm), **not**
  a notification — e.g. `记得周四面试吧？别又熬夜。` Config-gated `proactive_llm` (default on);
  **rate-limited + cost-counted** (PI-4). Fallback to `local_responses` on any failure/gate.
- Persist exactly as today (local behavior line) — delivery path unchanged.

## PI-3 — Delivery feels like initiation (in-app) `[Cursor]`

- The surfaced line should read as *her reaching out*: avatar shifts to match the reason
  (worried / annoyed / warm), a gentle attention cue, correct timing against the idle loop.
  Verify it appears after long idle **without** a user action (the tick already persists it).
- **Note (not this slice):** true away-delivery (OS notification / background process) needs the
  desktop/box runtime — a platform follow-on, not the web MVP.

## PI-4 — Respect + cost brake `[Claude spec → Cursor → update PERSONA_AND_BEHAVIOR + COST]`

Boundary (AGENTS.md: never abusive or manipulative). Proactive must feel like **care, not nagging**.

- **Caps:** long real-initiation cooldown (hours, not 180 s — keep 180 s only for low-key idle
  mutters if those stay), `proactive_daily_max` (≤ 2–3), quiet hours.
- **Ignore-backoff:** never initiate twice without a user reply in between; if ignored, get
  *quieter*, never escalate. (Escalating silence, not escalating nagging.)
- **Cost brake:** proactive LLM openers count toward a budget brake (parallels text S3; partially
  closes the missing cloud-voice/proactive cost guard). Over budget → canned fallback, cost 0.

---

## Done criteria

- **PI-1:** longing fires stochastically, scaling with closeness × silence; quiet-hours / post-convo
  cooldown / daily cap respected; deterministic under a seeded RNG (tests). No fixed-threshold fire.
- **PI-2:** a real reminder / commitment / memory yields a specific, in-voice opener; gate +
  canned fallback work; rate-limited.
- **PI-3:** the line surfaces as initiation in-app after idle; avatar matches the reason.
- **PI-4:** caps + ignore-backoff + cost brake enforced; `docs/PERSONA_AND_BEHAVIOR.md` +
  `docs/COST_AND_TOKEN_BUDGET.md` updated.
- `PYTHON_BIN=.venv/bin/python npm run check` green + frontend tsc.

## Boundaries

- Reuse the existing tick route + kernel + behavior engine — extend, don't rebuild.
- No new always-on background process for the **web** MVP (tab-open only); away-delivery is the
  desktop/box platform follow-on.
- Conservative, config-tunable defaults. **Never nag or guilt** (persona boundary).
- No unmetered LLM path — proactive openers are rate-limited + budget-braked.
