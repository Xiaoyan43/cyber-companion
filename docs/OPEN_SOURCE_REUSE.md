# Open Source Reuse Policy

## Intent

This project is for the user to play with and improve personal efficiency. It is assumed to be private personal-use unless the user says otherwise. We should move fast by learning from, connecting, and adapting existing open-source projects where practical.

The default is:

```text
reuse or adapt proven open-source pieces first, build from scratch only when needed
```

## What To Look For

Useful open-source categories:

- Pixel character renderers and sprite animation patterns.
- Desktop/web chat UI shells.
- Local memory or note-like SQLite patterns.
- LLM provider adapters.
- Prompt and structured-output patterns.
- Push-to-talk STT examples.
- Local TTS examples.
- Local VAD examples.
- Tauri desktop packaging examples.
- Safe file sandbox/path allowlist examples.

## License Rules

For this project, license checks are mostly for awareness, source tracking, and future cleanup. They should not block personal experimentation unless they create a practical risk or force a large architecture change.

Preferred when choices are otherwise similar:

- MIT
- Apache-2.0
- BSD
- ISC

Can be studied for ideas and may be acceptable for private personal experiments, but record the tradeoff before depending on them or adapting code:

- GPL
- AGPL
- LGPL
- MPL
- source-available but not open-source licenses
- unclear custom licenses

Treat as learn/reference-only by default:

- repositories with no license
- random snippets without clear usage rights
- projects whose license cannot be identified

If the project ever changes direction toward public GitHub release, commercial hardware, or distribution to others, do a fresh license audit before publishing. That is not the current goal.

## Reuse Levels

### Level 1 - Learn Only

Read the idea or architecture, then implement independently.

Record only if it materially influenced the design.

### Level 2 - Dependency

Install and use a package through normal package management.

Record:

- package name
- license
- purpose
- version if important

### Level 3 - Adapted Code

Copy and modify code for personal-use experiments.

Prefer licensed sources and keep copied code small. If adapting from restrictive or unclear sources, record the risk and keep it easy to replace.

Record:

- source repository URL
- license
- commit/tag/version
- copied files or adapted logic
- local files affected
- changes made

### Level 4 - Fork/Base Project

Use an existing project as the base.

This needs explicit user approval because it can dictate the architecture and make future replacement harder.

## Evaluation Checklist

Before using an open-source candidate, check:

- Does it solve a real MVP task?
- What is the license or reuse risk?
- Is it maintained enough for our use?
- Can it fit the architecture without bending the project around it?
- Is the dependency size acceptable?
- Does it introduce security or privacy risk?
- Can we replace it later if needed?

## Candidate Log

Add candidates here as they are evaluated.

