# 実装計画: mcp-docker register (Go CLI)

Issue #117 の実装計画たたき台。

---

## 前提・スコープ

- **対象**: CLI 登録対応エージェント（Claude / Copilot / Codex）のみ
- **対象外**: VS Code / Kiro / Amazon Q / Claude Desktop（既存の `generate-ide-config.sh` が継続担当）
- **情報源**:
  - `docker-compose.yml` の `mcp-gateway.environment.ROUTE_*` → 内部サービスの URL を導出
  - `config/mcp-external.yml` → 外部 SaaS MCP サービス

---

## ディレクトリ構成

```
cmd/
  mcp-docker/
    main.go             # エントリポイント・サブコマンドルーター

internal/
  compose/
    parse.go            # docker-compose.yml → ROUTE_* 抽出 → []Server
  external/
    parse.go            # config/mcp-external.yml → []Server
  register/
    agent.go            # Agent インターフェース + 共通ロジック（冪等化）
    claude.go           # ClaudeAgent
    copilot.go          # CopilotAgent
    codex.go            # CodexAgent

config/
  mcp-external.yml      # 新規作成（外部 SaaS 定義）

Makefile                # register-claude / register-copilot / register-codex ターゲット追加
```

---

## 内部モデル

```go
// internal/register/agent.go

type Server struct {
    Name     string // 登録名（例: "github-mcp-server"）
    URL      string // エンドポイント URL
    TokenEnv string // Bearer トークン環境変数名（省略可）
}

type Agent interface {
    Name() string
    List() ([]string, error)          // 登録済みサーバー名の一覧
    Add(s Server) error               // サーバーを登録
    Remove(name string) error         // サーバーを削除
}

// 冪等登録: List → 存在すれば Remove → Add
func Register(a Agent, servers []Server) error
```

---

## docker-compose.yml パース方針

`mcp-gateway` サービスの環境変数から `ROUTE_` プレフィックスのものを抽出する。

**ROUTE の形式:** `<path>|<upstream>[|auth=none]`
例: `ROUTE_GITHUB=/mcp/github|http://github-mcp:8082`

抽出手順:
1. `docker-compose.yml` を `gopkg.in/yaml.v3` でパース
2. `services.mcp-gateway.environment` から `ROUTE_*` を列挙
3. パス部分（`|` 前）を取り出す
4. `MCP_GATEWAY_PORT`（デフォルト 8080）と組み合わせて URL を生成
   → `http://127.0.0.1:8080/mcp/github`
5. サービス名は ROUTE キーから導出（`ROUTE_GITHUB` → `github-mcp-server`）

> **サービス名のマッピング問題**: `ROUTE_GITHUB` から `github-mcp-server` への変換に命名規則が必要。
> `config/mcp-external.yml` と同様の形式で `config/mcp-routes.yml` に名前マッピングを持つか、
> ROUTE 値にサービス名を埋め込むかは要検討。

---

## config/mcp-external.yml

```yaml
servers:
  - name: cloudflare-api
    url: https://mcp.cloudflare.com/mcp
    tokenEnv: CLOUDFLARE_API_TOKEN

  - name: supabase
    url: https://mcp.supabase.com/mcp
```

---

## エージェント別実装

### ClaudeAgent

```bash
# 登録
claude mcp add --transport http --scope user <name> <url>

# 一覧（stdout をパースして name を抽出）
claude mcp list

# 削除
claude mcp remove --scope user <name>
```

- `--scope user` 固定（グローバル登録）
- `list` の出力形式: `<name>: <url> (HTTP) - ✓ Connected`

### CopilotAgent

```bash
# 登録
gh copilot -- mcp add --transport http <name> <url>

# 一覧
gh copilot -- mcp list

# 削除
gh copilot -- mcp remove <name>
```

- `list` の出力形式: `  <name> (http)`

### CodexAgent

```bash
# 登録（上書き可 = 冪等化不要）
codex mcp add <name> --url <url>
codex mcp add <name> --url <url> --bearer-token-env-var <env>

# 一覧（確認用）
codex mcp list
```

- 同名 `add` が上書きになるため `Remove` 不要

---

## コマンドインターフェース

```
mcp-docker register [--agent <claude|copilot|codex|all>] [--compose <path>] [--external <path>]

  --agent    登録対象エージェント（デフォルト: all）
  --compose  docker-compose.yml のパス（デフォルト: ./docker-compose.yml）
  --external 外部サービス定義ファイルのパス（デフォルト: ./config/mcp-external.yml）
```

---

## Makefile ターゲット

```makefile
BIN_DIR     := bin
MCP_DOCKER  := $(BIN_DIR)/mcp-docker

$(MCP_DOCKER): $(shell find cmd internal -name '*.go')
	go build -o $(MCP_DOCKER) ./cmd/mcp-docker

register-claude: $(MCP_DOCKER)
	$(MCP_DOCKER) register --agent claude

register-copilot: $(MCP_DOCKER)
	$(MCP_DOCKER) register --agent copilot

register-codex: $(MCP_DOCKER)
	$(MCP_DOCKER) register --agent codex

register-all: $(MCP_DOCKER)
	$(MCP_DOCKER) register --agent all
```

---

## 設計決定

### 1. ROUTE → サーバー名のマッピング

**案C（機械的変換）+ インタラクティブ確認** を採用。

- `ROUTE_GITHUB` → サジェスト名 `github`（小文字化・ハイフン区切り変換）
- 起動時に各サーバー名をサジェストとして表示し、Enter で確定 / 任意入力で上書き可能にする
- 既存スキルや設定ファイルとの兼ね合いで名前を変えたいケースに対応

```
検出されたサーバー:
  ROUTE_GITHUB → サジェスト: "github"  [Enter で確定 / 別名を入力]:
  ROUTE_COPILOT_REVIEW → サジェスト: "copilot-review"  [Enter で確定 / 別名を入力]:
  ROUTE_PLAYWRIGHT → サジェスト: "playwright"  [Enter で確定 / 別名を入力]:
```

非インタラクティブモード（CI 等）では `--yes` フラグでサジェスト名をそのまま採用する。

### 2. `generate-ide-config.sh` との関係

- `generate-ide-config.sh` は**廃止予定**とし、今回は手を入れない
- Go 側への JSON / TOML エクスポート機能（VS Code / Kiro / Amazon Q 向け）は将来的に必要になる可能性があるが、**今回はスコープ外**
- `generate-ide-config.sh` には廃止予定コメントを入れるに留める

### 3. `go.mod` の配置

リポジトリルートに**独立モジュール**として配置する。

```
go.mod    ← module github.com/scottlz0310/mcp-docker/tools
go.sum
cmd/
internal/
```

このリポジトリの主役は `docker-compose.yml` とその周辺（Makefile 等）であり、
Go コードはあくまでサポートツール。独立モジュールにすることで主役の構成を汚さない。
