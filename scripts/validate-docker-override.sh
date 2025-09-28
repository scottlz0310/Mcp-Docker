#!/bin/bash
# =============================================================================
# Docker Override Configuration Validator
# GitHub Actions Simulator - Docker設定検証スクリプト
# =============================================================================

set -euo pipefail

# 色付きログ出力用の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ出力関数
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

# スクリプトの説明
show_help() {
    cat << EOF
Docker Override Configuration Validator

使用方法:
    $0 [オプション]

オプション:
    -h, --help          このヘルプを表示
    -v, --verbose       詳細な出力を表示
    -f, --fix           自動修正を試行
    --check-only        検証のみ実行（修正なし）

説明:
    Docker Compose Override設定の妥当性を検証し、
    一般的な問題を検出・修正します。

例:
    $0                  # 基本的な検証を実行
    $0 --verbose        # 詳細な検証を実行
    $0 --fix            # 問題の自動修正を試行
EOF
}

# 変数の初期化
VERBOSE=false
FIX_ISSUES=false
CHECK_ONLY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OVERRIDE_FILE="$PROJECT_ROOT/docker-compose.override.yml"
SAMPLE_FILE="$PROJECT_ROOT/docker-compose.override.yml.sample"
BASE_FILE="$PROJECT_ROOT/docker-compose.yml"

# コマンドライン引数の解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--fix)
            FIX_ISSUES=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            log_error "不明なオプション: $1"
            show_help
            exit 1
            ;;
    esac
done

# 詳細ログ出力関数
verbose_log() {
    if [[ "$VERBOSE" == "true" ]]; then
        log_info "$1"
    fi
}

# 必要なコマンドの確認
check_dependencies() {
    log_info "依存関係の確認中..."

    local missing_deps=()

    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi

    if ! command -v yq &> /dev/null; then
        log_warning "yq が見つかりません。YAML解析機能が制限されます。"
        log_info "インストール方法: brew install yq (macOS) または apt install yq (Ubuntu)"
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "以下の依存関係が不足しています: ${missing_deps[*]}"
        return 1
    fi

    verbose_log "すべての依存関係が利用可能です"
    return 0
}

# ファイル存在確認
check_files() {
    log_info "設定ファイルの確認中..."

    if [[ ! -f "$BASE_FILE" ]]; then
        log_error "ベース設定ファイルが見つかりません: $BASE_FILE"
        return 1
    fi
    verbose_log "ベース設定ファイル確認: $BASE_FILE"

    if [[ ! -f "$SAMPLE_FILE" ]]; then
        log_error "サンプル設定ファイルが見つかりません: $SAMPLE_FILE"
        return 1
    fi
    verbose_log "サンプル設定ファイル確認: $SAMPLE_FILE"

    if [[ ! -f "$OVERRIDE_FILE" ]]; then
        log_warning "Override設定ファイルが見つかりません: $OVERRIDE_FILE"
        if [[ "$FIX_ISSUES" == "true" ]]; then
            log_info "サンプルファイルからOverride設定を作成中..."
            cp "$SAMPLE_FILE" "$OVERRIDE_FILE"
            log_success "Override設定ファイルを作成しました"
        else
            log_info "自動作成するには --fix オプションを使用してください"
        fi
        return 1
    fi
    verbose_log "Override設定ファイル確認: $OVERRIDE_FILE"

    return 0
}

# YAML構文チェック
validate_yaml_syntax() {
    log_info "YAML構文の検証中..."

    # ベースファイルのみをチェック
    if [[ -f "$BASE_FILE" ]]; then
        verbose_log "YAML構文チェック: $BASE_FILE"

        local syntax_output
        syntax_output=$(docker-compose -f "$BASE_FILE" config 2>&1)
        local syntax_exit_code=$?

        if [[ $syntax_exit_code -ne 0 ]]; then
            log_error "ベース設定ファイルにYAML構文エラー: $BASE_FILE"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "$syntax_output" | head -10
            fi
            return 1
        else
            verbose_log "ベース設定ファイルYAML構文OK: $BASE_FILE"
        fi
    fi

    # 統合設定をチェック（Override適用後）
    if [[ -f "$OVERRIDE_FILE" ]]; then
        verbose_log "統合設定YAML構文チェック（Override適用後）"

        local combined_output
        combined_output=$(docker-compose config 2>&1)
        local combined_exit_code=$?

        if [[ $combined_exit_code -ne 0 ]]; then
            # 警告のみの場合は成功とみなす
            if echo "$combined_output" | grep -q "level=warning" && ! echo "$combined_output" | grep -q "level=error\|Error\|invalid\|failed"; then
                verbose_log "統合設定YAML構文OK (警告あり)"
                if [[ "$VERBOSE" == "true" ]]; then
                    echo "$combined_output" | grep "level=warning" | head -3
                fi
            else
                log_error "統合設定にYAML構文エラー"
                if [[ "$VERBOSE" == "true" ]]; then
                    echo "$combined_output" | head -10
                fi
                return 1
            fi
        else
            verbose_log "統合設定YAML構文OK"
        fi
    fi

    log_success "YAML構文チェック完了"
    return 0
}

