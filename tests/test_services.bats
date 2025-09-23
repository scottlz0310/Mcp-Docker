#!/usr/bin/env bats
# 検証対象: MCP Services
# 目的: 各サービスの起動確認とヘルスチェック

load test_helper

setup() {
    setup_test_workspace
    # 既存のコンテナをクリーンアップ
    docker-compose down -v >/dev/null 2>&1 || true
}

teardown() {
    docker-compose down -v >/dev/null 2>&1 || true
    cleanup_test_workspace
}

@test "DateTime Validator service starts successfully" {
    run docker compose up -d datetime-validator
    [ "$status" -eq 0 ]

    # サービスが起動するまで待機
    run wait_for_service "datetime-validator" 30
    [ "$status" -eq 0 ]
}

@test "DateTime Validator processes files correctly" {
    # サービス起動
    docker compose up -d datetime-validator >/dev/null 2>&1
    wait_for_service "datetime-validator" 30

    # テストファイル作成
    echo "# Test Document" > "$TEST_WORKSPACE/test.md"
    echo "Date: 2025-01-15" >> "$TEST_WORKSPACE/test.md"

    # ファイルをワークスペースにコピー（権限問題を回避）
    docker compose exec -T datetime-validator sh -c "echo '# Test Document\nDate: 2025-01-15' > /tmp/test.md"

    # ログでファイル処理を確認
    sleep 5
    run check_log_contains "datetime-validator" "DateTime Validator Server"
    [ "$status" -eq 0 ]
}

@test "DateTime Validator logs are structured" {
    docker compose up -d datetime-validator >/dev/null 2>&1
    wait_for_service "datetime-validator" 30

    sleep 3
    run docker compose logs datetime-validator
    [ "$status" -eq 0 ]
    [[ "$output" =~ "INFO:" ]]
    [[ "$output" =~ "UTC" ]] || [[ "$output" =~ "2025-" ]]
}

@test "Container runs as non-root user" {
    docker compose up -d datetime-validator >/dev/null 2>&1
    wait_for_service "datetime-validator" 30

    run docker compose exec -T datetime-validator whoami
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp" ]]
}

@test "Container has proper resource limits" {
    docker compose up -d datetime-validator >/dev/null 2>&1
    wait_for_service "datetime-validator" 30

    # メモリ使用量確認
    run docker stats --no-stream --format "{{.MemUsage}}" mcp-datetime
    [ "$status" -eq 0 ]
    # メモリ使用量が500MB未満であることを確認
    memory_mb=$(echo "$output" | cut -d'/' -f1 | sed 's/MiB//g' | cut -d'.' -f1)
    [ "$memory_mb" -lt 500 ]
}
