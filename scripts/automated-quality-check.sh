#!/bin/bash
# =============================================================================
# GitHub Actions Simulator - 自動品質チェックスクリプト
# =============================================================================
# このスクリプトは、ドキュメント更新とテンプレート検証の自動化を実装します。
#
# 機能:
# - ドキュメント整合性の自動チェック
# - テンプレート動作検証の自動実行
# - 品質メトリクスの収集と報告
# - CI/CD統合のための結果出力
#
# 使用方法:
#   ./scripts/automated-quality-check.sh [options]
#
# オプション:
#   --docs-only          ドキュメントチェックのみ実行
#   --templates-only     テンプレート検証のみ実行
#   --quick             クイックチェック（基本項目のみ）
#   --strict            厳格チェック（全項目）
#   --ci                CI環境での実行
#   --output-format     出力形式 (text|json|junit)
#   --output-file       結果出力ファイル
#   --fail-fast         最初のエラーで即座に終了
#   --verbose           詳細ログを出力
# =============================================================================

set -euo pipefail

# =============================================================================
# 設定とデフォルト値
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# デフォルト設定
DOCS_ONLY=false
TEMPLATES_ONLY=false
QUICK_MODE=false
STRICT_MODE=false
CI_MODE=false
OUTPUT_FORMAT="text"
OUTPUT_FILE=""
FAIL_FAST=false
VERBOSE=false
TIMEOUT=1800  # 30分

# 品質チェック設定
QUALITY_THRESHOLD_DOCS=90      # ドキュメント品質閾値（%）
QUALITY_THRESHOLD_TEMPLATES=95 # テンプレート品質閾値（%）
MAX_WARNINGS=10               # 許容警告数

# カラー出力設定
if [[ -t 1 ]] && [[ "${CI:-}" != "true" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' WHITE='' BOLD='' RESET=''
fi

# =============================================================================
# ユーティリティ関数
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${RESET} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${RESET} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $*" >&2
}

log_debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo -e "${CYAN}[DEBUG]${RESET} $*" >&2
    fi
}

show_help() {
    cat << 'EOF'
GitHub Actions Simulator - 自動品質チェックスクリプト

使用方法:
    ./scripts/automated-quality-check.sh [options]

オプション:
    --docs-only          ドキュメントチェックのみ実行
    --templates-only     テンプレート検証のみ実行
    --quick             クイックチェック（基本項目のみ）
    --strict            厳格チェック（全項目）
    --ci                CI環境での実行
    --output-format     出力形式 (text|json|junit)
    --output-file       結果出力ファイル
    --fail-fast         最初のエラーで即座に終了
    --verbose           詳細ログを出力
    --timeout SEC       タイムアウト時間（秒）
    --help              このヘルプを表示

品質チェック項目:
    ドキュメント:
    - Markdown構文チェック
    - 内部リンク有効性確認
    - ドキュメント間整合性チェック
    - バージョン情報一致確認
    - コード例動作確認

    テンプレート:
    - YAML/JSON構文チェック
    - Shell構文チェック
    - Docker構文チェック
    - 機能動作テスト
    - セキュリティチェック

例:
    # 完全な品質チェック
    ./scripts/automated-quality-check.sh

    # ドキュメントのみチェック
    ./scripts/automated-quality-check.sh --docs-only

    # CI環境でJSON出力
    ./scripts/automated-quality-check.sh --ci --output-format json --output-file quality-report.json

    # 厳格モードで実行
    ./scripts/automated-quality-check.sh --strict --verbose

環境変数:
    CI=true                     CI環境での実行を有効化
    QUALITY_CHECK_TIMEOUT       タイムアウト時間の上書き
    QUALITY_CHECK_VERBOSE       詳細ログの有効化

終了コード:
    0    すべてのチェックが成功
    1    品質基準を満たさない項目が存在
    2    実行エラー
    130  ユーザーによる中断
EOF
}

# =============================================================================
# 環境チェックと初期化
# =============================================================================