# Docker Compose設定の検証
validate_compose_config() {
    log_info "Docker Compose設定の検証中..."

    # 統合設定の検証
    local config_output
    config_output=$(docker-compose config 2>&1)
    local config_exit_code=$?

    if [[ $config_exit_code -ne 0 ]]; then
        # 警告メッセージのみの場合は成功とみなす
        if echo "$config_output" | grep -q "level=warning" && ! echo "$config_output" | grep -q "level=error\|invalid\|failed"; then
            verbose_log "Docker Compose設定に警告がありますが、動作可能です"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "$config_output" | grep "level=warning" | head -5
            fi
        else
            log_error "Docker Compose設定に問題があります"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "$config_output" | head -20
            fi
            return 1
        fi
    fi

    verbose_log "Docker Compose設定の統合チェック完了"

    # サービス定義の確認
    local services
    services=$(docker-compose config --services 2>/dev/null || echo "")

    if [[ -z "$services" ]]; then
        log_error "サービス定義が見つかりません"
        return 1
    fi

    verbose_log "検出されたサービス: $(echo "$services" | tr '\n' ' ')"

    # 基本サービスの確認（必須ではない）
    local expected_services=("github-mcp" "datetime-validator")
    local found_services=0
    for service in "${expected_services[@]}"; do
        if echo "$services" | grep -q "^$service$"; then
            verbose_log "基本サービス確認: $service"
            ((found_services++))
        fi
    done

    if [[ $found_services -eq 0 ]]; then
        log_warning "基本サービスが見つかりません。カスタム設定の可能性があります。"
    else
        verbose_log "$found_services 個の基本サービスが確認されました"
    fi

    log_success "Docker Compose設定検証完了"
    return 0
}

# リソース設定の検証
validate_resource_limits() {
    log_info "リソース制限の検証中..."

    # メモリ制限の確認
    local config_output
    config_output=$(docker-compose config 2>/dev/null || echo "")

    if [[ -n "$config_output" ]]; then
        # メモリ制限が適切に設定されているかチェック
        if echo "$config_output" | grep -q "memory:"; then
            verbose_log "メモリ制限が設定されています"
        else
            log_warning "メモリ制限が設定されていません"
        fi

        # CPU制限の確認
        if echo "$config_output" | grep -q "cpus:"; then
            verbose_log "CPU制限が設定されています"
        else
            log_warning "CPU制限が設定されていません"
        fi
    fi

    log_success "リソース制限検証完了"
    return 0
}

# セキュリティ設定の検証
validate_security_settings() {
    log_info "セキュリティ設定の検証中..."

    local config_output
    config_output=$(docker-compose config 2>/dev/null || echo "")

    if [[ -n "$config_output" ]]; then
        # privileged設定の確認
        if echo "$config_output" | grep -q "privileged: true"; then
            log_warning "privileged: true が設定されています（セキュリティリスク）"
        else
            verbose_log "privileged設定は安全です"
        fi

        # ユーザー設定の確認
        if echo "$config_output" | grep -q "user:"; then
            verbose_log "ユーザー設定が適用されています"
        else
            log_warning "ユーザー設定が見つかりません（rootで実行される可能性）"
        fi

        # capability設定の確認
        if echo "$config_output" | grep -q "cap_drop"; then
            verbose_log "capability制限が設定されています"
        else
            log_warning "capability制限が設定されていません"
        fi
    fi

    log_success "セキュリティ設定検証完了"
    return 0
}

# ボリューム設定の検証
validate_volume_settings() {
    log_info "ボリューム設定の検証中..."

    local config_output
    config_output=$(docker-compose config 2>/dev/null || echo "")

    if [[ -n "$config_output" ]]; then
        # 読み取り専用マウントの確認
        if echo "$config_output" | grep -q ":ro"; then
            verbose_log "読み取り専用マウントが設定されています"
        else
            log_warning "読み取り専用マウントが設定されていません"
        fi

        # 機密ディレクトリのマウント確認
        if echo "$config_output" | grep -q "/var/run/docker.sock"; then
            log_warning "Docker socketがマウントされています（必要な場合のみ使用）"
        fi
    fi

    log_success "ボリューム設定検証完了"
    return 0
}

