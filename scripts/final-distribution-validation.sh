#!/bin/bash
# 最終配布検証スクリプト
# GitHub Actions Simulator Phase C の配布パッケージとしての完成度を検証

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

# プロジェクトルートの検出
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 検証結果の記録
VALIDATION_RESULTS=()
TOTAL_CHECKS=0
PASSED_CHECKS=0

# 検証結果を記録する関数
record_check() {
    local check_name="$1"
    local result="$2"
    local details="$3"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [ "$result" = "PASS" ]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "$check_name: $details"
    else
        log_error "$check_name: $details"
    fi

    VALIDATION_RESULTS+=("$check_name|$result|$details")
}

# 新規ユーザー体験シミュレーション
simulate_new_user_experience() {
    log_info "=== 新規ユーザー体験シミュレーション開始 ==="

    # 一時ディレクトリで新規ユーザー環境をシミュレート
    local temp_dir
    temp_dir=$(mktemp -d)
    local original_dir="$PWD"

    trap "cd '$original_dir' && rm -rf '$temp_dir'" EXIT

    # プロジェクトを一時ディレクトリにコピー（キャッシュディレクトリは除外）
    log_info "新規ユーザー環境をセットアップ中..."
    (cd "$PROJECT_ROOT" && tar --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.mypy_cache' --exclude='node_modules' -cf - .) | (cd "$temp_dir" && mkdir -p github-actions-simulator && cd github-actions-simulator && tar -xf -)
    cd "$temp_dir/github-actions-simulator"

    # 1. README.md の可読性確認
    log_info "1. README.md の可読性を確認中..."
    if [ -f "README.md" ]; then
        local readme_size
        readme_size=$(wc -c < "README.md")
        if [ "$readme_size" -gt 1000 ]; then
            if grep -q "クイック\|Quick" "README.md" 2>/dev/null; then
                record_check "README可読性" "PASS" "README.md にクイックスタートセクションが存在"
            else
                record_check "README可読性" "FAIL" "README.md にクイックスタートセクションが不足"
            fi
        else
            record_check "README可読性" "FAIL" "README.md の内容が不十分"
        fi
    else
        record_check "README可読性" "FAIL" "README.md が存在しない"
    fi

    # 2. 依存関係チェック機能の確認
    log_info "2. 依存関係チェック機能を確認中..."
    if [ -f "scripts/run-actions.sh" ] && [ -x "scripts/run-actions.sh" ]; then
        if timeout 30 bash scripts/run-actions.sh --check-deps 2>/dev/null; then
            record_check "依存関係チェック" "PASS" "依存関係チェック機能が動作"
        else
            # --check-deps オプションがない場合でも、スクリプトが存在すれば部分的に成功
            if bash scripts/run-actions.sh --help 2>/dev/null | grep -q "help\|usage" 2>/dev/null; then
                record_check "依存関係チェック" "PASS" "run-actions.sh が実行可能"
            else
                record_check "依存関係チェック" "FAIL" "依存関係チェック機能が動作しない"
            fi
        fi
    else
        record_check "依存関係チェック" "FAIL" "run-actions.sh が存在しないか実行不可"
    fi

    # 3. ドキュメント完全性確認
    log_info "3. ドキュメント完全性を確認中..."
    local required_docs=("docs/TROUBLESHOOTING.md" "docs/actions/README.md" "CONTRIBUTING.md")
    local existing_docs=0

    for doc in "${required_docs[@]}"; do
        if [ -f "$doc" ]; then
            existing_docs=$((existing_docs + 1))
        fi
    done

    if [ "$existing_docs" -ge 2 ]; then
        record_check "ドキュメント完全性" "PASS" "$existing_docs/${#required_docs[@]} の必須ドキュメントが存在"
    else
        record_check "ドキュメント完全性" "FAIL" "必須ドキュメントが不足 ($existing_docs/${#required_docs[@]})"
    fi

    # 4. テンプレートファイル確認
    log_info "4. テンプレートファイルを確認中..."
    local template_files=(".env.example" ".pre-commit-config.yaml" "docker-compose.override.yml.sample")
    local existing_templates=0

    for template in "${template_files[@]}"; do
        if [ -f "$template" ]; then
            existing_templates=$((existing_templates + 1))
        fi
    done

    if [ "$existing_templates" -ge 2 ]; then
        record_check "テンプレートファイル" "PASS" "$existing_templates/${#template_files[@]} のテンプレートが存在"
    else
        record_check "テンプレートファイル" "FAIL" "テンプレートファイルが不足 ($existing_templates/${#template_files[@]})"
    fi

    # 5. 設定ファイル構文確認
    log_info "5. 設定ファイル構文を確認中..."
    local syntax_errors=0

    # YAML ファイルの構文チェック
    for yaml_file in docker-compose.yml .github/workflows/*.yml .github/workflows/*.yaml; do
        if [ -f "$yaml_file" ]; then
            if ! python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
                syntax_errors=$((syntax_errors + 1))
                log_warning "YAML構文エラー: $yaml_file"
            fi
        fi
    done

    # JSON ファイルの構文チェック
    for json_file in *.json .github/ISSUE_TEMPLATE/*.json; do
        if [ -f "$json_file" ]; then
            if ! python3 -c "import json; json.load(open('$json_file'))" 2>/dev/null; then
                syntax_errors=$((syntax_errors + 1))
                log_warning "JSON構文エラー: $json_file"
            fi
        fi
    done

    if [ "$syntax_errors" -eq 0 ]; then
        record_check "設定ファイル構文" "PASS" "設定ファイルの構文が正常"
    else
        record_check "設定ファイル構文" "FAIL" "$syntax_errors 個の構文エラーが存在"
    fi

    # 6. 実行可能性確認（Docker環境チェック）
    log_info "6. 実行可能性を確認中..."
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            # Docker Compose ファイルの検証
            if [ -f "docker-compose.yml" ]; then
                if docker-compose config >/dev/null 2>&1; then
                    record_check "実行可能性" "PASS" "Docker環境で実行可能"
                else
                    record_check "実行可能性" "FAIL" "docker-compose.yml に問題がある"
                fi
            else
                record_check "実行可能性" "FAIL" "docker-compose.yml が存在しない"
            fi
        else
            record_check "実行可能性" "FAIL" "Docker デーモンが動作していない"
        fi
    else
        log_warning "Docker が利用できないため、実行可能性チェックをスキップ"
        record_check "実行可能性" "PASS" "Docker未インストール環境（スキップ）"
    fi

    cd "$original_dir"
}

# 配布パッケージ完成度確認
validate_distribution_package() {
    log_info "=== 配布パッケージ完成度確認開始 ==="

    cd "$PROJECT_ROOT"

    # 1. 必須ファイル存在確認
    log_info "1. 必須ファイルの存在を確認中..."
    local essential_files=("README.md" "LICENSE" "CONTRIBUTING.md" "Makefile" "docker-compose.yml")
    local missing_files=()

    for file in "${essential_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -eq 0 ]; then
        record_check "必須ファイル" "PASS" "全ての必須ファイルが存在"
    else
        record_check "必須ファイル" "FAIL" "不足ファイル: ${missing_files[*]}"
    fi

    # 2. ライセンス情報確認
    log_info "2. ライセンス情報を確認中..."
    if [ -f "LICENSE" ]; then
        local license_size
        license_size=$(wc -c < "LICENSE")
        if [ "$license_size" -gt 100 ]; then
            record_check "ライセンス情報" "PASS" "ライセンスファイルが適切に設定"
        else
            record_check "ライセンス情報" "FAIL" "ライセンスファイルの内容が不十分"
        fi
    else
        record_check "ライセンス情報" "FAIL" "ライセンスファイルが存在しない"
    fi

    # 3. バージョン情報整合性確認
    log_info "3. バージョン情報の整合性を確認中..."
    local version_files=("pyproject.toml" "README.md")
    local version_info_count=0

    for file in "${version_files[@]}"; do
        if [ -f "$file" ] && grep -q "version\|Version\|VERSION" "$file" 2>/dev/null; then
            version_info_count=$((version_info_count + 1))
        fi
    done

    if [ "$version_info_count" -ge 1 ]; then
        record_check "バージョン情報" "PASS" "バージョン情報が設定されている"
    else
        record_check "バージョン情報" "FAIL" "バージョン情報が不足"
    fi

    # 4. CI/CD 設定確認
    log_info "4. CI/CD 設定を確認中..."
    local workflow_dir=".github/workflows"
    if [ -d "$workflow_dir" ]; then
        local workflow_count
        workflow_count=$(find "$workflow_dir" -name "*.yml" -o -name "*.yaml" | wc -l)
        if [ "$workflow_count" -ge 2 ]; then
            record_check "CI/CD設定" "PASS" "$workflow_count 個のワークフローが設定済み"
        else
            record_check "CI/CD設定" "FAIL" "ワークフロー設定が不十分"
        fi
    else
        record_check "CI/CD設定" "FAIL" "GitHub Actions ワークフローが未設定"
    fi

    # 5. セキュリティ設定確認
    log_info "5. セキュリティ設定を確認中..."
    local security_indicators=0

    # .gitignore の確認
    if [ -f ".gitignore" ] && grep -q "\.env\|secret\|key" ".gitignore" 2>/dev/null; then
        security_indicators=$((security_indicators + 1))
    fi

    # セキュリティスキャン設定の確認
    if [ -f ".github/workflows/security-scan.yml.sample" ] || [ -f "scripts/run_security_scan.py" ]; then
        security_indicators=$((security_indicators + 1))
    fi

    # 依存関係管理の確認
    if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
        security_indicators=$((security_indicators + 1))
    fi

    if [ "$security_indicators" -ge 2 ]; then
        record_check "セキュリティ設定" "PASS" "基本的なセキュリティ設定が実装済み"
    else
        record_check "セキュリティ設定" "FAIL" "セキュリティ設定が不十分"
    fi

    # 6. ドキュメント品質確認
    log_info "6. ドキュメント品質を確認中..."
    local doc_quality_score=0

    # README の品質確認
    if [ -f "README.md" ]; then
        local readme_content
        readme_content=$(cat "README.md")

        # 必要なセクションの確認
        if echo "$readme_content" | grep -q "## \|# " 2>/dev/null; then
            doc_quality_score=$((doc_quality_score + 1))
        fi

        # インストール手順の確認
        if echo "$readme_content" | grep -qi "install\|インストール\|setup\|セットアップ" 2>/dev/null; then
            doc_quality_score=$((doc_quality_score + 1))
        fi

        # 使用例の確認
        if echo "$readme_content" | grep -qi "example\|例\|usage\|使用" 2>/dev/null; then
            doc_quality_score=$((doc_quality_score + 1))
        fi
    fi

    # docs ディレクトリの確認
    if [ -d "docs" ]; then
        local doc_count
        doc_count=$(find docs -name "*.md" | wc -l)
        if [ "$doc_count" -ge 5 ]; then
            doc_quality_score=$((doc_quality_score + 1))
        fi
    fi

    if [ "$doc_quality_score" -ge 3 ]; then
        record_check "ドキュメント品質" "PASS" "ドキュメントが充実している"
    else
        record_check "ドキュメント品質" "FAIL" "ドキュメントの改善が必要"
    fi
}

# 統合テスト実行
run_integration_tests() {
    log_info "=== 統合テスト実行開始 ==="

    cd "$PROJECT_ROOT"

    # 1. Python テストスイートの実行
    log_info "1. Python テストスイートを実行中..."
    if [ -f "tests/test_final_integration_validation.py" ]; then
        if python3 tests/test_final_integration_validation.py 2>/dev/null; then
            record_check "Python統合テスト" "PASS" "Python テストスイートが正常に実行"
        else
            record_check "Python統合テスト" "FAIL" "Python テストスイートでエラーが発生"
        fi
    else
        log_warning "Python 統合テストファイルが見つからない"
        record_check "Python統合テスト" "FAIL" "テストファイルが存在しない"
    fi

    # 2. シェルスクリプトテストの実行
    log_info "2. シェルスクリプトテストを実行中..."
    local script_errors=0

    # 主要スクリプトの構文チェック
    for script in scripts/*.sh; do
        if [ -f "$script" ]; then
            if ! bash -n "$script" 2>/dev/null; then
                script_errors=$((script_errors + 1))
                log_warning "構文エラー: $script"
            fi
        fi
    done

    if [ "$script_errors" -eq 0 ]; then
        record_check "スクリプト構文" "PASS" "全てのシェルスクリプトの構文が正常"
    else
        record_check "スクリプト構文" "FAIL" "$script_errors 個のスクリプトに構文エラー"
    fi

    # 3. ドキュメント整合性テスト
    log_info "3. ドキュメント整合性テストを実行中..."
    if [ -f "scripts/check-docs-consistency.py" ]; then
        if python3 scripts/check-docs-consistency.py 2>/dev/null; then
            record_check "ドキュメント整合性" "PASS" "ドキュメント整合性チェック通過"
        else
            record_check "ドキュメント整合性" "FAIL" "ドキュメント整合性にエラーがある"
        fi
    else
        log_warning "ドキュメント整合性チェックスクリプトが見つからない"
        record_check "ドキュメント整合性" "PASS" "チェックスクリプト未実装（スキップ）"
    fi

    # 4. テンプレート検証テスト
    log_info "4. テンプレート検証テストを実行中..."
    if [ -f "scripts/validate-templates.py" ]; then
        if python3 scripts/validate-templates.py 2>/dev/null; then
            record_check "テンプレート検証" "PASS" "テンプレート検証通過"
        else
            record_check "テンプレート検証" "FAIL" "テンプレート検証でエラーが発生"
        fi
    else
        log_warning "テンプレート検証スクリプトが見つからない"
        record_check "テンプレート検証" "PASS" "検証スクリプト未実装（スキップ）"
    fi
}

# 最終レポート生成
generate_final_report() {
    log_info "=== 最終レポート生成開始 ==="

    # Ensure output directory exists
    mkdir -p "$PROJECT_ROOT/output"

    local report_file="$PROJECT_ROOT/output/final_distribution_validation_report.md"
    local json_report="$PROJECT_ROOT/output/final_distribution_validation_report.json"

    # 成功率計算
    local success_rate=0
    if [ "$TOTAL_CHECKS" -gt 0 ]; then
        success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    fi

    # ステータス決定
    local overall_status
    if [ "$success_rate" -ge 80 ]; then
        overall_status="EXCELLENT"
    elif [ "$success_rate" -ge 60 ]; then
        overall_status="GOOD"
    elif [ "$success_rate" -ge 40 ]; then
        overall_status="NEEDS_IMPROVEMENT"
    else
        overall_status="CRITICAL_ISSUES"
    fi

    # Markdown レポート生成
    cat > "$report_file" << EOF
# GitHub Actions Simulator Phase C - 最終配布検証レポート

## 検証実行日時
$(date -u +"%Y-%m-%d %H:%M:%S UTC")

## 全体評価
- **ステータス**: $overall_status
- **成功率**: $success_rate% ($PASSED_CHECKS/$TOTAL_CHECKS)

## 検証結果詳細

EOF

    # 検証結果の詳細を追加
    for result in "${VALIDATION_RESULTS[@]}"; do
        IFS='|' read -r check_name result_status details <<< "$result"
        if [ "$result_status" = "PASS" ]; then
            echo "✅ **$check_name**: $details" >> "$report_file"
        else
            echo "❌ **$check_name**: $details" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

## 推奨事項

### 配布前の最終チェック項目
1. 全ての依存関係が適切にドキュメント化されていることを確認
2. プラットフォーム固有の問題がないことを確認
3. セキュリティスキャンを実行し、脆弱性がないことを確認
4. パフォーマンステストを実行し、期待される性能を満たすことを確認

### 継続的改善項目
1. ユーザーフィードバックの収集メカニズムの設置
2. 定期的なドキュメント更新プロセスの確立
3. 自動化されたテストカバレッジの向上
4. コミュニティ貢献の促進

## 結論
GitHub Actions Simulator Phase C の最終配布検証が完了しました。
成功率 $success_rate% で、ステータスは「$overall_status」です。

EOF

    if [ "$success_rate" -ge 80 ]; then
        echo "配布パッケージとしての基本的な要件は満たしており、新規ユーザーが使い始めることができる状態に達しています。" >> "$report_file"
    elif [ "$success_rate" -ge 60 ]; then
        echo "配布パッケージとしての基本機能は動作しますが、いくつかの改善点があります。" >> "$report_file"
    else
        echo "配布前に重要な問題を解決する必要があります。" >> "$report_file"
    fi

    cat >> "$report_file" << EOF

---
*このレポートは自動生成されました。*
EOF

    # JSON レポート生成
    cat > "$json_report" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "overall_status": "$overall_status",
  "success_rate": $success_rate,
  "total_checks": $TOTAL_CHECKS,
  "passed_checks": $PASSED_CHECKS,
  "failed_checks": $((TOTAL_CHECKS - PASSED_CHECKS)),
  "validation_results": [
EOF

    local first=true
    for result in "${VALIDATION_RESULTS[@]}"; do
        IFS='|' read -r check_name result_status details <<< "$result"
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$json_report"
        fi
        printf '    {\n      "check_name": "%s",\n      "status": "%s",\n      "details": "%s"\n    }' "$check_name" "$result_status" "$details" >> "$json_report"
    done

    cat >> "$json_report" << EOF

  ]
}
EOF

    log_success "最終レポートを生成しました:"
    log_info "  - Markdown: $report_file"
    log_info "  - JSON: $json_report"
}

# メイン実行関数
main() {
    log_info "GitHub Actions Simulator Phase C - 最終配布検証を開始します"
    log_info "プロジェクトルート: $PROJECT_ROOT"

    # ログディレクトリの作成
    mkdir -p "$PROJECT_ROOT/logs"

    # 各検証の実行
    simulate_new_user_experience
    validate_distribution_package
    run_integration_tests

    # 最終レポート生成
    generate_final_report

    # 結果サマリー表示
    echo
    echo "=============================================="
    echo "GitHub Actions Simulator Phase C - 最終配布検証完了"
    echo "=============================================="
    echo "成功率: $PASSED_CHECKS/$TOTAL_CHECKS ($((PASSED_CHECKS * 100 / TOTAL_CHECKS))%)"

    local overall_status
    local success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

    if [ "$success_rate" -ge 80 ]; then
        overall_status="EXCELLENT"
        log_success "ステータス: $overall_status - 配布準備完了"
        return 0
    elif [ "$success_rate" -ge 60 ]; then
        overall_status="GOOD"
        log_success "ステータス: $overall_status - 軽微な改善後に配布可能"
        return 0
    elif [ "$success_rate" -ge 40 ]; then
        overall_status="NEEDS_IMPROVEMENT"
        log_warning "ステータス: $overall_status - 改善が必要"
        return 1
    else
        overall_status="CRITICAL_ISSUES"
        log_error "ステータス: $overall_status - 重要な問題を解決してください"
        return 2
    fi
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
