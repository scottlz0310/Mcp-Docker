#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🔍 シェルスクリプトのリント実行"
echo ""

EXIT_CODE=0

# コマンドの確認
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "❌ shellcheck がインストールされていません"
    echo "   インストール: brew install shellcheck"
    exit 1
fi

# スクリプトファイルを検索
SHELL_FILES=$(find "${PROJECT_ROOT}/scripts" -type f -name "*.sh" 2>/dev/null || true)

if [ -z "$SHELL_FILES" ]; then
    echo "⚠️  シェルスクリプトが見つかりません"
    exit 0
fi

echo "📋 検査対象:"
while IFS= read -r file; do
    echo "  - $file"
done <<< "$SHELL_FILES"
echo ""

# リント実行
for file in $SHELL_FILES; do
    echo "🔍 検査中: $(basename "$file")"
    if shellcheck "$file"; then
        echo "✅ $(basename "$file"): OK"
    else
        echo "❌ $(basename "$file"): エラーあり"
        EXIT_CODE=1
    fi
    echo ""
done

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 すべてのシェルスクリプトが正常です"
else
    echo "❌ エラーが見つかりました"
fi

exit $EXIT_CODE
