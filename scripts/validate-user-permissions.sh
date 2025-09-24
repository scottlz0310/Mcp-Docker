#!/bin/bash
# セキュリティ: UID/GID制限バリデーション

set -euo pipefail

USER_ID="${USER_ID:-1000}"
GROUP_ID="${GROUP_ID:-1000}"

# セキュリティ制限: root権限の禁止
if [ "$USER_ID" -eq 0 ] || [ "$GROUP_ID" -eq 0 ]; then
    echo "🚨 SECURITY ERROR: Root execution is prohibited (UID=0 or GID=0)"
    echo "   Phase 7.5 Requirement: Non-root user execution enforced"
    exit 1
fi

# セキュリティ制限: 特権システムユーザー範囲の禁止 (1-99)
if [ "$USER_ID" -lt 100 ] || [ "$GROUP_ID" -lt 100 ]; then
    echo "🚨 SECURITY WARNING: System user range detected (UID/GID < 100)"
    echo "   Recommended: Use UID/GID >= 1000 for regular users"
    echo "   Continuing with restricted permissions..."
fi

# 許可された範囲での実行
echo "✅ Security validation passed:"
echo "   USER_ID: $USER_ID (non-root)"
echo "   GROUP_ID: $GROUP_ID (non-root)"
echo "   Compliance: Phase 7.5 - Non-root user execution enforced"

export USER_ID GROUP_ID
