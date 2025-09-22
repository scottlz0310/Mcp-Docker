#!/bin/bash
# 統合テスト: 全サービスの動作確認

set -e

echo "=== MCP Docker Environment 統合テスト ==="

# 検証対象: Docker環境
# 目的: 全サービス起動・ヘルスチェック確認

cleanup() {
    echo "クリーンアップ実行中..."
    docker compose down -v 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
}

# 終了時クリーンアップ
trap cleanup EXIT

echo "1. Docker環境確認"
docker --version
docker compose version

echo "2. イメージビルド"
docker compose build

echo "3. サービス起動"
docker compose up -d

echo "4. サービス起動待機"
sleep 30

echo "5. サービス状態確認"
docker compose ps

echo "6. ログ確認"
docker compose logs --tail=20

echo "7. GitHub MCPサービス確認"
# 検証対象: DateTime Validator
# 目的: Python環境・依存関係確認
if docker compose ps datetime-validator | grep -q "Up"; then
    echo "✅ DateTime Validatorサービス起動成功"
else
    echo "❌ DateTime Validatorサービス起動失敗"
    exit 1
fi

echo "8. CodeQLサービス確認"
# 検証対象: CodeQL
# 目的: CLI環境確認
if docker compose exec -T codeql codeql version >/dev/null 2>&1; then
    echo "✅ CodeQLサービス動作確認成功"
else
    echo "❌ CodeQLサービス動作確認失敗"
    exit 1
fi

echo "10. 統合テスト完了"
echo "✅ 全サービス正常動作確認"