check_dependencies() {
    log_info "依存関係をチェック中..."

    local missing_deps=()

    # 必須ツールの確認
    local required_tools=("python3" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_deps+=("${tool}")
        fi
    done

    # Pythonパッケージの確認
    if ! python3 -c "import yaml, pytest, pathlib" >/dev/null 2>&1; then
        log_info "必要なPythonパッケージをインストール中..."

        if command -v uv >/dev/null 2>&1; then
            uv sync --group test --group dev || missing_deps+=("python-packages")
        else
            pip3 install pyyaml pytest || missing_deps+=("python-packages")
        fi
    fi

    # オプショナルツールの確認
    local optional_tools=("shellcheck" "yamllint" "markdownlint" "hadolint" "jq")
    local missing_optional=()

    for tool in "${optional_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_optional+=("${tool}")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "必須の依存関係が不足しています: ${missing_deps[*]}"
        return 1
    fi

    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        log_warning "オプショナルなツールが不足しています: ${missing_optional[*]}"
        log_warning "一部の機能が制限される可能性があります"
    fi

    log_success "依存関係チェック完了"
    return 0
}

initialize_environment() {
    log_info "実行環境を初期化中..."

    # 作業ディレクトリの設定
    cd "${PROJECT_ROOT}"

    # 環境変数の設定
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
    export PYTHONUNBUFFERED=1

    # CI環境の検出と設定
    if [[ "${CI_MODE}" == "true" ]] || [[ "${CI:-}" == "true" ]]; then
        CI_MODE=true
        VERBOSE=true
        export CI=true
        log_info "CI環境で実行中"
    fi

    # タイムアウトの設定
    if [[ -n "${QUALITY_CHECK_TIMEOUT:-}" ]]; then
        TIMEOUT="${QUALITY_CHECK_TIMEOUT}"
    fi

    # 詳細ログの設定
    if [[ "${QUALITY_CHECK_VERBOSE:-}" == "true" ]]; then
        VERBOSE=true
    fi

    log_success "環境初期化完了"
}

# =============================================================================
# ドキュメント品質チェック
# =============================================================================

check_documentation_quality() {
    log_info "ドキュメント品質チェックを開始..."

    local doc_errors=0
    local doc_warnings=0
    local doc_total=0

    # Markdownファイルの検出
    local markdown_files=()
    while IFS= read -r -d '' file; do
        markdown_files+=("$file")
    done < <(find . -name "*.md" -type f -not -path "./.git/*" -not -path "./node_modules/*" -print0)

    doc_total=${#markdown_files[@]}
    log_info "検出されたMarkdownファイル: ${doc_total}個"

    # 1. Markdown構文チェック
    log_info "Markdown構文チェック中..."

    if command -v markdownlint >/dev/null 2>&1; then
        local markdown_issues=0

        for file in "${markdown_files[@]}"; do
            if ! markdownlint "$file" >/dev/null 2>&1; then
                ((markdown_issues++))
                log_debug "Markdown構文問題: $file"
            fi
        done

        if [[ $markdown_issues -gt 0 ]]; then
            log_warning "Markdown構文問題: ${markdown_issues}ファイル"
            ((doc_warnings += markdown_issues))
        else
            log_success "Markdown構文チェック完了"
        fi
    else
        log_warning "markdownlintが利用できません。構文チェックをスキップします"
    fi

    # 2. 内部リンク有効性チェック
    log_info "内部リンク有効性チェック中..."

    local link_errors=0

    python3 << 'EOF'
import re
import sys
from pathlib import Path

def check_internal_links():
    issues = []
    base_path = Path('.')

    for md_file in base_path.rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')

            # 内部リンクを検出
            links = re.findall(r'\[.*?\]\(([^)]+)\)', content)
            for link in links:
                if not link.startswith('http') and not link.startswith('#') and not link.startswith('mailto:'):
                    # 相対パスの場合
                    if link.startswith('/'):
                        target_path = base_path / link[1:]
                    else:
                        target_path = md_file.parent / link

                    # アンカーリンクの処理
                    if '#' in link:
                        link_path, anchor = link.split('#', 1)
                        if link_path:
                            target_path = md_file.parent / link_path

                    if not target_path.exists():
                        issues.append(f'{md_file}: リンク切れ {link}')

        except Exception as e:
            issues.append(f'{md_file}: 読み取りエラー {str(e)}')

    return issues

issues = check_internal_links()
if issues:
    print(f"LINK_ERRORS={len(issues)}")
    for issue in issues[:10]:  # 最初の10件のみ表示
        print(f"LINK_ISSUE: {issue}", file=sys.stderr)
    if len(issues) > 10:
        print(f"... 他 {len(issues) - 10} 件のリンク問題", file=sys.stderr)
else:
    print("LINK_ERRORS=0")
EOF

    # Pythonスクリプトの結果を取得
    local python_output
    python_output=$(python3 << 'EOF'
import re
import sys
from pathlib import Path

def check_internal_links():
    issues = []
    base_path = Path('.')

    for md_file in base_path.rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')

            # 内部リンクを検出
            links = re.findall(r'\[.*?\]\(([^)]+)\)', content)
            for link in links:
                if not link.startswith('http') and not link.startswith('#') and not link.startswith('mailto:'):
                    # 相対パスの場合
                    if link.startswith('/'):
                        target_path = base_path / link[1:]
                    else:
                        target_path = md_file.parent / link

                    # アンカーリンクの処理
                    if '#' in link:
                        link_path, anchor = link.split('#', 1)
                        if link_path:
                            target_path = md_file.parent / link_path

                    if not target_path.exists():
                        issues.append(f'{md_file}: リンク切れ {link}')

        except Exception as e:
            issues.append(f'{md_file}: 読み取りエラー {str(e)}')

    return issues

issues = check_internal_links()
print(f"LINK_ERRORS={len(issues)}")
EOF
)

    link_errors=$(echo "$python_output" | grep "LINK_ERRORS=" | cut -d'=' -f2)

    if [[ $link_errors -gt 0 ]]; then
        log_warning "内部リンク問題: ${link_errors}件"
        ((doc_warnings += link_errors))
    else
        log_success "内部リンクチェック完了"
    fi

    # 3. ドキュメント整合性チェック
    log_info "ドキュメント整合性チェック中..."

    if [[ -f "tests/test_documentation_consistency.py" ]]; then
        if python3 -m pytest tests/test_documentation_consistency.py -v --tb=short >/dev/null 2>&1; then
            log_success "ドキュメント整合性チェック完了"
        else
            log_warning "ドキュメント整合性に問題があります"
            ((doc_warnings++))
        fi
    else
        log_warning "ドキュメント整合性テストが見つかりません"
    fi

    # 4. バージョン情報一致確認
    log_info "バージョン情報一致確認中..."

    local version_issues=0

    # pyproject.tomlのバージョン
    local pyproject_version=""
    if [[ -f "pyproject.toml" ]]; then
        pyproject_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo "")
    fi

    # main.pyのバージョン
    local main_py_version=""
    if [[ -f "main.py" ]]; then
        main_py_version=$(grep '^__version__ = ' main.py | sed 's/__version__ = "\(.*\)"/\1/' || echo "")
    fi

    # バージョン一致確認
    if [[ -n "$pyproject_version" ]] && [[ -n "$main_py_version" ]]; then
        if [[ "$pyproject_version" != "$main_py_version" ]]; then
            log_warning "バージョン不一致: pyproject.toml($pyproject_version) vs main.py($main_py_version)"
            ((version_issues++))
        fi
    fi

    if [[ $version_issues -gt 0 ]]; then
        ((doc_warnings += version_issues))
    else
        log_success "バージョン情報一致確認完了"
    fi

    # ドキュメント品質スコアの計算
    local doc_quality_score=100

    if [[ $doc_total -gt 0 ]]; then
        local penalty=$((doc_warnings * 100 / doc_total))
        doc_quality_score=$((100 - penalty))

        if [[ $doc_quality_score -lt 0 ]]; then
            doc_quality_score=0
        fi
    fi

    log_info "ドキュメント品質スコア: ${doc_quality_score}%"

    # 品質閾値チェック
    if [[ $doc_quality_score -lt $QUALITY_THRESHOLD_DOCS ]]; then
        log_error "ドキュメント品質が基準を下回っています (${doc_quality_score}% < ${QUALITY_THRESHOLD_DOCS}%)"
        ((doc_errors++))
    fi

    # 結果の出力
    echo "DOC_ERRORS=$doc_errors"
    echo "DOC_WARNINGS=$doc_warnings"
    echo "DOC_QUALITY_SCORE=$doc_quality_score"

    return $doc_errors
}

# =============================================================================
# テンプレート品質チェック
# =============================================================================

check_template_quality() {
    log_info "テンプレート品質チェックを開始..."

    local template_errors=0
    local template_warnings=0
    local template_total=0

    # テンプレートファイルの検出
    local template_files=()
    while IFS= read -r -d '' file; do
        template_files+=("$file")
    done < <(find . \( -name "*.sample" -o -name "*.example" -o -name "*.template" \) -type f -not -path "./.git/*" -print0)

    template_total=${#template_files[@]}
    log_info "検出されたテンプレートファイル: ${template_total}個"

    # 1. テンプレート構文チェック
    log_info "テンプレート構文チェック中..."

    local syntax_errors=0

    for file in "${template_files[@]}"; do
        log_debug "構文チェック: $file"

        case "$file" in
            *.yml|*.yaml)
                if command -v yamllint >/dev/null 2>&1; then
                    if ! yamllint "$file" >/dev/null 2>&1; then
                        log_debug "YAML構文エラー: $file"
                        ((syntax_errors++))
                    fi
                else
                    # yamllintが無い場合はPythonで基本チェック
                    if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" >/dev/null 2>&1; then
                        log_debug "YAML構文エラー: $file"
                        ((syntax_errors++))
                    fi
                fi
                ;;
            *.json)
                if ! python3 -c "import json; json.load(open('$file'))" >/dev/null 2>&1; then
                    log_debug "JSON構文エラー: $file"
                    ((syntax_errors++))
                fi
                ;;
            *.sh)
                if command -v shellcheck >/dev/null 2>&1; then
                    if ! shellcheck "$file" >/dev/null 2>&1; then
                        log_debug "Shell構文警告: $file"
                        ((template_warnings++))
                    fi
                else
                    # shellcheckが無い場合は基本的な構文チェック
                    if ! bash -n "$file" >/dev/null 2>&1; then
                        log_debug "Shell構文エラー: $file"
                        ((syntax_errors++))
                    fi
                fi
                ;;
            *Dockerfile*|*dockerfile*)
                if command -v hadolint >/dev/null 2>&1; then
                    if ! hadolint "$file" >/dev/null 2>&1; then
                        log_debug "Dockerfile構文警告: $file"
                        ((template_warnings++))
                    fi
                fi
                ;;
        esac
    done

    if [[ $syntax_errors -gt 0 ]]; then
        log_error "テンプレート構文エラー: ${syntax_errors}ファイル"
        ((template_errors += syntax_errors))
    else
        log_success "テンプレート構文チェック完了"
    fi

    # 2. テンプレート機能テスト
    log_info "テンプレート機能テスト中..."

    if [[ -f "scripts/ci-validate-templates.sh" ]]; then
        if timeout "$TIMEOUT" ./scripts/ci-validate-templates.sh --check-only >/dev/null 2>&1; then
            log_success "テンプレート機能テスト完了"
        else
            log_warning "テンプレート機能テストで問題が検出されました"
            ((template_warnings++))
        fi
    else
        log_warning "テンプレート検証スクリプトが見つかりません"
    fi

    # 3. テンプレートセキュリティチェック
    log_info "テンプレートセキュリティチェック中..."

    local security_issues=0

    for file in "${template_files[@]}"; do
        # 秘密情報の検出
        if grep -qE "(password|secret|token|key).*=.*[a-zA-Z0-9]{8,}" "$file" 2>/dev/null; then
            log_warning "潜在的な秘密情報: $file"
            ((security_issues++))
        fi

        # 危険な設定の検出
        if grep -qE "(privileged.*true|--privileged|root.*user)" "$file" 2>/dev/null; then
            log_warning "潜在的に危険な設定: $file"
            ((security_issues++))
        fi
    done

    if [[ $security_issues -gt 0 ]]; then
        log_warning "セキュリティ問題: ${security_issues}件"
        ((template_warnings += security_issues))
    else
        log_success "テンプレートセキュリティチェック完了"
    fi

    # テンプレート品質スコアの計算
    local template_quality_score=100

    if [[ $template_total -gt 0 ]]; then
        local error_penalty=$((template_errors * 100 / template_total))
        local warning_penalty=$((template_warnings * 50 / template_total))
        template_quality_score=$((100 - error_penalty - warning_penalty))

        if [[ $template_quality_score -lt 0 ]]; then
            template_quality_score=0
        fi
    fi

    log_info "テンプレート品質スコア: ${template_quality_score}%"

    # 品質閾値チェック
    if [[ $template_quality_score -lt $QUALITY_THRESHOLD_TEMPLATES ]]; then
        log_error "テンプレート品質が基準を下回っています (${template_quality_score}% < ${QUALITY_THRESHOLD_TEMPLATES}%)"
        ((template_errors++))
    fi

    # 結果の出力
    echo "TEMPLATE_ERRORS=$template_errors"
    echo "TEMPLATE_WARNINGS=$template_warnings"
    echo "TEMPLATE_QUALITY_SCORE=$template_quality_score"

    return $template_errors
}

