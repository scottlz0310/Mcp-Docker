#!/bin/bash
# コンテナ起動検証スクリプト
# GitHub Actions Simulatorコンテナの正常起動を検証します

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

# コンテナの存在確認
check_container_exists() {
    local container_name="$1"

    if docker ps -a --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        return 0
    else
        return 1
    fi
}

# コンテナの実行状態確認
check_container_running() {
    local container_name="$1"

    if docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        return 0
    else
        return 1
    fi
}

# コンテナのヘルスチェック状態確認
check_container_health() {
    local container_name="$1"

    local health_status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")

    case "$health_status" in
        "healthy")
            return 0
            ;;
        "unhealthy")
            return 1
            ;;
        "starting")
            return 2
            ;;
        "no-healthcheck")
            return 3
            ;;
        *)
            return 4
            ;;
    esac
}

# Docker統合ヘルスチェック実行
run_docker_integration_check() {
    log_info "Docker統合ヘルスチェックを実行中..."

    if docker exec mcp-actions-simulator python -c "
import sys
sys.path.append('/app')
from services.actions.docker_integration_checker import DockerIntegrationChecker
checker = DockerIntegrationChecker()
results = checker.run_comprehensive_docker_check()
if results['overall_success']:
    print('Docker統合チェック: 成功')
    exit(0)
else:
    print(f'Docker統合チェック: 失敗 - {results[\"summary\"]}')
    exit(1)
"; then
        log_success "Docker統合ヘルスチェックが成功しました"
        return 0
    else
        log_error "Docker統合ヘルスチェックが失敗しました"
        return 1
    fi
}

# actバイナリの動作確認
verify_act_functionality() {
    log_info "actバイナリの動作を確認中..."

    if docker exec mcp-actions-simulator act --version > /dev/null 2>&1; then
        local act_version
        act_version=$(docker exec mcp-actions-simulator act --version)
        log_success "actバイナリは正常に動作しています: $act_version"
        return 0
    else
        log_error "actバイナリが正常に動作していません"
        return 1
    fi
}

# Dockerソケットアクセス確認
verify_docker_socket_access() {
    log_info "Dockerソケットアクセスを確認中..."

    if docker exec mcp-actions-simulator docker version > /dev/null 2>&1; then
        log_success "Dockerソケットアクセスは正常です"
        return 0
    else
        log_error "Dockerソケットにアクセスできません"
        return 1
    fi
}

# ボリュームマウント確認
verify_volume_mounts() {
    log_info "ボリュームマウントを確認中..."

    local volumes_ok=true

    # 必要なディレクトリの存在確認
    local required_dirs=(
        "/app/.github"
        "/app/output"
        "/app/logs"
        "/opt/act/cache"
        "/github/workspace"
    )

    for dir in "${required_dirs[@]}"; do
        if docker exec mcp-actions-simulator test -d "$dir"; then
            log_info "ディレクトリ確認OK: $dir"
        else
            log_error "ディレクトリが見つかりません: $dir"
            volumes_ok=false
        fi
    done

    # Dockerソケットファイルの確認
    if docker exec mcp-actions-simulator test -S /var/run/docker.sock; then
        log_info "Dockerソケット確認OK: /var/run/docker.sock"
    else
        log_error "Dockerソケットが見つかりません: /var/run/docker.sock"
        volumes_ok=false
    fi

    if $volumes_ok; then
        log_success "全てのボリュームマウントが正常です"
        return 0
    else
        log_error "一部のボリュームマウントに問題があります"
        return 1
    fi
}

# 環境変数確認
verify_environment_variables() {
    log_info "環境変数を確認中..."

    local env_vars_ok=true

    # 必要な環境変数のリスト
    local required_env_vars=(
        "DOCKER_HOST"
        "ACT_CACHE_DIR"
        "ACTIONS_SIMULATOR_ENGINE"
        "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"
        "PYTHONUNBUFFERED"
    )

    for var in "${required_env_vars[@]}"; do
        if docker exec mcp-actions-simulator printenv "$var" > /dev/null 2>&1; then
            local value
            value=$(docker exec mcp-actions-simulator printenv "$var")
            log_info "環境変数確認OK: $var=$value"
        else
            log_error "環境変数が設定されていません: $var"
            env_vars_ok=false
        fi
    done

    if $env_vars_ok; then
        log_success "全ての環境変数が正常に設定されています"
        return 0
    else
        log_error "一部の環境変数に問題があります"
        return 1
    fi
}

# コンテナログの確認
check_container_logs() {
    local container_name="$1"

    log_info "コンテナログを確認中: $container_name"

    # 最新のログを取得（最後の20行）
    local logs
    logs=$(docker logs --tail 20 "$container_name" 2>&1)

    # エラーメッセージの検出
    if echo "$logs" | grep -i "error\|exception\|failed\|fatal" > /dev/null; then
        log_warning "コンテナログにエラーメッセージが検出されました:"
        echo "$logs" | grep -i "error\|exception\|failed\|fatal" | head -5
        return 1
    else
        log_success "コンテナログに重大なエラーは検出されませんでした"
        return 0
    fi
}

