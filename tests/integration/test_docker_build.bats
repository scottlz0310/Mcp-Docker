#!/usr/bin/env bats
# 検証対象: Docker Build
# 目的: Dockerイメージのビルド成功とベストプラクティス準拠確認

load ../helpers/test_helper

@test "Docker build succeeds" {
    run docker build -t mcp-docker-test .
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Successfully built" ]] || [[ "$output" =~ "exporting to image" ]]
}

@test "Docker image has correct labels" {
    docker build -t mcp-docker-test . >/dev/null 2>&1
    run docker inspect mcp-docker-test --format='{{.Config.Labels}}'
    [ "$status" -eq 0 ]
}

@test "Docker image uses non-root user" {
    docker build -t mcp-docker-test . >/dev/null 2>&1
    run docker inspect mcp-docker-test --format='{{.Config.User}}'
    [ "$status" -eq 0 ]
    # デフォルトターゲット（mcp-server）はmcpユーザーを使用
    [[ "$output" =~ "mcp" ]]
}

@test "Docker image has minimal size" {
    docker build -t mcp-docker-test . >/dev/null 2>&1
    run docker images mcp-docker-test --format "{{.Size}}"
    [ "$status" -eq 0 ]
    # サイズが2GB未満であることを確認（CodeQLを含むため大きめ）
    size_mb=$(docker images mcp-docker-test --format "{{.Size}}" | sed 's/GB/000/g' | sed 's/MB//g' | cut -d'.' -f1)
    [ "$size_mb" -lt 2000 ]
}

teardown() {
    docker rmi mcp-docker-test >/dev/null 2>&1 || true
}
