# Agent Operating Rules

This repository is for a low-cost AI desktop companion prototype. The product is a small "person trapped in a box": a pixel-style character with personality, memory, chat, later voice, and eventually hardware integration.

## Default Workflow

When the user says `推进`, continue from the project files instead of asking for fresh context.

Start every development session by reading:

1. `docs/PROJECT_BRIEF.md`
2. `docs/SESSION_PROTOCOL.md`
3. `docs/MVP_ROADMAP.md`
4. `docs/TODO.md`
5. `docs/SESSION_LOG.md`
6. `docs/OPEN_SOURCE_REUSE.md`
7. `docs/CURSOR_PHASE_PLAYBOOK.md` when Cursor is expected to own most implementation

Then select the next unfinished task from `docs/TODO.md` or the next milestone in `docs/MVP_ROADMAP.md`. Work on one coherent feature per session unless the user explicitly asks for a broader pass.

## Session Ending Rule

When the user says the session is about to end, update `docs/SESSION_LOG.md` with this exact structure:

```text
本次完成：
下次接着做：
已知问题：
相关文件：
测试结果：
不要改动的边界：
```

Also update `docs/TODO.md` if task status changed.

## Project Boundaries

- Do not start hardware work during the MVP unless the user explicitly asks.
- Do not implement STT/TTS before the text MVP, provider abstraction, memory layer, and behavior engine are usable.
- Do not grant broad local filesystem access. All agent file access must go through explicit allowed folders.
- Do not send full conversation history to the LLM by default. Retrieve relevant memory and include compact summaries.
- Do not let the LLM directly execute file operations or shell commands.
- Do not make the character a generic polite assistant. The default personality is "毒舌被困小人 + low-dose companionship".

## Open Source Reuse

This is a personal-use project, so speed matters more than future distribution readiness. Before building a module from scratch, check whether an existing open-source project or library can be used, studied, adapted, or connected.

Rules:

- Prefer mature open-source libraries over custom implementations when they fit the architecture.
- Prefer permissive licenses such as MIT, Apache-2.0, BSD, or ISC when choices are otherwise similar.
- GPL, AGPL, LGPL, MPL, source-available, or unclear-license projects can be studied for personal use, but record the tradeoff before depending on them or adapting code.
- Repositories with no license should be treated as learn/reference-only unless the user explicitly chooses a personal-use experiment.
- Prefer adding a dependency over copying source code.
- If code is copied or adapted, record the source URL, license, version/commit, and modified files in `docs/OPEN_SOURCE_REUSE.md`.
- Do not let external projects dictate the architecture. Adapt them to the companion's modules: UI, local API, provider adapters, memory engine, behavior engine, and file permission gateway.

## Tool Responsibilities

Codex is the primary implementer and source-of-truth maintainer:

- Owns architecture, backend, provider abstraction, memory system, behavior engine, tests, and documentation updates.
- May implement frontend structure and core UI, but should leave fine animation polish to Cursor when useful.
- Must keep session logs and TODO status current.

Claude Code is for review and second opinions:

- Use it for architecture review, security review, memory quality review, or complex bug investigation.
- Do not let it rewrite large parts of the project unless the user explicitly assigns that module.
- Claude review comments must be converted into concrete TODO items before implementation.

Cursor is for local editing and UI refinement:

- Use it for pixel UI tuning, CSS, component layout, animation timing, and small focused edits.
- Cursor should not change provider abstraction, memory schema, or file permission policy without updating the relevant docs.
- Avoid letting Cursor and Codex edit the same module at the same time.

## Coding Preferences

- Prefer TypeScript for frontend and Python/FastAPI for the local API unless the roadmap changes.
- Use SQLite for local memory.
- Use JSON config files for persona, providers, allowed folders, and budgets.
- Keep code modular: UI, local API, provider adapters, memory engine, behavior engine, and file permission gateway should stay separate.
- Add tests for memory retrieval, provider adapters, behavior decisions, and path permission checks.
