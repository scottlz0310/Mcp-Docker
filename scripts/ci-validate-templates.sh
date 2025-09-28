#!/bin/bash
# =============================================================================
# GitHub Actions Simulator - CI/CD テンプレート検証スクリプト
# =============================================================================
# このスクリプトは CI/CD パイプラインでテンプレートの自動検証を行います。
#
# 機能:
# - 全テンプレートファイルの構文チェック
# - 機能テストの実行
# - セキュリティチェック
# - 結果レポートの生成
# - 失敗時の詳細ログ出力
#
# 使用方法:
#   ./scripts/ci-validate-templates.sh [options]
#
# オプション:
#   --check-only     構文チェックのみ実行
#   --test-only      機能テストのみ実行
#   --verbose        詳細ログを出力
#   --format json    結果をJSON形式で出力
#   --output FILE    結果をファイルに出力
#   --fail-fast      最初のエラーで即座に終了
#   --help           このヘルプを表示
# =============================================================================

set -euo pipefail

# =============================================================================
# 設定とデフォルト値
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VALIDATOR_SCRIPT="${SCRIPT_DIR}/validate-templates.py"

# デフォルト設定
CHECK_ONLY=false
TEST_ONLY=false
VERBOSE=false
FORMAT="text"
OUTPUT_FILE=""
FAIL_FAST=false
TIMEOUT=300  # 5分

# カラー出力設定
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    MAGENTA=$(tput setaf 5)
    CYAN=$(tput setaf 6)
    WHITE=$(tput setaf 7)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BLUE="" MAGENTA="" CYAN="" WHITE="" BOLD="" RESET=""
fi

# =============================================================================
# ユーティリティ関数
# =============================================================================

log_info() {
    echo "${BLUE}[INFO]${RESET} $*" >&2
}

log_success() {
    echo "${GREEN}[SUCCESS]${RESET} $*" >&2
}

log_warning() {
    echo "${YELLOW}[WARNING]${RESET} $*" >&2
}

log_error() {
    echo "${RED}[ERROR]${RESET} $*" >&2
}

log_debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo "${CYAN}[DEBUG]${RESET} $*" >&2
    fi
}

show_help() {
    cat << 'EOF'
GitHub Actions Simulator - CI/CD テンプレート検証スクリプト

使用方法:
    ./scripts/ci-validate-templates.sh [options]

オプション:
    --check-only     構文チェックのみ実行
    --test-only      機能テストのみ実行
    --verbose        詳細ログを出力
    --format FORMAT  出力形式 (text|json)
    --output FILE    結果をファイルに出力
    --fail-fast      最初のエラーで即座に終了
    --timeout SEC    タイムアウト時間（秒）
    --help           このヘルプを表示

例:
    # 完全な検証を実行
    ./scripts/ci-validate-templates.sh

    # 構文チェックのみ実行
    ./scripts/ci-validate-templates.sh --check-only

    # JSON形式で結果をファイルに出力
    ./scripts/ci-validate-templates.sh --format json --output validation-report.json

    # 詳細ログ付きで実行
    ./scripts/ci-validate-templates.sh --verbose

    # 高速失敗モードで実行
    ./scripts/ci-validate-templates.sh --fail-fast

環境変数:
    CI                    CI環境での実行時に設定
    GITHUB_ACTIONS        GitHub Actions環境での実行時に設定
    TEMPLATE_VALIDATION_TIMEOUT  タイムアウト時間の上書き
    TEMPLATE_VALIDATION_VERBOSE  詳細ログの有効化

終了コード:
    0    すべてのテンプレートが有効
    1    無効なテンプレートが存在
    2    実行エラー
    130  ユーザーによる中断
EOF
}

