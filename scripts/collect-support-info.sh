#!/bin/bash
# GitHub Actions Simulator - サポート情報自動収集スクリプト
#
# このスクリプトは問題報告時に必要な診断情報を自動的に収集します。

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

# 設定
OUTPUT_FILE="support_info.txt"
INCLUDE_LOGS=true
INCLUDE_DOCKER_INFO=true
VERBOSE=false
INCLUDE_NETWORK_INFO=false
INCLUDE_PERFORMANCE_INFO=false
AUTO_TROUBLESHOOT=false

# ヘルプ表示
show_help() {
    cat << EOF
GitHub Actions Simulator - サポート情報収集スクリプト

使用方法:
    $0 [オプション]

オプション:
    --output FILE       出力ファイル名 (デフォルト: support_info.txt)
    --no-logs          ログ情報を含めない
    --no-docker        Docker情報を含めない
    --verbose          詳細な情報を含める
    --network          ネットワーク情報を含める
    --performance      パフォーマンス情報を含める
    --auto-troubleshoot 自動トラブルシューティングを実行
    --help             このヘルプを表示

例:
    $0                              # 標準情報収集
    $0 --output debug_info.txt      # カスタムファイル名
    $0 --verbose --no-docker        # 詳細情報、Docker情報なし
    $0 --auto-troubleshoot          # 自動診断と問題解決提案

EOF
}

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --no-logs)
            INCLUDE_LOGS=false
            shift
            ;;
        --no-docker)
            INCLUDE_DOCKER_INFO=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --network)
            INCLUDE_NETWORK_INFO=true
            shift
            ;;
        --performance)
            INCLUDE_PERFORMANCE_INFO=true
            shift
            ;;
        --auto-troubleshoot)
            AUTO_TROUBLESHOOT=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "不明なオプション: $1"
            show_help
            exit 1
            ;;
    esac
done

# 安全なコマンド実行
safe_exec() {
    local cmd="$1"
    local description="$2"

    echo "=== $description ===" >> "$OUTPUT_FILE"
    if eval "$cmd" >> "$OUTPUT_FILE" 2>&1; then
        echo "" >> "$OUTPUT_FILE"
        return 0
    else
        echo "エラー: コマンド実行に失敗しました" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        return 1
    fi
}

# 基本システム情報収集
collect_system_info() {
    log_info "システム情報を収集中..."

    {
        echo "GitHub Actions Simulator - サポート情報"
        echo "収集日時: $(date)"
        echo "収集スクリプト: $0"
        echo ""
    } > "$OUTPUT_FILE"

    # システム基本情報
    safe_exec "uname -a" "システム情報"
    safe_exec "whoami" "ユーザー情報"
    safe_exec "pwd" "現在のディレクトリ"

    # 環境変数（重要なもののみ）
    {
        echo "=== 環境変数 ==="
        echo "PATH: $PATH"
        echo "HOME: $HOME"
        echo "SHELL: ${SHELL:-未設定}"
        echo "LANG: ${LANG:-未設定}"
        echo ""
    } >> "$OUTPUT_FILE"
}

# バージョン情報収集
collect_version_info() {
    log_info "バージョン情報を収集中..."

    # GitHub Actions Simulator バージョン
    if command -v make &> /dev/null && [[ -f "Makefile" ]]; then
        safe_exec "make version" "GitHub Actions Simulator バージョン"
    else
        echo "=== GitHub Actions Simulator バージョン ===" >> "$OUTPUT_FILE"
        echo "make コマンドまたは Makefile が見つかりません" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi

    # Python バージョン
    if command -v python3 &> /dev/null; then
        safe_exec "python3 --version" "Python バージョン"
    fi

    if command -v python &> /dev/null; then
        safe_exec "python --version" "Python バージョン (python)"
    fi

    # uv バージョン
    if command -v uv &> /dev/null; then
        safe_exec "uv --version" "uv バージョン"
    else
        echo "=== uv バージョン ===" >> "$OUTPUT_FILE"
        echo "uv が見つかりません" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi

    # Git バージョン
    if command -v git &> /dev/null; then
        safe_exec "git --version" "Git バージョン"
        if git rev-parse --git-dir > /dev/null 2>&1; then
            safe_exec "git rev-parse HEAD" "現在のコミット"
            safe_exec "git status --porcelain" "Git ステータス"
        fi
    fi
}