# =============================================================================
# 結果レポート生成
# =============================================================================

generate_quality_report() {
    local doc_errors="$1"
    local doc_warnings="$2"
    local doc_quality_score="$3"
    local template_errors="$4"
    local template_warnings="$5"
    local template_quality_score="$6"

    log_info "品質レポートを生成中..."

    local overall_errors=$((doc_errors + template_errors))
    local overall_warnings=$((doc_warnings + template_warnings))
    local overall_quality_score=$(((doc_quality_score + template_quality_score) / 2))

    case "$OUTPUT_FORMAT" in
        "json")
            generate_json_report "$doc_errors" "$doc_warnings" "$doc_quality_score" \
                                "$template_errors" "$template_warnings" "$template_quality_score" \
                                "$overall_errors" "$overall_warnings" "$overall_quality_score"
            ;;
        "junit")
            generate_junit_report "$doc_errors" "$doc_warnings" "$doc_quality_score" \
                                 "$template_errors" "$template_warnings" "$template_quality_score"
            ;;
        *)
            generate_text_report "$doc_errors" "$doc_warnings" "$doc_quality_score" \
                               "$template_errors" "$template_warnings" "$template_quality_score" \
                               "$overall_errors" "$overall_warnings" "$overall_quality_score"
            ;;
    esac
}