# メイン検証処理
verify_actions_simulator() {
    local container_name="mcp-actions-simulator"
    local exit_code=0

    log_info "GitHub Actions Simulatorコンテナの起動検証を開始します"
    echo "=================================================================="

    # 1. コンテナの存在確認
    log_info "1. コンテナの存在確認"
    if check_container_exists "$container_name"; then
        log_success "コンテナが存在します: $container_name"
    else
        log_error "コンテナが存在しません: $container_name"
        log_info "docker-compose --profile tools up -d actions-simulator を実行してください"
        return 1
    fi

    # 2. コンテナの実行状態確認
    log_info "2. コンテナの実行状態確認"
    if check_container_running "$container_name"; then
        log_success "コンテナが実行中です: $container_name"
    else
        log_error "コンテナが実行されていません: $container_name"
        log_info "docker-compose --profile tools start actions-simulator を実行してください"
        return 1
    fi

    # 3. ヘルスチェック状態確認
    log_info "3. ヘルスチェック状態確認"
    check_container_health "$container_name"
    local health_result=$?

    case $health_result in
        0)
            log_success "コンテナのヘルスチェックが正常です"
            ;;
        1)
            log_error "コンテナのヘルスチェックが失敗しています"
            exit_code=1
            ;;
        2)
            log_warning "コンテナのヘルスチェックが開始中です（しばらく待ってから再実行してください）"
            exit_code=1
            ;;
        3)
            log_warning "コンテナにヘルスチェックが設定されていません"
            ;;
        *)
            log_error "ヘルスチェック状態を取得できませんでした"
            exit_code=1
            ;;
    esac

    # 4. ボリュームマウント確認
    log_info "4. ボリュームマウント確認"
    verify_volume_mounts || exit_code=1

    # 5. 環境変数確認
    log_info "5. 環境変数確認"
    verify_environment_variables || exit_code=1

    # 6. Dockerソケットアクセス確認
    log_info "6. Dockerソケットアクセス確認"
    verify_docker_socket_access || exit_code=1

    # 7. actバイナリ動作確認
    log_info "7. actバイナリ動作確認"
    verify_act_functionality || exit_code=1

    # 8. Docker統合ヘルスチェック
    log_info "8. Docker統合ヘルスチェック"
    run_docker_integration_check || exit_code=1

    # 9. コンテナログ確認
    log_info "9. コンテナログ確認"
    check_container_logs "$container_name" || exit_code=1

    echo "=================================================================="

    if [[ $exit_code -eq 0 ]]; then
        log_success "GitHub Actions Simulatorコンテナの起動検証が完了しました！"
        log_info "コンテナは正常に動作しています"
    else
        log_error "GitHub Actions Simulatorコンテナの起動検証で問題が発生しました"
        log_info "上記のエラーメッセージを確認して問題を修正してください"
    fi

    return $exit_code
}

# Docker Health Checkサービスの検証
verify_docker_health_check() {
    local container_name="mcp-docker-health-check"

    log_info "Docker Health Checkサービスの検証を開始します"

    if check_container_exists "$container_name"; then
        log_success "Docker Health Checkコンテナが存在します"

        # コンテナの終了コードを確認
        local exit_code
        exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container_name")

        if [[ $exit_code -eq 0 ]]; then
            log_success "Docker Health Checkが正常に完了しました"
            return 0
        else
            log_error "Docker Health Checkが失敗しました (終了コード: $exit_code)"
            log_info "ログを確認してください: docker logs $container_name"
            return 1
        fi
    else
        log_warning "Docker Health Checkコンテナが見つかりません"
        log_info "docker-compose --profile tools up docker-health-check を実行してください"
        return 1
    fi
}

# 使用方法の表示
show_usage() {
    echo "使用方法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  --actions-simulator    Actions Simulatorコンテナのみ検証"
    echo "  --docker-health-check  Docker Health Checkサービスのみ検証"
    echo "  --all                  全てのサービスを検証（デフォルト）"
    echo "  --help                 このヘルプを表示"
    echo ""
}

# メイン処理
main() {
    local mode="all"

    # コマンドライン引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --actions-simulator)
                mode="actions-simulator"
                shift
                ;;
            --docker-health-check)
                mode="docker-health-check"
                shift
                ;;
            --all)
                mode="all"
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
        "actions-simulator")
            verify_actions_simulator || exit_code=1
            ;;
        "docker-health-check")
            verify_docker_health_check || exit_code=1
            ;;
        "all")
            verify_docker_health_check || exit_code=1
            verify_actions_simulator || exit_code=1
            ;;
    esac

    exit $exit_code
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
