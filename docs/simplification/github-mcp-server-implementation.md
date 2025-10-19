# GitHub MCP Server 実装仕様

**作成日**: 2025-10-19
**バージョン**: 1.0.0
**関連**: [github-mcp-server-design.md](../architecture/github-mcp-server-design.md)

## 実装優先順位

### P0: 必須機能 (Phase 1)
- Docker Compose設定
- 環境変数管理
- 基本セットアップスクリプト

### P1: コア機能 (Phase 2)
- IDE設定生成スクリプト
- VS Code/Cursor統合
- 基本ドキュメント

### P2: 運用機能 (Phase 3)
- ヘルスチェック
- ログ管理
- 監視機能

### P3: 拡張機能 (Phase 4)
- マルチサーバー対応
- 高度な監視
- パフォーマンス最適化

## ファイル実装詳細

### 1. docker-compose.yml

```yaml
version: '3.8'

services:
  github-mcp:
    image: ghcr.io/github/github-mcp-server:latest
    container_name: mcp-github
    restart: unless-stopped
    
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}
      - GITHUB_API_URL=${GITHUB_API_URL:-https://api.github.com}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    
    ports:
      - "3000:3000"
    
    volumes:
      - ./config/github-mcp:/app/config
      - github-mcp-cache:/app/cache
    
    networks:
      - mcp-network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

volumes:
  github-mcp-cache:
    driver: local

networks:
  mcp-network:
    driver: bridge
```

### 2. .env.template

```bash
# GitHub Personal Access Token
# 取得方法: https://github.com/settings/tokens
# 必須スコープ: repo, workflow, read:org, read:user
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# GitHub API URL (GitHub Enterprise Server用)
# デフォルト: https://api.github.com
# GITHUB_API_URL=https://github.example.com/api/v3

# ログレベル (debug, info, warn, error)
LOG_LEVEL=info

# サーバーポート (デフォルト: 3000)
# SERVER_PORT=3000
```

### 3. scripts/setup.sh

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🚀 GitHub MCP Server セットアップ"
echo ""

# 環境変数ファイルの確認
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    echo "📝 .env ファイルを作成中..."
    cp "${PROJECT_ROOT}/.env.template" "${PROJECT_ROOT}/.env"
    echo "✅ .env ファイルを作成しました"
    echo ""
    echo "⚠️  .env ファイルに GITHUB_PERSONAL_ACCESS_TOKEN を設定してください:"
    echo "   1. https://github.com/settings/tokens でトークンを作成"
    echo "   2. スコープ: repo, workflow, read:org, read:user"
    echo "   3. .env ファイルの GITHUB_PERSONAL_ACCESS_TOKEN に設定"
    echo ""
    exit 1
fi

# GITHUB_PERSONAL_ACCESS_TOKENの確認
if ! grep -q "^GITHUB_PERSONAL_ACCESS_TOKEN=ghp_" "${PROJECT_ROOT}/.env"; then
    echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN が設定されていません"
    echo ""
    echo "📝 .env ファイルに GITHUB_PERSONAL_ACCESS_TOKEN を設定してください:"
    echo "   1. https://github.com/settings/tokens でトークンを作成"
    echo "   2. スコープ: repo, workflow, read:org, read:user"
    echo "   3. .env ファイルの GITHUB_PERSONAL_ACCESS_TOKEN に設定"
    echo ""
    exit 1
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
```

### 4. scripts/generate-ide-config.sh

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    cat <<EOF
使用方法: $0 --ide <IDE名>

IDE名:
  vscode          VS Code / Cursor
  claude-desktop  Claude Desktop
  kiro            Kiro

例:
  $0 --ide vscode
  $0 --ide claude-desktop
EOF
    exit 1
}

IDE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --ide)
            IDE="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

if [[ -z "$IDE" ]]; then
    usage
fi

OUTPUT_DIR="${PROJECT_ROOT}/config/ide-configs/${IDE}"
mkdir -p "${OUTPUT_DIR}"

case "$IDE" in
    vscode)
        cat > "${OUTPUT_DIR}/settings.json" <<'EOF'
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-github",
        "node",
        "/app/dist/index.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ VS Code設定を生成しました: ${OUTPUT_DIR}/settings.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. VS Code設定を開く (Cmd/Ctrl + ,)"
        echo "   2. 'mcp' で検索"
        echo "   3. 上記の設定を追加"
        ;;
    
    claude-desktop)
        cat > "${OUTPUT_DIR}/claude_desktop_config.json" <<'EOF'
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-github",
        "node",
        "/app/dist/index.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ Claude Desktop設定を生成しました: ${OUTPUT_DIR}/claude_desktop_config.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Claude Desktop設定ファイルを開く"
        echo "      macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
        echo "      Linux: ~/.config/Claude/claude_desktop_config.json"
        echo "      Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
        echo "   2. 上記の設定を追加"
        ;;
    
    kiro)
        cat > "${OUTPUT_DIR}/mcp.json" <<'EOF'
{
  "mcp": {
    "servers": {
      "github": {
        "type": "docker",
        "container": "mcp-github",
        "command": "node /app/dist/index.js",
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
EOF
        echo "✅ Kiro設定を生成しました: ${OUTPUT_DIR}/mcp.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Kiro設定ディレクトリに配置"
        echo "      ~/.kiro/settings/mcp.json"
        echo "   2. Kiroを再起動"
        ;;
    
    *)
        echo "❌ 未対応のIDE: $IDE"
        usage
        ;;
esac
```

