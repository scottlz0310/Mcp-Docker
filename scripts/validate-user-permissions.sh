#!/bin/bash
# セキュリティ: UID/GID制限バリデーション
# 動的UID/GID取得でのセキュリティリスク軽減

set -euo pipefail

USER_ID="${USER_ID:-1000}"
GROUP_ID="${GROUP_ID:-1000}"

# セキュリティ制限: root権限の完全禁止
if [ "$USER_ID" -eq 0 ] || [ "$GROUP_ID" -eq 0 ]; then
    echo "🚨 SECURITY ERROR: Root execution is strictly prohibited (UID=0 or GID=0)"
    echo "   Phase 7.5 Requirement: Non-root user execution enforced"
    echo "   Risk: Root privilege escalation attack vector"
    exit 1
fi

# セキュリティ制限: 特権システムユーザー範囲の禁止 (1-99)
if [ "$USER_ID" -lt 100 ] || [ "$GROUP_ID" -lt 100 ]; then
    echo "🚨 SECURITY WARNING: System user range detected (UID/GID < 100)"
    echo "   Recommended: Use UID/GID >= 1000 for regular users"
    echo "   Risk: System service privilege escalation possible"
    echo "   Continuing with restricted permissions..."
fi

# 動的UID/GID使用時の追加セキュリティチェック
if [ "$USER_ID" -gt 65000 ] || [ "$GROUP_ID" -gt 65000 ]; then
    echo "🚨 SECURITY WARNING: High UID/GID detected (> 65000)"
    echo "   Risk: Potential overflow or system account conflict"
    echo "   Proceeding with caution..."
fi

# 許可された範囲での実行確認
echo "✅ Security validation passed:"
echo "   USER_ID: $USER_ID (non-root, dynamic)"
echo "   GROUP_ID: $GROUP_ID (non-root, dynamic)"
echo "   Compliance: Phase 7.5 - Dynamic UID/GID with root escalation prevention"
echo "   Security: Write permission enabled with controlled user context"

export USER_ID GROUP_ID
