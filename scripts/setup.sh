#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🚀 GitHub MCP Server セットアップ"
echo ""

# GITHUB_PERSONAL_ACCESS_TOKENの確認（環境変数優先）
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    echo "✅ 環境変数 GITHUB_PERSONAL_ACCESS_TOKEN を使用します"
    echo ""
else
    # 環境変数ファイルの確認
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        echo "📝 .env ファイルを作成中..."
        cp "${PROJECT_ROOT}/.env.template" "${PROJECT_ROOT}/.env"
        echo "✅ .env ファイルを作成しました"
        echo ""
        echo "⚠️  .env ファイルに GITHUB_PERSONAL_ACCESS_TOKEN を設定してください:"
        echo "   1. Fine-grained tokenを作成 (推奨):"
        echo "      https://github.com/settings/tokens?type=beta"
        echo "      - Repository access: 対象リポジトリを選択"
        echo "      - Permissions: Contents, Issues, Pull requests, Workflows"
        echo "   2. .env ファイルの GITHUB_PERSONAL_ACCESS_TOKEN に設定"
        echo ""
        echo "💡 または環境変数で設定: export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxx"
        echo ""
        exit 1
    fi

    # .envファイルのトークン確認
    if ! grep -qE "^GITHUB_PERSONAL_ACCESS_TOKEN=(github_pat_|ghp_)" "${PROJECT_ROOT}/.env"; then
        echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN が設定されていません"
        echo ""
        echo "📝 .env ファイルに GITHUB_PERSONAL_ACCESS_TOKEN を設定してください:"
        echo "   1. Fine-grained tokenを作成 (推奨):"
        echo "      https://github.com/settings/tokens?type=beta"
        echo "      - Repository access: 対象リポジトリを選択"
        echo "      - Permissions: Contents, Issues, Pull requests, Workflows"
        echo "   2. .env ファイルの GITHUB_PERSONAL_ACCESS_TOKEN に設定"
        echo ""
        echo "💡 または環境変数で設定: export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxx"
        echo ""
        exit 1
    fi
fi

# 設定ディレクトリの作成
echo "📁 設定ディレクトリを作成中..."
mkdir -p "${PROJECT_ROOT}/config/github-mcp"
echo "✅ 設定ディレクトリを作成しました"
echo ""

# Dockerイメージのプル
echo "📦 Docker イメージをプル中..."
docker compose pull github-mcp
echo "✅ Docker イメージをプルしました"
echo ""

# サービスの起動
echo "🚀 サービスを起動中..."
docker compose up -d github-mcp
echo "✅ サービスを起動しました"
echo ""

# ヘルスチェック
echo "🏥 ヘルスチェック中..."
sleep 5
if docker compose exec github-mcp curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ サービスは正常に動作しています"
else
    echo "⚠️  ヘルスチェックに失敗しました"
    echo "   ログを確認してください: docker compose logs github-mcp"
fi
echo ""

echo "🎉 セットアップ完了！"
echo ""
echo "📋 次のステップ:"
echo "   1. IDE設定を生成: ./scripts/generate-ide-config.sh --ide vscode"
echo "   2. ログを確認: docker compose logs -f github-mcp"
echo "   3. ステータス確認: docker compose ps"