check_dependencies() {
    log_info "依存関係をチェック中..."

    local missing_deps=()

    # Python 3の確認
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    fi

    # 必要なPythonパッケージの確認
    if ! python3 -c "import yaml, pytest" >/dev/null 2>&1; then
        log_warning "必要なPythonパッケージが不足している可能性があります"
        log_info "uvを使用して依存関係をインストール中..."

        if command -v uv >/dev/null 2>&1; then
            uv sync --group test --group dev || {
                log_warning "uv syncに失敗しました。pipでフォールバック..."
                pip3 install pyyaml pytest || missing_deps+=("python-packages")
            }
        else
            pip3 install pyyaml pytest || missing_deps+=("python-packages")
        fi
    fi

    # オプショナルな依存関係の確認
    local optional_tools=("shellcheck" "yamllint" "hadolint" "docker" "act" "pre-commit")
    local missing_optional=()

    for tool in "${optional_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_optional+=("${tool}")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "必須の依存関係が不足しています: ${missing_deps[*]}"
        log_error "以下のコマンドでインストールしてください:"

        if [[ " ${missing_deps[*]} " =~ " python3 " ]]; then
            log_error "  # Ubuntu/Debian: sudo apt-get install python3 python3-pip"
            log_error "  # macOS: brew install python3"
        fi

        if [[ " ${missing_deps[*]} " =~ " python-packages " ]]; then
            log_error "  pip3 install pyyaml pytest"
        fi

        return 1
    fi

    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        log_warning "オプショナルなツールが不足しています: ${missing_optional[*]}"
        log_warning "これらのツールがないと一部の機能テストがスキップされます"

        if [[ "${VERBOSE}" == "true" ]]; then
            log_debug "オプショナルツールのインストール方法:"
            for tool in "${missing_optional[@]}"; do
                case "${tool}" in
                    "shellcheck")
                        log_debug "  shellcheck: sudo apt-get install shellcheck (Ubuntu) / brew install shellcheck (macOS)"
                        ;;
                    "yamllint")
                        log_debug "  yamllint: pip3 install yamllint"
                        ;;
                    "hadolint")
                        log_debug "  hadolint: https://github.com/hadolint/hadolint#install"
                        ;;
                    "docker")
                        log_debug "  docker: https://docs.docker.com/get-docker/"
                        ;;
                    "act")
                        log_debug "  act: https://github.com/nektos/act#installation"
                        ;;
                    "pre-commit")
                        log_debug "  pre-commit: pip3 install pre-commit"
                        ;;
                esac
            done
        fi
    fi

    log_success "依存関係チェック完了"
    return 0
}

setup_environment() {
    log_info "実行環境をセットアップ中..."

    # 作業ディレクトリの確認
    if [[ ! -d "${PROJECT_ROOT}" ]]; then
        log_error "プロジェクトルートディレクトリが見つかりません: ${PROJECT_ROOT}"
        return 1
    fi

    cd "${PROJECT_ROOT}"
    log_debug "作業ディレクトリ: $(pwd)"

    # バリデータースクリプトの確認
    if [[ ! -f "${VALIDATOR_SCRIPT}" ]]; then
        log_error "バリデータースクリプトが見つかりません: ${VALIDATOR_SCRIPT}"
        return 1
    fi

    # 実行権限の確認
    if [[ ! -x "${VALIDATOR_SCRIPT}" ]]; then
        log_debug "バリデータースクリプトに実行権限を付与中..."
        chmod +x "${VALIDATOR_SCRIPT}"
    fi

    # 環境変数の設定
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
    export PYTHONUNBUFFERED=1

    # CI環境の検出
    if [[ "${CI:-}" == "true" ]]; then
        log_info "CI環境を検出しました"

        if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
            log_info "GitHub Actions環境で実行中"
            # GitHub Actionsの場合の特別な設定
            export TERM=xterm-256color
        fi
    fi

    log_success "環境セットアップ完了"
    return 0
}

run_validation() {
    log_info "テンプレート検証を開始..."

    local validator_args=()

    # オプションの設定
    if [[ "${CHECK_ONLY}" == "true" ]]; then
        validator_args+=("--check-only")
        log_info "構文チェックのみ実行します"
    elif [[ "${TEST_ONLY}" == "true" ]]; then
        validator_args+=("--test-only")
        log_info "機能テストのみ実行します"
    else
        log_info "完全な検証を実行します"
    fi

    if [[ "${VERBOSE}" == "true" ]]; then
        validator_args+=("--verbose")
    fi

    if [[ "${FORMAT}" != "text" ]]; then
        validator_args+=("--format" "${FORMAT}")
    fi

    if [[ -n "${OUTPUT_FILE}" ]]; then
        validator_args+=("--output" "${OUTPUT_FILE}")
    fi

    # タイムアウト付きで実行
    local validation_result=0
    local temp_output
    temp_output=$(mktemp)

    log_debug "実行コマンド: uv run python ${VALIDATOR_SCRIPT} ${validator_args[*]}"

    if timeout "${TIMEOUT}" uv run python "${VALIDATOR_SCRIPT}" "${validator_args[@]}" > "${temp_output}" 2>&1; then
        validation_result=0
        log_success "テンプレート検証が正常に完了しました"
    else
        validation_result=$?

        if [[ ${validation_result} -eq 124 ]]; then
            log_error "テンプレート検証がタイムアウトしました (${TIMEOUT}秒)"
        elif [[ ${validation_result} -eq 1 ]]; then
            log_error "無効なテンプレートが検出されました"
        else
            log_error "テンプレート検証中にエラーが発生しました (終了コード: ${validation_result})"
        fi
    fi

    # 出力の表示
    if [[ -s "${temp_output}" ]]; then
        if [[ "${OUTPUT_FILE}" == "" ]]; then
            # 標準出力に結果を表示
            cat "${temp_output}"
        else
            # ファイル出力の場合は要約のみ表示
            log_info "検証結果を ${OUTPUT_FILE} に出力しました"

            # JSON形式の場合は要約を抽出
            if [[ "${FORMAT}" == "json" ]] && command -v jq >/dev/null 2>&1; then
                local summary
                summary=$(jq -r '.total_templates as $total | .valid_templates as $valid | .invalid_templates as $invalid | "総数: \($total), 有効: \($valid), 無効: \($invalid)"' "${OUTPUT_FILE}" 2>/dev/null || echo "要約の抽出に失敗")
                log_info "検証要約: ${summary}"
            fi
        fi

        # 詳細ログの表示（エラー時または詳細モード時）
        if [[ ${validation_result} -ne 0 ]] || [[ "${VERBOSE}" == "true" ]]; then
            if [[ "${OUTPUT_FILE}" != "" ]] && [[ -f "${OUTPUT_FILE}" ]]; then
                log_debug "詳細な検証結果:"
                cat "${OUTPUT_FILE}" >&2
            fi
        fi
    fi

    # 一時ファイルのクリーンアップ
    rm -f "${temp_output}"

    return ${validation_result}
}

