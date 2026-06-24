#!/usr/bin/env bash
set -euo pipefail

# Install uv if not already present
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv sync
uv run pre-commit install

if [ -d frontend ]; then
  (cd frontend && npm install)
fi
