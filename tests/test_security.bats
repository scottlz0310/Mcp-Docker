#!/usr/bin/env bats
# 検証対象: Security
# 目的: セキュリティ設定とベストプラクティスの確認

load test_helper

setup() {
    setup_test_workspace
}

teardown() {
    cleanup_test_workspace
    docker rmi mcp-docker-security-test >/dev/null 2>&1 || true
}

@test "Dockerfile follows security best practices" {
    # hadolintでDockerfileをチェック（利用可能な場合のみ）
    if command -v hadolint >/dev/null 2>&1; then
        run hadolint Dockerfile
        [ "$status" -eq 0 ]
    else
        # hadolintが利用できない場合はDockerで実行
        run docker run --rm -i hadolint/hadolint < Dockerfile
        # 警告レベルのエラーは許可（exit code 0または1）
        [ "$status" -le 1 ]
    fi
}

@test "No secrets in Docker image" {
    docker build -t mcp-docker-security-test . >/dev/null 2>&1
    
    # 環境変数に秘密情報が含まれていないことを確認
    run docker inspect mcp-docker-security-test --format='{{.Config.Env}}'
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "PASSWORD" ]]
    [[ ! "$output" =~ "SECRET" ]]
    [[ ! "$output" =~ "TOKEN" ]]
}

@test "Image uses minimal base image" {
    docker build -t mcp-docker-security-test . >/dev/null 2>&1
    
    # Alpine Linuxベースであることを確認
    run docker run --rm mcp-docker-security-test cat /etc/os-release
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Alpine" ]]
    
    # レイヤー数が適切であることを確認（50層未満）
    layer_count=$(docker history mcp-docker-security-test --quiet | wc -l)
    [ "$layer_count" -lt 50 ]
}

@test "Container has no unnecessary packages" {
    docker build -t mcp-docker-security-test . >/dev/null 2>&1
    
    # 不要なパッケージがインストールされていないことを確認
    run docker run --rm mcp-docker-security-test sh -c "which wget curl"
    [ "$status" -eq 0 ]  # 必要なツールは存在
    
    # 開発ツールが含まれていないことを確認
    run docker run --rm mcp-docker-security-test sh -c "which gcc make"
    [ "$status" -ne 0 ]  # 開発ツールは存在しない
}

@test "Trivy security scan passes" {
    docker build -t mcp-docker-security-test . >/dev/null 2>&1
    
    # Trivyでセキュリティスキャン実行（CRITICALのみチェック）
    run docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image --exit-code 1 --severity CRITICAL \
        --quiet mcp-docker-security-test
    
    # CRITICALな脆弱性がないことを確認
    [ "$status" -eq 0 ]
}

@test "File permissions are secure" {
    docker build -t mcp-docker-security-test . >/dev/null 2>&1
    
    # コンテナが非rootユーザーで実行されていることを確認
    run docker run --rm mcp-docker-security-test whoami
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp" ]]
    
    # /appディレクトリが存在し、アクセス可能であることを確認
    run docker run --rm mcp-docker-security-test ls -la /app
    [ "$status" -eq 0 ]
    
    # ファイルの所有者がmcpユーザーであることを確認
    run docker run --rm mcp-docker-security-test stat -c "%U" /app
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp" ]]
}