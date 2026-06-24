#!/usr/bin/env bash
# Run the Virtual Alan Turing stack locally: FastAPI backend + Vite frontend.
# Both run in the foreground; Ctrl+C stops both cleanly.
#
# Usage: ./tools/run.sh
# Env overrides: BACKEND_PORT (default 8000), FRONTEND_PORT (default 5173)
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

command -v uv >/dev/null 2>&1 || { echo "error: 'uv' not found — install it or open the dev container." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "error: 'npm' not found — install Node or open the dev container." >&2; exit 1; }

# A Gemini key is needed for /chat (not for /personas). Warn, don't block.
if [ ! -f .env ] && [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "warning: no .env and GEMINI_API_KEY unset — chat will fail until you 'cp .env.example .env' and add a key." >&2
fi

# Ensure frontend deps are present (first run only).
if [ ! -d frontend/node_modules ]; then
  echo "installing frontend dependencies (first run)..."
  (cd frontend && npm install)
fi

# Recursively kill a process and all its descendants. `uv run` and `npm` spawn
# the real servers (uvicorn reloader/worker, vite) as children in their own
# process groups, so we walk the ppid tree rather than relying on group kills.
kill_tree() {
  local pid=$1 child
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

pids=()
cleanup() {
  trap - INT TERM EXIT
  echo
  echo "shutting down..."
  for pid in "${pids[@]}"; do
    kill_tree "$pid"
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "starting backend  → http://localhost:${BACKEND_PORT}"
uv run uvicorn turing.api.app:app --reload --port "${BACKEND_PORT}" &
pids+=($!)

echo "starting frontend → http://localhost:${FRONTEND_PORT}"
npm --prefix frontend run dev -- --port "${FRONTEND_PORT}" &
pids+=($!)

echo
echo "ready — open http://localhost:${FRONTEND_PORT}  (Ctrl+C to stop both)"
wait