```text
Name: PixiJS
URL: https://pixijs.com/
License: MIT
Reuse level: Level 1 - Learn Only
Purpose: Canvas/WebGL sprite animation for pixel characters.
Decision: Rejected for MVP.
Notes: Powerful but would push the UI toward canvas rendering and a heavier runtime. Current CSS/DOM pixel art fits the trapped-in-box MVP and keeps bundle size small.

Name: react-spring
URL: https://www.react-spring.dev/
License: MIT
Reuse level: Level 2 - Dependency candidate
Purpose: State-driven motion for avatar transitions.
Decision: Rejected for MVP.
Notes: CSS `steps()` keyframes are enough for low-res pixel motion. Avoid adding animation runtime before behavior engine drives states.

Name: CSS pixel-art tutorials / sprite-state patterns
URL: n/a
License: n/a
Reuse level: Level 1 - Learn Only
Purpose: Separate base renderer layout from per-state animation rules.
Decision: Adopted as design pattern only.
Notes: Implemented as `PixelCharacter` + `stateAnimations.css` without copying external source.

Name: react-use / custom timer hooks
URL: https://github.com/streamich/react-use
License: Unlicense
Reuse level: Level 2 - Dependency candidate
Purpose: Timeout/state sequence helpers for avatar chat timing.
Decision: Rejected for MVP.
Notes: Small local `useAvatarState` hook with `setTimeout` cleanup is enough and avoids another dependency.

Name: OpenAI Python SDK / DeepSeek official SDK
URL: https://github.com/openai/openai-python
License: Apache-2.0
Reuse level: Level 2 - Dependency candidate
Purpose: Provider HTTP clients for chat completions.
Decision: Rejected for MVP first pass.
Notes: DeepSeek uses OpenAI-compatible HTTP; a small `httpx` adapter keeps dependencies minimal and makes mock testing easy.

Name: SQLAlchemy
URL: https://www.sqlalchemy.org/
License: MIT
Reuse level: Level 2 - Dependency candidate
Purpose: SQLite ORM and migrations for memory storage.
Decision: Rejected for MVP first pass.
Notes: Python stdlib `sqlite3` matches the current schema size and keeps the memory layer easy to inspect and replace.

Name: Chroma / vector DB retrieval
URL: https://www.trychroma.com/
License: Apache-2.0
Reuse level: Level 2 - Dependency candidate
Purpose: Semantic memory retrieval for long-term context selection.
Decision: Rejected for MVP first pass.
Notes: Phase 5 uses deterministic keyword/type/importance scoring first, per playbook guidance to avoid embeddings before simple retrieval works.

Name: python-sandbox-path / path-validation libraries
URL: n/a (category search)
License: varies
Reuse level: Level 2 - Dependency candidate
Purpose: Safe path allowlist checks with symlink escape protection.
Decision: Rejected for MVP first pass.
Notes: Python stdlib `pathlib` + `os.path.realpath` with lexical pre-check is enough for Phase 7 and keeps the gateway easy to audit/replace.

Name: OpenAI Whisper API / cloud STT SDK
URL: https://platform.openai.com/docs/guides/speech-to-text
License: n/a (service/API)
Reuse level: Level 2 - Dependency candidate
Purpose: Cloud speech-to-text for push-to-talk input.
Decision: Deferred placeholder only.
Notes: Phase 9 adds mock/local-first STT routing and config gates (`allow_cloud_stt`, `config/stt.json`). Cloud Whisper adapter remains a placeholder until explicitly wired.
```

## Accepted Dependencies And Adapted Sources

Record accepted items here once used.

```text
Name:
URL:
License:
Version/commit:
Used for:
Local files:
Notes:
```

