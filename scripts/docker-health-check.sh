#!/bin/bash
# Docker統合ヘルスチェックスクリプト
# GitHub Actions Simulatorのための包括的なDocker環境ヘルスチェック

set -euo pipefail

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker daemon接続確認
check_docker_daemon() {
    log_info "Docker daemon接続を確認中..."

    if ! docker version --format '{{.Server.Version}}' > /dev/null 2>&1; then
        log_error "Docker daemonに接続できません"
        return 1
    fi

    local server_version
    server_version=$(docker version --format '{{.Server.Version}}')
    log_success "Docker daemon接続OK: バージョン $server_version"
    return 0
}

# Docker info確認
check_docker_info() {
    log_info "Docker情報を確認中..."

    local docker_info
    if ! docker_info=$(docker info --format json 2>/dev/null); then
        log_error "Docker情報を取得できません"
        return 1
    fi

    # 重要な情報を抽出
    local containers_running containers_total images
    containers_running=$(echo "$docker_info" | jq -r '.ContainersRunning // 0')
    containers_total=$(echo "$docker_info" | jq -r '.Containers // 0')
    images=$(echo "$docker_info" | jq -r '.Images // 0')

    log_success "Docker情報OK:"
    log_info "  実行中コンテナ: $containers_running/$containers_total"
    log_info "  イメージ数: $images"

    return 0
}

# Dockerソケットアクセス確認
check_docker_socket() {
    log_info "Dockerソケットアクセスを確認中..."

    local socket_path="/var/run/docker.sock"

    if [[ ! -S "$socket_path" ]]; then
        log_error "Dockerソケットが見つかりません: $socket_path"
        return 1
    fi

    # ソケットの権限確認
    local socket_perms
    socket_perms=$(stat -c "%a" "$socket_path" 2>/dev/null || echo "unknown")
    log_info "Dockerソケット権限: $socket_perms"

    # ソケットへの書き込み権限確認
    if [[ -w "$socket_path" ]]; then
        log_success "Dockerソケットへの書き込み権限があります"
    else
        log_warning "Dockerソケットへの書き込み権限がありません"
        log_info "ユーザーをdockerグループに追加してください: sudo usermod -aG docker \$USER"
    fi

    return 0
}

# コンテナ実行テスト
test_container_execution() {
    log_info "コンテナ実行テストを実行中..."

    local test_image="alpine:latest"
    local test_name="docker-health-test-$$"

    # テストイメージのプル
    if ! docker pull "$test_image" > /dev/null 2>&1; then
        log_error "テストイメージのプルに失敗しました: $test_image"
        return 1
    fi

    # テストコンテナの実行
    if docker run --rm --name "$test_name" "$test_image" echo "Docker container test successful" > /dev/null 2>&1; then
        log_success "コンテナ実行テストが成功しました"
        return 0
    else
        log_error "コンテナ実行テストが失敗しました"
        return 1
    fi
}

# Docker Composeネットワーク確認
check_docker_network() {
    log_info "Docker Composeネットワークを確認中..."

    if docker network ls --format "{{.Name}}" | grep -q "^mcp-network$"; then
        log_success "mcp-networkが存在します"

        # ネットワークの詳細情報を取得
        local network_info
        network_info=$(docker network inspect mcp-network --format '{{.Driver}}' 2>/dev/null || echo "unknown")
        log_info "ネットワークドライバー: $network_info"

        return 0
    else
        log_warning "mcp-networkが存在しません"
        log_info "ネットワークを作成してください: docker network create mcp-network"
        return 1
    fi
}

# Docker Composeボリューム確認
check_docker_volumes() {
    log_info "Docker Composeボリュームを確認中..."

    local volumes=("act-cache" "act-workspace")
    local volumes_ok=true

    for volume in "${volumes[@]}"; do
        if docker volume ls --format "{{.Name}}" | grep -q "^${volume}$"; then
            log_success "ボリュームが存在します: $volume"
        else
            log_warning "ボリュームが存在しません: $volume"
            log_info "docker-compose up でボリュームが自動作成されます"
            volumes_ok=false
        fi
    done

    if $volumes_ok; then
        return 0
    else
        return 1
    fi
}

# actバイナリ確認
check_act_binary() {
    log_info "actバイナリを確認中..."

    if ! command -v act > /dev/null 2>&1; then
        log_error "actバイナリが見つかりません"
        log_info "actをインストールしてください: brew install act"
        return 1
    fi

    local act_version
    act_version=$(act --version 2>/dev/null || echo "unknown")
    log_success "actバイナリが利用可能です: $act_version"

    return 0
}

