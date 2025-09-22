#!/bin/bash
set -e

echo "🚀 MCP Docker Environment Setup"
echo "================================"

# 環境変数チェック
./scripts/check-env.sh

# 必要なディレクトリ作成
mkdir -p logs config

# ビルド
echo "🔨 Building services..."
make build

echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  make start    - Start core services"
echo "  make github   - GitHub MCP only"
echo "  make datetime - DateTime validator only"
echo "  make codeql   - Run CodeQL analysis"
