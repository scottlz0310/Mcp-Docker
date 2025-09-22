#!/bin/bash
set -e

# .bashrcから環境変数を読み込み
source ~/.bashrc

# 環境変数チェック（.bashrcまたは.envから）
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    if [ ! -f .env ]; then
        echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN not found in .bashrc and .env file not found."
        echo "   Set token in .bashrc or copy .env.template to .env and configure it."
        exit 1
    fi
    echo "📄 Using .env file for configuration"
else
    echo "📄 Using .bashrc environment variables"
fi

echo "🚀 Starting MCP Docker services..."
docker-compose up -d

echo "✅ Services started!"
docker-compose ps