#!/usr/bin/env bash
# GitHub Actions Simulator one-shot launcher.
#
# Usage:
#   ./scripts/run-actions.sh [WORKFLOW_FILE] [-- <additional CLI args>]
#
# The script ensures the simulator image is up-to-date, then executes the
# Click CLI inside the dedicated Docker container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

info() {
  printf '👉 %s\n' "$*"
}

error() {
  printf '❌ %s\n' "$*" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "required command not found: $1"
    exit 1
  fi
}

require_cmd docker

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
else
  error "docker compose plugin is required."
  exit 1
fi

info "Docker version: $(docker --version)"
info "Docker Compose: $("${COMPOSE_CMD[@]}" version)"

if command -v uv >/dev/null 2>&1; then
  info "Host uv: $(uv --version)"
else
  info "Host uv not found (will use container-bundled uv)"
fi

info "Pulling latest actions-simulator image..."
"${COMPOSE_CMD[@]}" --profile tools pull actions-simulator >/dev/null 2>&1 || true

WORKFLOW=""
REST_ARGS=()
if [[ $# -gt 0 ]]; then
  WORKFLOW="$1"
  shift
fi

if [[ $# -gt 0 ]]; then
  REST_ARGS=("$@")
fi

CMD=("uv" "run" "python" "main.py" "actions")
if [[ -n "${WORKFLOW}" ]]; then
  CMD+=("simulate" "${WORKFLOW}")
else
  CMD+=("--help")
fi

if [[ ${#REST_ARGS[@]} -gt 0 ]]; then
  CMD+=("${REST_ARGS[@]}")
fi

info "Running actions-simulator container..."
"${COMPOSE_CMD[@]}" --profile tools run --rm \
  -e WORKFLOW_FILE="${WORKFLOW}" \
  actions-simulator \
  "${CMD[@]}"

RUN_EXIT=$?

if [[ ${RUN_EXIT} -ne 0 ]]; then
  error "Simulation exited with status ${RUN_EXIT}"
fi

exit "${RUN_EXIT}"