# Docker情報収集
collect_docker_info() {
    if [[ "$INCLUDE_DOCKER_INFO" == "false" ]]; then
        log_info "Docker情報をスキップします"
        return 0
    fi

    log_info "Docker情報を収集中..."

    # Docker バージョン
    if command -v docker &> /dev/null; then
        safe_exec "docker --version" "Docker バージョン"
        safe_exec "docker system info" "Docker システム情報"
        safe_exec "docker ps -a" "Docker コンテナ一覧"
        safe_exec "docker images" "Docker イメージ一覧"
    else
        echo "=== Docker 情報 ===" >> "$OUTPUT_FILE"
        echo "Docker が見つかりません" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi

    # Docker Compose バージョン
    if command -v docker-compose &> /dev/null; then
        safe_exec "docker-compose --version" "Docker Compose バージョン"
    elif docker compose version &> /dev/null; then
        safe_exec "docker compose version" "Docker Compose バージョン (プラグイン)"
    else
        echo "=== Docker Compose バージョン ===" >> "$OUTPUT_FILE"
        echo "Docker Compose が見つかりません" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
}

# 診断情報収集
collect_diagnostic_info() {
    log_info "診断情報を収集中..."

    # 依存関係チェック
    if [[ -f "scripts/run-actions.sh" ]]; then
        safe_exec "./scripts/run-actions.sh --check-deps" "依存関係チェック"

        # 拡張診断（利用可能な場合）
        if ./scripts/run-actions.sh --help 2>&1 | grep -q "check-deps-extended"; then
            safe_exec "./scripts/run-actions.sh --check-deps-extended" "拡張依存関係チェック"
        fi
    else
        echo "=== 依存関係チェック ===" >> "$OUTPUT_FILE"
        echo "scripts/run-actions.sh が見つかりません" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi

    # プロジェクト構造
    if [[ "$VERBOSE" == "true" ]]; then
        safe_exec "find . -maxdepth 2 -type f -name '*.md' -o -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name 'Makefile' -o -name 'Dockerfile*' | head -20" "プロジェクトファイル構造"
    fi
}

# ログ情報収集
collect_log_info() {
    if [[ "$INCLUDE_LOGS" == "false" ]]; then
        log_info "ログ情報をスキップします"
        return 0
    fi

    log_info "ログ情報を収集中..."

    # Docker Compose ログ
    if [[ -f "docker-compose.yml" ]] && command -v docker-compose &> /dev/null; then
        safe_exec "docker-compose logs --tail=50" "Docker Compose ログ (最新50行)"
    fi

    # プロジェクト固有のログファイル
    local log_files=(
        "logs/error.log"
        "logs/diagnostic.log"
        "*.log"
    )

    for pattern in "${log_files[@]}"; do
        if ls "$pattern" &> /dev/null; then
            for file in $pattern; do
                if [[ -f "$file" ]]; then
                    safe_exec "tail -20 '$file'" "ログファイル: $file (最新20行)"
                fi
            done
        fi
    done
}

# 設定ファイル情報収集
collect_config_info() {
    log_info "設定ファイル情報を収集中..."

    # 重要な設定ファイルの存在確認
    local config_files=(
        ".env"
        ".env.example"
        "docker-compose.yml"
        "docker-compose.override.yml"
        "pyproject.toml"
        "Makefile"
        ".pre-commit-config.yaml"
    )

    echo "=== 設定ファイル存在確認 ===" >> "$OUTPUT_FILE"
    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "✓ $file (存在)" >> "$OUTPUT_FILE"
            if [[ "$VERBOSE" == "true" && "$file" != ".env" ]]; then
                echo "  サイズ: $(wc -l < "$file") 行" >> "$OUTPUT_FILE"
            fi
        else
            echo "✗ $file (不存在)" >> "$OUTPUT_FILE"
        fi
    done
    echo "" >> "$OUTPUT_FILE"

    # pyproject.toml の内容（バージョン情報のみ）
    if [[ -f "pyproject.toml" ]]; then
        echo "=== pyproject.toml バージョン情報 ===" >> "$OUTPUT_FILE"
        grep -E "^(name|version|description)" pyproject.toml >> "$OUTPUT_FILE" 2>/dev/null || echo "バージョン情報の抽出に失敗" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
}