```text
Name: React
URL: https://react.dev/
License: MIT
Version/commit: ^18.3.1
Used for: Frontend UI shell.
Local files: frontend/package.json, frontend/src/App.tsx, frontend/src/main.tsx
Notes: Dependency only. No source copied.

Name: Vite
URL: https://vite.dev/
License: MIT
Version/commit: ^6.4.3
Used for: Frontend dev server and build tooling.
Local files: frontend/package.json, frontend/vite.config.ts
Notes: Dependency only. No source copied. Upgraded from 5.4.x in Session 23 to clear npm audit advisories (GHSA-4w7w-66w2-5vf9 path traversal, GHSA-67mh-4wv8-2f99 esbuild dev-server). Dev server remains localhost-only per docs/SECURITY_AND_PERMISSIONS.md.

Name: TypeScript
URL: https://www.typescriptlang.org/
License: Apache-2.0
Version/commit: ^5.6.0
Used for: Frontend type checking.
Local files: frontend/package.json, frontend/tsconfig.json
Notes: Dependency only. No source copied.

Name: FastAPI
URL: https://fastapi.tiangolo.com/
License: MIT
Version/commit: >=0.115.0
Used for: Local API shell and health endpoint.
Local files: backend/requirements.txt, backend/app/main.py
Notes: Dependency only. No source copied.

Name: Uvicorn
URL: https://www.uvicorn.org/
License: BSD-3-Clause
Version/commit: >=0.30.0
Used for: Local API development server.
Local files: backend/requirements.txt, scripts/dev_backend.sh
Notes: Dependency only. No source copied.

Name: pytest
URL: https://docs.pytest.org/
License: MIT
Version/commit: >=8.0.0
Used for: Backend health endpoint tests.
Local files: backend/requirements-dev.txt, backend/tests/test_health.py
Notes: Dependency only. No source copied.

Name: HTTPX
URL: https://www.python-httpx.org/
License: BSD-3-Clause
Version/commit: >=0.27.0
Used for: DeepSeek provider adapter HTTP client.
Local files: backend/requirements.txt, backend/app/providers/deepseek.py
Notes: Dependency only. No source copied. Production provider calls only; tests use httpx2 via Starlette TestClient.

Name: httpx2
URL: https://github.com/pydantic/httpx2
License: BSD-3-Clause
Version/commit: >=2.0.0
Used for: Starlette/FastAPI TestClient in backend pytest suite (Starlette 1.2+ prefers httpx2 over httpx).
Local files: backend/requirements-dev.txt
Notes: Dev/test dependency only. No source copied. Keeps pytest output free of TestClient deprecation warnings without changing production httpx usage.

Name: python-multipart
URL: https://github.com/Kludex/python-multipart
License: Apache-2.0
Version/commit: >=0.0.9
Used for: FastAPI `/stt/transcribe` audio upload handling.
Local files: backend/requirements.txt, backend/app/main.py
Notes: Dependency only. No source copied.

Name: Web Audio API (browser built-in)
URL: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API
License: N/A (browser platform API)
Used for: Playing mock/base64 TTS audio returned by `/tts/synthesize`.
Local files: frontend/src/voice/useTextToSpeech.ts
Notes: No dependency added. Mock backend TTS generates silent WAV locally in Python for duration sync.

Name: Python struct (stdlib)
URL: https://docs.python.org/3/library/struct.html
License: PSF
Used for: Generating minimal silent WAV bytes in mock TTS provider.
Local files: backend/app/tts/wav_utils.py
Notes: Stdlib only. No source copied.

Name: macOS `say` (system API)
URL: https://ss64.com/osx/say.html
License: N/A (macOS built-in)
Used for: Local offline TTS via `MacSayTTSProvider` (`backend/app/tts/mac_say.py`).
Local files: backend/app/tts/mac_say.py, config/tts.json, config/tts.example.json
Notes: No dependency added. Invoked with `subprocess.run([...], shell=False)`; text passed as a single argv element. Default zh voice `Tingting` configurable in `tts.json`. Unavailable on non-macOS hosts — raises `TTSError`; `CYBER_COMPANION_TTS_MODE=mock` still forces mock.

Name: faster-whisper
URL: https://github.com/SYSTRAN/faster-whisper
License: MIT
Version/commit: >=1.1.0
Used for: Local offline STT via `FasterWhisperProvider` (`backend/app/stt/faster_whisper.py`). CPU int8, lazy module-level model cache.
Local files: backend/app/stt/faster_whisper.py, backend/requirements.txt, config/stt.json, config/stt.example.json
Notes: Dependency only. No source copied. Whisper `base` model downloads on first transcribe (~142 MB). `CYBER_COMPANION_STT_MODE=mock` still forces mock.

Name: PyAV (av)
URL: https://github.com/PyAV-Org/PyAV
License: BSD-3-Clause
Version/commit: >=12.0.0
Used for: Decoding browser webm/opus recordings to 16 kHz mono float32 before Whisper transcription.
Local files: backend/app/stt/faster_whisper.py, backend/requirements.txt
Notes: Dependency only. No source copied. Requires system `ffmpeg` (`brew install ffmpeg`) for codec support.

Name: ffmpeg (system binary)
URL: https://ffmpeg.org/
License: LGPL/GPL (system install via Homebrew)
Used for: Audio codec support for PyAV when decoding push-to-talk webm/opus uploads.
Local files: (none — `brew install ffmpeg`)
Notes: Not a Python dependency. Checked via `shutil.which("ffmpeg")` in provider status. User installs locally.

Name: NumPy
URL: https://numpy.org/
License: BSD-3-Clause
Version/commit: >=1.26.0
Used for: Float32 audio array passed to faster-whisper `transcribe`.
Local files: backend/app/stt/faster_whisper.py, backend/requirements.txt
Notes: Dependency only (also pulled by faster-whisper). No source copied.

Name: Playwright
URL: https://playwright.dev/
License: Apache-2.0
Version/commit: ^1.60.0
Used for: scripts/ui_verify.mjs browser smoke verification.
Local files: package.json, package-lock.json, scripts/ui_verify.mjs
Notes: devDependency only; no source copied. Bumped in Session 23 to clear GHSA-7mvr-c777-76hp advisory.
```
