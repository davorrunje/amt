#!/usr/bin/env bash
# Set up and run the archive sourcing pipeline:
#   1. install Python deps (including the `sourcing` group) and headless Chromium
#   2. fetch + transcribe the references listed in corpus/sources.yaml
#
# Usage: ./tools/source.sh [args passed through to `python -m turing.sourcing`]
#   e.g.  ./tools/source.sh --force
#         ./tools/source.sh --sources corpus/sources.yaml --model gemini-2.5-flash
#
# Requires GEMINI_API_KEY, taken from the environment or a .env file in the repo root.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

command -v uv >/dev/null 2>&1 || { echo "error: 'uv' not found — install it or open the dev container." >&2; exit 1; }

echo "==> Installing Python dependencies (uv sync)"
uv sync

echo "==> Installing headless Chromium for Playwright"
uv run playwright install chromium

# Load GEMINI_API_KEY from .env if present and not already set in the environment.
if [ -z "${GEMINI_API_KEY:-}" ] && [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "error: GEMINI_API_KEY is not set. Add it to .env (cp .env.example .env) or export it." >&2
  exit 1
fi

echo "==> Sourcing archive references from corpus/sources.yaml"
uv run python -m turing.sourcing "$@"
echo "==> Done. Transcriptions are in corpus/ (gitignored, local only)."
