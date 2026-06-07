# Cursor Phase Playbook

## Purpose

Cursor can own most day-to-day implementation for this project. This file tells Cursor what to do in each phase, what not to touch, and how to verify the work.

Default rule:

```text
one Cursor chat = one phase slice = one verifiable outcome
```

Before editing, Cursor should read:

- `AGENTS.md`
- `.cursor/rules/cyber-companion.mdc`
- `docs/PROJECT_BRIEF.md`
- `docs/ARCHITECTURE.md`
- `docs/MVP_ROADMAP.md`
- `docs/TODO.md`
- `docs/SESSION_LOG.md`
- `docs/HANDOFF.md`
- `docs/OPEN_SOURCE_REUSE.md`

## Every Cursor Session

Do:

- Inspect current git status first.
- Respect existing uncommitted user/Codex changes.
- Work on one bounded task.
- Prefer small, reviewable edits.
- Run checks before ending.
- Update `docs/TODO.md` and `docs/SESSION_LOG.md`.

Do not:

- Rewrite the whole app in a new stack.
- Start hardware work before the software MVP is stable.
- Start voice before the text MVP is coherent.
- Add broad filesystem access.
- Send full chat history to LLM by default.
- Turn Boxi into a generic polite assistant.

## Phase 0 - Foundation

Status: done.

Cursor should not redo this phase unless asked.

Owned artifacts:

- `.cursor/rules/cyber-companion.mdc`
- documentation awareness
- UI-specific rules

Verification:

- Rules reference the project docs and this playbook.

## Phase 1 - Project Scaffold

Status: done.

Cursor should not redo this phase unless fixing a scaffold bug.

Owned artifacts:

- frontend shell
- basic local API status display
- small frontend wiring fixes

Do not:

- Replace React/Vite/FastAPI without explicit approval.

Verification:

```text
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

## Phase 2 - Pixel Character UI

Cursor can own most of this phase.

Goal:

- Make the first screen feel like a trapped pixel companion, not a demo page.

Do:

- Build or refine the pixel character renderer.
- Add state-specific visuals for idle, happy, sad, angry, sleepy, thinking, talking, worried, annoyed, and silent.
- Add stable state transition controls for development.
- Add restrained idle animation.
- Keep the chat panel usable.
- Make layout work at desktop and narrow mobile widths.

Open-source reuse:

- It is fine to study pixel avatar/sprite animation examples.
- Prefer CSS/canvas/PixiJS patterns that fit the existing app.
- Record copied/adapted sources in `docs/OPEN_SOURCE_REUSE.md`.

Do not:

- Add LLM calls.
- Add memory implementation.
- Add voice.
- Replace the app shell.

Acceptance:

- Character state changes are visible.
- Text does not overflow controls at 390px width.
- No horizontal overflow on mobile.
- API status still appears.
- Chat shell still accepts typed input.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

## Phase 3 - Provider Abstraction

Cursor may implement the first version, but should stay close to the architecture docs.

Goal:

- Add a provider interface and DeepSeek-first adapter without coupling UI directly to providers.

Do:

- Define backend provider interface.
- Add DeepSeek adapter.
- Add OpenAI and local model placeholders.
- Load provider settings from config/env.
- Return structured provider metadata and estimated token usage where possible.
- Keep secrets out of git.

Open-source reuse:

- Prefer official clients or small HTTP wrappers.
- Record dependencies in `docs/OPEN_SOURCE_REUSE.md`.

Do not:

- Put API keys in source.
- Call providers directly from the frontend.
- Add memory retrieval in this phase unless explicitly assigned.
- Add voice.

Acceptance:

- Backend has a provider route or service that can be tested without real keys through mock/dummy provider mode.
- DeepSeek config exists but secrets are env-only.
- Provider errors return clear local API errors.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
```

## Phase 4 - SQLite Memory

Cursor can implement CRUD and schema, but schema changes must match `docs/MEMORY_DESIGN.md`.

Goal:

- Add local long-term memory storage.

Do:

- Create SQLite initialization.
- Add tables for messages, summaries, memories, mood state, reminders, and file access logs.
- Add CRUD helpers.
- Add tests for schema creation and basic writes/reads.
- Keep database files out of git.

Do not:

- Store raw API keys or secrets.
- Build complex retrieval/ranking yet.
- Send memory to providers yet.

Acceptance:

- SQLite database can initialize locally.
- Tests can create an isolated temporary DB.
- Memory types match the docs.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
```

## Phase 5 - Memory Retrieval And Summaries

Cursor can own the initial implementation, but Codex should review after the phase.

Goal:

- Stop full-history prompting.

Do:

- Build compact context assembly.
- Retrieve relevant memories by type/tags/recency/importance.
- Include recent summary and only a few raw turns.
- Add a summary storage/update path.
- Add tests proving full transcript is not sent by default.

Do not:

- Over-optimize embeddings before the simple retrieval path works.
- Add cloud vector DBs.
- Ignore token budget limits.

Acceptance:

- Context builder has deterministic tests.
- It respects max token/character budget.
- It can include job progress and project memory when relevant.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
```

