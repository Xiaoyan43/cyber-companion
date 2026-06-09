#!/usr/bin/env bash
# Start soul_llm_server + expose it via cloudflared or ngrok for RTC Stage 2b.
# Prints the public URL to paste into rtc-aigc-demo VoiceChat.Config.LLMConfig.Url
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

HOST="${SOUL_LLM_HOST:-127.0.0.1}"
PORT="${SOUL_LLM_PORT:-8100}"
PROVIDER="${SOUL_TUNNEL_PROVIDER:-cloudflared}"
HEALTH_PATH="/health"
LOCAL_BASE="http://${HOST}:${PORT}"
SOUL_PID=""
TUNNEL_PID=""

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

cleanup() {
  if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
    wait "$TUNNEL_PID" 2>/dev/null || true
  fi
  if [ -n "$SOUL_PID" ]; then
    kill "$SOUL_PID" 2>/dev/null || true
    wait "$SOUL_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [ -z "${SOUL_LLM_API_KEY:-}" ]; then
  echo "Warning: SOUL_LLM_API_KEY is unset." >&2
  echo "Volcengine cloud cannot reach localhost-only auth — set SOUL_LLM_API_KEY in .env for Stage 2b." >&2
fi

echo "Starting soul LLM server at ${LOCAL_BASE} …"
"$PYTHON_BIN" -m backend.realtime.soul_llm_server &
SOUL_PID=$!

echo -n "Waiting for soul health"
for _ in $(seq 1 30); do
  if curl -sf "${LOCAL_BASE}${HEALTH_PATH}" >/dev/null 2>&1; then
    echo " ok"
    break
  fi
  echo -n "."
  sleep 0.5
done

if ! curl -sf "${LOCAL_BASE}${HEALTH_PATH}" >/dev/null 2>&1; then
  echo >&2
  echo "Soul server did not become healthy at ${LOCAL_BASE}${HEALTH_PATH}" >&2
  exit 1
fi

PUBLIC_HOST=""
PUBLIC_URL=""

case "$PROVIDER" in
  cloudflared)
    require_cmd cloudflared
    LOG_FILE="$(mktemp -t soul-tunnel-cloudflared.XXXXXX.log)"
    cloudflared tunnel --url "${LOCAL_BASE}" >"$LOG_FILE" 2>&1 &
    TUNNEL_PID=$!
    echo -n "Waiting for cloudflared URL"
    for _ in $(seq 1 60); do
      PUBLIC_HOST="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | head -1 || true)"
      if [ -n "$PUBLIC_HOST" ]; then
        echo " ok"
        break
      fi
      echo -n "."
      sleep 0.5
    done
    if [ -z "$PUBLIC_HOST" ]; then
      echo >&2
      echo "Could not read cloudflared URL from $LOG_FILE" >&2
      tail -20 "$LOG_FILE" >&2 || true
      exit 1
    fi
    PUBLIC_URL="${PUBLIC_HOST}/v1/chat/completions"
    ;;
  ngrok)
    require_cmd ngrok
    LOG_FILE="$(mktemp -t soul-tunnel-ngrok.XXXXXX.log)"
    ngrok http "${PORT}" --log=stdout >"$LOG_FILE" 2>&1 &
    TUNNEL_PID=$!
    echo -n "Waiting for ngrok URL"
    for _ in $(seq 1 60); do
      PUBLIC_HOST="$(curl -sf http://127.0.0.1:4040/api/tunnels 2>/dev/null \
        | grep -oE 'https://[a-z0-9.-]+\.ngrok[^"]*' | head -1 || true)"
      if [ -n "$PUBLIC_HOST" ]; then
        echo " ok"
        break
      fi
      echo -n "."
      sleep 0.5
    done
    if [ -z "$PUBLIC_HOST" ]; then
      echo >&2
      echo "Could not read ngrok public URL (is ngrok authenticated?)" >&2
      tail -20 "$LOG_FILE" >&2 || true
      exit 1
    fi
    PUBLIC_URL="${PUBLIC_HOST}/v1/chat/completions"
    ;;
  *)
    echo "Unknown SOUL_TUNNEL_PROVIDER=${PROVIDER} (use cloudflared or ngrok)" >&2
    exit 1
    ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Soul LLM (local):  ${LOCAL_BASE}"
echo "Health:            ${LOCAL_BASE}${HEALTH_PATH}"
echo "Tunnel provider:   ${PROVIDER}"
echo "Public LLM URL:    ${PUBLIC_URL}"
echo ""
echo "Paste into rtc-aigc-demo → VoiceChat.Config.LLMConfig:"
echo "  \"Mode\": \"CustomLLM\","
echo "  \"Url\": \"${PUBLIC_URL}\","
echo "  \"APIKey\": \"\${SOUL_LLM_API_KEY}\","
echo "  \"ModelName\": \"boxi-soul\""
echo ""
echo "Set VoiceChat.Config.S2SConfig.OutputMode = 1 for hybrid mode."
echo "Press Ctrl+C to stop soul server and tunnel."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait "$SOUL_PID"
