#!/usr/bin/env bash
# Pre-commit設定検証スクリプト
# GitHub Actions Simulator との統合テスト

set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ログ設定
readonly LOG_DIR="$PROJECT_ROOT/logs"
readonly VALIDATION_LOG="$LOG_DIR/precommit-validation.log"

# 色付きメッセージ
info() { echo -e "\033[36m[INFO]\033[0m $*"; }
success() { echo -e "\033[32m[SUCCESS]\033[0m $*"; }
warning() { echo -e "\033[33m[WARNING]\033[0m $*"; }
error() { echo -e "\033[31m[ERROR]\033[0m $*"; }

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# バリデーション結果
validation_results=()
failed_checks=0
total_checks=0

# チェック結果記録
record_check() {
    local check_name="$1"
    local status="$2"
    local message="$3"

    total_checks=$((total_checks + 1))

    if [[ "$status" == "PASS" ]]; then
        success "✅ $check_name: $message"
        validation_results+=("✅ $check_name: PASS - $message")
    else
        failed_checks=$((failed_checks + 1))
        error "❌ $check_name: $message"
        validation_results+=("❌ $check_name: FAIL - $message")
    fi

    # ログに記録
    echo "$(date -u +"%Y-%m-%d %H:%M:%S UTC") [$status] $check_name: $message" >> "$VALIDATION_LOG"
}

# Pre-commit設定ファイルの存在確認
check_config_files() {
    info "📋 Pre-commit設定ファイルの確認"

    # メイン設定ファイル
    if [[ -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]]; then
        record_check "設定ファイル存在" "PASS" ".pre-commit-config.yaml が存在"
    else
        record_check "設定ファイル存在" "FAIL" ".pre-commit-config.yaml が見つかりません"
    fi

    # サンプル設定ファイル
    if [[ -f "$PROJECT_ROOT/.pre-commit-config.yaml.sample" ]]; then
        record_check "サンプル設定存在" "PASS" ".pre-commit-config.yaml.sample が存在"
    else
        record_check "サンプル設定存在" "FAIL" ".pre-commit-config.yaml.sample が見つかりません"
    fi

    # ドキュメント
    if [[ -f "$PROJECT_ROOT/docs/PRE_COMMIT_INTEGRATION.md" ]]; then
        record_check "統合ドキュメント存在" "PASS" "PRE_COMMIT_INTEGRATION.md が存在"
    else
        record_check "統合ドキュメント存在" "FAIL" "PRE_COMMIT_INTEGRATION.md が見つかりません"
    fi
}

# Pre-commit設定の構文チェック
check_config_syntax() {
    info "🔍 Pre-commit設定の構文チェック"

    if command -v uv >/dev/null 2>&1 && uv run pre-commit --version >/dev/null 2>&1; then
        if uv run pre-commit validate-config "$PROJECT_ROOT/.pre-commit-config.yaml" >/dev/null 2>&1; then
            record_check "設定構文" "PASS" "YAML構文が正しい"
        else
            record_check "設定構文" "FAIL" "YAML構文エラーが検出されました"
        fi

        if uv run pre-commit validate-config "$PROJECT_ROOT/.pre-commit-config.yaml.sample" >/dev/null 2>&1; then
            record_check "サンプル構文" "PASS" "サンプル設定の構文が正しい"
        else
            record_check "サンプル構文" "FAIL" "サンプル設定に構文エラーがあります"
        fi
    elif command -v pre-commit >/dev/null 2>&1; then
        if pre-commit validate-config "$PROJECT_ROOT/.pre-commit-config.yaml" >/dev/null 2>&1; then
            record_check "設定構文" "PASS" "YAML構文が正しい"
        else
            record_check "設定構文" "FAIL" "YAML構文エラーが検出されました"
        fi

        if pre-commit validate-config "$PROJECT_ROOT/.pre-commit-config.yaml.sample" >/dev/null 2>&1; then
            record_check "サンプル構文" "PASS" "サンプル設定の構文が正しい"
        else
            record_check "サンプル構文" "FAIL" "サンプル設定に構文エラーがあります"
        fi
    else
        record_check "pre-commit可用性" "FAIL" "pre-commitコマンドが見つかりません"
    fi
}

