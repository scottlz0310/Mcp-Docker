#!/usr/bin/env bats
# 検証対象: シェルスクリプト全般
# 目的: 基本的な構文と動作の確認

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
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
