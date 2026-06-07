# Session Protocol

## New Session

When the user says `推进`, do this:

1. Read `AGENTS.md`.
2. Read `docs/PROJECT_BRIEF.md`.
3. Read `docs/MVP_ROADMAP.md`.
4. Read `docs/TODO.md`.
5. Read the latest entry in `docs/SESSION_LOG.md`.
6. Pick the next unfinished task.
7. State briefly what will be done.
8. Implement only that task unless the user expands scope.
9. Verify with the relevant tests or manual checks.
10. Update `docs/TODO.md` and `docs/SESSION_LOG.md` when ending the session or when the user asks.

## Work Granularity

One session should handle one coherent feature:

Good:

- project scaffold
- pixel character state machine
- provider abstraction
- SQLite memory schema
- memory retrieval and summaries
- behavior engine
- sandbox file permission gateway
- push-to-talk STT prototype

Too small:

- one button
- one CSS value
- one prompt sentence

Too large:

- full MVP in one session
- UI plus memory plus voice plus hardware

## End Session Template

Append this to `docs/SESSION_LOG.md`:

```text
## YYYY-MM-DD - Session N

本次完成：

下次接着做：

已知问题：

相关文件：

测试结果：

不要改动的边界：
```

## Cross-Tool Rule

Do not let Codex, Claude Code, and Cursor edit the same module at the same time.

If a tool hands off work, it must update `docs/SESSION_LOG.md` or leave a clear note in `docs/TODO.md`.

