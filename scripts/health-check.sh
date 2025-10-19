#!/bin/bash
set -euo pipefail

echo "🏥 GitHub MCP Server ヘルスチェック"
echo ""

# コンテナ状態確認
if ! docker compose ps github-mcp | grep -q "Up"; then
    echo "❌ コンテナが起動していません"
    echo "   起動: docker compose up -d github-mcp"
    exit 1
fi
echo "✅ コンテナは起動しています"

# ヘルスチェック
if docker compose exec github-mcp curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ ヘルスチェック成功"
else
    echo "❌ ヘルスチェック失敗"
    echo "   ログ確認: docker compose logs github-mcp"
    exit 1
fi

# GitHub API接続確認
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    if docker compose exec github-mcp curl -f -H "Authorization: token ${GITHUB_PERSONAL_ACCESS_TOKEN}" https://api.github.com/user > /dev/null 2>&1; then
        echo "✅ GitHub API接続成功"
    else
        echo "❌ GitHub API接続失敗"
        echo "   GITHUB_PERSONAL_ACCESS_TOKEN を確認してください"
        exit 1
    fi
else
    echo "⚠️  GITHUB_PERSONAL_ACCESS_TOKEN が設定されていないため、API接続確認をスキップします"
fi

echo ""
echo "🎉 すべてのチェックに合格しました"
