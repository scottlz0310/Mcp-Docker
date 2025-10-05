#!/bin/bash
# =============================================================================
# GitHub Release Watcher - 起動スクリプト
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
echo -e "${GREEN}GitHub Release Watcher - Starting...${NC}"
echo -e "${GREEN}==============================================================================${NC}"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# .env ファイルの確認
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "${YELLOW}Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and set your GitHub token and notification settings${NC}"
    echo -e "${YELLOW}Then run this script again${NC}"
    exit 1
fi

# config.toml の確認
CONFIG_FILE="$PROJECT_ROOT/examples/github-release-watcher/config/config.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: config.toml not found at $CONFIG_FILE${NC}"
    exit 1
fi

# GitHub Token の確認
if [ -f .env ]; then
    # shellcheck source=/dev/null
    source .env
fi
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}Warning: GITHUB_TOKEN is not set in .env${NC}"
    echo -e "${YELLOW}The service may not work properly without it${NC}"
fi

# Docker Compose でサービスを起動
echo -e "${GREEN}Starting GitHub Release Watcher service...${NC}"
docker compose up -d github-release-watcher

# ステータス確認
echo ""
echo -e "${GREEN}Service started successfully!${NC}"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo "  docker compose logs -f github-release-watcher"
echo ""
echo -e "${GREEN}Status:${NC}"
echo "  docker compose ps github-release-watcher"
echo ""
echo -e "${GREEN}Stop:${NC}"
echo "  docker compose stop github-release-watcher"
echo "  # or use: $SCRIPT_DIR/stop.sh"
echo ""
echo -e "${GREEN}==============================================================================${NC}"

# ログをフォロー（オプション）
if [ "$1" = "--follow" ] || [ "$1" = "-f" ]; then
    echo -e "${GREEN}Following logs (Ctrl+C to exit)...${NC}"
    docker compose logs -f github-release-watcher
fi
