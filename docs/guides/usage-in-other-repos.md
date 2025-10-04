# 他リポジトリでの使用方法

このガイドでは、Mcp-Docker のサービスを他のプロジェクトで使用する方法を説明します。

## 概要

Mcp-Docker は以下の方法で他のプロジェクトから利用できます：

1. **Docker Compose での参照** - 既存のプロジェクトに追加
2. **examples/ のコピー** - 設定ファイルをコピーして使用
3. **スクリプトの単体使用** - 特定のツールのみ使用

## 方法1: Docker Compose での参照

### 既存プロジェクトに追加

```yaml
# あなたのプロジェクトの docker-compose.yml
services:
  # 既存のサービス...
  your-app:
    build: .
    depends_on:
      - github-mcp

  # Mcp-Docker のサービスを追加
  github-mcp:
    image: ghcr.io/scottlz0310/mcp-docker:latest
    container_name: mcp-github
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}
    command:
      - "node"
      - "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"
    restart: unless-stopped
```

### 環境変数の設定

```bash
# .env ファイルに追加
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

## 方法2: Examples のコピー

### GitHub MCP サーバーの場合

```bash
# 1. 設定をコピー
cd ~/your-project
cp -r ~/workspace/Mcp-Docker/examples/github-mcp ./mcp

# 2. 環境変数を設定
cd mcp
cp .env.example .env
vim .env  # GITHUB_TOKENを設定

# 3. 起動
docker compose up -d
```

### Actions Simulator の場合

```bash
# 1. スクリプトをコピー
cd ~/your-project
cp ~/workspace/Mcp-Docker/examples/actions-simulator/run-actions.sh .
chmod +x run-actions.sh

# 2. 実行
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
./run-actions.sh .github/workflows/ci.yml
```

### DateTime Validator の場合

```bash
# 1. 設定をコピー
cd ~/your-docs-project
cp -r ~/workspace/Mcp-Docker/examples/datetime-validator ./date-check

# 2. 設定を調整
cd date-check
cp .env.example .env
# WATCH_DIRECTORYを適切なパスに変更

# 3. バリデーション実行
docker compose up -d
```

## 方法3: Git Submodule として管理

```bash
# Submodule として追加
cd ~/your-project
git submodule add https://github.com/scottlz0310/Mcp-Docker.git tools/mcp-docker

# 使用
cd tools/mcp-docker
docker compose up -d github-mcp
```

## IDE との統合

### VS Code での使用

`.vscode/tasks.json` に追加：

```json
{
  "tasks": [
    {
      "label": "Start GitHub MCP",
      "type": "shell",
      "command": "docker",
      "args": ["compose", "-f", "mcp/docker-compose.yml", "up", "-d"],
      "group": "build"
    },
    {
      "label": "Run Actions Test",
      "type": "shell",
      "command": "./run-actions.sh",
      "args": ["${input:workflowFile}"],
      "group": "test"
    }
  ],
  "inputs": [
    {
      "id": "workflowFile",
      "description": "Workflow file path",
      "default": ".github/workflows/ci.yml",
      "type": "promptString"
    }
  ]
}
```

### Claude Desktop での MCP 設定

`~/.config/claude-desktop/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "exec", "mcp-github",
        "node", "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

## トラブルシューティング

### よくある問題

**Q: GitHub Token の権限が足りない**
```bash
# 解決: Token の権限を確認
# GitHub Settings → Developer settings → Personal access tokens
# 必要な権限: repo, read:org, read:user
```

**Q: Docker の権限エラー**
```bash
# 解決: ユーザーを docker グループに追加
sudo usermod -aG docker $USER
# ログアウト・ログインして反映
```

**Q: ポートが既に使用されている**
```yaml
# 解決: docker-compose.yml でポートを変更
services:
  github-mcp:
    ports:
      - "3001:3000"  # 3000から3001に変更
```

### ログの確認方法

```bash
# サービスのログを確認
docker compose logs -f github-mcp

# 全サービスのログ
docker compose logs

# 特定の時刻以降のログ
docker compose logs --since="2025-01-01T10:00:00"
```

## ベストプラクティス

### 1. 環境変数の管理

```bash
# .env.example を必ず作成
echo "GITHUB_TOKEN=your_token_here" > .env.example

# .gitignore に .env を追加
echo ".env" >> .gitignore
```

### 2. Docker イメージの更新

```bash
# 定期的にイメージを更新
docker compose pull
docker compose up -d
```

### 3. 設定の分離

```yaml
# プロジェクト固有の設定は extends で分離
services:
  github-mcp:
    extends:
      file: ./mcp/docker-compose.yml
      service: github-mcp
    environment:
      - PROJECT_SPECIFIC_VAR=value
```

## 複数プロジェクトでの共有

### 共通設定の作成

```bash
# ~/shared/mcp-docker/ に共通設定を配置
mkdir -p ~/shared/mcp-docker
cp -r ~/workspace/Mcp-Docker/examples/* ~/shared/mcp-docker/
```

### プロジェクトでの参照

```yaml
# docker-compose.yml
services:
  github-mcp:
    extends:
      file: ~/shared/mcp-docker/github-mcp/docker-compose.yml
      service: github-mcp
    env_file:
      - ~/shared/mcp-docker/github-mcp/.env
```

## サポート

- 詳細な使用方法は各サービスの [examples/](../examples/) を参照
- 問題が発生した場合は [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) を確認
- 設定例は [examples/](../examples/) ディレクトリを参照