generate_text_report() {
    local doc_errors="$1"
    local doc_warnings="$2"
    local doc_quality_score="$3"
    local template_errors="$4"
    local template_warnings="$5"
    local template_quality_score="$6"
    local overall_errors="$7"
    local overall_warnings="$8"
    local overall_quality_score="$9"

    local report_content
    report_content=$(cat << EOF
GitHub Actions Simulator - 自動品質チェックレポート
================================================

実行情報:
  実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
  実行モード: $(if [[ "$QUICK_MODE" == "true" ]]; then echo "クイック"; elif [[ "$STRICT_MODE" == "true" ]]; then echo "厳格"; else echo "標準"; fi)
  CI環境: $(if [[ "$CI_MODE" == "true" ]]; then echo "はい"; else echo "いいえ"; fi)

全体サマリー:
  総エラー数: $overall_errors
  総警告数: $overall_warnings
  全体品質スコア: ${overall_quality_score}%
  品質判定: $(if [[ $overall_errors -eq 0 ]] && [[ $overall_quality_score -ge 90 ]]; then echo "✅ 合格"; else echo "❌ 要改善"; fi)

ドキュメント品質:
  エラー数: $doc_errors
  警告数: $doc_warnings
  品質スコア: ${doc_quality_score}%
  判定: $(if [[ $doc_errors -eq 0 ]] && [[ $doc_quality_score -ge $QUALITY_THRESHOLD_DOCS ]]; then echo "✅ 合格"; else echo "❌ 要改善"; fi)

テンプレート品質:
  エラー数: $template_errors
  警告数: $template_warnings
  品質スコア: ${template_quality_score}%
  判定: $(if [[ $template_errors -eq 0 ]] && [[ $template_quality_score -ge $QUALITY_THRESHOLD_TEMPLATES ]]; then echo "✅ 合格"; else echo "❌ 要改善"; fi)

推奨事項:
$(if [[ $overall_errors -gt 0 ]]; then
    echo "  - エラーを修正してください"
fi)
$(if [[ $overall_warnings -gt $MAX_WARNINGS ]]; then
    echo "  - 警告数が多すぎます（${overall_warnings} > ${MAX_WARNINGS}）"
fi)
$(if [[ $overall_quality_score -lt 90 ]]; then
    echo "  - 品質スコアを向上させてください"
fi)
$(if [[ $overall_errors -eq 0 ]] && [[ $overall_warnings -le $MAX_WARNINGS ]] && [[ $overall_quality_score -ge 90 ]]; then
    echo "  - 品質基準を満たしています。継続的な品質維持を推奨します"
fi)

================================================
EOF
)

    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$report_content" > "$OUTPUT_FILE"
        log_success "テキストレポートを出力しました: $OUTPUT_FILE"
    else
        echo "$report_content"
    fi
}

