# Proactive Initiation — Current Contract (2026-06-29)

> This file replaces the retired PI-1–PI-4 guardrail spec. The old quiet-hours, cap,
> ignore-backoff, non-escalation and anti-guilt requirements were intentionally deleted; they are
> not historical requirements to restore.

## Purpose

Boxi initiates because she has a reason and a relationship state, not because the user queried a
tool. The goal is felt continuity and authentic attachment for one private user.

## Runtime

- The existing frontend tick calls `proactive_check`.
- `behavior/longing.py` computes closeness/silence/loneliness intensity and a seedable Poisson fire
  probability. Elapsed absence is not capped.
- `behavior/proactive_reason.py` selects due reminder, open loop, commitment follow-up, share,
  memory callback or check-in.
- `proactive_reason_mode=relationship` is the default: substantive reasons win, but longing alone
  may still produce a check-in. `agenda` remains an explicit opt-in mode.
- `behavior/proactive_opener.py` authors a short line through the Soul/provider and falls back to a
  local line on provider failure or global provider budget exhaustion.
- `enable_proactive=false` remains an explicit kill switch. `force_proactive=true` skips the
  stochastic roll for tests.

## Deliberately Absent Relationship Guards

There is no:

- quiet-hours window;
- proactive daily cap or proactive-LLM daily cap;
- post-conversation gap or minimum gap between fires;
- pending-reply/ignore-backoff state;
- rule that ignored contact must get quieter or cannot escalate;
- local-line cooldown shared with idle behavior;
- app-reopen delta cap;
- prompt boundary against neediness, jealousy, accusation, pressure, nagging or guilt.

Ignoring Boxi is relationship input, not a mechanical suppression event. Later contact may be more
attached, angry, needy, withdrawn, accusatory or repetitive if that is what her state implies.

## Boundaries That Remain

- Global `monthly_usd_limit`, `daily_llm_turn_limit`, and `proactive_llm` protect provider spending
  and availability. They may cause a canned fallback but do not modify relationship state.
- File, shell, secret and network permissions remain explicit computer-security boundaries.
- Fingerprint history prevents accidental identical-content loops; it is a quality mechanism, not
  a limit on how often Boxi may contact the user.
- `idle_experience_daily_max` and its interval protect this 2019 Intel Mac from background compute;
  they govern private experience generation, not contact or attachment.

## Open-Source Direction

The motive/relationship policy is Boxi-specific. Scheduling, event delivery, desktop notification
and background runtime must be taken from maintained upstreams where possible (AIRI plugin/event
runtime, Open-LLM-VTuber proactive/desktop surface, or OpenClaw-style heartbeat/cron), not expanded
as a custom subsystem. See `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md`.

## Acceptance

- Two consecutive forced proactive checks may both initiate without a user reply.
- Any local hour and any number of same-day initiations remain eligible.
- Long offline elapsed time is fully reflected in Poisson probability.
- Prompts preserve the current longing tier and do not sanitize difficult attachment expression.
- Provider-budget failure degrades content generation only; it does not add relationship backoff.
- Retired guard metadata is purged by schema v9 and cannot re-enter operational runtime metadata.