run_additional_checks() {
    log_info "追加チェックを実行中..."

    local additional_errors=0

    # テンプレートファイルの存在確認
    local expected_templates=(
        ".env.example"
        "docker-compose.override.yml.sample"
        ".pre-commit-config.yaml.sample"
        ".github/workflows/local-ci.yml.sample"
        ".github/workflows/basic-test.yml.sample"
        ".github/workflows/security-scan.yml.sample"
    )

    local missing_templates=()
    for template in "${expected_templates[@]}"; do
        if [[ ! -f "${template}" ]]; then
            missing_templates+=("${template}")
        fi
    done

    if [[ ${#missing_templates[@]} -gt 0 ]]; then
        log_warning "期待されるテンプレートファイルが見つかりません:"
        for template in "${missing_templates[@]}"; do
            log_warning "  - ${template}"
        done
        ((additional_errors++))
    fi

    # ファイル権限の確認
    for template in "${expected_templates[@]}"; do
        if [[ -f "${template}" ]]; then
            local file_perms
            file_perms=$(stat -c "%a" "${template}" 2>/dev/null || stat -f "%A" "${template}" 2>/dev/null || echo "unknown")

            if [[ "${file_perms}" != "unknown" ]] && [[ "${file_perms}" -gt 644 ]]; then
                log_warning "テンプレートファイルの権限が緩すぎます: ${template} (${file_perms})"
            fi
        fi
    done

    # Git管理状況の確認
    if command -v git >/dev/null 2>&1 && [[ -d ".git" ]]; then
        local untracked_templates
        untracked_templates=$(git ls-files --others --exclude-standard | grep -E '\.(sample|example|template)$' || true)

        if [[ -n "${untracked_templates}" ]]; then
            log_warning "Gitで管理されていないテンプレートファイルがあります:"
            echo "${untracked_templates}" | while read -r file; do
                log_warning "  - ${file}"
            done
        fi
    fi

    if [[ ${additional_errors} -gt 0 ]]; then
        log_warning "追加チェックで ${additional_errors} 個の問題が見つかりました"
    else
        log_success "追加チェック完了"
    fi

    return 0
}

generate_ci_summary() {
    log_info "CI要約を生成中..."

    local summary_file="${PROJECT_ROOT}/template-validation-summary.txt"

    cat > "${summary_file}" << EOF
GitHub Actions Simulator - テンプレート検証要約
=============================================

実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
実行環境: ${CI:-local}
実行モード: $(if [[ "${CHECK_ONLY}" == "true" ]]; then echo "構文チェックのみ"; elif [[ "${TEST_ONLY}" == "true" ]]; then echo "機能テストのみ"; else echo "完全検証"; fi)

検証対象テンプレート:
$(find . -name "*.sample" -o -name "*.example" -o -name "*.template" | head -20 | sed 's/^/  - /')

実行結果:
$(if [[ -f "${OUTPUT_FILE}" ]] && [[ "${FORMAT}" == "json" ]] && command -v jq >/dev/null 2>&1; then
    jq -r '
        "  総テンプレート数: " + (.total_templates | tostring) + "\n" +
        "  有効なテンプレート: " + (.valid_templates | tostring) + "\n" +
        "  無効なテンプレート: " + (.invalid_templates | tostring) + "\n" +
        "  警告があるテンプレート: " + (.templates_with_warnings | tostring) + "\n" +
        "  成功率: " + ((.valid_templates / .total_templates * 100) | floor | tostring) + "%"
    ' "${OUTPUT_FILE}" 2>/dev/null || echo "  結果の解析に失敗しました"
else
    echo "  詳細な結果は検証ログを参照してください"
fi)

推奨事項:
$(if [[ -f "${OUTPUT_FILE}" ]] && [[ "${FORMAT}" == "json" ]] && command -v jq >/dev/null 2>&1; then
    local invalid_count
    invalid_count=$(jq -r '.invalid_templates' "${OUTPUT_FILE}" 2>/dev/null || echo "0")
    if [[ "${invalid_count}" -gt 0 ]]; then
        echo "  - 無効なテンプレートを修正してください"
        echo "  - 詳細なエラー情報は検証レポートを確認してください"
    else
        echo "  - すべてのテンプレートが有効です"
        echo "  - 定期的な検証の継続を推奨します"
    fi
else
    echo "  - 検証結果を確認して必要に応じて修正してください"
fi)

=============================================
EOF

    log_info "CI要約を ${summary_file} に生成しました"

    # GitHub Actions環境の場合は要約を出力
    if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
        echo "::group::テンプレート検証要約"
        cat "${summary_file}"
        echo "::endgroup::"
    fi

    return 0
}

cleanup() {
    log_debug "クリーンアップを実行中..."

    # 一時ファイルの削除
    find "${PROJECT_ROOT}" -name "*.tmp" -name "*template-validation*" -mtime +1 -delete 2>/dev/null || true

    log_debug "クリーンアップ完了"
}

# =============================================================================
# メイン処理
# =============================================================================

main() {
    local exit_code=0

    # シグナルハンドラーの設定
    trap 'log_warning "検証が中断されました"; cleanup; exit 130' INT TERM
    trap 'cleanup' EXIT

    # 引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --format)
                FORMAT="$2"
                if [[ "${FORMAT}" != "text" ]] && [[ "${FORMAT}" != "json" ]]; then
                    log_error "無効な出力形式: ${FORMAT}"
                    exit 2
                fi
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --fail-fast)
                FAIL_FAST=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                if ! [[ "${TIMEOUT}" =~ ^[0-9]+$ ]]; then
                    log_error "無効なタイムアウト値: ${TIMEOUT}"
                    exit 2
                fi
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 2
                ;;
        esac
    done

    # 環境変数からの設定上書き
    if [[ -n "${TEMPLATE_VALIDATION_TIMEOUT:-}" ]]; then
        TIMEOUT="${TEMPLATE_VALIDATION_TIMEOUT}"
    fi

    if [[ "${TEMPLATE_VALIDATION_VERBOSE:-}" == "true" ]]; then
        VERBOSE=true
    fi

    # 相互排他的なオプションのチェック
    if [[ "${CHECK_ONLY}" == "true" ]] && [[ "${TEST_ONLY}" == "true" ]]; then
        log_error "--check-only と --test-only は同時に指定できません"
        exit 2
    fi

    # 実行開始
    log_info "${BOLD}GitHub Actions Simulator - テンプレート検証開始${RESET}"
    log_info "実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

    # 依存関係チェック
    if ! check_dependencies; then
        exit_code=2
        if [[ "${FAIL_FAST}" == "true" ]]; then
            log_error "依存関係チェックに失敗しました（fail-fastモード）"
            exit ${exit_code}
        fi
    fi

    # 環境セットアップ
    if ! setup_environment; then
        exit_code=2
        if [[ "${FAIL_FAST}" == "true" ]]; then
            log_error "環境セットアップに失敗しました（fail-fastモード）"
            exit ${exit_code}
        fi
    fi

    # メイン検証の実行
    if ! run_validation; then
        exit_code=1
        if [[ "${FAIL_FAST}" == "true" ]]; then
            log_error "テンプレート検証に失敗しました（fail-fastモード）"
            exit ${exit_code}
        fi
    fi

    # 追加チェックの実行
    if ! run_additional_checks; then
        # 追加チェックの失敗は警告レベル
        log_warning "追加チェックで問題が見つかりました"
    fi

    # CI要約の生成
    if [[ "${CI:-}" == "true" ]]; then
        generate_ci_summary
    fi

    # 結果の表示
    if [[ ${exit_code} -eq 0 ]]; then
        log_success "${BOLD}テンプレート検証が正常に完了しました${RESET}"
    else
        log_error "${BOLD}テンプレート検証で問題が検出されました${RESET}"
        log_error "詳細は上記のログまたは出力ファイルを確認してください"
    fi

    exit ${exit_code}
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
