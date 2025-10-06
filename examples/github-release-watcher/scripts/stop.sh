#!/bin/bash
# =============================================================================
# GitHub Release Watcher - 停止スクリプト
# =============================================================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# スクリプトのディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}GitHub Release Watcher - Stopping...${NC}"
echo -e "${GREEN}==============================================================================${NC}"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# サービスを停止
echo -e "${GREEN}Stopping GitHub Release Watcher service...${NC}"
docker compose stop github-release-watcher

echo ""
echo -e "${GREEN}Service stopped successfully!${NC}"
echo ""
echo -e "${GREEN}To remove the container:${NC}"
echo "  docker compose rm -f github-release-watcher"
echo ""
echo -e "${GREEN}To restart:${NC}"
echo "  $SCRIPT_DIR/start.sh"
echo ""
echo -e "${GREEN}==============================================================================${NC}"
