#!/bin/bash
set -euo pipefail

VOLUME=$(docker volume ls --filter label=com.docker.compose.volume=mcp-gateway-data -q | head -1 | tr -d '\r')
if [ -z "$VOLUME" ]; then
  echo "mcp-gateway-data volume が見つかりません（初回起動前の状態です）"
  exit 0
fi

docker run --rm -v "$VOLUME:/data" alpine rm -f /data/config.yaml
echo "config.yaml を削除しました ($VOLUME)"
