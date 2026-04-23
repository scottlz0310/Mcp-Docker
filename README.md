# GitHub MCP Server - Docker統合環境

VS Code、Cursor、Kiro、Claude Desktop等の統合IDEにGitHub MCP Server機能を提供するDocker常駐サービス。

## HTTP transport対応

このプロジェクトは `github-mcp-server` のHTTP接続を優先採用しています。
複数IDEウィンドウから同時接続しやすく、`stdio` 方式より並列利用に向いた構成です。
Claude Desktop だけは HTTP transport 非対応のため、`docker run -i ... stdio` でサーバーを直接起動します。

**イメージ方針（2026-04-24時点）:**
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
- Node.js 18+ / `npx`（`mcp-http-bridge` を使う場合のみ）
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

### OAuthの準備（GitHub OAuth App登録）

OAuthプロキシ経由で接続する場合は、GitHub OAuth App の Client ID / Client Secret が必要です。

1. GitHub OAuth App を作成
  - https://github.com/settings/applications/new にアクセス
  - Application name: 任意（例: GitHub MCP Proxy）
  - Homepage URL: http://localhost:8084
  - Authorization callback URL: http://localhost:8084/callback

2. 作成後に Client ID と Client Secret を取得

3. `.env` に設定

```bash
GITHUB_MCP_CLIENT_ID=Ov23xxxxxxxxxxxxxxxx
GITHUB_MCP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 必要に応じて変更（未設定時は 8084）
# GITHUB_OAUTH_PROXY_PORT=8084
# GITHUB_OAUTH_PROXY_BASE_URL=http://localhost:8084
```

4. OAuthプロキシを起動

```bash
make start-oauth
```

カスタムイメージで起動する場合:

```bash
make start-custom-oauth
```

5. 起動確認

```bash
make status-oauth
curl -i "http://127.0.0.1:${GITHUB_OAUTH_PROXY_PORT:-8084}/.well-known/oauth-authorization-server"
```

補足:
- callback URL は `GITHUB_OAUTH_PROXY_BASE_URL` と一致させてください（末尾 `/callback` を付与）。
- `copilot-review-mcp` で使っている OAuth App を共有しても問題ありません。

## copilot-review-mcp

`services/copilot-review-mcp` は Copilot code review の依頼・待機・スレッド対応を自動化する MCP サーバー（Go 実装）です。

### ツール一覧

| ツール | 説明 |
|---|---|
| `request_copilot_review` | Copilot にレビューを依頼（GraphQL mutation） |
| `get_copilot_review_status` | GitHub 上のレビュー状態を即時取得 |
| `start_copilot_review_watch` | 非同期 watch を開始（SQLite 永続化） |
| `get_copilot_review_watch_status` | watch の現在状態を cheap read |
| `list_copilot_review_watches` | アクティブな watch 一覧（watch_id 回復用） |
| `cancel_copilot_review_watch` | watch をキャンセル |
| `get_pr_review_cycle_status` | PR レビューサイクル全体の状態を取得 |
| `get_review_threads` | レビュースレッド一覧を取得 |
| `reply_to_review_thread` | レビュースレッドに返信 |
| `reply_and_resolve_review_thread` | 返信して同時に解決済みへ変更 |
| `resolve_review_thread` | レビュースレッドを解決済みへ変更 |
| `wait_for_copilot_review` | blocking で完了を待機（legacy fallback） |

### 推奨フロー（非同期 Watch）

1. `get_copilot_review_status` で GitHub 上の即時 snapshot を確認する
2. 未完了なら `start_copilot_review_watch` を呼ぶ
3. 他の作業を進めながら `get_copilot_review_watch_status` で cheap read する
4. `watch_id` を見失ったら `list_copilot_review_watches` で回復する
5. 不要になった watch は `cancel_copilot_review_watch` で止める

`wait_for_copilot_review` は host 都合で blocking wait が必要な場合だけ使う legacy fallback です。

詳細は [docs/copilot-review-watch-tools.md](docs/copilot-review-watch-tools.md) を参照してください。

## HTTPエンドポイント

- 既定でホストに公開されるURL（OAuthプロキシ経由）: `http://127.0.0.1:8084`
- `github-mcp` 本体の `8082` は Docker ネットワーク内向け（`expose`）で、ホスト直公開はしません。
- OAuth で接続する場合は `make start-oauth`（カスタムイメージは `make start-custom-oauth`）を実行してください。
- ポートを変更する場合:
  - `GITHUB_OAUTH_PROXY_PORT`（未設定時は `8084`）
  - `GITHUB_MCP_HTTP_PORT`（コンテナ内向け、未設定時は `8082`）
