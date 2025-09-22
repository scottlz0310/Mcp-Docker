#!/bin/bash

# GitHubトークンを.bashrcから読み込む（すでに読み込まれていれば不要）
# shellcheck disable=SC1090
source ~/.bashrc

# チェック
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
  echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN が設定されていません"
  exit 1
fi
# MCPサーバー起動
docker run -p 8080:8080 \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
  ghcr.io/github/github-mcp-server
