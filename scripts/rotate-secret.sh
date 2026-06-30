#!/bin/bash
set -euo pipefail

DOCKER_BIN=${DOCKER_BIN:-docker}

PROJECT=$("$DOCKER_BIN" compose config 2>/dev/null | grep -E '^name:' | awk '{print $2}' | tr -d '\r')
if [ -z "$PROJECT" ]; then
  echo "エラー: Compose project 名を取得できませんでした" >&2
  exit 1
fi

VOLUME=$("$DOCKER_BIN" volume ls \
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

# Git Bash によるコンテナ内パスの Windows パス変換を無効化する。
if ! MSYS_NO_PATHCONV=1 "$DOCKER_BIN" run --rm -v "$VOLUME:/data" alpine \
  sh -c 'rm -f /data/config.yaml && test ! -e /data/config.yaml'; then
  echo "エラー: /data/config.yaml の削除を確認できませんでした ($VOLUME)" >&2
  exit 1
fi
echo "config.yaml を削除しました ($VOLUME)"
