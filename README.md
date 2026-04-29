# Mcp-Docker — MCP Server Docker 統合環境

GitHub MCP Server をはじめとする複数の MCP サーバーを Docker で常駐させ、OAuth 2.0 認証を一元化して各 IDE から統一的に利用する環境。

## アーキテクチャ

```
IDE（VS Code / Cursor / Kiro / Amazon Q / Copilot CLI）
  ↓ HTTP  localhost:8080
mcp-gateway  ← OAuth 2.0 認証・ルーティング
  ├── /mcp/github          → github-mcp-server   [OAuth 必須]
  ├── /mcp/copilot-review  → copilot-review-mcp  [OAuth 必須]
  └── /mcp/playwright      → playwright-mcp      [auth=none]

Claude Desktop（stdio のみ）
  ↓ stdio
docker run -i --rm ghcr.io/github/github-mcp-server:main stdio
```

### 設計思想：認証の一元化

各 IDE の設定ファイルにはトークン値ではなく `http://127.0.0.1:8080/<path>` という URL のみを書く。
OAuth フローは mcp-gateway コンテナ内で完結するため、IDE の起動方法（GUI / ターミナル / スタートメニュー）に関わらず認証が安定する。

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
#   GITHUB_CLIENT_ID                 (copilot-review-mcp OAuth App Client ID)
#   GITHUB_CLIENT_SECRET             (copilot-review-mcp OAuth App Client Secret)
# ※ 同一 OAuth App を共有する場合は GITHUB_MCP_CLIENT_* と GITHUB_CLIENT_* に同じ値を設定

# 3. 全サービス起動
make start-gateway
```

初回は setup スクリプトも利用できます：

```bash
./scripts/setup.sh
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
   - Homepage URL: `http://localhost:8080`
   - Authorization callback URL: `http://localhost:8080/callback`
3. Client ID / Secret を取得し `.env` に設定：

```bash
GITHUB_MCP_CLIENT_ID=Ov23xxxxxxxxxxxxxxxx
GITHUB_MCP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> `copilot-review-mcp` で使っている OAuth App を共有しても問題ありません。
> callback URL は `MCP_GATEWAY_BASE_URL` と一致させてください（末尾に `/callback`）。


## IDE 統合

設定生成スクリプトで IDE 別の JSON/TOML 設定が得られます：

```bash
make gen-config IDE=vscode       # VS Code / Cursor
make gen-config IDE=kiro         # Kiro: ~/.kiro/settings/mcp.json
make gen-config IDE=amazonq      # Amazon Q
make gen-config IDE=codex        # Codex CLI: ~/.codex/config.toml
make gen-config IDE=copilot-cli  # Copilot CLI: ~/.copilot/mcp-config.json
make gen-config IDE=claude-desktop  # Claude Desktop（stdio 方式）
```

`.mcp.json.example` に設定例があります：

```json
{
  "mcpServers": {
    "github":         { "type": "http", "url": "http://127.0.0.1:8080/mcp/github" },
    "copilot-review": { "type": "http", "url": "http://127.0.0.1:8080/mcp/copilot-review" },
    "playwright":     { "type": "http", "url": "http://127.0.0.1:8080/mcp/playwright" }
  }
}
```

> キー名はユーザーが自由に命名できます。上記は `.mcp.json.example` の例です。
> IDE によっては `type` フィールドが不要な場合があります（省略可能）。

IDE は mcp-gateway の OAuth フローでブラウザ認証を自動処理します。設定ファイルにトークンを書く必要はありません。

### Claude Desktop（例外）

Claude Desktop は HTTP transport 非対応のため、`docker run -i --rm ... stdio` で直接起動します：

```json
{
  "mcpServers": {
    "github-mcp-server-docker": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-v", "/path/to/Mcp-Docker/config/github-mcp:/app/config:rw",
        "-v", "github-mcp-cache:/app/cache:rw",
        "ghcr.io/github/github-mcp-server:main",
        "stdio"
      ]
    }
  }
}
```

- `-i` は必須（省略すると stdio 通信が切断されます）
- `-e GITHUB_PERSONAL_ACCESS_TOKEN` は値を書かずそのまま記述（ホスト環境変数を転送）
- パス `/path/to/Mcp-Docker/config/github-mcp` はクローン先の絶対パスに置き換えてください


## サービス操作

### Makefile コマンド

| コマンド | 説明 |
|---|---|
| `make start-gateway` | 全サービス起動（推奨） |
| `make stop` | 全サービス停止 |
| `make restart` | 再起動（stop → start） |
| `make status` | 全コンテナ状態一覧 |
| `make status-gateway` | github-mcp / mcp-gateway / copilot-review-mcp の状態確認 |
| `make logs` | github-mcp ログ表示 |
| `make logs-gateway` | mcp-gateway ログ表示 |
| `make pull` | github-mcp イメージ更新 |
| `make gen-config` | IDE 設定生成（`IDE=vscode` 等を指定） |
| `make gen-config-crm` | copilot-review-mcp の IDE 設定生成 |
| `make lint` | シェルスクリプト Lint |
| `make test-shell` | シェルスクリプトテスト（BATS） |
| `make clean` | キャッシュ削除 |
| `make clean-docker` | Docker リソースクリーンアップ |
| `make clean-all` | 全クリーンアップ |

### copilot-review-mcp 操作

| コマンド | 説明 |
|---|---|
| `make crm-start` | copilot-review-mcp コンテナ起動 |
| `make crm-stop` | 停止・削除 |
| `make crm-restart` | 再起動 |
| `make crm-logs` | ログ表示 |
| `make crm-status` | 状態確認 |
| `make crm-health` | ヘルスチェック |

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
make logs          # github-mcp ログ
make logs-gateway  # mcp-gateway ログ
```

`GITHUB_PERSONAL_ACCESS_TOKEN` が未設定または無効な場合は設定を確認してください。

### IDE から接続できない

1. mcp-gateway が起動しているか確認（`make status-gateway`）
2. ポート確認（デフォルト 8080）
3. IDE の MCP サーバー設定 URL が `http://127.0.0.1:8080/mcp/github` 等になっているか確認
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

## ディレクトリ構成

```
Mcp-Docker/
├── docker-compose.yml          # メインの Compose 定義（4サービス）
├── Makefile                    # 操作コマンド集
├── tasks.md                    # 開発タスク管理
├── config/
│   └── github-mcp/             # github-mcp-server の設定（ボリュームマウント）
├── scripts/
│   ├── setup.sh                # 初回セットアップ
│   ├── health-check.sh         # ヘルスチェック
│   ├── lint-shell.sh           # シェルスクリプト Lint（make lint-shell）
│   └── generate-ide-config.sh  # IDE 設定生成
├── docs/
│   ├── SECURITY_PATCHES.md     # セキュリティ対応履歴
│   └── copilot-review-mcp-tasks.md  # copilot-review-mcp 固有タスク
├── tests/
│   └── shell/                  # BATS シェルテスト
└── services/
    └── copilot-review-mcp/     # ※ 将来削除予定（外部リポジトリへ移行済み）
```

`services/copilot-review-mcp/` は外部リポジトリ（`scottlz0310/copilot-review-mcp`）への移行に伴い、将来のリリースで削除される予定です。

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
