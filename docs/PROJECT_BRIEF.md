# Project Brief

## Product

Build a low-cost AI desktop companion that can later become a small physical box. The box contains a low-resolution screen showing a pixel-style character that feels like a small person trapped inside the device.

The software MVP comes first. Hardware integration is out of scope until the software architecture is stable.

## Build Strategy

This is a personal-use project. Development should optimize for speed, practical progress, and fun over future distribution readiness.

The project may use existing GitHub/open-source projects as references, dependencies, or adaptation sources. Do not reinvent mature pieces such as pixel rendering utilities, chat UI patterns, local STT/TTS integrations, provider clients, or SQLite helpers if a suitable open-source option exists.

Open-source reuse should still follow `docs/OPEN_SOURCE_REUSE.md` so we know what was used, copied, or adapted. License checks are mainly for awareness and future cleanup, not for blocking personal experimentation by default.

## MVP Requirements

1. Desktop application prototype, no hardware required.
2. Pixel-style character UI with multiple states:
   - idle
   - happy
   - sad
   - angry
   - sleepy
   - thinking
   - talking
   - worried
   - annoyed
   - silent/muted
3. Configurable LLM chat interface.
4. Provider abstraction:
   - DeepSeek first
   - OpenAI optional
   - local model optional
5. Long-term memory using SQLite and JSON config.
6. Memory types:
   - stable user profile
   - recent events
   - emotion state
   - projects
   - job progress
   - reminders
   - relationship state
   - behavior preferences
7. Do not send full chat history every time. Retrieve relevant memory and use compact conversation summaries.
8. Voice roadmap:
   - stage 1: text input and text output
   - stage 2: push-to-talk STT
   - stage 3: TTS output
   - stage 4: local VAD and always-alive voice loop
9. Agent file access must be restricted to specific local folders, not the whole computer.
10. Interaction should simulate real-world behavior:
   - not always question-answer
   - can stay silent
   - can refuse
   - can interrupt
   - can proactively remind or complain

## Personality

Default personality:

```text
毒舌被困小人 + a small amount of companionship
```

The character can tease, complain, interrupt, and act annoyed. Under the surface, it should still help the user make progress and should not become abusive, manipulative, or genuinely hostile.

## User Memory Permission

The user allows long-term memory to store personal background and job-search details.

Sensitive data should still be handled carefully:

- Store only what is useful.
- Prefer summarized facts over raw private transcripts.
- Keep confidence and importance metadata.
- Allow future deletion/export.
