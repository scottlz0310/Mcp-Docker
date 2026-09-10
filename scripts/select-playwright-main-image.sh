#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "使用方法: $0 <main イメージ> <fallback イメージ>" >&2
    exit 2
fi

MAIN_IMAGE="$1"
FALLBACK_IMAGE="$2"
DOCKER_BIN="${DOCKER_BIN:-docker}"

inspect_image() {
    local image="$1"
    local output

    if output=$("${DOCKER_BIN}" image inspect "${image}" 2>&1); then
        return 0
    fi

    if grep -Eqi 'no such image|image.*not found|not found.*image' <<<"${output}"; then
        return 1
    fi

    printf '%s\n' "${output}" >&2
    echo "❌ Playwright MCP のローカルイメージ確認に失敗しました: ${image}" >&2
    return 125
}

if inspect_image "${MAIN_IMAGE}"; then
    printf '%s\n' "${MAIN_IMAGE}"
    exit 0
else
    main_status=$?
fi

if [[ "${main_status}" -ne 1 ]]; then
    exit "${main_status}"
fi

if inspect_image "${FALLBACK_IMAGE}"; then
    printf '%s\n' "${FALLBACK_IMAGE}"
    exit 0
else
    fallback_status=$?
fi

if [[ "${fallback_status}" -eq 1 ]]; then
    echo "❌ Playwright MCP のローカルイメージが見つかりません。先に make pull-main を実行してください。" >&2
fi
exit "${fallback_status}"
