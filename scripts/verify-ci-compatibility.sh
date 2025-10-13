#!/bin/bash
# CI互換性検証スクリプト
set -euo pipefail

echo "🔍 CI互換性検証開始"

WORKFLOW="${1:-.github/workflows/basic-test.yml}"
RUN_ID="${2:-}"
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOCAL_LOG="${LOG_DIR}/local.log"
CI_LOG="${LOG_DIR}/ci.log"
DIFF_LOG="${LOG_DIR}/diff.log"

# ローカル実行
echo "📦 ローカル実行中..."
act -W "${WORKFLOW}" > "${LOCAL_LOG}" 2>&1 || true

# CI実行ログ取得
echo "☁️  CI実行ログ取得中..."
if command -v gh &> /dev/null; then
    if gh auth status &> /dev/null; then
        if [ -n "${RUN_ID}" ]; then
            echo "   実行ID指定: ${RUN_ID}"
            gh run view "${RUN_ID}" --log > "${CI_LOG}" 2>&1 || {
                echo "❌ 実行ID ${RUN_ID} のログ取得失敗"
                echo "💡 URLから実行IDを抽出: https://github.com/USER/REPO/actions/runs/18464895672 → 18464895672"
                exit 1
            }
        else
            gh run view --log > "${CI_LOG}" 2>&1 || {
                echo "⚠️  CI実行ログ取得失敗。最新のCI実行がない可能性があります"
                echo ""
                echo "✅ ローカル実行完了: ${LOCAL_LOG}"
                echo "💡 CI実行ログと比較するには:"
                echo "   1. 特定の実行IDを指定: ./scripts/verify-ci-compatibility.sh ${WORKFLOW} 18464895672"
                echo "   2. またはGitHubで新しいワークフローを実行して再実行"
                exit 0
            }
        fi
    else
        echo "⚠️  GitHub CLI未認証"
        echo ""
        echo "✅ ローカル実行完了: ${LOCAL_LOG}"
        echo "💡 CI互換性を検証するには:"
        echo "   1. GitHub CLIを認証: gh auth login"
        echo "   2. 再度このスクリプトを実行"
        exit 0
    fi
else
    echo "⚠️  GitHub CLI未インストール"
    echo ""
    echo "✅ ローカル実行完了: ${LOCAL_LOG}"
    echo "💡 CI互換性を検証するには:"
    echo "   1. GitHub CLIをインストール: https://cli.github.com/"
    echo "   2. 認証: gh auth login"
    echo "   3. 再度このスクリプトを実行"
    exit 0
fi

# ログ正規化
echo "🔄 ログ正規化中..."
NORMALIZED_CI="${LOG_DIR}/ci_normalized.log"
NORMALIZED_LOCAL="${LOG_DIR}/local_normalized.log"

./scripts/normalize-log.sh "${CI_LOG}" > "${NORMALIZED_CI}"
./scripts/normalize-log.sh "${LOCAL_LOG}" > "${NORMALIZED_LOCAL}"

# 差分分析（正規化後）
echo "📊 差分分析中..."
diff -u "${NORMALIZED_CI}" "${NORMALIZED_LOCAL}" | tee "${DIFF_LOG}" || true

# 差異率計算
DIFF_LINES=$(wc -l < "${DIFF_LOG}" || echo 0)
TOTAL_LINES=$(wc -l < "${NORMALIZED_CI}" || echo 1)
if [ "$TOTAL_LINES" -eq 0 ]; then
    TOTAL_LINES=1
fi
SIMILARITY=$((100 - (DIFF_LINES * 100 / TOTAL_LINES)))

echo ""
if [ "$TOTAL_LINES" -eq 1 ] && [ "$DIFF_LINES" -eq 0 ]; then
    echo "⚠️  正規化後のログが空です"
else
    echo "✅ CI互換性: ${SIMILARITY}%"
fi
echo "📄 ログファイル:"
echo "  - ローカル: ${LOCAL_LOG}"
echo "  - CI: ${CI_LOG}"
echo "  - 正規化済みローカル: ${NORMALIZED_LOCAL}"
echo "  - 正規化済みCI: ${NORMALIZED_CI}"
echo "  - 差分: ${DIFF_LOG}"
