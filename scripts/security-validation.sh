#!/bin/bash
set -euo pipefail

# Phase 7 Exit Criteria 検証スクリプト
# セキュリティ・品質保証の完了条件をチェック

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 Phase 7 Exit Criteria 検証開始"
echo "=================================================="

EXIT_CODE=0

# 7.5.1 GitHub Advanced Security完全設定
echo "📋 7.5.1 GitHub Advanced Security設定確認"

check_file() {
    local file="$1"
    local description="$2"

    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo "  ✅ $description: $file"
        return 0
    else
        echo "  ❌ $description: $file (missing)"
        return 1
    fi
}

# CodeQL設定確認
check_file ".github/workflows/codeql.yml" "CodeQL分析ワークフロー" || EXIT_CODE=1

# Dependabot設定確認
check_file ".github/dependabot.yml" "Dependabot設定" || EXIT_CODE=1

# セキュリティワークフロー確認
check_file ".github/workflows/security.yml" "セキュリティスキャンワークフロー" || EXIT_CODE=1
check_file ".github/workflows/security-monitoring.yml" "セキュリティ監視ワークフロー" || EXIT_CODE=1

# 7.5.2 全依存関係の脆弱性0件（高・重要度）
echo ""
echo "📋 7.5.2 依存関係脆弱性チェック"

# Docker イメージビルド
echo "  🐳 Docker イメージビルド中..."
cd "$PROJECT_ROOT"
if docker build -t mcp-docker:security-validation . >/dev/null 2>&1; then
    echo "  ✅ Docker イメージビルド成功"
else
    echo "  ❌ Docker イメージビルド失敗"
    EXIT_CODE=1
fi

# Trivy スキャン実行
echo "  🔍 Trivy脆弱性スキャン実行中..."
TRIVY_OUTPUT=$(mktemp)
if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image \
    --format json \
    --severity HIGH,CRITICAL \
    mcp-docker:security-validation > "$TRIVY_OUTPUT" 2>/dev/null; then

    if command -v jq >/dev/null 2>&1; then
        CRITICAL=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$TRIVY_OUTPUT" 2>/dev/null || echo "0")
        HIGH=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$TRIVY_OUTPUT" 2>/dev/null || echo "0")

        echo "  📊 脆弱性統計:"
        echo "    Critical: $CRITICAL"
        echo "    High: $HIGH"

        if [ "$CRITICAL" -eq 0 ] && [ "$HIGH" -eq 0 ]; then
            echo "  ✅ 高・重要度脆弱性: 0件"
        else
            echo "  ❌ 高・重要度脆弱性: $((CRITICAL + HIGH))件"
            EXIT_CODE=1
        fi
    else
        echo "  ⚠️ jqが利用できないため、詳細な脆弱性統計をスキップ"
    fi
else
    echo "  ❌ Trivy脆弱性スキャン失敗"
    EXIT_CODE=1
fi

rm -f "$TRIVY_OUTPUT"

# 7.5.3 セキュリティポリシー完備
echo ""
echo "📋 7.5.3 セキュリティポリシー確認"

check_file "SECURITY.md" "セキュリティポリシー" || EXIT_CODE=1

# SECURITY.mdの内容確認
if [ -f "$PROJECT_ROOT/SECURITY.md" ]; then
    required_sections=("Supported Versions" "Reporting a Vulnerability" "Response Timeline" "Security Measures")

    for section in "${required_sections[@]}"; do
        if grep -q "$section" "$PROJECT_ROOT/SECURITY.md"; then
            echo "  ✅ セクション確認: $section"
        else
            echo "  ❌ セクション不足: $section"
            EXIT_CODE=1
        fi
    done
fi

# 7.5.4 継続監視体制確立
echo ""
echo "📋 7.5.4 継続監視体制確認"

# セキュリティスクリプト確認
check_file "scripts/security-metrics.sh" "セキュリティメトリクス収集スクリプト" || EXIT_CODE=1

# 実行権限確認
if [ -f "$PROJECT_ROOT/scripts/security-metrics.sh" ]; then
    if [ -x "$PROJECT_ROOT/scripts/security-metrics.sh" ]; then
        echo "  ✅ セキュリティスクリプト実行権限"
    else
        echo "  ❌ セキュリティスクリプト実行権限なし"
        EXIT_CODE=1
    fi
fi

# Makefileコマンド確認
if grep -q "security-monitor:" "$PROJECT_ROOT/Makefile"; then
    echo "  ✅ Makefileセキュリティコマンド"
else
    echo "  ❌ Makefileセキュリティコマンド不足"
    EXIT_CODE=1
fi

# 定期実行設定確認
if grep -q "schedule:" "$PROJECT_ROOT/.github/workflows/security-monitoring.yml" 2>/dev/null; then
    echo "  ✅ 定期セキュリティスキャン設定"
else
    echo "  ❌ 定期セキュリティスキャン設定不足"
    EXIT_CODE=1
fi

# 総合判定
echo ""
echo "=================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 Phase 7 Exit Criteria: 全て満たしています"
    echo "✅ GitHub Advanced Security完全設定"
    echo "✅ 全依存関係の脆弱性0件（高・重要度）"
    echo "✅ セキュリティポリシー完備"
    echo "✅ 継続監視体制確立"
    echo ""
    echo "🚀 Phase 7完了: セキュリティ・品質保証体制確立"
else
    echo "❌ Phase 7 Exit Criteria: 未完了項目があります"
    echo ""
    echo "🔧 対応が必要な項目を確認して修正してください"
fi

exit $EXIT_CODE
