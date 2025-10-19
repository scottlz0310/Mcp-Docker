# GitHub MCP Server - Docker統合環境

VS Code、Cursor、Kiro等の統合IDEにGitHub MCP Server機能を提供するDocker常駐サービス。

## 概要

GitHub公式のMCPサーバーをDockerコンテナとして常駐させ、各IDEから統一的にGitHub機能を利用できます。

### 提供機能

- **リポジトリ管理**: 作成、削除、設定
- **Issue/PR操作**: 作成、更新、コメント、レビュー
- **GitHub Actions連携**: ワークフロー実行、ログ取得
- **Code Search**: コード検索、ファイル検索
- **Discussions**: ディスカッション管理
- **Projects**: プロジェクト管理

## クイックスタート

### 前提条件

- Docker 20.10+
- GitHub Personal Access Token (PAT)

### インストール

```bash
# 1. リポジトリクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 2. セットアップ実行
./scripts/setup.sh
```

セットアップスクリプトが以下を実行します：
1. `.env`ファイルの作成（初回のみ）
2. GITHUB_PERSONAL_ACCESS_TOKENの設定確認
3. 設定ディレクトリの作成
4. Dockerイメージのプル
5. サービスの起動
6. ヘルスチェック

### GitHub Token設定

**方法1: 環境変数で設定 (推奨)**

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_your_token_here
./scripts/setup.sh
```

環境変数が設定されている場合、`.env`ファイルの設定は不要です。

**方法2: .envファイルで設定**

**Fine-grained personal access token (推奨)**

1. [GitHub Settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta) でトークンを作成
2. 設定:
   - **Repository access**: 対象リポジトリを選択 (または All repositories)
   - **Permissions**:
     - Contents: Read and write
     - Issues: Read and write
     - Pull requests: Read and write
     - Workflows: Read and write
     - Metadata: Read-only (自動選択)
3. `.env`ファイルに設定:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_your_token_here
```

**Classic token (非推奨)**

1. [GitHub Settings > Tokens (classic)](https://github.com/settings/tokens) でトークンを作成
2. スコープ: `repo`, `workflow`, `read:org`, `read:user`
3. `.env`ファイルに設定:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

**注意**: 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` が設定されている場合、`.env`ファイルの設定より優先されます。

## IDE統合

### VS Code / Cursor

```bash
# 設定生成
./scripts/generate-ide-config.sh --ide vscode

# 設定ファイルに追加
# VS Code: settings.json
# Cursor: settings.json
```

### Claude Desktop

```bash
# 設定生成
./scripts/generate-ide-config.sh --ide claude-desktop

# 設定ファイルに追加
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
# Linux: ~/.config/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json
```

### Kiro

```bash
# 設定生成
./scripts/generate-ide-config.sh --ide kiro

# 設定ファイルに配置
# ~/.kiro/settings/mcp.json
```

## 基本操作

### サービス管理

```bash
# 起動
docker compose up -d

# 停止
docker compose down

# 再起動
docker compose restart github-mcp

# ステータス確認
docker compose ps

# ログ確認
docker compose logs -f github-mcp
```

### ヘルスチェック

```bash
./scripts/health-check.sh
```

## ディレクトリ構成

```
Mcp-Docker/
├── docker-compose.yml          # サービス定義
├── .env.template              # 環境変数テンプレート
├── .env                       # 環境変数（gitignore）
├── config/
│   └── github-mcp/           # サーバー設定
├── scripts/
│   ├── setup.sh              # セットアップ
│   ├── generate-ide-config.sh # IDE設定生成
│   └── health-check.sh       # ヘルスチェック
├── docs/
│   └── setup/                # IDE別セットアップガイド
└── examples/
    └── ide-configs/          # IDE設定例
```

## トラブルシューティング

### サービスが起動しない

```bash
# ログ確認
docker compose logs github-mcp

# コンテナ再作成
docker compose down
docker compose up -d
```

### GitHub API接続エラー

```bash
# トークン確認
cat .env | grep GITHUB_PERSONAL_ACCESS_TOKEN

# トークンの有効性確認
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### ヘルスチェック失敗

```bash
# コンテナ状態確認
docker compose ps

# ヘルスチェックログ
docker compose logs github-mcp | grep health
```

## セキュリティ

- トークンは`.env`ファイルで管理（gitignore済み）
- コンテナは専用ネットワークで分離
- ログは機密情報をマスキング
- リソース制限: 512MB/1CPU

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照

## 関連リンク

- [GitHub MCP Server公式](https://github.com/github/github-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [設計ドキュメント](.kiro/specs/architecture/github-mcp-server-design.md)
