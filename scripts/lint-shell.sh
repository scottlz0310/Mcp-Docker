#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🔍 シェルスクリプトのリント実行"
echo ""

EXIT_CODE=0

# コマンドの確認
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "⚠️  shellcheck がインストールされていません（スキップ）"
    echo "   インストール: brew install shellcheck"
    exit 0
fi

# スクリプトファイルを配列に収集 (bash 4.0+ mapfile を使用)
mapfile -t SHELL_FILES < <(find "${PROJECT_ROOT}/scripts" -type f -name "*.sh" 2>/dev/null)

if [ "${#SHELL_FILES[@]}" -eq 0 ]; then
    echo "⚠️  シェルスクリプトが見つかりません"
    exit 0
fi

echo "📋 検査対象:"
for file in "${SHELL_FILES[@]}"; do
    echo "  - $file"
done
echo ""

# リント実行
for file in "${SHELL_FILES[@]}"; do
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
