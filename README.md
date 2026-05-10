# Mcp-Docker — MCP Server Docker 統合環境

GitHub MCP Server をはじめとする複数の MCP サーバーを Docker で常駐させ、OAuth 2.0 認証を一元化して各 CLI から統一的に利用する環境。

## アーキテクチャ

```
CLI（Claude CLI / GitHub Copilot CLI / Codex CLI）
  ↓ HTTP  127.0.0.1:8080
mcp-gateway  ← OAuth 2.0 認証・ルーティング
  ├── /mcp/github          → github-mcp-server   [OAuth 必須]
  ├── /mcp/copilot-review  → copilot-review-mcp  [OAuth 必須]
  └── /mcp/playwright      → playwright-mcp      [auth=none]
```

### 設計思想：認証の一元化

各 CLI の MCP 設定にはトークン値ではなく `http://127.0.0.1:8080/<path>` という URL のみを書く。
OAuth フローは mcp-gateway コンテナ内で完結するため、CLI の起動方法に関わらず認証が安定する。

## サービス構成

| サービス | イメージ | ポート | 説明 |
|---|---|---|---|
| `mcp-gateway` | `ghcr.io/scottlz0310/mcp-gateway:latest` | 8080（ホスト公開） | OAuth ゲートウェイ |
| `github-mcp` | `ghcr.io/github/github-mcp-server:main` | 8082（内部のみ） | GitHub MCP サーバー |
| `copilot-review-mcp` | `ghcr.io/scottlz0310/copilot-review-mcp:latest` | 8083（内部のみ） | Copilot レビュー自動化 |
| `playwright-mcp` | `mcr.microsoft.com/playwright/mcp:latest` | 8931（内部のみ） | ブラウザ操作（auth=none） |

`github-mcp`・`copilot-review-mcp`・`playwright-mcp` はホストに直接公開されません。
すべて mcp-gateway（ポート 8080）経由でアクセスします。


## クイックスタート

### 前提条件

- Docker 20.10+
- GitHub Personal Access Token（PAT）
- GitHub OAuth App の Client ID / Secret（mcp-gateway 経由接続に必要）

### セットアップ

```bash
# 1. リポジトリクローン
git clone https://github.com/scottlz0310/Mcp-Docker.git
cd Mcp-Docker

# 2. 環境ファイル作成
cp .env.template .env
# .env を編集して以下を設定:
#   GITHUB_PERSONAL_ACCESS_TOKEN     (github-mcp-server 用 PAT)
#   GITHUB_MCP_CLIENT_ID             (mcp-gateway OAuth App Client ID)
#   GITHUB_MCP_CLIENT_SECRET         (mcp-gateway OAuth App Client Secret)
# ※ copilot-review-mcp v3.0.0 以降、OAuth は mcp-gateway が一元管理します。
# ※ GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET の個別設定は不要です。

# 3. 全サービス起動
make start-gateway
```

### GitHub Personal Access Token

**Fine-grained token（推奨）**

1. [GitHub Settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta) でトークンを作成
2. Permissions:
   - Contents: Read and write
   - Issues: Read and write
   - Pull requests: Read and write
   - Workflows: Read and write
   - Metadata: Read-only（自動選択）
3. `.env` に設定：

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxxx
```

環境変数が設定済みの場合、`.env` の設定より優先されます：

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxxx
make start-gateway
```

**Classic token（非推奨）**: スコープ `repo, workflow, read:org, read:user`

### GitHub OAuth App 登録

mcp-gateway 経由で接続するには GitHub OAuth App が必要です。

