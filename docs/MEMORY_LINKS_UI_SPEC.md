# Spec — Memory-links read-only API + "Boxi 把这些联系起来了" panel

**Owner: `[Claude]`-class** (adds a read-only memory route) **but DELEGATED to Cursor via
this spec.** Claude spec → Cursor implements + gates → Claude review → checkpoint.
Finishes the soul dashboard: relationship + memory + mood panels exist; this adds the
SD-5/SD-5b cross-links visualization.

This spec **authorizes Cursor** to add ONE read-only GET route in `main.py` + one store
method, and **requires** the `MEMORY_DESIGN.md` doc update below. No other backend change.

## Task 1 — Store: list links (`backend/app/memory/store.py`)

Add `list_memory_links(limit: int = 100) -> list[MemoryLinkRecord]` returning **logical**
links (dedup the bidirectional rows — emit each unordered pair once; e.g. keep rows where
`memory_id < related_memory_id`). Order by `id`. Each record carries enough to render
without extra queries: link id, both memory ids, `relation`, `created_at`, and both
memories' `type` + a short `content` snippet (join `memories`).

- Add a small dataclass `MemoryLinkRecord` in `backend/app/memory/database.py` (mirror the
  existing `*Record` dataclasses) with: `id`, `memory_id`, `related_memory_id`, `relation`,
  `created_at`, `memory_type`, `memory_content`, `related_type`, `related_content`.
- Use one SQL `SELECT ... FROM memory_links ml JOIN memories a ON a.id = ml.memory_id
  JOIN memories b ON b.id = ml.related_memory_id WHERE ml.memory_id < ml.related_memory_id
  ORDER BY ml.id LIMIT ?`. Clip `content` to ~80 chars in Python (don't change stored data).

## Task 2 — API route (`backend/app/main.py` + `backend/app/schemas.py`)

- `schemas.py`: `MemoryLinkSchema` (the 9 fields above) + `MemoryLinkListResponse{ links: list[MemoryLinkSchema] }`.
- `main.py`: `@app.get("/memory/links", response_model=MemoryLinkListResponse)` →
  `def list_memory_links(limit: int = 100)`, calls `get_memory_store().list_memory_links(limit)`,
  maps to schema. **Read-only. No auth, no write, mirrors the existing `/memory/memories`
  GET route exactly in style.**

## Task 3 — Frontend API (`frontend/src/api/memoryLinks.ts`)

`fetchMemoryLinks(limit = 100): Promise<MemoryLink[]>` hitting `GET /memory/links`, same
`apiBaseUrl` + error pattern as `frontend/src/api/memories.ts`. Export a `MemoryLink` type
matching `MemoryLinkSchema`.

## Task 4 — Panel (`frontend/src/components/MemoryLinksPanel.tsx`)

Read-only `<details>` panel titled **"Boxi 把这些联系起来了"**, same pattern/gating as
`MemoryPanel.tsx`/`RelationshipPanel.tsx` (loading / offline / ready states).
- Each link as one row: `(类型) 内容片段  ↔  (类型) 内容片段`. Reuse the Chinese type-label
  map already in `MemoryPanel.tsx` (factor it into a shared `frontend/src/memory/typeLabels.ts`
  if convenient, or duplicate — Cursor's call, keep it DRY if cheap).
- Empty state: 「Boxi 还没把任何事联系起来。」 Offline: same copy as the other panels.
- Wire `<MemoryLinksPanel>` into `App.tsx` right after `<MemoryPanel>`, same `enabled` gating.
- CSS reuse the existing companion-panel styles; add minimal rules only if needed.

## Task 5 — Docs

- `docs/MEMORY_DESIGN.md`: under the `memory_links` / Retrieval section, note the read-only
  `GET /memory/links` route (logical pairs, joined snippets, inspection-only).
- Tick the `Memory links visualization in UI` backlog item in `docs/TODO.md`.

## Tests

- Backend: `test_memory_links.py` (or a route test file) — create two linked memories,
  assert `GET /memory/links` returns **one logical** link (not two), with both snippets and
  types populated. Assert empty DB → `{ "links": [] }`.
- Frontend: `tsc --noEmit` green (no unit test required for the panel).

## Done criteria

1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green.
2. `GET /memory/links` returns deduped logical pairs with joined type+snippet; read-only.
3. Panel renders linked pairs, mirrors existing panels, API-gated.
4. Diff confined to: `memory/store.py`, `memory/database.py`, `main.py`, `schemas.py`,
   `frontend/src/api/memoryLinks.ts`, `frontend/src/components/MemoryLinksPanel.tsx`,
   `App.tsx`, `styles.css` (if needed), `frontend/src/memory/typeLabels.ts` (optional),
   tests, `docs/MEMORY_DESIGN.md`, `docs/TODO.md`.

## Boundaries

- Read-only. No new write path, no schema change (table already exists), no change to the
  SD-5 linker / 1-hop retrieval / any SD contract.
- Don't send full history; don't expose anything beyond linked memory type + short snippet.