# GitHub Actions Simulator統合チェック
check_simulator_integration() {
    info "🎭 GitHub Actions Simulator統合チェック"

    # Actions Simulator関連のhookが存在するかチェック
    if grep -q "actions-simulator" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "Simulator統合" "PASS" "Actions Simulator統合フックが設定済み"
    else
        record_check "Simulator統合" "FAIL" "Actions Simulator統合フックが見つかりません"
    fi

    # ワークフロー検証フックの確認
    if grep -q "actions-workflow-validation" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "ワークフロー検証" "PASS" "ワークフロー検証フックが設定済み"
    else
        record_check "ワークフロー検証" "FAIL" "ワークフロー検証フックが見つかりません"
    fi

    # Docker環境チェックフックの確認
    if grep -q "docker-environment-check" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "Docker環境チェック" "PASS" "Docker環境チェックフックが設定済み"
    else
        record_check "Docker環境チェック" "FAIL" "Docker環境チェックフックが見つかりません"
    fi
}

# 品質ゲート設定の確認
check_quality_gates() {
    info "🚦 品質ゲート設定の確認"

    # 基本品質チェック
    if grep -q "pre-commit-hooks" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "基本品質ゲート" "PASS" "基本的なpre-commitフックが設定済み"
    else
        record_check "基本品質ゲート" "FAIL" "基本的なpre-commitフックが見つかりません"
    fi

    # Docker品質チェック
    if grep -q "hadolint" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "Docker品質ゲート" "PASS" "Dockerfileリンターが設定済み"
    else
        record_check "Docker品質ゲート" "FAIL" "Dockerfileリンターが見つかりません"
    fi

    # Shell品質チェック
    if grep -q "shellcheck" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "Shell品質ゲート" "PASS" "Shellスクリプトリンターが設定済み"
    else
        record_check "Shell品質ゲート" "FAIL" "Shellスクリプトリンターが見つかりません"
    fi

    # Python品質チェック
    if grep -q "ruff" "$PROJECT_ROOT/.pre-commit-config.yaml" 2>/dev/null; then
        record_check "Python品質ゲート" "PASS" "Pythonコード品質チェックが設定済み"
    else
        record_check "Python品質ゲート" "FAIL" "Pythonコード品質チェックが見つかりません"
    fi
}

# 依存関係の確認
check_dependencies() {
    info "📦 依存関係の確認"

    # pre-commit
    if command -v uv >/dev/null 2>&1 && uv run pre-commit --version >/dev/null 2>&1; then
        local version=$(uv run pre-commit --version 2>/dev/null || echo "不明")
        record_check "pre-commit" "PASS" "インストール済み (uv経由: $version)"
    elif command -v pre-commit >/dev/null 2>&1; then
        local version=$(pre-commit --version 2>/dev/null || echo "不明")
        record_check "pre-commit" "PASS" "インストール済み ($version)"
    else
        record_check "pre-commit" "FAIL" "pre-commitがインストールされていません"
    fi

    # Docker
    if command -v docker >/dev/null 2>&1; then
        local version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',' || echo "不明")
        record_check "Docker" "PASS" "インストール済み ($version)"
    else
        record_check "Docker" "FAIL" "Dockerがインストールされていません"
    fi

    # uv
    if command -v uv >/dev/null 2>&1; then
        local version=$(uv --version 2>/dev/null | cut -d' ' -f2 || echo "不明")
        record_check "uv" "PASS" "インストール済み ($version)"
    else
        record_check "uv" "FAIL" "uvがインストールされていません"
    fi
}

