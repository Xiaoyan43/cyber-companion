#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
STRICT="${CYBER_COMPANION_STRICT_CHECK:-0}"

missing_dependency() {
  local message="$1"
  echo "$message"

  if [ "$STRICT" = "1" ]; then
    exit 1
  fi
}

echo "Checking backend syntax..."
"$PYTHON_BIN" -m compileall backend

if "$PYTHON_BIN" -c "import fastapi, httpx, pytest" >/dev/null 2>&1; then
  echo "Running backend tests..."
  "$PYTHON_BIN" -m pytest backend/tests
else
  missing_dependency "Skipping backend tests: create a venv and install backend/requirements-dev.txt first."
fi

if [ -d node_modules ]; then
  echo "Running frontend typecheck..."
  npm run check --workspace frontend
else
  missing_dependency "Skipping frontend typecheck: run npm install first."
fi

echo "Scaffold check finished."
