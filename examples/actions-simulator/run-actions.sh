#!/bin/bash
# Actions Simulator - シンプルな起動スクリプト

set -euo pipefail

WORKFLOW=${1:-.github/workflows/ci.yml}
JOB=${2:-}
EVENT=${3:-push}

echo "🚀 GitHub Actions シミュレーターを実行中..."
echo "   ワークフロー: $WORKFLOW"
echo "   イベント: $EVENT"
${JOB:+echo "   ジョブ: $JOB"}
echo ""

# Docker イメージを使用
docker run --rm \
  -v "$PWD:/workspace" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
  -w /workspace \
  ghcr.io/scottlz0310/mcp-docker-actions:latest \
  act "$EVENT" \
  -W "$WORKFLOW" \
  ${JOB:+-j "$JOB"} \
  --verbose
