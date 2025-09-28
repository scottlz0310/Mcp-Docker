#!/bin/bash
# GitHub Actions Simulator - 診断ヘルパースクリプト
#
# 一般的な問題の自動診断と解決提案を行います

set -euo pipefail

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
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

# ヘルプ表示
show_help() {
    cat << EOF
GitHub Actions Simulator - 診断ヘルパースクリプト

使用方法:
    $0 [オプション] [診断タイプ]

診断タイプ:
    all                 全ての診断を実行 (デフォルト)
    docker              Docker関連の問題診断
    ports               ポート競合の診断
    permissions         権限問題の診断
    dependencies        依存関係の診断
    performance         パフォーマンス問題の診断
    network             ネットワーク問題の診断

オプション:
    --fix               自動修復を試行する
    --verbose           詳細な出力を表示
    --help              このヘルプを表示

例:
    $0                          # 全診断を実行
    $0 docker                   # Docker問題のみ診断
    $0 --fix permissions        # 権限問題を診断・修復
    $0 --verbose all            # 詳細出力で全診断

EOF
}

# 設定
DIAGNOSTIC_TYPE="all"
AUTO_FIX=false
VERBOSE=false

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            AUTO_FIX=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        all|docker|ports|permissions|dependencies|performance|network)
            DIAGNOSTIC_TYPE="$1"
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            show_help
            exit 1
            ;;
    esac
done

# 詳細ログ関数
verbose_log() {
    if [[ "$VERBOSE" == "true" ]]; then
        log_info "$1"
    fi
}

# Docker診断
diagnose_docker() {
    log_info "Docker環境を診断中..."

    # Docker インストール確認
    if ! command -v docker &> /dev/null; then
        log_error "Docker が見つかりません"
        echo "解決策:"
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install docker.io"
        echo "  CentOS/RHEL: sudo yum install docker"
        echo "  macOS: brew install docker"
        echo "  または Docker Desktop をインストール: https://www.docker.com/products/docker-desktop"
        return 1
    fi

    verbose_log "Docker コマンドが見つかりました"

    # Docker デーモン確認
    if ! docker info &> /dev/null; then
        log_error "Docker デーモンが起動していません"
        echo "解決策:"
        echo "  sudo systemctl start docker"
        echo "  sudo systemctl enable docker  # 自動起動設定"

        if [[ "$AUTO_FIX" == "true" ]]; then
            log_info "Docker デーモンの起動を試行中..."
            if sudo systemctl start docker 2>/dev/null; then
                log_success "Docker デーモンを起動しました"
            else
                log_error "Docker デーモンの起動に失敗しました"
            fi
        fi
        return 1
    fi

    verbose_log "Docker デーモンが起動しています"

    # Docker 権限確認
    if ! docker ps &> /dev/null; then
        log_warning "Docker コマンドの実行に sudo が必要です"
        echo "解決策:"
        echo "  sudo usermod -aG docker \$USER"
        echo "  その後、ログアウト・ログインしてください"

        if [[ "$AUTO_FIX" == "true" ]]; then
            log_info "ユーザーをdockerグループに追加中..."
            if sudo usermod -aG docker "$USER" 2>/dev/null; then
                log_success "dockerグループに追加しました（再ログインが必要）"
            else
                log_error "dockerグループへの追加に失敗しました"
            fi
        fi
        return 1
    fi

    # Docker Compose 確認
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose が見つかりません"
        echo "解決策:"
        echo "  Docker Compose V2 (推奨): Docker Desktop に含まれています"
        echo "  Docker Compose V1: sudo apt install docker-compose"
        return 1
    fi

    log_success "Docker環境は正常です"
    return 0
}

# ポート競合診断
diagnose_ports() {
    log_info "ポート競合を診断中..."

    local common_ports=(8000 8080 3000 5000 5432 6379)
    local conflicts_found=false

    for port in "${common_ports[@]}"; do
        local process_info=""

        if command -v netstat &> /dev/null; then
            process_info=$(netstat -tlnp 2>/dev/null | grep ":$port " || true)
        elif command -v ss &> /dev/null; then
            process_info=$(ss -tlnp 2>/dev/null | grep ":$port " || true)
        fi

        if [[ -n "$process_info" ]]; then
            log_warning "ポート $port が使用中です"
            echo "  $process_info"
            conflicts_found=true

            if [[ "$AUTO_FIX" == "true" ]]; then
                local pid=$(echo "$process_info" | grep -o 'pid=[0-9]*' | cut -d= -f2 || true)
                if [[ -n "$pid" ]]; then
                    log_info "プロセス $pid の停止を試行中..."
                    if kill "$pid" 2>/dev/null; then
                        log_success "プロセス $pid を停止しました"
                    else
                        log_error "プロセス $pid の停止に失敗しました"
                    fi
                fi
            fi
        else
            verbose_log "ポート $port は利用可能です"
        fi
    done

    if [[ "$conflicts_found" == "false" ]]; then
        log_success "ポート競合は検出されませんでした"
        return 0
    else
        echo "解決策:"
        echo "  1. 使用中のプロセスを停止: sudo kill <PID>"
        echo "  2. 別のポートを使用: docker-compose.override.yml でポート設定変更"
        echo "  3. Docker Composeサービス停止: docker-compose down"
        return 1
    fi
}

