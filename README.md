# GitHub MCP Server - Docker統合環境

VS Code、Cursor、Kiro、Claude Desktop等の統合IDEにGitHub MCP Server機能を提供するDocker常駐サービス。

## HTTP transport対応

このプロジェクトは `github-mcp-server` のHTTP接続を優先採用しています。
複数IDEウィンドウから同時接続しやすく、`stdio` 方式より並列利用に向いた構成です。
Claude Desktop だけは HTTP transport 非対応のため、`docker run -i ... stdio` でサーバーを直接起動します。

**イメージ方針（2026-04-24時点）:**
- 既定イメージ: `ghcr.io/github/github-mcp-server:main`
- 理由: 公式安定リリースの最新は `v1.0.0`（`v0.31.0` 以降 Streamable HTTP / `http` サブコマンドが正式搭載）。安定性より最新機能を優先する場合は `main` タグを使用
- セキュリティ: `.github/workflows/security.yml` でTrivyスキャンを継続実行

## 設計思想：GitHub認証の一元化

従来のローカル Docker 環境では、依然として各 MCP ホストへの PAT（Personal Access Token）の注入が必要です。
GUI ショートカットやスタートメニュー、あるいは環境変数が一貫して継承されない異なるシェルから IDE を起動する場合、
この仕組みは不安定になりがちです。

本プロジェクトでは、**GitHub 認証を Docker ランタイム内に一元化**することで、この問題を回避しています。
OAuth プロキシ経由で接続する場合、MCP ホスト（各 IDE）の設定にはシークレット値ではなくローカルエンドポイントの URL のみが含まれます。直接 HTTP 接続する場合も、トークン値をファイルに書かず環境変数参照（`${env:GITHUB_PERSONAL_ACCESS_TOKEN}`）で渡せます。

```
IDE（VS Code / Cursor / Kiro 等）
  │  URL のみ（mcp-gateway 経由）または env var 参照（直接 HTTP 接続）
  ▼
mcp-gateway  ←── Docker ランタイム内で OAuth 認証・ルーティングを担当
  │
  ├──▶ github-mcp-server（Docker ネットワーク内に閉じ込め）
  └──▶ copilot-review-mcp（Docker ネットワーク内に閉じ込め）
```

これにより：

- IDE 側の設定ファイルにトークン値を書かなくて済む（`.vscode/settings.json` 等にシークレット値不要）
- 起動方法（GUI ショートカット・ターミナル・スタートメニュー）に関わらず認証が安定して機能する
- トークンの差し替えは Docker 側の `.env` または `GITHUB_PERSONAL_ACCESS_TOKEN` 環境変数で完結し、環境変数が `.env` より優先される

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
- Node.js 18+（`verify-mcp-endpoint.js` を使用する場合、または `generate-ide-config.sh --ide claude-desktop --service mcp-gateway` が生成する `npx mcp-remote` 設定で Claude Desktop を利用する場合に必要。Claude Desktop は `mcp-gateway` 経由ではなく `docker run -i --rm <image> stdio` による直接利用を推奨）

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

mcp-gateway 経由で接続する場合は、GitHub OAuth App の Client ID / Client Secret が必要です。

1. GitHub OAuth App を作成
  - https://github.com/settings/applications/new にアクセス
  - Application name: 任意（例: GitHub MCP Gateway）
  - Homepage URL: http://localhost:8080
  - Authorization callback URL: http://localhost:8080/callback

2. 作成後に Client ID と Client Secret を取得

3. `.env` に設定

```bash
GITHUB_MCP_CLIENT_ID=Ov23xxxxxxxxxxxxxxxx
GITHUB_MCP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 必要に応じて変更（未設定時は 8080）
# MCP_GATEWAY_PORT=8080
# MCP_GATEWAY_BASE_URL=http://localhost:8080
```

4. mcp-gateway を起動

```bash
make start-gateway
```

5. 起動確認

