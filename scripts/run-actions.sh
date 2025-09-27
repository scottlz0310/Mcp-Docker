#!/usr/bin/env bash
# GitHub Actions Simulator one-shot launcher.
#
# Usage:
#   ./scripts/run-actions.sh [WORKFLOW_FILE] [-- <additional CLI args>]
#
# The script ensures the simulator image is up-to-date, then executes the
# Click CLI inside the dedicated Docker container.

set -euo pipefail

prepare_output_dir() {
  local dir="${PROJECT_ROOT}/output"
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir" 2>/dev/null || true
  fi
  if [[ ! -w "$dir" ]]; then
    cat <<'EOF' >&2
❌ output ディレクトリに書き込みできません。
権限を修正してください（例）:
  sudo chown -R $(id -u):$(id -g) output
  # または
  sudo chmod -R 777 output
EOF
    exit 1
  fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

DEFAULT_WORKFLOW=".github/workflows/ci.yml"
declare -a WORKFLOW_CHOICES=()

prepare_output_dir

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

normalize_workflow_path() {
  local path="$1"
  path="${path#./}"
  printf '%s' "$path"
}

discover_workflows() {
  WORKFLOW_CHOICES=()
  while IFS= read -r wf; do
    wf="${wf#./}"
    WORKFLOW_CHOICES+=("$wf")
  done < <(find .github/workflows -type f \( -name '*.yml' -o -name '*.yaml' \) -print | sort)
}

workflow_exists() {
  local target="$1"
  for wf in "${WORKFLOW_CHOICES[@]}"; do
    if [[ "$wf" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}

print_workflow_menu() {
  local default="$1"
  info "📋 使用可能なワークフロー:"
  local idx=1
  for wf in "${WORKFLOW_CHOICES[@]}"; do
    local marker=""
    if [[ "$wf" == "$default" ]]; then
      marker=" (default)"
    fi
    printf '  %2d) %s%s
' "$idx" "$wf" "$marker"
    ((idx++))
  done
}

choose_workflow() {
  if [[ ${#WORKFLOW_CHOICES[@]} -eq 0 ]]; then
    discover_workflows
  fi
  if [[ ${#WORKFLOW_CHOICES[@]} -eq 0 ]]; then
    error "ワークフローファイルが見つかりません (.github/workflows)"
    exit 1
  fi

  local default_path
  default_path=$(normalize_workflow_path "$DEFAULT_WORKFLOW")
  local default_index=1
  local found_default="false"
  if [[ -n "$default_path" ]]; then
    for i in "${!WORKFLOW_CHOICES[@]}"; do
      if [[ "${WORKFLOW_CHOICES[$i]}" == "$default_path" ]]; then
        default_index=$((i + 1))
        found_default="true"
        break
      fi
    done
  fi

  if [[ "$found_default" != "true" ]]; then
    default_index=1
    default_path="${WORKFLOW_CHOICES[0]}"
  fi

  print_workflow_menu "$default_path" >&2

  local choice="${INDEX:-}"
  if [[ -z "$choice" ]]; then
    if [[ -t 0 ]]; then
  printf '🎯 実行するワークフローを選択してください (Enter=%d): ' "$default_index" >&2
  read -r choice || choice=""
    else
      choice=""
    fi
  else
  info "INDEX=${choice} を使用します" >&2
  fi

  if [[ -z "$choice" ]]; then
    choice=$default_index
  fi

  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
  error "無効な選択です: $choice"
    exit 1
  fi

  local choice_index=$((choice))
  if (( choice_index < 1 || choice_index > ${#WORKFLOW_CHOICES[@]} )); then
  error "無効な番号です: $choice"
    exit 1
  fi

  local selected="${WORKFLOW_CHOICES[$((choice_index - 1))]}"
  info "🚀 実行ワークフロー: ${selected}" >&2
  printf '%s' "$selected"
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

WORKFLOW="${WORKFLOW:-}"
workflow_from_argument="false"
workflow_selected_interactively="false"
REST_ARGS=()
ACT_TIMEOUT="${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS:-}"

pass_remaining="false"
while [[ $# -gt 0 ]]; do
  arg="$1"
  shift

  if [[ "$pass_remaining" == "true" ]]; then
    REST_ARGS+=("$arg")
    continue
  fi

  case "$arg" in
    --)
      pass_remaining="true"
      ;;
    --timeout|--act-timeout)
      if [[ $# -eq 0 ]]; then
        error "--timeout には秒数を指定してください"
        exit 1
      fi
      ACT_TIMEOUT="$1"
      shift
      ;;
    --timeout=*|--act-timeout=*)
      ACT_TIMEOUT="${arg#*=}"
      ;;
    -* )
      REST_ARGS+=("$arg")
      ;;
    *)
      if [[ -z "$WORKFLOW" ]]; then
        WORKFLOW="$arg"
      else
        REST_ARGS+=("$arg")
      fi
      ;;
  esac
done

if [[ -n "$ACT_TIMEOUT" ]]; then
  if ! [[ "$ACT_TIMEOUT" =~ ^[0-9]+$ ]] || (( ACT_TIMEOUT <= 0 )); then
    error "タイムアウト値は正の整数（秒）で指定してください: $ACT_TIMEOUT"
    exit 1
  fi
  info "act タイムアウト: ${ACT_TIMEOUT} 秒"
  ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS="$ACT_TIMEOUT"
fi

discover_workflows

if [[ -n "$WORKFLOW" ]]; then
  if [[ "$WORKFLOW" == /* ]]; then
    error "ワークフローファイルはリポジトリ相対パスで指定してください: $WORKFLOW"
    exit 1
  fi
  normalized=$(normalize_workflow_path "$WORKFLOW")
  if [[ -f "$normalized" ]]; then
    WORKFLOW="$normalized"
    workflow_from_argument="true"
  elif workflow_exists "$normalized"; then
    WORKFLOW="$normalized"
    workflow_from_argument="true"
  else
    error "指定されたワークフローが見つかりません: $WORKFLOW"
    exit 1
  fi
fi

if [[ -z "$WORKFLOW" ]]; then
  should_prompt="true"
  if [[ ${#REST_ARGS[@]} -gt 0 ]]; then
    first_arg="${REST_ARGS[0]}"
    if [[ -n "$first_arg" && "$first_arg" != -* ]]; then
      should_prompt="false"
    fi
  fi

  if [[ "$should_prompt" == "true" ]]; then
    WORKFLOW="$(choose_workflow)"
    workflow_selected_interactively="true"
  fi
fi

if [[ "$workflow_from_argument" == "true" && "$workflow_selected_interactively" == "false" && -n "$WORKFLOW" ]]; then
  info "🚀 実行ワークフロー: ${WORKFLOW}"
fi

CMD=("uv" "run" "python" "main.py" "actions")
if [[ -n "${WORKFLOW}" ]]; then
  CMD+=("simulate" "${WORKFLOW}")
elif [[ ${#REST_ARGS[@]} -eq 0 ]]; then
  CMD+=("--help")
fi

if [[ ${#REST_ARGS[@]} -gt 0 ]]; then
  CMD+=("${REST_ARGS[@]}")
fi

info "Running actions-simulator container..."
COMPOSE_RUN_ARGS=("--profile" "tools" "run" "--rm")
COMPOSE_ENV_VARS=('-e' "WORKFLOW_FILE=${WORKFLOW}")
if [[ -n "${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS:-}" ]]; then
  COMPOSE_ENV_VARS+=(
    "-e" "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS}"
  )
fi
if [[ -n "${ACTIONS_SIMULATOR_ENGINE:-}" ]]; then
  COMPOSE_ENV_VARS+=(
    "-e" "ACTIONS_SIMULATOR_ENGINE=${ACTIONS_SIMULATOR_ENGINE}"
  )
fi

"${COMPOSE_CMD[@]}" \
  "${COMPOSE_RUN_ARGS[@]}" \
  "${COMPOSE_ENV_VARS[@]}" \
  actions-simulator \
  "${CMD[@]}"

RUN_EXIT=$?

if [[ ${RUN_EXIT} -ne 0 ]]; then
  error "Simulation exited with status ${RUN_EXIT}"
fi

exit "${RUN_EXIT}"
