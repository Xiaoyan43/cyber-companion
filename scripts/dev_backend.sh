#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# Always prefer project venv when present (shell PYTHON_BIN often lacks uvicorn).
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
HOST="${CYBER_COMPANION_API_HOST:-127.0.0.1}"
PORT="${CYBER_COMPANION_API_PORT:-8000}"
RELOAD="${CYBER_COMPANION_API_RELOAD:-1}"

UVICORN_ARGS=(backend.app.main:app --host "$HOST" --port "$PORT")

if [ "$RELOAD" = "1" ]; then
  UVICORN_ARGS+=(--reload)
fi

exec "$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}"
