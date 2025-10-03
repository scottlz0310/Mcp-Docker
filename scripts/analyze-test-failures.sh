#!/usr/bin/env bash
# 失敗テストのエラー原因を分析するスクリプト

set -euo pipefail

LOG_DIR="test-results"
LATEST_SUMMARY=$(ls -t "${LOG_DIR}"/test-summary-*.log 2>/dev/null | head -1)

if [[ -z "${LATEST_SUMMARY}" ]]; then
    echo "エラー: テスト結果が見つかりません"
    exit 1
fi

echo "=== 失敗テストのエラー分析 ==="
echo "ログディレクトリ: ${LOG_DIR}"
echo ""

# 失敗テストのログファイルを抽出
TIMESTAMP=$(basename "${LATEST_SUMMARY}" | sed 's/test-summary-\(.*\)\.log/\1/')

echo "## エラー分類"
echo ""

# エラーパターンごとに分類
declare -A ERROR_TYPES
ERROR_TYPES["ImportError"]="インポートエラー"
ERROR_TYPES["ModuleNotFoundError"]="モジュール未検出"
ERROR_TYPES["FileNotFoundError"]="ファイル未検出"
ERROR_TYPES["docker"]="Docker関連エラー"
ERROR_TYPES["Connection"]="接続エラー"
ERROR_TYPES["Timeout"]="タイムアウト"

for log_file in "${LOG_DIR}"/*-${TIMESTAMP}.log; do
    [[ -f "${log_file}" ]] || continue

    test_name=$(basename "${log_file}" | sed "s/-${TIMESTAMP}\.log//")

    # エラー内容を抽出
    if grep -q "FAILED\|ERROR\|ERRORS" "${log_file}" 2>/dev/null; then
        echo "### ${test_name}"

        # 主要エラーを抽出
        for pattern in "${!ERROR_TYPES[@]}"; do
            if grep -i "${pattern}" "${log_file}" | head -3; then
                echo "  → ${ERROR_TYPES[$pattern]}"
                break
            fi
        done 2>/dev/null

        echo ""
    fi
done

echo ""
echo "=== エラー統計 ==="

# エラータイプ別カウント
echo "インポートエラー: $(grep -l "ImportError\|ModuleNotFoundError" "${LOG_DIR}"/*-${TIMESTAMP}.log 2>/dev/null | wc -l)"
echo "Docker関連: $(grep -l -i "docker" "${LOG_DIR}"/*-${TIMESTAMP}.log 2>/dev/null | wc -l)"
echo "ファイル未検出: $(grep -l "FileNotFoundError" "${LOG_DIR}"/*-${TIMESTAMP}.log 2>/dev/null | wc -l)"
echo "接続エラー: $(grep -l -i "connection" "${LOG_DIR}"/*-${TIMESTAMP}.log 2>/dev/null | wc -l)"

echo ""
echo "=== 推奨修正アクション ==="
echo "1. conftest.py実装（プロジェクトルート取得の一元化）"
echo "2. インポートパス修正"
echo "3. Docker環境依存の問題解決"