- 直接 HTTP 接続するクライアントでは、必要に応じて `Authorization: Bearer <PAT/OAuth Token>` ヘッダーを送ってください。
- Claude Desktop は `docker run -i ... stdio` で接続します。`-e GITHUB_PERSONAL_ACCESS_TOKEN`（値なし）を指定すると、ホスト環境変数を安全に受け渡せます。
- 疎通確認（`200 OK` で discovery ドキュメントが返ることを確認）:

```bash
curl -i "http://127.0.0.1:${GITHUB_OAUTH_PROXY_PORT:-8084}/.well-known/oauth-authorization-server"
```

```bash
# 例: 18084でOAuthプロキシ起動
export GITHUB_OAUTH_PROXY_PORT=18084
make start-oauth
```

```bash
# github-mcp本体のみ起動（ホスト直アクセスなし）
make start
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

生成される設定は `docker run -i --rm ... stdio` で GitHub MCP Server を直接起動する形式です。

```json
{
  "mcpServers": {
    "github-mcp-server-docker": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-v",
        "C:\\Users\\dev\\src\\Mcp-Docker\\config\\github-mcp:/app/config:rw",
        "-v",
        "github-mcp-cache:/app/cache:rw",
        "ghcr.io/github/github-mcp-server:main",
        "stdio"
      ]
    }
  }
}
```

`-i` は必須です。省略すると stdio 通信が切断されます。

`-e GITHUB_PERSONAL_ACCESS_TOKEN` は値を埋め込まずに書いてください。

カスタムイメージを使う場合は `GITHUB_MCP_IMAGE` を設定して再生成できます。

### mcp-http-bridge

`mcp-http-bridge` は MCP stdio フレームを受け取り、HTTP POST で MCP サーバーへそのまま転送する最小CLIです。

```bash
npx -y mcp-http-bridge --url http://127.0.0.1:8084/mcp
```

```bash
npx -y mcp-http-bridge \
  --url http://127.0.0.1:8084/mcp \
  --header "Authorization: Bearer your_token_here" \
  --timeout 10000
```

サポートするオプション:

- `--url`: 転送先の MCP HTTP エンドポイント
- `--header`: 追加 HTTP ヘッダ。複数回指定可能
- `--timeout`: HTTP タイムアウト（ミリ秒、既定 `30000`）

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
# 起動（github-mcp本体のみ）
make start

# OAuthプロキシ経由で起動（localhost:8084）
make start-oauth

# カスタムビルド + OAuthプロキシ起動
make start-custom-oauth

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
├── docker-compose.yml          # サービス定義（github-mcp）
├── docker-compose.custom.yml   # カスタムビルドイメージ用 Compose
├── Dockerfile.github-mcp-server # カスタムイメージ Dockerfile
├── Makefile                    # タスク管理
├── SECURITY.md                 # セキュリティポリシー
├── ci-helper.toml.example     # ci-helper 設定例
├── .env.template              # 環境変数テンプレート
├── .env                       # 環境変数（gitignore）
├── renovate.json              # Renovate 依存更新設定
├── services/
│   ├── copilot-review-mcp/   # Copilot review 非同期 Watch MCP サーバー（Go）
│   └── github-oauth-proxy/   # GitHub OAuth プロキシサーバー（Go）
├── patches/
│   └── github/               # github-mcp-server ソースパッチ
│       └── list_pr_review_threads.go  # PR レビュースレッド一覧ツール
├── config/
│   └── github-mcp/           # github-mcp-server 設定
├── scripts/
│   ├── setup.sh              # セットアップ
│   ├── generate-ide-config.sh # IDE設定生成
│   ├── health-check.sh       # ヘルスチェック
│   ├── lint-shell.sh         # シェルスクリプトLint
│   ├── verify-bridge-e2e.js  # mcp-http-bridge E2E 検証
│   └── verify-mcp-endpoint.js # MCP エンドポイント疎通確認
├── bin/
│   └── mcp-http-bridge.js    # MCP stdio-to-HTTP ブリッジ CLI
├── src/
│   └── mcp-http-bridge.js    # mcp-http-bridge ソース
├── tests/
│   ├── node/                 # Node.js テスト
│   │   └── mcp-http-bridge.test.js
│   └── shell/                # シェルスクリプトテスト（Bats）
│       └── test_scripts.bats
├── docs/
│   ├── SECURITY_PATCHES.md   # セキュリティ方針
│   ├── copilot-review-watch-tools.md # Watch ツール仕様
│   ├── design/               # 設計ドキュメント
│   ├── skills/               # Claude スキルテンプレート
│   └── bug-reports/          # バグレポート
└── examples/
    └── github-mcp/           # サンプル Compose 設定
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

- トークンは`.env`ファイルやコンテナ環境変数で管理し、Claude Desktop 側には極力持ち込まない
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
