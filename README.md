# GitHub MCP Server - Docker統合環境

VS Code、Cursor、Kiro等の統合IDEにGitHub MCP Server機能を提供するDocker常駐サービス。

## HTTP transport対応

このプロジェクトは `github-mcp-server` のHTTP接続を優先採用しています。  
複数IDEウィンドウから同時接続しやすく、`stdio` 方式より並列利用に向いた構成です。

**イメージ方針（2026-02-07時点）:**
- 既定イメージ: `ghcr.io/github/github-mcp-server:main`
- 理由: 公式最新リリース `v0.30.3` には `http` サブコマンドが未搭載で、`http` 対応は現時点で `main` タグに含まれるため
- セキュリティ: `.github/workflows/security.yml` でTrivyスキャンを継続実行

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
- GitHub Personal Access Token (PAT) または OAuth対応クライアント

### インストール

```bash
# 1. リポジトリクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 2. 環境整備のみ実行（初回推奨）
./scripts/setup.sh --prepare-only

# 3. セットアップ本実行
./scripts/setup.sh
```

セットアップスクリプトが以下を実行します：
1. `.env`ファイルの作成（初回のみ）
2. GITHUB_PERSONAL_ACCESS_TOKENの設定確認（未設定でも起動可能）
3. 設定ディレクトリの作成
4. Docker依存関係の確認
5. Dockerイメージの取得（pull）
6. サービスの起動
7. コンテナ状態の確認

`--prepare-only` を使うと、Docker未導入の段階でも `.env` と設定ディレクトリの準備だけ先に完了できます。

```bash
# Makefile経由でも実行可能
make prepare
```

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

## HTTPエンドポイント

- 既定URL: `http://127.0.0.1:8082`
- ポートを変更する場合: `GITHUB_MCP_HTTP_PORT` を設定（未設定時は `8082`）
- HTTPモードでは各クライアントから `Authorization: Bearer <PAT/OAuth Token>` ヘッダーを送る必要があります。
- 疎通確認（`401 Unauthorized` でもサーバー起動確認としては正常）:

```bash
curl -i "http://127.0.0.1:${GITHUB_MCP_HTTP_PORT:-8082}/"
```

```bash
# 例: 18082で起動
export GITHUB_MCP_HTTP_PORT=18082
docker compose up -d github-mcp
```

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

### Amazon Q

```bash
# 設定生成
./scripts/generate-ide-config.sh --ide amazonq

# 設定方法
# VS Code: 設定 > Amazon Q > MCP Servers
```

### Codex CLI

```bash
# 設定生成 (TOML)
./scripts/generate-ide-config.sh --ide codex

# 設定ファイルに追記
# ~/.codex/config.toml
```

### Copilot CLI

```bash
# 設定生成 (JSON)
./scripts/generate-ide-config.sh --ide copilot-cli

# Copilot CLI MCP設定ファイルに配置
# ~/.copilot/mcp-config.json
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

# ログ（最新100行）
docker compose logs --tail=100 github-mcp
```

### ヘルスチェック

```bash
# 標準チェック（コンテナ状態 + トークンがあればAPI確認）
./scripts/health-check.sh

# API確認をスキップ
./scripts/health-check.sh --no-api

# API確認を強制実行
./scripts/health-check.sh --with-api
```

## セキュリティ

### イメージのバージョン固定

- `docker-compose.yml` と各サンプルは `GITHUB_MCP_IMAGE` 変数を参照し、デフォルトで `ghcr.io/github/github-mcp-server:main` を使用します。
- 別のバージョンを使う場合は次のように上書きします:

```bash
export GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server:v0.30.3
docker compose pull github-mcp
```

### GitHub Actionsでのセキュリティスキャン

- `Security Scan` ワークフロー（`.github/workflows/security.yml`）で、Trivy の結果を GitHub Security タブへ送信します。
- ワークフローは `push`/`pull_request` に加えて毎週月曜 15:00 JST (`0 6 * * 1` UTC) に実行され、リポジトリ/コンテナ双方の脆弱性を継続的に監視します。

## 開発

### リント・テスト

```bash
# すべてのリント実行
make lint

# シェルスクリプトのみ
make lint-shell

# シェルスクリプトテスト
make test-shell
```

## メンテナンス

### コンテナ管理

