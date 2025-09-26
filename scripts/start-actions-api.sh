#!/usr/bin/env bash
# Start the Actions simulation REST API with uv.

set -eu -o pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

exec uv run uvicorn services.actions.api:app --host "$HOST" --port "$PORT"
