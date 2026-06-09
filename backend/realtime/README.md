# backend/realtime — V2 brain (voice loop)

The **brain** is this package plus the existing Python **soul** in `backend/app/`
(memory, behavior, providers, persona). Phase 1+ adds a Pipecat pipeline here;
Phase 0 only declares the seam.

The **surface** is `frontend/` — V1 CSS avatar today; a PixiJS room replaces it in
Phase 5. Audio I/O and rendering live on the surface.

Brain and surface meet over a **WebSocket** (Phase 1+). The V1 HTTP app in
`backend/app/main.py` stays runnable throughout the rebuild.

See `docs/ARCHITECTURE_V2.md` for the full target architecture.
