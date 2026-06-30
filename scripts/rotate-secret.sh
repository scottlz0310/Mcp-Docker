#!/bin/bash
set -euo pipefail

PROJECT=$(docker compose config 2>/dev/null | grep -E '^name:' | awk '{print $2}' | tr -d '\r')
if [ -z "$PROJECT" ]; then
  echo "エラー: Compose project 名を取得できませんでした" >&2
  exit 1
fi

VOLUME=$(docker volume ls \
  --filter label=com.docker.compose.volume=mcp-gateway-data \
  --filter label=com.docker.compose.project="$PROJECT" \
  -q | tr -d '\r')

COUNT=$(printf '%s' "$VOLUME" | grep -c . || true)
if [ "$COUNT" -eq 0 ]; then
  echo "mcp-gateway-data volume が見つかりません（初回起動前の状態です）"
  exit 0
elif [ "$COUNT" -gt 1 ]; then
  echo "エラー: mcp-gateway-data volume が複数見つかりました:" >&2
  printf '%s\n' "$VOLUME" >&2
  exit 1
fi

docker run --rm -v "$VOLUME:/data" alpine rm -f /data/config.yaml
echo "config.yaml を削除しました ($VOLUME)"
