# Cost And Token Budget

## Goal

Keep the companion cheap enough for frequent daily use.

The design should avoid sending full chat history and should avoid unnecessary cloud STT/TTS usage.

## Default Policy

- Use DeepSeek as the default low-cost provider.
- Use short context construction:
  - relevant memories
  - current mood
  - recent summary
  - last few raw messages
- Use local rules for idle animation, mood ticks, silence, and proactive timing.
- Call LLM only when natural language understanding or generation is needed.
- Use stronger/reasoning models only for complex planning or debugging.

## Approximate Per-Turn Budget

Target per LLM turn:

```text
input: 2,500-4,000 tokens
output: 150-300 tokens
```

This requires memory retrieval and summaries. Full-history prompting is not acceptable as the default.

## Budget Controls

`config/budget.json` (falling back to `budget.example.json`) supports:

```json
{
  "monthly_usd_limit": 10,
  "daily_llm_turn_limit": 200,
  "max_input_tokens_per_turn": 4000,
  "max_output_tokens_per_turn": 300,
  "allow_reasoning_model": false,
  "allow_cloud_stt": false,
  "allow_cloud_tts": false,
  "enable_proactive": true,
  "proactive_quiet_hours": [23, 8],
  "proactive_min_gap_minutes": 30,
  "proactive_min_fire_gap_hours": 6,
  "proactive_daily_max": 2,
  "longing_silence_hours_scale": 48,
  "longing_closeness_weight": 0.55,
  "longing_loneliness_weight": 0.45,
  "longing_lambda_base_per_hour": 0.004,
  "longing_lambda_longing_gain": 2.5
}
```

### Proactive initiation (PI-1)

Local `proactive_check` timing uses the longing model in `behavior/longing.py`
(no LLM). Knobs above default to a quiet companion: low base Poisson rate,
2 proactive lines/day max, 30-minute post-conversation cooldown, no outreach
during quiet hours. Set `enable_proactive` to `false` to disable entirely.

### Proactive opener (PI-2 + PI-4)

When longing fires, `proactive_llm` (default on) lets the route author one short
line via the provider (`proactive_max_output_tokens`, default 80).
`proactive_llm_daily_max` rate-limits LLM openers per UTC day. Off, over cap,
or over the shared spend brake → canned fallback from `proactive_reason.fallback_line_for_reason`
(cost 0).

**PI-4 respect + cost brake:**

- `proactive_pending_since` — after a proactive fire, no second initiation until
  the user speaks (`awaiting_user_reply` gate). Ignored outreach stays quiet.
- `proactive_min_fire_gap_hours` (default 6) — minimum hours between real fires
  (`last_proactive_fired_at`), separate from the 30-minute post-conversation gap.
- Proactive LLM calls run through `evaluate_llm_budget_gate` (same
  `monthly_usd_limit` / `daily_llm_turn_limit` / reasoning-model rules as chat).
  Successful proactive LLM turns persist real `usage`/`cost` on the behavior_tick
  line with `should_call_llm=true`, so they count toward the same caps.

### Enforcement (implemented)

Before every would-be LLM turn, `/chat/complete` runs a spend brake
(`backend/app/memory/usage_guard.py`) that blocks the provider call when:

- `daily_llm_turn_limit` — assistant turns with `should_call_llm=true` since
  UTC midnight reach the cap.
- `monthly_usd_limit` — summed `cost.total_usd` of assistant turns since the
  first of the UTC month reaches the cap.
- `allow_reasoning_model` is `false` and the target model looks like a reasoning
  model (e.g. `deepseek-reasoner`, `o1-*`).

A blocked turn never reaches a provider: Boxi answers with a short in-character
"budget exhausted" line, the turn is persisted with `should_call_llm=false` and
zero cost, so it neither counts toward the daily cap nor adds to monthly spend.
Set any limit to `0` (or `allow_reasoning_model=true`) to disable that brake.

`max_input_tokens_per_turn` / `max_output_tokens_per_turn` are applied during
context building and output capping; counts use the
`estimate_token_count` heuristic, so treat USD figures as estimates and verify
against official provider pricing.

`max_user_input_tokens` (default 1500) hard-truncates the current user turn
before it is appended to the provider context (behavior evaluation and SQLite
persistence still use the full original text).

## Voice Cost Policy

Stage 1 uses text only.

Stage 2 push-to-talk STT should send audio only when the user intentionally presses the voice key.

Stage 3 TTS should be selective:

- important replies
- reminders
- short expressive lines

Do not synthesize every long answer by default.

Stage 4 always-alive voice loop should still use local VAD/wake detection first. Do not stream continuous microphone audio to cloud services.

## Provider Notes

Provider prices change. Always verify official pricing before making hard monthly cost claims.