# 権限問題診断
diagnose_permissions() {
    log_info "権限問題を診断中..."

    local issues_found=false

    # スクリプト実行権限確認
    local script_files=("scripts/run-actions.sh" "scripts/collect-support-info.sh")
    for script in "${script_files[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ ! -x "$script" ]]; then
                log_warning "$script に実行権限がありません"
                issues_found=true

                if [[ "$AUTO_FIX" == "true" ]]; then
                    log_info "$script に実行権限を付与中..."
                    if chmod +x "$script" 2>/dev/null; then
                        log_success "$script に実行権限を付与しました"
                    else
                        log_error "$script への権限付与に失敗しました"
                    fi
                fi
            else
                verbose_log "$script は実行可能です"
            fi
        fi
    done

    # ディレクトリ書き込み権限確認
    local test_file=".permission_test_$$"
    if ! touch "$test_file" 2>/dev/null; then
        log_warning "現在のディレクトリに書き込み権限がありません"
        issues_found=true
    else
        rm -f "$test_file"
        verbose_log "ディレクトリ書き込み権限は正常です"
    fi

    # Docker権限確認（既にdocker診断で実施済みの場合はスキップ）
    if [[ "$DIAGNOSTIC_TYPE" != "docker" ]] && command -v docker &> /dev/null; then
        if ! docker ps &> /dev/null; then
            log_warning "Docker コマンドの実行権限がありません"
            issues_found=true
        else
            verbose_log "Docker実行権限は正常です"
        fi
    fi

    if [[ "$issues_found" == "false" ]]; then
        log_success "権限問題は検出されませんでした"
        return 0
    else
        echo "解決策:"
        echo "  スクリプト権限: chmod +x scripts/*.sh"
        echo "  Docker権限: sudo usermod -aG docker \$USER"
        echo "  ディレクトリ権限: sudo chown -R \$USER:\$USER ."
        return 1
    fi
}

