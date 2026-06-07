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
Name:
URL:
License:
Reuse level:
Purpose:
Decision:
Notes:
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
Version/commit: ^5.4.0
Used for: Frontend dev server and build tooling.
Local files: frontend/package.json, frontend/vite.config.ts
Notes: Dependency only. No source copied. npm audit reports a moderate esbuild dev-server advisory for Vite 5.x; production dependency audit is clean, and major Vite upgrade is deferred.

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
Used for: FastAPI TestClient test dependency.
Local files: backend/requirements-dev.txt
Notes: Dependency only. No source copied.
```
