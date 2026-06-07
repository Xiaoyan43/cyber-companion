#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_HOST="${CYBER_COMPANION_API_HOST:-127.0.0.1}"
API_PORT="${CYBER_COMPANION_API_PORT:-8000}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://${API_HOST}:${API_PORT}}"

bash scripts/dev_backend.sh &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

npm run dev --workspace frontend