# 依存関係診断
diagnose_dependencies() {
    log_info "依存関係を診断中..."

    local missing_deps=()

    # 必須依存関係チェック
    local required_commands=("git" "python3")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
            log_error "$cmd が見つかりません"
        else
            verbose_log "$cmd は利用可能です"
        fi
    done

    # 推奨依存関係チェック
    local recommended_commands=("uv" "make")
    for cmd in "${recommended_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_warning "$cmd が見つかりません（推奨）"
        else
            verbose_log "$cmd は利用可能です"
        fi
    done

    # Python バージョンチェック
    if command -v python3 &> /dev/null; then
        if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            log_warning "Python 3.8以上が推奨されます"
            python3 --version
        else
            verbose_log "Python バージョンは要件を満たしています"
        fi
    fi

    # プロジェクトファイル確認
    local required_files=("Makefile" "docker-compose.yml" "pyproject.toml")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "$file が見つかりません"
            missing_deps+=("$file")
        else
            verbose_log "$file が存在します"
        fi
    done

    if [[ ${#missing_deps[@]} -eq 0 ]]; then
        log_success "依存関係は正常です"
        return 0
    else
        echo "解決策:"
        echo "  Git: sudo apt install git"
        echo "  Python3: sudo apt install python3"
        echo "  uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  Make: sudo apt install build-essential"
        echo "  プロジェクトファイル: 正しいディレクトリにいるか確認"
        return 1
    fi
}

# パフォーマンス診断
diagnose_performance() {
    log_info "パフォーマンス問題を診断中..."

    local issues_found=false

    # ディスク容量チェック
    local disk_usage
    disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')

    if [[ "$disk_usage" -gt 90 ]]; then
        log_error "ディスク使用量が危険レベルです: ${disk_usage}%"
        issues_found=true

        if [[ "$AUTO_FIX" == "true" ]]; then
            log_info "Docker システムクリーンアップを実行中..."
            if docker system prune -f &> /dev/null; then
                log_success "Docker システムクリーンアップを実行しました"
            fi
        fi
    elif [[ "$disk_usage" -gt 80 ]]; then
        log_warning "ディスク使用量が高めです: ${disk_usage}%"
        issues_found=true
    else
        verbose_log "ディスク使用量は正常です: ${disk_usage}%"
    fi

    # メモリ使用量チェック
    if command -v free &> /dev/null; then
        local mem_usage
        mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')

        if [[ "$mem_usage" -gt 90 ]]; then
            log_warning "メモリ使用量が高いです: ${mem_usage}%"
            issues_found=true
        else
            verbose_log "メモリ使用量は正常です: ${mem_usage}%"
        fi
    fi

    # Docker イメージサイズチェック
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        local docker_size
        docker_size=$(docker system df --format "table {{.Size}}" | tail -n +2 | head -1 || echo "0B")
        verbose_log "Docker使用容量: $docker_size"
    fi

    if [[ "$issues_found" == "false" ]]; then
        log_success "パフォーマンス問題は検出されませんでした"
        return 0
    else
        echo "解決策:"
        echo "  ディスク: docker system prune -f"
        echo "  ログ: find . -name '*.log' -size +100M -delete"
        echo "  キャッシュ: rm -rf .mypy_cache .pytest_cache"
        return 1
    fi
}

# ネットワーク診断
diagnose_network() {
    log_info "ネットワーク問題を診断中..."

    local issues_found=false

    # インターネット接続確認
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        log_error "インターネット接続に問題があります"
        issues_found=true
    else
        verbose_log "インターネット接続は正常です"
    fi

    # DNS解決確認
    if ! nslookup github.com &> /dev/null; then
        log_warning "DNS解決に問題がある可能性があります"
        issues_found=true
    else
        verbose_log "DNS解決は正常です"
    fi

    # Docker ネットワーク確認
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        if ! docker network ls &> /dev/null; then
            log_warning "Docker ネットワークに問題があります"
            issues_found=true
        else
            verbose_log "Docker ネットワークは正常です"
        fi
    fi

    if [[ "$issues_found" == "false" ]]; then
        log_success "ネットワーク問題は検出されませんでした"
        return 0
    else
        echo "解決策:"
        echo "  インターネット: ネットワーク接続を確認"
        echo "  DNS: /etc/resolv.conf を確認"
        echo "  Docker: docker network prune"
        return 1
    fi
}

# 全診断実行
run_all_diagnostics() {
    log_info "全ての診断を実行中..."

    local total_issues=0

    echo "=== Docker診断 ==="
    if ! diagnose_docker; then
        ((total_issues++))
    fi
    echo ""

    echo "=== 依存関係診断 ==="
    if ! diagnose_dependencies; then
        ((total_issues++))
    fi
    echo ""

    echo "=== 権限診断 ==="
    if ! diagnose_permissions; then
        ((total_issues++))
    fi
    echo ""

    echo "=== ポート競合診断 ==="
    if ! diagnose_ports; then
        ((total_issues++))
    fi
    echo ""

    echo "=== パフォーマンス診断 ==="
    if ! diagnose_performance; then
        ((total_issues++))
    fi
    echo ""

    echo "=== ネットワーク診断 ==="
    if ! diagnose_network; then
        ((total_issues++))
    fi
    echo ""

    # 結果サマリー
    echo "=== 診断結果サマリー ==="
    if [[ "$total_issues" -eq 0 ]]; then
        log_success "全ての診断をパスしました！"
        echo "GitHub Actions Simulator は正常に動作する準備ができています。"
    else
        log_warning "$total_issues 個の問題が検出されました"
        echo ""
        echo "次のステップ:"
        echo "  1. 上記の解決策を実行してください"
        echo "  2. 問題が解決しない場合は GitHub Issues で報告してください"
        echo "  3. サポート情報収集: ./scripts/collect-support-info.sh"
    fi

    return "$total_issues"
}

# メイン処理
main() {
    log_info "GitHub Actions Simulator 診断ヘルパーを開始します"

    if [[ "$AUTO_FIX" == "true" ]]; then
        log_info "自動修復モードが有効です"
    fi

    case "$DIAGNOSTIC_TYPE" in
        "docker")
            diagnose_docker
            ;;
        "ports")
            diagnose_ports
            ;;
        "permissions")
            diagnose_permissions
            ;;
        "dependencies")
            diagnose_dependencies
            ;;
        "performance")
            diagnose_performance
            ;;
        "network")
            diagnose_network
            ;;
        "all")
            run_all_diagnostics
            ;;
        *)
            log_error "不明な診断タイプ: $DIAGNOSTIC_TYPE"
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