# Docker BuildKit確認
check_docker_buildkit() {
    log_info "Docker BuildKit設定を確認中..."

    local buildkit_enabled
    buildkit_enabled=$(docker info --format '{{.ClientInfo.BuildkitVersion}}' 2>/dev/null || echo "")

    if [[ -n "$buildkit_enabled" ]]; then
        log_success "Docker BuildKitが有効です: $buildkit_enabled"
        return 0
    else
        log_warning "Docker BuildKitが無効または確認できません"
        log_info "DOCKER_BUILDKIT=1 環境変数を設定してください"
        return 1
    fi
}

# システムリソース確認
check_system_resources() {
    log_info "システムリソースを確認中..."

    # メモリ使用量確認
    if command -v free > /dev/null 2>&1; then
        local memory_info
        memory_info=$(free -h | grep "^Mem:")
        log_info "メモリ使用量: $memory_info"
    fi

    # ディスク使用量確認
    if command -v df > /dev/null 2>&1; then
        local disk_usage
        disk_usage=$(df -h / | tail -1)
        log_info "ディスク使用量: $disk_usage"
    fi

    # Docker システム使用量確認
    if docker system df > /dev/null 2>&1; then
        log_info "Docker システム使用量:"
        docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" | while read -r line; do
            log_info "  $line"
        done
    fi

    return 0
}

# 包括的ヘルスチェック実行
run_comprehensive_health_check() {
    log_info "包括的Docker統合ヘルスチェックを開始します"
    echo "=================================================================="

    local exit_code=0
    local checks_passed=0
    local total_checks=0

    # 各チェックを実行
    local checks=(
        "check_docker_daemon"
        "check_docker_info"
        "check_docker_socket"
        "test_container_execution"
        "check_docker_network"
        "check_docker_volumes"
        "check_act_binary"
        "check_docker_buildkit"
        "check_system_resources"
    )

    for check in "${checks[@]}"; do
        echo ""
        total_checks=$((total_checks + 1))

        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            exit_code=1
        fi
    done

    echo ""
    echo "=================================================================="

    # 結果サマリー
    log_info "ヘルスチェック結果: $checks_passed/$total_checks 項目が正常"

    if [[ $exit_code -eq 0 ]]; then
        log_success "Docker統合ヘルスチェックが完了しました！"
        log_info "GitHub Actions Simulatorを使用する準備ができています"
    else
        log_error "Docker統合ヘルスチェックで問題が検出されました"
        log_info "上記のエラーメッセージを確認して問題を修正してください"

        # 修正提案
        echo ""
        log_info "一般的な修正方法:"
        echo "  1. Docker Desktopを起動してください"
        echo "  2. ユーザーをdockerグループに追加: sudo usermod -aG docker \$USER"
        echo "  3. ログアウト・ログインしてグループ変更を反映してください"
        echo "  4. actをインストール: brew install act"
        echo "  5. 必要なネットワークを作成: docker network create mcp-network"
    fi

    return $exit_code
}

# 使用方法の表示
show_usage() {
    echo "使用方法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  --daemon-only          Docker daemon接続のみ確認"
    echo "  --socket-only          Dockerソケットアクセスのみ確認"
    echo "  --container-test-only  コンテナ実行テストのみ実行"
    echo "  --network-only         ネットワーク設定のみ確認"
    echo "  --volumes-only         ボリューム設定のみ確認"
    echo "  --act-only             actバイナリのみ確認"
    echo "  --resources-only       システムリソースのみ確認"
    echo "  --comprehensive        包括的ヘルスチェック実行（デフォルト）"
    echo "  --help                 このヘルプを表示"
    echo ""
}

# メイン処理
main() {
    local mode="comprehensive"

    # コマンドライン引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --daemon-only)
                mode="daemon"
                shift
                ;;
            --socket-only)
                mode="socket"
                shift
                ;;
            --container-test-only)
                mode="container-test"
                shift
                ;;
            --network-only)
                mode="network"
                shift
                ;;
            --volumes-only)
                mode="volumes"
                shift
                ;;
            --act-only)
                mode="act"
                shift
                ;;
            --resources-only)
                mode="resources"
                shift
                ;;
            --comprehensive)
                mode="comprehensive"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    local exit_code=0

    case $mode in
        "daemon")
            check_docker_daemon || exit_code=1
            ;;
        "socket")
            check_docker_socket || exit_code=1
            ;;
        "container-test")
            test_container_execution || exit_code=1
            ;;
        "network")
            check_docker_network || exit_code=1
            ;;
        "volumes")
            check_docker_volumes || exit_code=1
            ;;
        "act")
            check_act_binary || exit_code=1
            ;;
        "resources")
            check_system_resources || exit_code=1
            ;;
        "comprehensive")
            run_comprehensive_health_check || exit_code=1
            ;;
    esac

    exit $exit_code
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