# 追加の詳細情報収集
collect_detailed_info() {
    if [[ "$VERBOSE" == "false" ]]; then
        return 0
    fi

    log_info "詳細情報を収集中..."

    # ディスク使用量
    safe_exec "df -h ." "ディスク使用量"

    # メモリ使用量
    if command -v free &> /dev/null; then
        safe_exec "free -h" "メモリ使用量"
    fi

    # プロセス情報
    safe_exec "ps aux | grep -E '(docker|python|act)' | grep -v grep" "関連プロセス"

    # ネットワーク情報
    if command -v netstat &> /dev/null; then
        safe_exec "netstat -tlnp | grep -E ':(8000|8080|3000)'" "使用中のポート"
    fi
}

# ネットワーク情報収集
collect_network_info() {
    if [[ "$INCLUDE_NETWORK_INFO" == "false" ]]; then
        return 0
    fi

    log_info "ネットワーク情報を収集中..."

    # ポート使用状況
    if command -v netstat &> /dev/null; then
        safe_exec "netstat -tlnp | grep -E ':(8000|8080|3000|5000)'" "使用中のポート"
    elif command -v ss &> /dev/null; then
        safe_exec "ss -tlnp | grep -E ':(8000|8080|3000|5000)'" "使用中のポート (ss)"
    fi

    # Docker ネットワーク
    if command -v docker &> /dev/null; then
        safe_exec "docker network ls" "Docker ネットワーク一覧"
        safe_exec "docker network inspect bridge" "Docker bridge ネットワーク詳細"
    fi

    # DNS設定
    if [[ -f "/etc/resolv.conf" ]]; then
        safe_exec "cat /etc/resolv.conf" "DNS設定"
    fi
}

# パフォーマンス情報収集
collect_performance_info() {
    if [[ "$INCLUDE_PERFORMANCE_INFO" == "false" ]]; then
        return 0
    fi

    log_info "パフォーマンス情報を収集中..."

    # CPU情報
    if [[ -f "/proc/cpuinfo" ]]; then
        safe_exec "grep -E '^(processor|model name|cpu cores)' /proc/cpuinfo | head -10" "CPU情報"
    fi

    # メモリ使用量
    if command -v free &> /dev/null; then
        safe_exec "free -h" "メモリ使用量"
    fi

    # ディスク使用量
    safe_exec "df -h ." "ディスク使用量"

    # Docker統計情報
    if command -v docker &> /dev/null; then
        safe_exec "docker system df" "Docker ディスク使用量"
        if docker ps -q | head -1 > /dev/null; then
            safe_exec "docker stats --no-stream" "Docker コンテナ統計"
        fi
    fi

    # 負荷平均
    if [[ -f "/proc/loadavg" ]]; then
        safe_exec "cat /proc/loadavg" "システム負荷"
    fi
}

# 自動トラブルシューティング
auto_troubleshoot() {
    if [[ "$AUTO_TROUBLESHOOT" == "false" ]]; then
        return 0
    fi

    log_info "自動トラブルシューティングを実行中..."

    {
        echo "=== 自動トラブルシューティング結果 ==="
        echo "実行日時: $(date)"
        echo ""
    } >> "$OUTPUT_FILE"

    # Docker関連の問題チェック
    check_docker_issues

    # ポート競合チェック
    check_port_conflicts

    # 権限問題チェック
    check_permission_issues

    # ディスク容量チェック
    check_disk_space

    # 依存関係チェック
    check_dependencies_detailed

    echo "" >> "$OUTPUT_FILE"
}

