#!/bin/bash
# skills/<name>/ の内容が変わったのに catalog.json の revision が据え置きなら失敗する。
#
# revision は配置済みと実行中バイナリのどちらが新しいかを判定する唯一の手掛かりであり、
# 更新を忘れると「バイナリが古い」を検出できず、install が確認なしで巻き戻す。
# 更新忘れを誤判定ではなく CI 失敗として顕在化させるのがこのスクリプトの役割。
set -euo pipefail

BASE_REF="${1:-origin/main}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CATALOG="skills/catalog.json"

cd "${PROJECT_ROOT}"

if ! command -v jq >/dev/null 2>&1; then
    if [ "${CI:-}" = "true" ]; then
        echo "❌ CI 環境で jq が見つかりません（必須）"
        exit 1
    fi
    echo "⚠️  jq がインストールされていません（スキップ）"
    exit 0
fi

if ! git rev-parse --verify --quiet "${BASE_REF}" >/dev/null; then
    echo "❌ base ref ${BASE_REF} を解決できません"
    exit 1
fi

# 比較対象は merge base。base ブランチが進んでいても無関係な差分を拾わないようにする。
MERGE_BASE="$(git merge-base "${BASE_REF}" HEAD)"

revision_of() {
    printf '%s' "$1" | jq -r --arg name "$2" '.skills[$name].revision // empty'
}

BASE_CATALOG="$(git show "${MERGE_BASE}:${CATALOG}" 2>/dev/null || echo '{}')"
HEAD_CATALOG="$(cat "${CATALOG}")"

EXIT_CODE=0
for dir in skills/*/; do
    name="$(basename "${dir}")"

    head_rev="$(revision_of "${HEAD_CATALOG}" "${name}")"
    if [ -z "${head_rev}" ]; then
        echo "❌ ${name}: ${CATALOG} に revision がありません"
        EXIT_CODE=1
        continue
    fi

    # base に存在しない skill は新規追加。revision があれば十分。
    if ! git cat-file -e "${MERGE_BASE}:${dir%/}" 2>/dev/null; then
        echo "✅ ${name}: 新規追加 (rev ${head_rev})"
        continue
    fi

    if git diff --quiet "${MERGE_BASE}" HEAD -- "${dir}"; then
        echo "✅ ${name}: 変更なし (rev ${head_rev})"
        continue
    fi

    base_rev="$(revision_of "${BASE_CATALOG}" "${name}")"
    base_rev="${base_rev:-0}"
    if [ "${head_rev}" -le "${base_rev}" ]; then
        echo "❌ ${name}: 内容が変更されていますが revision が上がっていません (base rev ${base_rev} → HEAD rev ${head_rev})"
        echo "   ${CATALOG} の \"${name}\" の revision を ${base_rev} より大きい値へ更新してください"
        EXIT_CODE=1
        continue
    fi
    echo "✅ ${name}: 内容変更あり (rev ${base_rev} → ${head_rev})"
done

exit "${EXIT_CODE}"
