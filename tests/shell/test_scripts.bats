#!/usr/bin/env bats
# 検証対象: シェルスクリプト全般
# 目的: 基本的な構文と動作の確認

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
}

create_docker_mock() {
    local mock_path="$1"
    cat >"$mock_path" <<'EOF'
#!/bin/bash
set -euo pipefail

case "$1" in
    compose)
        printf 'name: test-project\n'
        ;;
    volume)
        printf 'test-volume\n'
        ;;
    run)
        printf 'MSYS_NO_PATHCONV=%s\n' "${MSYS_NO_PATHCONV:-}" >"${DOCKER_MOCK_LOG:?}"
        printf 'arg=%s\n' "$@" >>"${DOCKER_MOCK_LOG}"
        exit "${DOCKER_MOCK_RUN_STATUS:-0}"
        ;;
    *)
        printf 'unexpected docker command: %s\n' "$1" >&2
        exit 2
        ;;
esac
EOF
    chmod +x "$mock_path"
}

@test "health-check.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/health-check.sh" ]
    [ -x "${SCRIPTS_DIR}/health-check.sh" ]
}

@test "health-check.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/health-check.sh"
}

@test "health-check.sh: --helpオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: -hオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: 不明なオプションでエラー終了する" {
    run "${SCRIPTS_DIR}/health-check.sh" --unknown-option
    [ "$status" -eq 1 ]
    [[ "$output" =~ "不明なオプション" ]]
}

@test "health-check.sh: --helpオプションにサービス説明が含まれる" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp-gateway" ]]
}

@test "lint-shell.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/lint-shell.sh" ]
    [ -x "${SCRIPTS_DIR}/lint-shell.sh" ]
}

@test "lint-shell.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/lint-shell.sh"
}

@test "rotate-secret.sh: Git Bashのパス変換を無効化して削除を検証する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_docker_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        "${SCRIPTS_DIR}/rotate-secret.sh"

    [ "$status" -eq 0 ]
    grep -Fx 'MSYS_NO_PATHCONV=1' "$mock_log"
    grep -Fx 'arg=test-volume:/data' "$mock_log"
    grep -Fx "arg=rm -f /data/config.yaml && test ! -e /data/config.yaml" "$mock_log"
    [ "$output" = "config.yaml を削除しました (test-volume)" ]
}

@test "rotate-secret.sh: config削除の検証失敗を伝播する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_docker_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_RUN_STATUS=1 \
        "${SCRIPTS_DIR}/rotate-secret.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"エラー: /data/config.yaml の削除を確認できませんでした (test-volume)"* ]]
    [[ ! "$output" =~ "config.yaml を削除しました" ]]
}
