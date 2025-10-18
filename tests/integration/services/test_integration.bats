#!/usr/bin/env bats
# 検証対象: Integration
# 目的: サービス間連携とE2Eテスト

load ../../helpers/test_helper

setup() {
    setup_test_workspace
    docker compose down -v >/dev/null 2>&1 || true
}

teardown() {
    docker compose down -v >/dev/null 2>&1 || true
    cleanup_test_workspace
}

@test "All services can be built" {
    run docker compose build
    [ "$status" -eq 0 ]
}

@test "Services start in correct order" {
    run docker compose up -d
    [ "$status" -eq 0 ]

    # 全サービスが起動するまで待機
    sleep 10

    # サービス状態確認
    run docker compose ps
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Up" ]]
}

@test "Network connectivity between services" {
    docker compose up -d >/dev/null 2>&1
    sleep 10

    # ネットワーク確認
    run docker network ls
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp-network" ]]
}

@test "Log aggregation works correctly" {
    docker compose up -d >/dev/null 2>&1
    sleep 5

    # 全サービスのログが取得できることを確認
    run docker compose logs
    [ "$status" -eq 0 ]
}

@test "Environment variables are properly set" {
    skip "CI環境でdocker compose execが失敗するためスキップ"
    docker compose up -d >/dev/null 2>&1
    sleep 5

    # github-mcpサービスで環境変数が正しく設定されていることを確認
    run docker compose exec -T github-mcp env
    [ "$status" -eq 0 ]
    # 基本的な環境変数の存在を確認
    [[ "$output" =~ "PATH" ]]
    [[ "$output" =~ "HOME" ]]
}

@test "Volume mounts work correctly" {
    skip "CI環境でdocker compose execが失敗するためスキップ"
    docker compose up -d >/dev/null 2>&1
    sleep 5

    # github-mcpサービスで書き込み権限の確認
    run docker compose exec -T github-mcp touch /tmp/test_write
    [ "$status" -eq 0 ]
}

@test "Service graceful shutdown" {
    docker compose up -d >/dev/null 2>&1
    sleep 5

    # サービスが起動していることを確認
    run docker compose ps -q
    [ "$status" -eq 0 ]
    [ -n "$output" ]  # コンテナがIDが存在する

    # グレースフルシャットダウンの確認
    run timeout 30 docker compose down
    [ "$status" -eq 0 ]
}