# ネットワーク設定の検証
validate_network_settings() {
    log_info "ネットワーク設定の検証中..."

    local config_output
    config_output=$(docker-compose config 2>/dev/null || echo "")

    if [[ -n "$config_output" ]]; then
        # ネットワーク定義の確認
        if echo "$config_output" | grep -q "networks:"; then
            verbose_log "ネットワーク設定が定義されています"
        else
            log_warning "カスタムネットワーク設定が見つかりません"
        fi

        # ポート公開の確認
        if echo "$config_output" | grep -q "ports:"; then
            verbose_log "ポート公開が設定されています"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "$config_output" | grep -A 2 "ports:" | grep -E "^\s*-\s*\".*:.*\"" || true
            fi
        fi
    fi

    log_success "ネットワーク設定検証完了"
    return 0
}

# 環境変数の検証
validate_environment_variables() {
    log_info "環境変数設定の検証中..."

    # .env ファイルの確認
    local env_file="$PROJECT_ROOT/.env"
    if [[ -f "$env_file" ]]; then
        verbose_log ".env ファイルが見つかりました"

        # 必須環境変数の確認
        local required_vars=("GITHUB_PERSONAL_ACCESS_TOKEN")
        for var in "${required_vars[@]}"; do
            if grep -q "^$var=" "$env_file" 2>/dev/null; then
                verbose_log "必須環境変数確認: $var"
            else
                log_warning "必須環境変数が設定されていません: $var"
            fi
        done
    else
        log_warning ".env ファイルが見つかりません"
        if [[ "$FIX_ISSUES" == "true" ]]; then
            local env_example="$PROJECT_ROOT/.env.example"
            if [[ -f "$env_example" ]]; then
                log_info ".env.example から .env を作成中..."
                cp "$env_example" "$env_file"
                log_success ".env ファイルを作成しました"
                log_warning "必要な環境変数を設定してください"
            fi
        fi
    fi

    log_success "環境変数検証完了"
    return 0
}

# 設定の最適化提案
suggest_optimizations() {
    log_info "設定最適化の提案..."

    local suggestions=()

    # システムリソースの確認
    if command -v free &> /dev/null; then
        local total_memory
        total_memory=$(free -m | awk 'NR==2{print $2}')
        if [[ $total_memory -lt 8192 ]]; then
            suggestions+=("システムメモリが8GB未満です。メモリ制限を調整することを推奨します。")
        fi
    fi

    # CPU数の確認
    if command -v nproc &> /dev/null; then
        local cpu_count
        cpu_count=$(nproc)
        if [[ $cpu_count -lt 4 ]]; then
            suggestions+=("CPU数が4未満です。並列処理数を調整することを推奨します。")
        fi
    fi

    # Docker設定の確認
    if command -v docker &> /dev/null; then
        if ! docker info &> /dev/null; then
            suggestions+=("Dockerデーモンが起動していません。")
        fi
    fi

    # 提案の表示
    if [[ ${#suggestions[@]} -gt 0 ]]; then
        log_info "最適化提案:"
        for suggestion in "${suggestions[@]}"; do
            echo "  - $suggestion"
        done
    else
        log_success "現在の設定は最適化されています"
    fi
}

# メイン実行関数
main() {
    log_info "Docker Override Configuration Validator を開始します..."
    echo

    local exit_code=0

    # 依存関係チェック
    if ! check_dependencies; then
        exit_code=1
    fi
    echo

    # ファイル存在確認
    if ! check_files; then
        if [[ "$CHECK_ONLY" == "true" ]]; then
            exit_code=1
        fi
    fi
    echo

    # YAML構文チェック
    if [[ -f "$OVERRIDE_FILE" ]]; then
        if ! validate_yaml_syntax; then
            exit_code=1
        fi
        echo

        # Docker Compose設定検証
        if ! validate_compose_config; then
            exit_code=1
        fi
        echo

        # リソース設定検証
        validate_resource_limits
        echo

        # セキュリティ設定検証
        validate_security_settings
        echo

        # ボリューム設定検証
        validate_volume_settings
        echo

        # ネットワーク設定検証
        validate_network_settings
        echo

        # 環境変数検証
        validate_environment_variables
        echo

        # 最適化提案
        suggest_optimizations
        echo
    fi

    # 結果サマリー
    if [[ $exit_code -eq 0 ]]; then
        log_success "すべての検証が完了しました"
        log_info "次のステップ:"
        echo "  1. docker-compose up -d でサービスを起動"
        echo "  2. docker-compose ps でサービス状態を確認"
        echo "  3. docker-compose logs -f でログを監視"
    else
        log_error "検証中に問題が見つかりました"
        log_info "修正方法:"
        echo "  1. --fix オプションで自動修正を試行"
        echo "  2. --verbose オプションで詳細情報を確認"
        echo "  3. 手動で設定ファイルを修正"
    fi

    exit $exit_code
}

# スクリプト実行
main "$@"