1. [https://github.com/settings/applications/new](https://github.com/settings/applications/new) にアクセス
2. 設定：
   - Homepage URL: `http://127.0.0.1:8080`
   - Authorization callback URL: `http://127.0.0.1:8080/callback`
3. Client ID / Secret を取得し `.env` に設定：

```bash
GITHUB_MCP_CLIENT_ID=Ov23xxxxxxxxxxxxxxxx
GITHUB_MCP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> callback URL は `MCP_GATEWAY_PUBLIC_URL`（未設定時は `MCP_GATEWAY_BASE_URL`）と一致させてください（末尾に `/callback`）。


## CLI 統合

### Primary: CLI 登録（推奨）

CLI 登録に対応しているエージェント（Claude CLI / GitHub Copilot CLI / Codex CLI）は、`mcp-docker register` で mcp-gateway の HTTP エンドポイントを直接登録できます。

```bash
# 事前に make start-gateway で mcp-gateway を起動
make build-go

# 対話的に agent / MCP サーバーを選択（TTY 環境）
make register

make register-claude   REGISTER_FLAGS=--yes
make register-copilot  REGISTER_FLAGS=--yes
make register-codex    REGISTER_FLAGS=--yes

# 3 種類まとめて登録
make register-all      REGISTER_FLAGS=--yes
```

`make register` は引数なしで `mcp-docker register` を呼び出し、TTY であれば agent と MCP サーバーを番号入力で複数選択できます。`--interactive`, `--agent`, `--server`, `--yes`, `--dry-run` のいずれかを `REGISTER_FLAGS` で渡した場合は **暗黙的な対話モードには入らず**、従来通りフラグの内容に従って実行します（`--interactive` 明示時はそのまま対話モードに入ります）。

```bash
# 例: claude と codex に github / playwright だけ登録（非対話）
make register REGISTER_FLAGS="--agent claude,codex --server github,playwright --yes"
```

Makefile 経由のビルド成果物は OS に合わせて決まります。Windows (`OS=Windows_NT`) では `bin/mcp-docker.exe` を生成し、`register-*` も `.exe` 付きのバイナリを実行します。Linux/macOS では従来通り `bin/mcp-docker` です。

Makefile を使わず Go ツールチェーンから直接ビルド・実行する場合：

```bash
# Linux/macOS/Git Bash
go build -trimpath -ldflags="-X main.version=2.9.0" -o ./bin/mcp-docker ./cmd/mcp-docker
./bin/mcp-docker --version
./bin/mcp-docker register --dry-run
./bin/mcp-docker register --agent all --yes
```

Windows のネイティブシェルで実行する場合：

```powershell
go build -trimpath -ldflags="-X main.version=2.9.0" -o .\bin\mcp-docker.exe .\cmd\mcp-docker
.\bin\mcp-docker.exe --version
.\bin\mcp-docker.exe register --dry-run
.\bin\mcp-docker.exe register --agent all --yes
```

ビルド済みバイナリを残したくない場合は `go run` でも同じ登録フローを実行できます：

```bash
go run ./cmd/mcp-docker --version
go run ./cmd/mcp-docker register --dry-run
go run ./cmd/mcp-docker register --agent all --yes
```

`go install` でグローバルツールとしてインストールすることもできます：

```bash
go install github.com/scottlz0310/mcp-docker/v2/cmd/mcp-docker@latest
mcp-docker --version
mcp-docker register --agent all --yes
```

登録対象は以下から読み取ります：

- `docker-compose.yml` の `mcp-gateway.environment.ROUTE_*`
- `config/mcp-external.yml` の外部 MCP サーバー定義

`ROUTE_GITHUB` は `github`、`ROUTE_COPILOT_REVIEW` は `copilot-review` のようにサーバー名へ変換されます。`REGISTER_FLAGS=--yes` を外すと、検出した名前を対話的に変更できます。

## サービス操作

### Makefile コマンド

| コマンド | 説明 |
|---|---|
| `make start-gateway` | 全サービス起動（推奨） |
| `make stop` / `make stop-gateway` | 全サービス停止 |
| `make restart` / `make restart-gateway` | 再起動（stop → start） |
| `make status` / `make status-gateway` | 全コンテナ状態一覧 |
| `make logs` / `make logs-gateway` | mcp-gateway ログ表示 |
| `make pull` / `make pull-gateway` | 全イメージ更新 |
| `make pull-main` | mcp-gateway / copilot-review-mcp の `:main` イメージ取得 |
| `make start-main` | 最新開発版イメージで全サービス起動 |
| `make restart-main` | 最新開発版イメージで全サービス再起動 |
| `make register` | 対話的に IDE/CLI と MCP サーバーを選択して登録 |
| `make register-claude` | Claude CLI に MCP サーバーを登録 |
| `make register-copilot` | GitHub Copilot CLI に MCP サーバーを登録 |
| `make register-codex` | Codex CLI に MCP サーバーを登録 |
| `make register-all` | Claude / Copilot / Codex CLI に MCP サーバーを登録 |
| `make lint` | シェルスクリプト Lint |
| `make test-go` | Go CLI テスト |
| `make test-shell` | シェルスクリプトテスト（BATS） |
| `make clean` | キャッシュ削除 |
| `make clean-docker` | Docker リソースクリーンアップ |
| `make clean-all` | 全クリーンアップ |

### HTTP エンドポイント

| URL | サービス | 認証 |
|---|---|---|
| `http://127.0.0.1:8080/mcp/github` | github-mcp-server | OAuth 必須 |
| `http://127.0.0.1:8080/mcp/copilot-review` | copilot-review-mcp | OAuth 必須 |
| `http://127.0.0.1:8080/mcp/playwright` | playwright-mcp | なし |
| `http://127.0.0.1:8080/health` | mcp-gateway | なし |

疎通確認：

```bash
./scripts/health-check.sh
# または
curl -i http://127.0.0.1:8080/health
```

ポートを変更する場合：

```bash
# .env または環境変数で設定
MCP_GATEWAY_PORT=18080
make start-gateway
```


## playwright-mcp（auth=none）

playwright-mcp は認証なしで利用できるブラウザ操作サービスです。
`docker-compose.yml` でデフォルト有効。`/mcp/playwright` から直接接続できます：

```json
{
  "mcpServers": {
    "playwright-mcp": { "url": "http://127.0.0.1:8080/mcp/playwright" }
  }
}
```

## イメージのカスタマイズ

| 環境変数 | 既定値 | 説明 |
|---|---|---|
| `GITHUB_MCP_GATEWAY_IMAGE` | `ghcr.io/scottlz0310/mcp-gateway:latest` | ゲートウェイイメージ |
| `GITHUB_MCP_IMAGE` | `ghcr.io/github/github-mcp-server:main` | github-mcp-server イメージ |
| `COPILOT_REVIEW_MCP_IMAGE` | `ghcr.io/scottlz0310/copilot-review-mcp:latest` | copilot-review-mcp イメージ |

```bash
GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server:v1.0.0 make start-gateway
```

## トラブルシューティング

### コンテナが起動しない

```bash
make status        # コンテナ状態確認
make logs-gateway  # mcp-gateway ログ
```

`GITHUB_PERSONAL_ACCESS_TOKEN` が未設定または無効な場合は設定を確認してください。

### CLI から接続できない

1. mcp-gateway が起動しているか確認（`make status-gateway`）
2. ポート確認（デフォルト 8080）
3. CLI の MCP サーバー設定 URL が `http://127.0.0.1:8080/mcp/github` 等になっているか確認
4. OAuth フローが完了しているか確認（ブラウザで `http://127.0.0.1:8080/health` にアクセス可能か）

### タイムアウト

デフォルトの HTTP タイムアウトは 30 秒。複雑な操作では `--timeout` の調整が必要な場合があります。

### コンテナ内部に入れない（Distroless）

`github-mcp-server` コンテナはシェルなし（Distroless）のため、`docker exec -it ... bash` は動作しません。
ヘルスチェックはホスト側スクリプト（`scripts/health-check.sh`）で行ってください。

### コンフィグボリュームが古い

`make clean` 後も `./config/github-mcp` ボリュームは残ります。
最初から設定し直す場合は手動で削除してください：

```bash
docker volume rm mcp-docker_github-mcp-cache
```

### mcp-gateway トークンストアボリューム（`mcp-gateway-data`）

`mcp-gateway` はブラウザ認証後に取得した OAuth トークンを `/data/tokens.db` に永続化します。
このファイルは **検証済み OAuth トークンのキャッシュ**であり、GitHub 認証情報（PAT）そのものではありません。

ボリューム情報確認（Mountpoint 等のメタデータ）：

> ボリューム名のプレフィックスは Compose プロジェクト名（デフォルト: ディレクトリ名）に依存します。
> まず `docker volume ls | grep mcp-gateway-data` で実際のボリューム名を確認してください。

```bash
# 実際のボリューム名を確認
docker volume ls | grep mcp-gateway-data

# メタデータを表示（上記で確認した名前を使用）
docker volume inspect <実際のボリューム名>
```

認証状態のリセット（再認証が必要な場合）：

```bash
# 実際のボリューム名を確認してから削除
docker compose down
docker volume ls | grep mcp-gateway-data
docker volume rm <実際のボリューム名>
docker compose up -d
```

**セキュリティ注意事項**:
- `mcp-gateway-data` ボリュームは `mcp-gateway` コンテナ専用です。他のサービスには公開しないでください。
- ボリュームパスやトークンファイルの内容を CLI 設定に含めないでください。CLI へは `http://127.0.0.1:8080/mcp/github` 等の URL のみを記載します。

## ディレクトリ構成

```
Mcp-Docker/
├── cmd/
│   └── mcp-docker/             # CLI 登録オーケストレータ
├── internal/
│   ├── compose/                # docker-compose.yml の ROUTE_* 抽出
│   ├── external/               # config/mcp-external.yml 読み込み
│   └── register/               # Claude / Copilot / Codex adapter
├── docker-compose.yml          # メインの Compose 定義（4サービス）
├── Makefile                    # 操作コマンド集
├── config/
│   ├── mcp-external.yml        # 外部 MCP サーバー定義
│   └── github-mcp/             # GitHub MCP のローカル bind mount 用（未作成時は Docker が作成）
├── scripts/
│   ├── health-check.sh         # ヘルスチェック
│   ├── lint-shell.sh           # シェルスクリプト Lint（make lint-shell）
│   └── verify-mcp-endpoint.js  # MCP エンドポイント疎通確認
├── docs/
│   ├── SECURITY_PATCHES.md     # セキュリティ対応履歴
│   ├── e2e-runbook-mcp-docker-cli.md  # CLI E2E 確認手順
│   ├── archives/               # 旧設計メモ・検証ログ
│   └── skills/                 # Codex / LLM 向け運用スキル
├── tests/
│   └── shell/                  # BATS シェルテスト
```

## セキュリティ

- トークンはコンテナ外（`.env` またはホスト環境変数）で管理してください
- `.env` ファイルは `.gitignore` で除外済みです
- `.env` をコミットしないでください
- トークンスコープ要件・Fine-grained PAT の詳細は [SECURITY.md](SECURITY.md) を参照
- セキュリティパッチ・CVE 対応履歴は [docs/SECURITY_PATCHES.md](docs/SECURITY_PATCHES.md) を参照

## 関連リソース

- [github-mcp-server](https://github.com/github/github-mcp-server) — 本家 GitHub MCP サーバー
- [mcp-gateway](https://github.com/scottlz0310/mcp-gateway) — OAuth ゲートウェイ
- [copilot-review-mcp](https://github.com/scottlz0310/copilot-review-mcp) — Copilot レビュー自動化 MCP
- [CHANGELOG.md](CHANGELOG.md) — リリース履歴・破壊的変更

## ライセンス

MIT License — see [LICENSE](LICENSE)
