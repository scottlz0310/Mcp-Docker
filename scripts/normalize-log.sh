#!/bin/bash
# ログ正規化スクリプト - CI/actのログフォーマット差異を吸収（行内置換方式）

set -euo pipefail

INPUT="${1:-}"
if [ -z "$INPUT" ]; then
    echo "Usage: $0 <log-file>" >&2
    exit 1
fi

# 行内のパターンを置換（行自体は削除しない）
sed -E \
    -e 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+Z//g' \
    -e 's/time="[^"]+"\s*//g' \
    -e 's/level=(debug|info|warning|error)\s*//g' \
    -e 's/msg="([^"]+)"/\1/g' \
    -e 's/module=[a-z]+\s*//g' \
    -e 's/\s*UNKNOWN STEP\s*/ /g' \
    -e 's/##\[(group|endgroup)\]//g' \
    -e 's/\[command\]//g' \
    -e 's/\[DEBUG\]\s*//g' \
    -e 's/\[36;1m//g' \
    -e 's/\[0m//g' \
    -e 's/SHA:[a-f0-9]{40}/SHA:NORMALIZED/g' \
    -e 's/[a-f0-9]{40}/COMMIT_HASH/g' \
    -e 's|/home/runner/work/[^/]+/[^/]+|/workspace|g' \
    -e 's|/home/[^/]+/workspace/[^/]+|/workspace|g' \
    -e 's/token: \*\*\*/token: REDACTED/g' \
    -e 's/AUTHORIZATION: basic \*\*\*/AUTHORIZATION: REDACTED/g' \
    "$INPUT" | \
# 空行のみ削除
grep -v "^[[:space:]]*$" || true
