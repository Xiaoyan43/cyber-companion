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

Config should eventually support:

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

