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
  "allow_cloud_tts": false
}
```

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