```bash
# distrolessイメージのためシェルはありません（exec sh不可）
# 起動コマンドを確認
docker inspect mcp-github --format='Entrypoint={{.Config.Entrypoint}} Cmd={{.Config.Cmd}}'

# コンテナの詳細情報
docker compose ps --format json
docker inspect mcp-github

# リソース使用状況
docker stats mcp-github

# コンテナ再作成（設定変更後）
docker compose up -d --force-recreate github-mcp
```

### イメージ管理

```bash
# イメージ更新
docker compose pull github-mcp
docker compose up -d github-mcp

# イメージ一覧
docker images | grep github-mcp-server

# 古いイメージ削除
docker image prune -f
```

### ログ管理

```bash
# ログ確認（リアルタイム）
docker compose logs -f github-mcp

# ログ確認（最新N行）
docker compose logs --tail=100 github-mcp

# ログ確認（タイムスタンプ付き）
docker compose logs -t github-mcp

# ログ確認（特定期間）
docker compose logs --since="2024-01-01" github-mcp

# ログファイル確認
docker inspect mcp-github --format='{{.LogPath}}'
```

### データ管理

```bash
# ボリューム一覧
docker volume ls | grep mcp

# ボリューム詳細
docker volume inspect mcp-docker_github-mcp-cache

# キャッシュクリア
docker compose down
docker volume rm mcp-docker_github-mcp-cache
docker compose up -d

# 設定ファイルバックアップ
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/
```

### トラブルシューティング

```bash
# コンテナ完全リセット
docker compose down -v
docker compose up -d

# ネットワーク確認
docker network ls | grep mcp
docker network inspect mcp-docker_mcp-network

# リソースクリーンアップ
docker system prune -f
docker volume prune -f

# 全コンテナ・イメージ削除（注意）
docker compose down -v --rmi all

# 全コンテナを強制停止・削除
docker ps -aq | xargs -r docker stop
docker ps -aq | xargs -r docker rm
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
│   ├── health-check.sh       # ヘルスチェック
│   └── lint-shell.sh         # シェルスクリプトLint
├── tests/
│   └── shell/                # シェルスクリプトテスト
├── docs/
│   └── SECURITY_PATCHES.md   # セキュリティ方針
└── examples/
    └── github-mcp/           # サンプルCompose
```

## トラブルシューティング

### サービスが起動しない

```bash
# ログ確認
docker compose logs github-mcp

# 詳細ログ確認
docker compose logs --tail=200 github-mcp

# コンテナ再作成
docker compose down
docker compose up -d

# 強制再作成
docker compose up -d --force-recreate github-mcp
```

### GitHub API接続エラー

```bash
# トークン確認
cat .env | grep GITHUB_PERSONAL_ACCESS_TOKEN

# トークンの有効性確認
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.github.com/user

# コンテナ設定から確認（distrolessのため exec env は非対応）
docker inspect mcp-github --format='{{range .Config.Env}}{{println .}}{{end}}' | grep GITHUB
```

### ヘルスチェック失敗

```bash
# コンテナ状態確認
docker compose ps github-mcp

# 再起動回数の確認
docker inspect mcp-github --format='running={{.State.Running}} restart={{.RestartCount}}'

# ログ確認
docker compose logs --tail=200 github-mcp

# API含むヘルスチェック
./scripts/health-check.sh --with-api
```

### メモリ不足

```bash
# リソース使用状況確認
docker stats mcp-github

# メモリ制限変更（docker-compose.yml編集後）
docker compose up -d --force-recreate github-mcp
```

### ポート競合

```bash
# ポート使用状況確認（使用中のポート番号を指定）
lsof -i :${GITHUB_MCP_HTTP_PORT:-8082}
netstat -an | grep ${GITHUB_MCP_HTTP_PORT:-8082}

# ポート変更（環境変数）
export GITHUB_MCP_HTTP_PORT=8083
docker compose up -d --force-recreate github-mcp
```

## 運用ガードレール

- トークンは`.env`ファイルで管理（gitignore済み）
- コンテナは専用ネットワークで分離
- ログは機密情報をマスキング
- リソース制限: 512MB/1CPU

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照

## 関連プロジェクト

- **[ci-helper](https://github.com/scottlz0310/ci-helper)** - GitHub Actions ローカル実行ツール（旧Actions Simulator）
- **WSL-kernel-watcher** - WSLカーネル更新監視ツール（開発予定）

## 関連リンク

- [GitHub MCP Server公式](https://github.com/github/github-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)
