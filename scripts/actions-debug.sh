#!/usr/bin/env bash
# Actions Simulator デバッグ用ユーティリティスクリプト

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

info() {
    printf '🔍 %s\n' "$*"
}

error() {
    printf '❌ %s\n' "$*" >&2
}

success() {
    printf '✅ %s\n' "$*"
}

# ヘルプ表示
show_help() {
    cat <<EOF
Actions Simulator デバッグユーティリティ

使用方法:
  $0 [コマンド] [オプション]

コマンド:
  status      - サーバーとコンテナの状態を確認
  logs        - ログファイルを表示
  test        - サーバーのテスト実行
  shell       - デバッグシェルに接続
  restart     - サーバーを再起動
  clean       - ログとキャッシュをクリア
  help        - このヘルプを表示

例:
  $0 status
  $0 logs --follow
  $0 test --workflow .github/workflows/ci.yml
  $0 shell
EOF
}

# サーバー状態確認
check_status() {
    info "Actions Simulator 状態確認"
    echo ""

    # Docker コンテナ状態
    info "Docker コンテナ状態:"
    if docker compose --profile debug ps actions-server actions-shell 2>/dev/null | grep -q "Up"; then
        docker compose --profile debug ps actions-server actions-shell
        success "デバッグコンテナが起動中です"
    else
        echo "  デバッグコンテナは停止中です"
    fi
    echo ""

    # HTTPサーバー状態
    info "HTTPサーバー状態:"
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        success "HTTPサーバーは正常に動作中です (http://localhost:8000)"
        echo "  ヘルスチェック結果:"
        curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
    else
        echo "  HTTPサーバーは停止中です"
    fi
    echo ""

    # ログファイル状態
    info "ログファイル:"
    if [ -d "logs" ]; then
        find logs/ -type f -exec ls -la {} \; | head -10
        log_count=$(find logs/ -type f | wc -l)
        if [ "$log_count" -gt 10 ]; then
            echo "  ... ($log_count ファイル)"
        fi
    else
        echo "  ログディレクトリが見つかりません"
    fi
    echo ""

    # 出力ファイル状態
    info "出力ファイル:"
    if [ -d "output/actions" ]; then
        find output/actions/ -type f -exec ls -la {} \; | head -10
        output_count=$(find output/actions/ -type f | wc -l)
        if [ "$output_count" -gt 10 ]; then
            echo "  ... ($output_count ファイル)"
        fi
    else
        echo "  出力ディレクトリが見つかりません"
    fi
}

# ログ表示
show_logs() {
    local follow=false
    local service="actions-server"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --follow|-f)
                follow=true
                shift
                ;;
            --service|-s)
                service="$2"
                shift 2
                ;;
            *)
                echo "不明なオプション: $1"
                exit 1
                ;;
        esac
    done

    info "ログ表示: $service"

    if [ "$follow" = true ]; then
        docker compose --profile debug logs -f "$service"
    else
        docker compose --profile debug logs "$service"
    fi
}

# サーバーテスト
test_server() {
    local workflow=""
    local job=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --workflow|-w)
                workflow="$2"
                shift 2
                ;;
            --job|-j)
                job="$2"
                shift 2
                ;;
            *)
                echo "不明なオプション: $1"
                exit 1
                ;;
        esac
    done

    info "サーバーテスト実行"

    # ヘルスチェック
    info "1. ヘルスチェック"
    if curl -s http://localhost:8000/health | jq . 2>/dev/null; then
        success "ヘルスチェック成功"
    else
        error "ヘルスチェック失敗"
        return 1
    fi
    echo ""

    # ワークフロー一覧
    info "2. ワークフロー一覧"
    if curl -s http://localhost:8000/workflows | jq . 2>/dev/null; then
        success "ワークフロー一覧取得成功"
    else
        error "ワークフロー一覧取得失敗"
        return 1
    fi
    echo ""

    # ワークフロー実行テスト（指定された場合）
    if [ -n "$workflow" ]; then
        info "3. ワークフロー実行テスト: $workflow"
        local payload="{\"workflow_file\": \"$workflow\""
        if [ -n "$job" ]; then
            payload="$payload, \"job_name\": \"$job\""
        fi
        payload="$payload, \"dry_run\": true}"

        if curl -s -X POST -H "Content-Type: application/json" -d "$payload" http://localhost:8000/simulate | jq . 2>/dev/null; then
            success "ワークフロー実行テスト成功"
        else
            error "ワークフロー実行テスト失敗"
            return 1
        fi
    fi

    success "全てのテストが成功しました"
}

# デバッグシェル接続
connect_shell() {
    info "デバッグシェルに接続中..."

    # 既存のコンテナがあるかチェック
    if docker compose --profile debug ps actions-server | grep -q "Up"; then
        info "既存のサーバーコンテナに接続"
        docker compose --profile debug exec actions-server bash
    else
        info "新しいシェルコンテナを起動"
        make actions-shell
    fi
}

# サーバー再起動
restart_server() {
    info "サーバーを再起動中..."
    make actions-server-restart
    success "サーバーが再起動されました"
}

# クリーンアップ
clean_up() {
    info "ログとキャッシュをクリア中..."

    # ログファイルクリア
    if [ -d "logs" ]; then
        rm -rf logs/*
        success "ログファイルをクリアしました"
    fi

    # 出力ファイルクリア
    if [ -d "output/actions" ]; then
        rm -rf output/actions/*
        success "出力ファイルをクリアしました"
    fi

    # Dockerキャッシュクリア
    docker system prune -f >/dev/null 2>&1 || true
    success "Dockerキャッシュをクリアしました"

    success "クリーンアップが完了しました"
}

# メイン処理
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    case "$1" in
        status)
            shift
            check_status "$@"
            ;;
        logs)
            shift
            show_logs "$@"
            ;;
        test)
            shift
            test_server "$@"
            ;;
        shell)
            shift
            connect_shell "$@"
            ;;
        restart)
            shift
            restart_server "$@"
            ;;
        clean)
            shift
            clean_up "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "不明なコマンド: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