## Phase 6 - Behavior Engine

Cursor can implement the first pass. Codex should review because this module defines product feel.

Goal:

- Make Boxi behave less like a one-question-one-answer chatbot.

Do:

- Define behavior decision contract.
- Implement reply, silent, mutter, refuse, interrupt, proactive, and observe decisions.
- Add mood/energy/annoyance/boredom/worry/trust state transitions.
- Keep behavior local where possible.
- Add tests for common behavior decisions.

Do not:

- Put all behavior into one prompt.
- Make every event call the LLM.
- Make the character abusive or manipulative.

Acceptance:

- Empty/low-value input can trigger annoyed/silent behavior.
- Long user rambling can trigger interrupt.
- Stale project/job events can trigger proactive lines.
- Low mood reduces sarcasm.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
```

## Phase 7 - File Permission Gateway

Cursor can implement tests and basic gateway. Codex should review security.

Goal:

- Restrict local file access to explicit allowed folders only.

Do:

- Load allowed folder config.
- Resolve real absolute paths.
- Reject traversal and symlink escape.
- Log allowed and denied attempts.
- Add tests for allowed path, traversal, and symlink escape.

Do not:

- Give broad home/Desktop/Documents/Downloads access.
- Add shell execution from the companion.
- Let provider calls read local files directly.

Acceptance:

- Denied paths get clear reasons.
- Tests cover path escape behavior.
- File access log table/service works.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
```

## Phase 8 - Text MVP Integration

Cursor can do integration wiring. Codex should review after.

Goal:

- Make text chat, provider, behavior, avatar state, and memory work together.

Do:

- Connect frontend chat to backend dialogue endpoint.
- Persist messages.
- Retrieve compact memory context.
- Call provider through backend only.
- Parse structured assistant response.
- Update avatar state from behavior/provider output.
- Add basic cost metadata display or log.

Do not:

- Add voice yet.
- Send full chat history.
- Let frontend own provider secrets.

Acceptance:

- User can chat through the local API.
- Avatar state changes based on response.
- Messages persist locally.
- Context builder uses summary + relevant memories.
- App works without provider key in a mock/local fallback mode.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

## Phase 9 - Push-To-Talk STT

Cursor should only start this after text MVP integration is stable.

Goal:

- Add intentional voice input, not always-cloud listening.

Do:

- Add push-to-talk UI.
- Add local audio capture flow.
- Add STT adapter interface.
- Add cloud STT only behind config.
- Keep clear recording indicators.

Do not:

- Stream continuous microphone audio to cloud.
- Hide recording state from the UI.
- Add TTS in the same phase unless explicitly assigned.

Acceptance:

- Voice recording is user-initiated.
- STT can be disabled by config.
- Text result flows into the normal chat path.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

## Phase 10 - TTS Output

Cursor can implement a selective first pass.

Goal:

- Let Boxi speak short selected lines.

Do:

- Add TTS adapter interface.
- Add selective speech policy.
- Sync speaking audio with avatar talking state.
- Allow mute/disable.

Do not:

- Speak every long message by default.
- Make cloud TTS mandatory.

Acceptance:

- TTS can be toggled off.
- Only selected short messages are spoken by default.
- Avatar enters talking state while speaking.

Checks:

```text
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

## Phase 11 - Hardware Preparation

Cursor should not start this without explicit user approval.

Goal:

- Prepare software constraints for a future physical box.

Do:

- Document display resolution assumptions.
- Define hardware API boundary.
- Identify microphone/speaker/button needs.
- Keep software usable on desktop.

Do not:

- Buy/install hardware dependencies.
- Lock the app to one board prematurely.

Acceptance:

- Hardware assumptions are documented.
- Desktop MVP still works.

## Suggested Cursor Start Prompt

```text
请先阅读 AGENTS.md、.cursor/rules/cyber-companion.mdc、docs/CURSOR_PHASE_PLAYBOOK.md、docs/TODO.md、docs/SESSION_LOG.md、docs/OPEN_SOURCE_REUSE.md。

本次只推进：[填写一个阶段或一个阶段切片]。
不要做 provider/memory/voice/hardware，除非本阶段明确要求。
先检查 git status，尊重已有未提交改动。
优先评估可复用开源方案，但不要大改架构。
完成后运行相关 checks，并更新 docs/TODO.md、docs/SESSION_LOG.md、docs/OPEN_SOURCE_REUSE.md。
```
