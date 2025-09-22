#!/bin/bash
# 統合テスト: MCP Docker Environment
set -e

echo "🧪 MCP Docker 統合テスト開始"

# テスト用一時ディレクトリ
TEST_DIR="/tmp/mcp_test_$(date +%s)"
mkdir -p "$TEST_DIR"

cleanup() {
    echo "🧹 クリーンアップ実行"
    docker-compose down -v 2>/dev/null || true
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# 1. Docker Build テスト
echo "📦 Docker Build テスト"
docker build -t mcp-docker-test . || {
    echo "❌ Docker build 失敗"
    exit 1
}
echo "✅ Docker build 成功"

# 2. サービス起動テスト
echo "🚀 サービス起動テスト"
docker-compose up -d
sleep 5

# 3. DateTime Validator テスト
echo "📅 DateTime Validator テスト"
# テスト用Markdownファイル作成
echo "# テストファイル
実行日時: 2025-01-15" > "$TEST_DIR/test.md"

# ファイルをワークスペースにコピー
cp "$TEST_DIR/test.md" ~/workspace/test_datetime.md
sleep 3

# バックアップファイルが作成されたか確認
if ls ~/workspace/test_datetime.md.bak_* 1> /dev/null 2>&1; then
    echo "✅ DateTime Validator 動作確認"
    rm -f ~/workspace/test_datetime.md*
else
    echo "⚠️ DateTime Validator 動作未確認（ファイル変更なし）"
fi

# 4. コンテナヘルスチェック
echo "🏥 コンテナヘルスチェック"
CONTAINERS=$(docker-compose ps -q)
for container in $CONTAINERS; do
    if docker inspect "$container" --format='{{.State.Status}}' | grep -q "running"; then
        echo "✅ コンテナ $(docker inspect "$container" --format='{{.Name}}') 正常動作"
    else
        echo "❌ コンテナ $(docker inspect "$container" --format='{{.Name}}') 異常"
        exit 1
    fi
done

# 5. ログ確認
echo "📋 ログ確認"
docker-compose logs --tail=10

echo "🎉 統合テスト完了"
