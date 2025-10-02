#!/usr/bin/env bash
# Bats test helper functions

# テスト用の共通設定
export TEST_TIMEOUT=30
export TEST_WORKSPACE="/tmp/mcp_test_workspace"

# テスト前の共通セットアップ
setup_test_workspace() {
    mkdir -p "$TEST_WORKSPACE"
    export TZ=UTC
}

# テスト後の共通クリーンアップ
cleanup_test_workspace() {
    rm -rf "$TEST_WORKSPACE"
}

# Docker Composeサービスの起動確認
wait_for_service() {
    local service_name="$1"
    local timeout="${2:-30}"
    local count=0

    while [ "$count" -lt "$timeout" ]; do
        if docker compose ps "$service_name" | grep -q "Up"; then
            return 0
        fi
        sleep 1
        ((count++))
    done
    return 1
}

# ログ出力の確認
check_log_contains() {
    local service_name="$1"
    local expected_text="$2"

    docker compose logs "$service_name" | grep -q "$expected_text"
}

# UTC時刻の取得
get_utc_timestamp() {
    date -u +"%Y-%m-%d %H:%M:%S"
}

# プロジェクトルートでコマンドを実行
run_in_project_root() {
    cd "$PROJECT_ROOT" || return 1
    "$@"
}

# Batsアサーション関数
assert_success() {
    if [ "$status" -ne 0 ]; then
        echo "Expected success but got exit code $status"
        echo "Output: $output"
        return 1
    fi
}

assert_failure() {
    if [ "$status" -eq 0 ]; then
        echo "Expected failure but got success"
        echo "Output: $output"
        return 1
    fi
}

assert_output() {
    if [[ "$1" == "--partial" ]]; then
        local expected="$2"
        if [[ "$output" != *"$expected"* ]]; then
            echo "Expected output to contain '$expected'"
            echo "Actual output: $output"
            return 1
        fi
    else
        local expected="$1"
        if [[ "$output" != "$expected" ]]; then
            echo "Expected: $expected"
            echo "Actual: $output"
            return 1
        fi
    fi
}

# runコマンドの実装（簡易版）
run() {
    local errexit_was_set=0
    if [[ $- == *e* ]]; then
        errexit_was_set=1
        set +e
    fi

    output=$("$@" 2>&1)
    status=$?

    if [[ $errexit_was_set -eq 1 ]]; then
        set -e
    fi
}
