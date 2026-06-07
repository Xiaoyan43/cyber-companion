#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${CYBER_COMPANION_API_HOST:-127.0.0.1}"
PORT="${CYBER_COMPANION_API_PORT:-8000}"
RELOAD="${CYBER_COMPANION_API_RELOAD:-1}"

UVICORN_ARGS=(backend.app.main:app --host "$HOST" --port "$PORT")

if [ "$RELOAD" = "1" ]; then
  UVICORN_ARGS+=(--reload)
fi

exec "$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}"
