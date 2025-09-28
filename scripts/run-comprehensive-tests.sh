#!/usr/bin/env bash
# GitHub Actions Simulator - 包括的テストスイート実行スクリプト
#
# このスクリプトは、タスク18で実装された包括的テストスイートを実行します。
#
# 使用方法:
#   ./scripts/run-comprehensive-tests.sh [options]
#
# オプション:
#   --quick         クイックテストのみ実行
#   --full          フルテストスイートを実行
#   --ci            CI環境での実行
#   --report        詳細レポートを生成
#   --output FILE   結果をファイルに出力

set -euo pipefail

# スクリプトの設定
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ログ設定
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly TEST_LOG="${LOG_DIR}/comprehensive-tests.log"

# デフォルト設定
QUICK_MODE=false
FULL_MODE=false
CI_MODE=false
GENERATE_REPORT=false
OUTPUT_FILE=""
VERBOSE=false

# 色付き出力の設定
if [[ -t 1 ]] && [[ "${CI:-}" != "true" ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m' # No Color
else
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly NC=''
fi

# ログ関数
info() {
    printf "${BLUE}ℹ️  %s${NC}\n" "$*"
}

success() {
    printf "${GREEN}✅ %s${NC}\n" "$*"
}

warning() {
    printf "${YELLOW}⚠️  %s${NC}\n" "$*"
}

error() {
    printf "${RED}❌ %s${NC}\n" "$*" >&2
}

# ヘルプ表示
show_help() {
    cat <<'EOF'
GitHub Actions Simulator - 包括的テストスイート実行スクリプト

使用方法:
  ./scripts/run-comprehensive-tests.sh [オプション]

オプション:
  --quick         クイックテストのみ実行（必須テストのみ）
  --full          フルテストスイートを実行（デフォルト）
  --ci            CI環境での実行（非対話モード、詳細ログ）
  --report        詳細レポートを生成
  --output FILE   結果をファイルに出力
  --verbose       詳細ログを出力
  --help, -h      このヘルプを表示

環境変数:
  CI=true                     CI環境での実行を有効化
  COMPREHENSIVE_TEST_TIMEOUT  テストタイムアウト時間（秒）
  PYTHON_EXECUTABLE          使用するPythonインタープリター

例:
  ./scripts/run-comprehensive-tests.sh                    # フルテスト実行
  ./scripts/run-comprehensive-tests.sh --quick           # クイックテスト実行
  ./scripts/run-comprehensive-tests.sh --ci --report     # CI環境でレポート生成
  ./scripts/run-comprehensive-tests.sh --output report.txt  # ファイル出力

詳細情報:
  docs/TESTING.md を参照してください
EOF
}

# 引数解析
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --full)
                FULL_MODE=true
                shift
                ;;
            --ci)
                CI_MODE=true
                shift
                ;;
            --report)
                GENERATE_REPORT=true
                shift
                ;;
            --output)
                if [[ $# -lt 2 ]]; then
                    error "--output には出力ファイル名を指定してください"
                    exit 1
                fi
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "不明なオプション: $1"
                echo
                show_help
                exit 1
                ;;
        esac
    done
}

# 環境チェック
check_environment() {
    info "環境をチェック中..."

    # プロジェクトルートの確認
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        error "プロジェクトルートが見つかりません: $PROJECT_ROOT"
        exit 1
    fi

    # Pythonの確認
    local python_cmd="${PYTHON_EXECUTABLE:-python3}"
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        python_cmd="python"
        if ! command -v "$python_cmd" >/dev/null 2>&1; then
            error "Pythonが見つかりません。Python 3.8以上をインストールしてください"
            exit 1
        fi
    fi

    # Pythonバージョンの確認
    local python_version
    python_version=$("$python_cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    local major_version="${python_version%%.*}"
    local minor_version="${python_version##*.}"

    if [[ "$major_version" -lt 3 ]] || [[ "$major_version" -eq 3 && "$minor_version" -lt 8 ]]; then
        error "Python 3.8以上が必要です。現在のバージョン: $python_version"
        exit 1
    fi

    success "Python $python_version を使用します"

    # pytestの確認
    if ! "$python_cmd" -m pytest --version >/dev/null 2>&1; then
        warning "pytestが見つかりません。インストールを試行します..."

        if ! "$python_cmd" -m pip install pytest >/dev/null 2>&1; then
            error "pytestのインストールに失敗しました"
            exit 1
        fi

        success "pytestをインストールしました"
    fi

    # ログディレクトリの作成
    mkdir -p "$LOG_DIR"

    # テストファイルの存在確認
    local test_runner="${PROJECT_ROOT}/tests/run_comprehensive_test_suite.py"
    if [[ ! -f "$test_runner" ]]; then
        error "包括的テストスイートが見つかりません: $test_runner"
        exit 1
    fi

    success "環境チェック完了"
}

# CI環境の設定
setup_ci_environment() {
    if [[ "$CI_MODE" == "true" ]] || [[ "${CI:-}" == "true" ]]; then
        info "CI環境を設定中..."

        # CI環境変数の設定
        export CI=true
        export NON_INTERACTIVE=1

        # タイムアウトの設定
        export COMPREHENSIVE_TEST_TIMEOUT="${COMPREHENSIVE_TEST_TIMEOUT:-1800}"  # 30分

        # 詳細ログを有効化
        VERBOSE=true

        success "CI環境設定完了"
    fi
}

# テスト実行
run_comprehensive_tests() {
    local start_time
    start_time=$(date +%s)

    info "包括的テストスイートを開始..."
    info "プロジェクト: $PROJECT_ROOT"
    info "モード: $(if [[ "$QUICK_MODE" == "true" ]]; then echo "クイック"; else echo "フル"; fi)"

    # Pythonコマンドの決定
    local python_cmd="${PYTHON_EXECUTABLE:-python3}"
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        python_cmd="python"
    fi

    # テスト実行コマンドの構築
    local test_cmd=("$python_cmd" "tests/run_comprehensive_test_suite.py")

    if [[ "$QUICK_MODE" == "true" ]]; then
        test_cmd+=("--quick")
    elif [[ "$FULL_MODE" == "true" ]]; then
        test_cmd+=("--full")
    fi

    if [[ "$GENERATE_REPORT" == "true" ]] || [[ -n "$OUTPUT_FILE" ]]; then
        test_cmd+=("--report")
    fi

    if [[ -n "$OUTPUT_FILE" ]]; then
        test_cmd+=("--output" "$OUTPUT_FILE")
    fi

    if [[ "$VERBOSE" == "true" ]]; then
        test_cmd+=("--verbose")
    fi

    # テストの実行
    local exit_code=0

    {
        echo "=== 包括的テストスイート実行ログ ==="
        echo "開始時刻: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "コマンド: ${test_cmd[*]}"
        echo "作業ディレクトリ: $PROJECT_ROOT"
        echo "======================================"
        echo
    } > "$TEST_LOG"

    if [[ "$VERBOSE" == "true" ]]; then
        info "実行コマンド: ${test_cmd[*]}"
    fi

    # タイムアウト設定
    local timeout="${COMPREHENSIVE_TEST_TIMEOUT:-3600}"  # デフォルト1時間

    if command -v timeout >/dev/null 2>&1; then
        # timeoutコマンドが利用可能な場合
        if timeout "$timeout" "${test_cmd[@]}" 2>&1 | tee -a "$TEST_LOG"; then
            exit_code=0
        else
            exit_code=${PIPESTATUS[0]}
        fi
    else
        # timeoutコマンドが利用できない場合
        if "${test_cmd[@]}" 2>&1 | tee -a "$TEST_LOG"; then
            exit_code=0
        else
            exit_code=${PIPESTATUS[0]}
        fi
    fi

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    {
        echo
        echo "======================================"
        echo "終了時刻: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "実行時間: ${duration}秒"
        echo "終了コード: $exit_code"
        echo "======================================"
    } >> "$TEST_LOG"

    # 結果の表示
    if [[ $exit_code -eq 0 ]]; then
        success "包括的テストスイートが正常に完了しました"
        success "実行時間: ${duration}秒"
    else
        error "包括的テストスイートが失敗しました（終了コード: $exit_code）"
        error "実行時間: ${duration}秒"

        # エラー時の追加情報
        echo
        warning "詳細ログ: $TEST_LOG"

        if [[ "$CI_MODE" == "true" ]]; then
            warning "CI環境でのテスト失敗です。ログを確認してください"
        else
            warning "個別のテストスイートを実行して問題を特定してください:"
            echo "  pytest tests/test_comprehensive_distribution.py -v"
            echo "  pytest tests/test_documentation_consistency.py -v"
            echo "  pytest tests/test_end_to_end_user_experience.py -v"
        fi
    fi

    # 出力ファイルの確認
    if [[ -n "$OUTPUT_FILE" ]] && [[ -f "$OUTPUT_FILE" ]]; then
        success "レポートを出力しました: $OUTPUT_FILE"
    fi

    return $exit_code
}

# クリーンアップ
cleanup() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo
        error "テスト実行が異常終了しました"

        # 診断情報の収集
        {
            echo
            echo "=== 診断情報 ==="
            echo "OS: $(uname -a)"
            echo "Python: $(python3 --version 2>&1 || python --version 2>&1 || echo '不明')"
            echo "作業ディレクトリ: $(pwd)"
            echo "環境変数:"
            env | grep -E '^(CI|PYTHON|COMPREHENSIVE_TEST)' | sort || true
            echo "================="
        } >> "$TEST_LOG"

        warning "診断情報をログに記録しました: $TEST_LOG"
    fi
}

# メイン処理
main() {
    # トラップの設定
    trap cleanup EXIT

    # 引数解析
    parse_arguments "$@"

    # プロジェクトルートに移動
    cd "$PROJECT_ROOT" || {
        error "プロジェクトディレクトリに移動できません: $PROJECT_ROOT"
        exit 1
    }

    # 環境チェック
    check_environment

    # CI環境の設定
    setup_ci_environment

    # テスト実行
    run_comprehensive_tests
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