# Docker問題チェック
check_docker_issues() {
    echo "--- Docker問題チェック ---" >> "$OUTPUT_FILE"

    if ! command -v docker &> /dev/null; then
        echo "❌ Docker が見つかりません" >> "$OUTPUT_FILE"
        echo "💡 解決策: Docker をインストールしてください" >> "$OUTPUT_FILE"
        echo "   Ubuntu: sudo apt install docker.io" >> "$OUTPUT_FILE"
        echo "   macOS: brew install docker" >> "$OUTPUT_FILE"
        return
    fi

    if ! docker info &> /dev/null; then
        echo "❌ Docker デーモンが起動していません" >> "$OUTPUT_FILE"
        echo "💡 解決策: Docker デーモンを起動してください" >> "$OUTPUT_FILE"
        echo "   sudo systemctl start docker" >> "$OUTPUT_FILE"
        return
    fi

    echo "✅ Docker は正常に動作しています" >> "$OUTPUT_FILE"

    # Docker Compose チェック
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "❌ Docker Compose が見つかりません" >> "$OUTPUT_FILE"
        echo "💡 解決策: Docker Compose をインストールしてください" >> "$OUTPUT_FILE"
    else
        echo "✅ Docker Compose は利用可能です" >> "$OUTPUT_FILE"
    fi
}

# ポート競合チェック
check_port_conflicts() {
    echo "--- ポート競合チェック ---" >> "$OUTPUT_FILE"

    local common_ports=(8000 8080 3000 5000)
    local conflicts_found=false

    for port in "${common_ports[@]}"; do
        if command -v netstat &> /dev/null; then
            if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
                echo "⚠️  ポート $port が使用中です" >> "$OUTPUT_FILE"
                netstat -tlnp 2>/dev/null | grep ":$port " >> "$OUTPUT_FILE"
                conflicts_found=true
            fi
        elif command -v ss &> /dev/null; then
            if ss -tlnp 2>/dev/null | grep -q ":$port "; then
                echo "⚠️  ポート $port が使用中です" >> "$OUTPUT_FILE"
                ss -tlnp 2>/dev/null | grep ":$port " >> "$OUTPUT_FILE"
                conflicts_found=true
            fi
        fi
    done

    if [[ "$conflicts_found" == "true" ]]; then
        echo "💡 解決策: 使用中のプロセスを停止するか、別のポートを使用してください" >> "$OUTPUT_FILE"
        echo "   プロセス停止: sudo kill <PID>" >> "$OUTPUT_FILE"
        echo "   ポート変更: docker-compose.override.yml でポート設定を変更" >> "$OUTPUT_FILE"
    else
        echo "✅ 一般的なポートに競合はありません" >> "$OUTPUT_FILE"
    fi
}

# 権限問題チェック
check_permission_issues() {
    echo "--- 権限問題チェック ---" >> "$OUTPUT_FILE"

    # Docker権限チェック
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            echo "✅ Docker コマンドの実行権限があります" >> "$OUTPUT_FILE"
        else
            echo "❌ Docker コマンドの実行権限がありません" >> "$OUTPUT_FILE"
            echo "💡 解決策: ユーザーをdockerグループに追加してください" >> "$OUTPUT_FILE"
            echo "   sudo usermod -aG docker \$USER" >> "$OUTPUT_FILE"
            echo "   その後、ログアウト・ログインしてください" >> "$OUTPUT_FILE"
        fi
    fi

    # ファイル権限チェック
    local script_files=("scripts/run-actions.sh" "scripts/collect-support-info.sh")
    for script in "${script_files[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ -x "$script" ]]; then
                echo "✅ $script は実行可能です" >> "$OUTPUT_FILE"
            else
                echo "❌ $script に実行権限がありません" >> "$OUTPUT_FILE"
                echo "💡 解決策: chmod +x $script" >> "$OUTPUT_FILE"
            fi
        fi
    done
}

# ディスク容量チェック
check_disk_space() {
    echo "--- ディスク容量チェック ---" >> "$OUTPUT_FILE"

    local current_usage
    current_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')

    if [[ "$current_usage" -gt 90 ]]; then
        echo "❌ ディスク使用量が高すぎます: ${current_usage}%" >> "$OUTPUT_FILE"
        echo "💡 解決策: 不要なファイルを削除してください" >> "$OUTPUT_FILE"
        echo "   Docker: docker system prune -f" >> "$OUTPUT_FILE"
        echo "   ログ: find . -name '*.log' -size +100M -delete" >> "$OUTPUT_FILE"
    elif [[ "$current_usage" -gt 80 ]]; then
        echo "⚠️  ディスク使用量が高めです: ${current_usage}%" >> "$OUTPUT_FILE"
        echo "💡 推奨: 定期的なクリーンアップを実行してください" >> "$OUTPUT_FILE"
    else
        echo "✅ ディスク容量は十分です: ${current_usage}%" >> "$OUTPUT_FILE"
    fi
}