### 5. scripts/health-check.sh

```bash
#!/bin/bash
set -euo pipefail

echo "🏥 GitHub MCP Server ヘルスチェック"
echo ""

# コンテナ状態確認
if ! docker compose ps github-mcp | grep -q "Up"; then
    echo "❌ コンテナが起動していません"
    echo "   起動: docker compose up -d github-mcp"
    exit 1
fi
echo "✅ コンテナは起動しています"

# ヘルスチェック
if docker compose exec github-mcp curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ ヘルスチェック成功"
else
    echo "❌ ヘルスチェック失敗"
    echo "   ログ確認: docker compose logs github-mcp"
    exit 1
fi

# GitHub API接続確認
if docker compose exec github-mcp curl -f -H "Authorization: token ${GITHUB_PERSONAL_ACCESS_TOKEN}" https://api.github.com/user > /dev/null 2>&1; then
    echo "✅ GitHub API接続成功"
else
    echo "❌ GitHub API接続失敗"
    echo "   GITHUB_PERSONAL_ACCESS_TOKEN を確認してください"
    exit 1
fi

echo ""
echo "🎉 すべてのチェックに合格しました"
```

## 実装チェックリスト

### Phase 1: 基盤構築
- [ ] `docker-compose.yml` 作成
- [ ] `.env.template` 作成
- [ ] `.gitignore` 更新 (`.env` 追加)
- [ ] `scripts/setup.sh` 作成
- [ ] `config/` ディレクトリ作成
- [ ] 基本動作確認

### Phase 2: IDE統合
- [ ] `scripts/generate-ide-config.sh` 作成
- [ ] VS Code設定テンプレート作成
- [ ] Cursor設定テンプレート作成
- [ ] Kiro設定テンプレート作成
- [ ] Claude Desktop設定テンプレート作成
- [ ] 各IDE動作確認

### Phase 3: 運用機能
- [ ] `scripts/health-check.sh` 作成
- [ ] ログローテーション設定
- [ ] ヘルスチェック設定
- [ ] 自動再起動設定
- [ ] バックアップスクリプト作成

### Phase 4: ドキュメント
- [ ] README.md 更新
- [ ] セットアップガイド作成
- [ ] トラブルシューティングガイド作成
- [ ] API仕様ドキュメント作成
- [ ] FAQ作成

## テスト計画

### 統合テスト
```bash
# 1. セットアップテスト
./scripts/setup.sh

# 2. ヘルスチェックテスト
./scripts/health-check.sh

# 3. IDE設定生成テスト
./scripts/generate-ide-config.sh --ide vscode
./scripts/generate-ide-config.sh --ide claude-desktop
./scripts/generate-ide-config.sh --ide kiro
```

### E2Eテスト
- VS Codeでリポジトリ操作
- CursorでIssue作成
- KiroでPR作成
- Claude DesktopでCode Search

## デプロイ手順

```bash
# 1. リポジトリクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 2. セットアップ実行
./scripts/setup.sh

# 3. IDE設定生成
./scripts/generate-ide-config.sh --ide vscode

# 4. 動作確認
./scripts/health-check.sh
```

## ロールバック手順

```bash
# サービス停止
docker compose down

# データ削除 (オプション)
docker volume rm mcp-docker_github-mcp-cache

# 再セットアップ
./scripts/setup.sh
```