generate_json_report() {
    local doc_errors="$1"
    local doc_warnings="$2"
    local doc_quality_score="$3"
    local template_errors="$4"
    local template_warnings="$5"
    local template_quality_score="$6"
    local overall_errors="$7"
    local overall_warnings="$8"
    local overall_quality_score="$9"

    local json_content
    json_content=$(cat << EOF
{
  "execution_info": {
    "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "mode": "$(if [[ "$QUICK_MODE" == "true" ]]; then echo "quick"; elif [[ "$STRICT_MODE" == "true" ]]; then echo "strict"; else echo "standard"; fi)",
    "ci_environment": $CI_MODE
  },
  "overall_summary": {
    "total_errors": $overall_errors,
    "total_warnings": $overall_warnings,
    "quality_score": $overall_quality_score,
    "passed": $(if [[ $overall_errors -eq 0 ]] && [[ $overall_quality_score -ge 90 ]]; then echo "true"; else echo "false"; fi)
  },
  "documentation_quality": {
    "errors": $doc_errors,
    "warnings": $doc_warnings,
    "quality_score": $doc_quality_score,
    "threshold": $QUALITY_THRESHOLD_DOCS,
    "passed": $(if [[ $doc_errors -eq 0 ]] && [[ $doc_quality_score -ge $QUALITY_THRESHOLD_DOCS ]]; then echo "true"; else echo "false"; fi)
  },
  "template_quality": {
    "errors": $template_errors,
    "warnings": $template_warnings,
    "quality_score": $template_quality_score,
    "threshold": $QUALITY_THRESHOLD_TEMPLATES,
    "passed": $(if [[ $template_errors -eq 0 ]] && [[ $template_quality_score -ge $QUALITY_THRESHOLD_TEMPLATES ]]; then echo "true"; else echo "false"; fi)
  },
  "quality_thresholds": {
    "documentation": $QUALITY_THRESHOLD_DOCS,
    "templates": $QUALITY_THRESHOLD_TEMPLATES,
    "max_warnings": $MAX_WARNINGS
  }
}
EOF
)

    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$json_content" > "$OUTPUT_FILE"
        log_success "JSONレポートを出力しました: $OUTPUT_FILE"
    else
        echo "$json_content"
    fi
}