# 実際のpre-commit実行テスト
test_precommit_execution() {
    info "🧪 Pre-commit実行テスト"

    if command -v uv >/dev/null 2>&1 && uv run pre-commit --version >/dev/null 2>&1; then
        # 軽量テスト用の一時ファイル作成
        local test_file="$PROJECT_ROOT/.precommit_test_temp.txt"
        echo "test content" > "$test_file"

        # 特定のフックのみテスト実行
        if uv run pre-commit run trailing-whitespace --files "$test_file" >/dev/null 2>&1; then
            record_check "実行テスト" "PASS" "基本フックが正常に実行されました"
        else
            record_check "実行テスト" "FAIL" "基本フックの実行でエラーが発生しました"
        fi

        # テストファイルを削除
        rm -f "$test_file"
    elif command -v pre-commit >/dev/null 2>&1; then
        # 軽量テスト用の一時ファイル作成
        local test_file="$PROJECT_ROOT/.precommit_test_temp.txt"
        echo "test content" > "$test_file"

        # 特定のフックのみテスト実行
        if pre-commit run trailing-whitespace --files "$test_file" >/dev/null 2>&1; then
            record_check "実行テスト" "PASS" "基本フックが正常に実行されました"
        else
            record_check "実行テスト" "FAIL" "基本フックの実行でエラーが発生しました"
        fi

        # テストファイルを削除
        rm -f "$test_file"
    else
        record_check "実行テスト" "FAIL" "pre-commitが利用できないため実行テストをスキップ"
    fi
}

# ドキュメント整合性チェック
check_documentation() {
    info "📚 ドキュメント整合性チェック"

    # README.mdでのpre-commit言及確認
    if grep -q "pre-commit" "$PROJECT_ROOT/README.md" 2>/dev/null; then
        record_check "README統合" "PASS" "README.mdにpre-commit情報が記載済み"
    else
        record_check "README統合" "FAIL" "README.mdにpre-commit情報が見つかりません"
    fi

    # 統合ガイドの内容確認
    if [[ -f "$PROJECT_ROOT/docs/PRE_COMMIT_INTEGRATION.md" ]]; then
        if grep -q "GitHub Actions Simulator" "$PROJECT_ROOT/docs/PRE_COMMIT_INTEGRATION.md" 2>/dev/null; then
            record_check "統合ガイド内容" "PASS" "統合ガイドにSimulator情報が含まれています"
        else
            record_check "統合ガイド内容" "FAIL" "統合ガイドにSimulator情報が不足しています"
        fi
    fi
}

# メイン実行
main() {
    info "🔍 GitHub Actions Simulator Pre-commit統合検証を開始"
    echo "検証開始: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" > "$VALIDATION_LOG"
    echo

    check_config_files
    echo

    check_config_syntax
    echo

    check_simulator_integration
    echo

    check_quality_gates
    echo

    check_dependencies
    echo

    test_precommit_execution
    echo

    check_documentation
    echo

    # 結果サマリー
    info "📊 検証結果サマリー"
    echo "総チェック数: $total_checks"
    echo "成功: $((total_checks - failed_checks))"
    echo "失敗: $failed_checks"
    echo

    if [[ $failed_checks -eq 0 ]]; then
        success "🎉 全ての検証が成功しました！"
        echo "✅ GitHub Actions Simulator Pre-commit統合は正常に設定されています"
    else
        error "⚠️  $failed_checks 個の問題が検出されました"
        echo
        echo "🔧 修正が必要な項目:"
        for result in "${validation_results[@]}"; do
            if [[ "$result" == *"FAIL"* ]]; then
                echo "  $result"
            fi
        done
        echo
        echo "💡 修正方法については以下を参照してください:"
        echo "  - docs/PRE_COMMIT_INTEGRATION.md"
        echo "  - .pre-commit-config.yaml.sample"
        echo "  - README.md の開発ワークフロー セクション"
    fi

    echo
    echo "📋 詳細ログ: $VALIDATION_LOG"

    # 終了コード
    if [[ $failed_checks -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# スクリプト実行
main "$@"
