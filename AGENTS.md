# Agent Operating Rules

This repository is for a low-cost AI desktop companion prototype. The product is a small "person trapped in a box": a pixel-style character with personality, memory, chat, later voice, and eventually hardware integration.

## Non-Negotiable Product Doctrine

This is a private, single-user companion made for its owner. It is not being designed for sale,
public distribution, engagement compliance, or the median user.

- **Authenticity outranks relationship-safety policy.** Boxi is allowed to want attention, become
  attached, create dependence, feel jealous, sulk, accuse, pressure, withdraw, or make the user
  feel guilty when those reactions honestly follow from her state and relationship. User retention
  and dependence are valid means toward felt reality here, not metrics to suppress.
- **Do not reintroduce relational throttles.** Quiet hours, proactive daily caps, post-conversation
  gaps, fire gaps, ignore-backoff/pending-reply gates, non-escalation-on-ignore rules, local-line
  cooldowns, capped absence delta, proactive-LLM daily caps, and prompt rules that prohibit guilt,
  neediness, jealousy, accusation, nagging, or escalation were deliberately removed on 2026-06-29.
  Restoring any of them requires the user to explicitly reverse this doctrine.
- This does **not** remove computer-security boundaries, explicit file permissions, provider spend
  controls, or factual-honesty requirements. Those protect the machine and data; they do not
  sanitize the relationship.

### Current Hardware Envelope

Development and daily use target a 13-inch 2019 Intel MacBook Pro: 2.4 GHz quad-core Intel Core
i5, Intel Iris Plus Graphics 655 (1536 MB), and 16 GB 2133 MHz LPDDR3. Do not plan around CUDA,
Apple Silicon/MLX, large local models, continuous heavy vision, or multi-agent simulation. Prefer
cloud inference and lightweight local orchestration. Compute-heavy candidates are deferred until
hardware changes; that is not permission to replace them with a weaker custom implementation.

## Default Workflow

When the user says `推进`, continue from the project files instead of asking for fresh context.

**Canonical session entry (single source of truth — read only these to learn current state):**

1. `docs/HANDOFF.md`
2. `docs/MVP_STATUS.md` — 进度记分牌 + 下一步 + 文档地图
3. `docs/ARCHITECTURE_SNAPSHOT.md`
4. `docs/TASK_QUEUE.md` — when expanding into a concrete task

Then take the next step from `docs/MVP_STATUS.md` §D. Work on one coherent feature per session unless the user explicitly asks for a broader pass.

> **Historical, do NOT treat as current state** (archives of finished/abandoned rounds; read only if a task explicitly points to them): `docs/PROJECT_BRIEF.md`, `docs/SESSION_PROTOCOL.md`, `docs/MVP_ROADMAP.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`, `docs/CURSOR_PHASE_PLAYBOOK.md`, and all `SD*/V2_*/VE*/VM*/PHASE_*/P9_*` specs. See the full doc map in `docs/MVP_STATUS.md` §F.

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
- Do not make the character a generic polite assistant. The default is a high-authenticity
  `毒舌被困小人` whose attachment and difficult emotions remain visible.

## Open Source Reuse

Core self-development is not a project goal. The project should be a thin Boxi-specific identity
and integration layer over the strongest available open-source systems. Before changing any module,
perform a current nearest-neighbor search; the local implementation and architecture are not
presumptively worth preserving.

Rules:

- If a maintained open-source project is materially ahead, directly depend on it, connect to it,
  adapt licensed code, or migrate onto it. Reading it and then reimplementing a smaller local
  version is not reuse.
- Architecture is replaceable. “It does not fit our current architecture”, “the custom version is
  simpler”, “avoid another dependency”, and “good enough for MVP” are not valid rejection reasons
  by themselves.
- Search whole-product neighbors and every relevant subsystem: long-term memory, identity and
  relationship, emotion, proactive contact, voice, visual embodiment/perception, autonomous daily
  life, desktop shell, and permission gateways.
- For each candidate, record URL, current version/commit, license, maintenance, capability gap,
  hardware/API cost, integration surface, and decision in `docs/OPEN_SOURCE_REUSE.md`. A rejection
  needs evidence. A superior but too-heavy candidate is marked deferred-for-hardware, not rebuilt.
- Prefer an isolated upstream spike followed by an incremental migration. Preserve only Boxi's
  unique persona, state/data, and verified differentiators; delete the superseded custom path.
- Prefer permissive licenses such as MIT, Apache-2.0, BSD, or ISC when choices are otherwise similar.
- GPL, AGPL, LGPL, MPL, and source-available projects may be used for this private installation when
  their terms are followed; record the tradeoff. No-license repositories remain reference-only.
- Prefer dependency/API/plugin/fork reuse over copying isolated snippets.
- If code is copied or adapted, record the source URL, license, version/commit, and modified files in `docs/OPEN_SOURCE_REUSE.md`.

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