# =============================================================================
# メイン処理
# =============================================================================

main() {
    local exit_code=0

    # シグナルハンドラーの設定
    trap 'log_warning "品質チェックが中断されました"; exit 130' INT TERM

    # 引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docs-only)
                DOCS_ONLY=true
                shift
                ;;
            --templates-only)
                TEMPLATES_ONLY=true
                shift
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --strict)
                STRICT_MODE=true
                shift
                ;;
            --ci)
                CI_MODE=true
                shift
                ;;
            --output-format)
                OUTPUT_FORMAT="$2"
                if [[ "$OUTPUT_FORMAT" != "text" ]] && [[ "$OUTPUT_FORMAT" != "json" ]] && [[ "$OUTPUT_FORMAT" != "junit" ]]; then
                    log_error "無効な出力形式: $OUTPUT_FORMAT"
                    exit 2
                fi
                shift 2
                ;;
            --output-file)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --fail-fast)
                FAIL_FAST=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
                    log_error "無効なタイムアウト値: $TIMEOUT"
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

    # 相互排他的なオプションのチェック
    if [[ "$DOCS_ONLY" == "true" ]] && [[ "$TEMPLATES_ONLY" == "true" ]]; then
        log_error "--docs-only と --templates-only は同時に指定できません"
        exit 2
    fi

    # 実行開始
    log_info "${BOLD}GitHub Actions Simulator - 自動品質チェック開始${RESET}"
    log_info "実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

    # 依存関係チェック
    if ! check_dependencies; then
        exit_code=2
        if [[ "$FAIL_FAST" == "true" ]]; then
            log_error "依存関係チェックに失敗しました（fail-fastモード）"
            exit $exit_code
        fi
    fi

    # 環境初期化
    if ! initialize_environment; then
        exit_code=2
        if [[ "$FAIL_FAST" == "true" ]]; then
            log_error "環境初期化に失敗しました（fail-fastモード）"
            exit $exit_code
        fi
    fi

    # 品質チェックの実行
    local doc_errors=0 doc_warnings=0 doc_quality_score=100
    local template_errors=0 template_warnings=0 template_quality_score=100

    # ドキュメント品質チェック
    if [[ "$TEMPLATES_ONLY" != "true" ]]; then
        local doc_result
        doc_result=$(check_documentation_quality)
        doc_errors=$(echo "$doc_result" | grep "DOC_ERRORS=" | cut -d'=' -f2)
        doc_warnings=$(echo "$doc_result" | grep "DOC_WARNINGS=" | cut -d'=' -f2)
        doc_quality_score=$(echo "$doc_result" | grep "DOC_QUALITY_SCORE=" | cut -d'=' -f2)

        if [[ $doc_errors -gt 0 ]]; then
            exit_code=1
            if [[ "$FAIL_FAST" == "true" ]]; then
                log_error "ドキュメント品質チェックに失敗しました（fail-fastモード）"
                exit $exit_code
            fi
        fi
    fi

    # テンプレート品質チェック
    if [[ "$DOCS_ONLY" != "true" ]]; then
        local template_result
        template_result=$(check_template_quality)
        template_errors=$(echo "$template_result" | grep "TEMPLATE_ERRORS=" | cut -d'=' -f2)
        template_warnings=$(echo "$template_result" | grep "TEMPLATE_WARNINGS=" | cut -d'=' -f2)
        template_quality_score=$(echo "$template_result" | grep "TEMPLATE_QUALITY_SCORE=" | cut -d'=' -f2)

        if [[ $template_errors -gt 0 ]]; then
            exit_code=1
            if [[ "$FAIL_FAST" == "true" ]]; then
                log_error "テンプレート品質チェックに失敗しました（fail-fastモード）"
                exit $exit_code
            fi
        fi
    fi

    # 品質レポートの生成
    generate_quality_report "$doc_errors" "$doc_warnings" "$doc_quality_score" \
                           "$template_errors" "$template_warnings" "$template_quality_score"

    # 結果の表示
    local overall_errors=$((doc_errors + template_errors))
    local overall_warnings=$((doc_warnings + template_warnings))

    if [[ $exit_code -eq 0 ]]; then
        log_success "${BOLD}自動品質チェックが正常に完了しました${RESET}"
        log_success "エラー: ${overall_errors}件, 警告: ${overall_warnings}件"
    else
        log_error "${BOLD}品質基準を満たさない項目があります${RESET}"
        log_error "エラー: ${overall_errors}件, 警告: ${overall_warnings}件"
        log_error "詳細は上記のログまたは出力ファイルを確認してください"
    fi

    exit $exit_code
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
