# Claude Code Collaboration Rules

Claude Code is not the primary builder for this project. Use Claude Code mainly as a reviewer, debugger, or architecture critic.

## Read First

Before doing any work, read:

1. `AGENTS.md`
2. `docs/PROJECT_BRIEF.md`
3. `docs/SESSION_PROTOCOL.md`
4. `docs/MVP_ROADMAP.md`
5. `docs/TODO.md`
6. `docs/SESSION_LOG.md`

## Allowed Work

Claude Code may:

- Review architecture decisions.
- Review security boundaries.
- Review memory design and prompt behavior.
- Inspect code for bugs or maintainability problems.
- Suggest focused patches when explicitly requested.

## Restricted Work

Claude Code should not:

- Rewrite broad modules without explicit instruction.
- Change the memory schema without updating `docs/MEMORY_DESIGN.md`.
- Change provider interfaces without updating `docs/ARCHITECTURE.md`.
- Add broad filesystem access.
- Start STT, TTS, or hardware integration before the MVP text stack is stable.

## Review Format

When reviewing, lead with findings:

```text
Findings:
Open questions:
Suggested next actions:
```

Convert accepted review items into `docs/TODO.md` before implementation.