```bash
make status-gateway
curl -i "http://127.0.0.1:${MCP_GATEWAY_PORT:-8080}/health"
```

補足:
- callback URL は `MCP_GATEWAY_BASE_URL` と一致させてください（末尾 `/callback` を付与）。
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

### スキルテンプレートとの一体運用（推奨）

`copilot-review-mcp` は単体でも使えますが、`docs/skills/pr-review-cycle.md` のスキルテンプレートと組み合わせることで、Copilot レビュー依頼から完了待機・スレッド対応・サマリ投稿までを AI エージェントに一括して自律実行させられます。

**自動化できるサイクル:**

```
Copilot レビュー依頼
  → async watch で完了待機（notifications/resources/updated 通知対応）
  → スレッド取得・分類・採否判断
  → 修正・コミット
  → 全スレッドへ返信 & resolve
  → サイクル評価（再レビュー要否判定）
  → PR サマリコメント投稿
  → マージ判断はユーザーに委ねる
```

**セットアップ:**

```bash
# スキルテンプレートを AI エージェントのスキルディレクトリへコピー
cp docs/skills/pr-review-cycle.md ~/.claude/skills/
```

コピー後、IDE のツール名プレフィックス（`{CRM}` / `{GH}`）をお使いの環境に合わせて書き換えてください（詳細はテンプレート内の「プレースホルダーの読み替え」を参照）。

**使い方:**

PR 作成直後または `request_copilot_review` ツール呼び出し直後に `/pr-review-cycle` スキルを起動するだけです。

## HTTPエンドポイント

- mcp-gateway 経由 URL: `http://127.0.0.1:8080`
  - GitHub MCP Server: `http://127.0.0.1:8080/mcp/github`
  - Copilot Review MCP: `http://127.0.0.1:8080/mcp/copilot-review`
- `github-mcp` と `copilot-review-mcp` は Docker ネットワーク内向け（`expose`）でホスト直公開しません。
- mcp-gateway で接続するには `make start-gateway` を実行してください。
- ポートを変更する場合:
  - `MCP_GATEWAY_PORT`（未設定時は `8080`）
  - `GITHUB_MCP_HTTP_PORT`（コンテナ内向け、未設定時は `8082`）
- 直接 HTTP 接続するクライアントでは、必要に応じて `Authorization: Bearer <PAT/OAuth Token>` ヘッダーを送ってください。
- Claude Desktop は `docker run -i ... stdio` で接続します。`-e GITHUB_PERSONAL_ACCESS_TOKEN`（値なし）を指定すると、ホスト環境変数を安全に受け渡せます。
- 疎通確認（`200 OK` でヘルス情報が返ることを確認）:

```bash
curl -i "http://127.0.0.1:${MCP_GATEWAY_PORT:-8080}/health"
```

```bash
# 例: 18080でmcp-gateway起動
export MCP_GATEWAY_PORT=18080
make start-gateway
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

# OAuthプロキシ(mcp-gateway)経由で起動（localhost:8080）
make start-gateway

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
export GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server:v1.0.0
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
├── Makefile                    # タスク管理
├── SECURITY.md                 # セキュリティポリシー
├── ci-helper.toml.example     # ci-helper 設定例
├── .env.template              # 環境変数テンプレート
├── .env                       # 環境変数（gitignore）
├── renovate.json              # Renovate 依存更新設定
├── services/
│   ├── copilot-review-mcp/   # Copilot review 非同期 Watch MCP サーバー（Go）
│   └── (github-oauth-proxy は削除 → mcp-gateway に移行)
├── config/
│   └── github-mcp/           # github-mcp-server 設定
├── scripts/
│   ├── setup.sh              # セットアップ
│   ├── generate-ide-config.sh # IDE設定生成
│   ├── health-check.sh       # ヘルスチェック
│   ├── lint-shell.sh         # シェルスクリプトLint
│   └── verify-mcp-endpoint.js # MCP エンドポイント疎通確認
├── tests/
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