# 詳細依存関係チェック
check_dependencies_detailed() {
    echo "--- 詳細依存関係チェック ---" >> "$OUTPUT_FILE"

    # Python チェック
    if command -v python3 &> /dev/null; then
        local python_version
        python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo "✅ Python: $python_version" >> "$OUTPUT_FILE"

        # Python バージョンチェック
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            echo "✅ Python バージョンは要件を満たしています" >> "$OUTPUT_FILE"
        else
            echo "⚠️  Python 3.8以上が推奨されます" >> "$OUTPUT_FILE"
        fi
    else
        echo "❌ Python3 が見つかりません" >> "$OUTPUT_FILE"
        echo "💡 解決策: Python3 をインストールしてください" >> "$OUTPUT_FILE"
    fi

    # uv チェック
    if command -v uv &> /dev/null; then
        local uv_version
        uv_version=$(uv --version 2>&1)
        echo "✅ uv: $uv_version" >> "$OUTPUT_FILE"
    else
        echo "⚠️  uv が見つかりません（pip で代替可能）" >> "$OUTPUT_FILE"
        echo "💡 推奨: uv をインストールしてください" >> "$OUTPUT_FILE"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh" >> "$OUTPUT_FILE"
    fi

    # Git チェック
    if command -v git &> /dev/null; then
        local git_version
        git_version=$(git --version 2>&1)
        echo "✅ Git: $git_version" >> "$OUTPUT_FILE"
    else
        echo "❌ Git が見つかりません" >> "$OUTPUT_FILE"
        echo "💡 解決策: Git をインストールしてください" >> "$OUTPUT_FILE"
    fi

    # プロジェクト固有ファイルチェック
    local required_files=("Makefile" "docker-compose.yml" "pyproject.toml")
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "✅ $file が存在します" >> "$OUTPUT_FILE"
        else
            echo "❌ $file が見つかりません" >> "$OUTPUT_FILE"
            echo "💡 確認: 正しいディレクトリにいるか確認してください" >> "$OUTPUT_FILE"
        fi
    done
}

# メイン処理
main() {
    log_info "GitHub Actions Simulator サポート情報収集を開始します"
    log_info "出力ファイル: $OUTPUT_FILE"

    # 既存ファイルのバックアップ
    if [[ -f "$OUTPUT_FILE" ]]; then
        cp "$OUTPUT_FILE" "${OUTPUT_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "既存ファイルをバックアップしました"
    fi

    # 各種情報を収集
    collect_system_info
    collect_version_info
    collect_docker_info
    collect_diagnostic_info
    collect_config_info
    collect_log_info
    collect_detailed_info
    collect_network_info
    collect_performance_info

    # 自動トラブルシューティング実行
    auto_troubleshoot

    # 完了メッセージ
    {
        echo "=== 収集完了 ==="
        echo "収集完了日時: $(date)"
        echo "ファイルサイズ: $(wc -l < "$OUTPUT_FILE") 行"
    } >> "$OUTPUT_FILE"

    log_success "サポート情報収集が完了しました"
    log_info "収集された情報: $OUTPUT_FILE"
    log_info "ファイルサイズ: $(wc -l < "$OUTPUT_FILE") 行"

    # 次のステップを案内
    echo
    log_info "次のステップ:"
    echo "  1. 収集された情報を確認: cat $OUTPUT_FILE"
    echo "  2. GitHub Issues で問題を報告"
    echo "  3. $OUTPUT_FILE の内容を問題報告に添付"

    # 機密情報の警告
    log_warning "注意: 機密情報が含まれていないか確認してから共有してください"
}

# スクリプト実行
main "$@"
