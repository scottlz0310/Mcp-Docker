#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "使用方法: $0 <main イメージ> <fallback イメージ>" >&2
    exit 2
fi

MAIN_IMAGE="$1"
FALLBACK_IMAGE="$2"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PULL_OUTPUT=""

pull_image() {
    local image="$1"
    local status

    if PULL_OUTPUT=$(PLAYWRIGHT_MCP_IMAGE="${image}" "${DOCKER_BIN}" compose pull playwright-mcp 2>&1); then
        return 0
    else
        status=$?
        return "${status}"
    fi
}

print_pull_output() {
    if [[ -n "${PULL_OUTPUT}" ]]; then
        printf '%s\n' "${PULL_OUTPUT}" >&2
    fi
}

is_missing_manifest() {
    local output="$1"

    grep -Eqi 'no such manifest|manifest[[:space:]]+unknown|manifest.*not found|not found.*manifest|resolve reference.*not found|status code[^0-9]*404' <<<"${output}"
}

if pull_image "${MAIN_IMAGE}"; then
    print_pull_output
    printf '%s\n' "${MAIN_IMAGE}"
    exit 0
else
    main_status=$?
fi

if ! is_missing_manifest "${PULL_OUTPUT}"; then
    print_pull_output
    echo "❌ Playwright MCP の :main イメージ取得に失敗しました。manifest 未公開以外のエラーのため fallback は行いません。" >&2
    exit "${main_status}"
fi

print_pull_output
echo "⚠️ Playwright MCP の :main イメージが公開されていないため、${FALLBACK_IMAGE} にフォールバックします。" >&2

if pull_image "${FALLBACK_IMAGE}"; then
    print_pull_output
    printf '%s\n' "${FALLBACK_IMAGE}"
    exit 0
else
    fallback_status=$?
fi

print_pull_output
echo "❌ Playwright MCP の fallback イメージ取得にも失敗しました。" >&2
exit "${fallback_status}"
