#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${CYBER_COMPANION_API_HOST:-127.0.0.1}"
PORT="${CYBER_COMPANION_API_PORT:-8000}"
URL="${CYBER_COMPANION_HEALTH_URL:-http://${HOST}:${PORT}/health}"

"$PYTHON_BIN" - "$URL" <<'PY'
import json
import sys
from urllib.request import urlopen

url = sys.argv[1]

with urlopen(url, timeout=3) as response:
    status_code = response.status
    payload = json.loads(response.read().decode("utf-8"))

if status_code != 200:
    raise SystemExit(f"Health check failed with HTTP {status_code}")

if payload.get("status") != "ok":
    raise SystemExit(f"Health check returned unexpected payload: {payload}")

print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY
