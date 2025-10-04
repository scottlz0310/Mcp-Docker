# GitHub MCP サーバー

GitHub リポジトリの情報取得・操作を行う Model Context Protocol (MCP) サーバーです。

## 概要

- **用途**: GitHub API を使ったリポジトリ情報の取得、Issue/PR の管理
- **MCP 対応**: Claude Desktop、VS Code、その他 MCP 対応ツールで使用可能
- **導入時間**: 約5分

## クイックスタート

### 1. ファイルをコピー

```bash
# 他のプロジェクトで使用する場合
cd ~/your-project
cp -r ~/workspace/Mcp-Docker/examples/github-mcp ./mcp-server
cd mcp-server
```

### 2. 環境変数を設定

```bash
cp .env.example .env
vim .env
```

`.env` ファイルで以下を設定：

```bash
# 必須: GitHub Personal Access Token
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxx

# オプション
LOG_LEVEL=info
```

### 3. サーバー起動

```bash
docker compose up -d
```

### 4. MCP クライアントで接続

#### Claude Desktop の場合

`~/.config/claude-desktop/claude_desktop_config.json` に追加：

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["exec", "mcp-github", "node", "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

#### VS Code MCP 拡張機能の場合

VS Code の設定で MCP サーバーを追加：

```json
{
  "mcp.servers": [
    {
      "name": "github",
      "command": "docker",
      "args": ["exec", "mcp-github", "node", "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"]
    }
  ]
}
```

## GitHub Token の取得方法

1. GitHub の Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" をクリック
3. 必要な権限を選択：
   - `repo` - プライベートリポジトリアクセス（必要に応じて）
   - `public_repo` - パブリックリポジトリアクセス
   - `read:org` - Organization情報読み取り
   - `read:user` - ユーザー情報読み取り

## 利用可能な機能

- リポジトリ情報の取得
- Issue の一覧・詳細表示・作成・更新
- Pull Request の一覧・詳細表示・作成・更新
- ファイル内容の取得・更新
- ブランチ操作
- コミット履歴の参照

## トラブルシューティング

### サーバーが起動しない

```bash
# ログを確認
docker compose logs github-mcp

# コンテナの状態を確認
docker compose ps
```

### MCP クライアントで接続できない

1. GitHub Token が正しく設定されているか確認
2. Token の権限が適切か確認
3. サーバーが起動しているか確認

### API レート制限に達した場合

GitHub API のレート制限（認証済み: 5000回/時間）に達した場合は、しばらく待ってから再試行してください。

## 設定オプション

| 環境変数 | 必須 | デフォルト | 説明 |
|---------|------|----------|------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | ✅ | - | GitHub Personal Access Token |
| `LOG_LEVEL` | ❌ | `info` | ログレベル (debug, info, warn, error) |

## 他の使用方法

### 既存のプロジェクトに追加

既存の `docker-compose.yml` にサービスを追加：

```yaml
services:
  # 既存のサービス...

  github-mcp:
    image: ghcr.io/scottlz0310/mcp-docker:latest
    container_name: mcp-github
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}
    command:
      - "node"
      - "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"
```

### カスタム設定

必要に応じて `docker-compose.yml` をカスタマイズ：

```yaml
services:
  github-mcp:
    image: ghcr.io/scottlz0310/mcp-docker:latest
    ports:
      - "3000:3000"  # ポート公開（必要に応じて）
    volumes:
      - ./config:/config  # 設定ファイル（必要に応じて）
    restart: always  # 自動再起動
```
