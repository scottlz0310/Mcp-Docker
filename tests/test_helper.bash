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
