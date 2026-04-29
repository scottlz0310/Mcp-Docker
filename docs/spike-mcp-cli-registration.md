# Spike: MCP CLI 登録方式の調査

> Issue #117 の Spike タスクに対応。各エージェント CLI の `mcp add` コマンドの動作・オプション・設定ファイルを調査した結果をまとめる。

調査日: 2026-04-29

> **命名方針:** MCP サーバー名 `<name>` は各 CLI で任意だが、このリポジトリの mcp-gateway 経由例では `.mcp.json.example` と同じ `github` / `copilot-review` / `playwright` を推奨名として使う。

---

## 1. Claude CLI (`claude mcp add`)

### コマンド形式

```bash
# HTTP (Streamable HTTP)
claude mcp add --transport http <name> <url>
claude mcp add --transport http --header "Authorization: Bearer ..." <name> <url>

# stdio
claude mcp add <name> -- <command> [args...]
claude mcp add -e KEY=VALUE <name> -- <command> [args...]
```

### オプション

| オプション | 説明 |
|---|---|
| `-t, --transport` | `stdio`（デフォルト）/ `sse` / `http` |
| `-s, --scope` | `local`（デフォルト）/ `user` / `project` |
| `-e, --env KEY=VALUE` | 環境変数（stdio 用）|
| `-H, --header "Key: Value"` | HTTP ヘッダ（HTTP/SSE 用）|
| `--client-id` | OAuth クライアント ID |
| `--client-secret` | OAuth クライアントシークレット（プロンプト入力）|
| `--callback-port` | OAuth コールバック固定ポート |

### 設定ファイル

| スコープ | パス | 形式 |
|---|---|---|
| `user` | `~/.claude.json` の `mcpServers` キー | JSON |
| `local` | `~/.claude.json` の `projects.<path>.mcpServers` | JSON |
| `project` | `.mcp.json` | JSON |

**`~/.claude.json` の格納形式（HTTP）:**
```json
"mcpServers": {
  "github": {
    "type": "http",
    "url": "http://127.0.0.1:8080/mcp/github"
  }
}
```

### 冪等性・削除

```bash
claude mcp remove <name>
claude mcp remove -s user <name>
claude mcp list
claude mcp get <name>
```

**重複登録時の挙動（実測）:**

- **同スコープ・同名** で `add` を再実行すると **エラー終了**（exit code 1）
  ```
  MCP server github already exists in user config
  ```
- **異スコープ（例: user に存在 → local で add）** は成功する（スコープが優先順位で重なるだけ）
- **冪等化の方法**: `remove` してから `add`、または `list` で存在確認してから `add` をスキップ

---

## 2. GitHub Copilot CLI (`gh copilot -- mcp add`)

> 本ドキュメントでは GitHub CLI 経由の `gh copilot -- mcp ...` を実行表記として統一する。CLI のエラーメッセージに `copilot mcp ...` と出る場合も、実行時は `gh copilot -- mcp ...` に読み替える。

### コマンド形式

```bash
# HTTP
gh copilot -- mcp add --transport http <name> <url>
gh copilot -- mcp add --transport http --header "Authorization: Bearer ..." <name> <url>

# stdio
gh copilot -- mcp add <name> -- <command> [args...]
gh copilot -- mcp add --env KEY=VALUE <name> -- <command> [args...]
```

### オプション

| オプション | 説明 |
|---|---|
| `--transport` | `stdio`（デフォルト）/ `http` / `sse` |
| `--env KEY=VALUE` | 環境変数（繰り返し可）|
| `--header "Key: Value"` | HTTP ヘッダ（繰り返し可）|
| `--tools` | ツールフィルタ（`*` で全て、カンマ区切りリスト、`""` で無効）|
| `--timeout` | タイムアウト（ms）|
| `--json` | 追加結果を JSON で出力 |
| `--config-dir` | 設定ディレクトリのパスを上書き |

### 設定ファイル

| スコープ | パス | 形式 |
|---|---|---|
| User | `~/.copilot/mcp-config.json` | JSON |
| Workspace | `.mcp.json` | JSON |
| Plugin | インストール済みプラグイン（読み取り専用）| — |

**`~/.copilot/mcp-config.json` の格納形式（HTTP）:**
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp/github",
      "tools": ["*"]
    }
  }
}
```

**stdio の場合:**
```json
{
  "mcpServers": {
    "desktop-commander": {
      "type": "local",
      "command": "C:\\Users\\dev\\AppData\\Local\\pnpm\\desktop-commander.CMD",
      "args": [],
      "tools": ["*"]
    }
  }
}
```

### 冪等性・削除

```bash
gh copilot -- mcp remove <name>
gh copilot -- mcp list
gh copilot -- mcp get <name>
```

**重複登録時の挙動（実測）:**

- 同名で `add` を再実行すると **エラー終了**（exit code 1）
  ```
  Error: Server "github" already exists. To update it, remove it first:
    copilot mcp remove github
  ```
- エラーメッセージ内では `copilot mcp remove` と表示されるが、本手順では `gh copilot -- mcp remove <name>` として実行する
- **冪等化の方法**: `remove` してから `add`（CLI 自身が案内している）

---

## 3. Codex CLI (`codex mcp add`)

### コマンド形式

```bash
# HTTP (Streamable HTTP)
codex mcp add <name> --url <url>
codex mcp add <name> --url <url> --bearer-token-env-var ENV_VAR

# stdio
codex mcp add <name> -- <command> [args...]
codex mcp add <name> --env KEY=VALUE -- <command> [args...]
```

> 注意: `--transport` フラグは存在しない。`--url` の有無で HTTP/stdio を区別する。

### オプション

| オプション | 説明 |
|---|---|
| `--url <URL>` | Streamable HTTP サーバーの URL |
| `--bearer-token-env-var <ENV_VAR>` | Bearer トークンを読む環境変数名（HTTP のみ）|
| `--env KEY=VALUE` | 環境変数（stdio のみ）|

### 設定ファイル

| パス | 形式 |
|---|---|
| `~/.codex/config.toml` | TOML（`[mcp_servers.<name>]` セクション）|

**`~/.codex/config.toml` の格納形式（HTTP）:**
```toml
[mcp_servers.github]
url = "http://127.0.0.1:8080/mcp/github"
```

**Bearer トークン付き:**
```toml
[mcp_servers.cloudflare-api]
url = "https://mcp.cloudflare.com/mcp"
bearer_token_env_var = "CLOUDFLARE_API_TOKEN"
```

**stdio の場合:**
```toml
[mcp_servers.desktop-commander]
command = 'C:\Users\dev\AppData\Local\pnpm\desktop-commander.CMD'
```

### 冪等性・削除

```bash
codex mcp remove <name>
codex mcp list
codex mcp get <name>
```

**重複登録時の挙動（実測）:**

- 同名で `add` を再実行しても **エラーにならず上書き**（exit code 0）
  ```
  Added global MCP server 'github'.
  ```
- **3 CLI の中で唯一、remove なしで上書き可能**
- ただし HTTP サーバーの場合、上書き時に OAuth フローが再起動されることがある
- **冪等化の方法**: そのまま `add` を再実行するだけでよい（最もシンプル）

---

## 4. 比較サマリー

### コマンド構文比較（HTTP の場合）

| CLI | コマンド |
|---|---|
| Claude | `claude mcp add --transport http <name> <url>` |
| Copilot | `gh copilot -- mcp add --transport http <name> <url>` |
| Codex | `codex mcp add <name> --url <url>` |

### 機能比較

| 機能 | Claude | Copilot | Codex |
|---|---|---|---|
| HTTP transport | ✓ | ✓ | ✓ |
| stdio transport | ✓ | ✓ | ✓ |
| SSE transport | ✓ | ✓ | — |
| スコープ指定 | `local`/`user`/`project` | `user`/`workspace` | — |
| ヘッダ指定 | ✓ | ✓ | — |
| 環境変数指定 | ✓ | ✓ | ✓（stdio のみ）|
| Bearer トークン env var | — | — | ✓（HTTP のみ）|
| OAuth 対応 | ✓ | — | — |
| ツールフィルタ | — | ✓ | — |
| 設定ファイル形式 | JSON (`~/.claude.json`) | JSON (`~/.copilot/mcp-config.json`) | TOML (`~/.codex/config.toml`) |
| **同名 add の挙動** | **エラー（同スコープ）** | **エラー** | **上書き（エラーなし）** |
| **冪等化の方法** | `remove` → `add` or skip | `remove` → `add` | `add` 再実行でよい |

### transport フラグの違い

3 CLI とも HTTP に対応するが、フラグ名と引数の位置が微妙に異なる:

```bash
# Claude / Copilot: --transport フラグ + URL は位置引数
claude mcp add --transport http github http://127.0.0.1:8080/mcp/github
gh copilot -- mcp add --transport http github http://127.0.0.1:8080/mcp/github

# Codex: --url フラグで URL を指定（transport フラグなし）
codex mcp add github --url http://127.0.0.1:8080/mcp/github
```

---

## 5. register-agent.sh への実装方針

上記の差異を吸収する `scripts/register-agent.sh` の関数設計案:

```bash
register_http() {
  local agent="$1" name="$2" url="$3"
  case "$agent" in
    claude)   claude mcp add --transport http "$name" "$url" ;;
    copilot)  gh copilot -- mcp add --transport http "$name" "$url" ;;
    codex)    codex mcp add "$name" --url "$url" ;;
  esac
}

register_stdio() {
  local agent="$1" name="$2" command="$3"
  shift 3
  case "$agent" in
    claude)   claude mcp add "$name" -- "$command" "$@" ;;
    copilot)  gh copilot -- mcp add "$name" -- "$command" "$@" ;;
    codex)    codex mcp add "$name" -- "$command" "$@" ;;
  esac
}
```

冪等性の確保は「登録済みなら skip / --force で上書き」のどちらかで実装する必要がある。  
現状 3 CLI とも `remove` → `add` で対処するか、`list` で存在確認してから `add` する形になる。

---

## 6. 設計決定（Spike 完了時点）

### 情報源

| 情報源 | 対象 |
|---|---|
| `docker-compose.yml` の `mcp-gateway.environment.ROUTE_*` | gateway 経由の内部 MCP サービス |
| `config/mcp-external.yml` | 外部 SaaS MCP サービス（cloudflare-api, supabase 等）|

`docker-compose.yml` に外部サービスを載せると関心が混在するため、外部サービスは別ファイルで管理する。

**`config/mcp-external.yml` の形式:**
```yaml
servers:
  - name: cloudflare-api
    url: https://mcp.cloudflare.com/mcp
    tokenEnv: CLOUDFLARE_API_TOKEN   # オプション: Bearer トークン環境変数名

  - name: supabase
    url: https://mcp.supabase.com/mcp
```

### 実装言語: Go

- 姉妹 repo（`mcp-gateway`, `copilot-review-mcp`）が Go で統一されている
- シングルバイナリ配布のためインストールが簡単でユーザーに優しい
- YAML パースは `gopkg.in/yaml.v3` で標準的に対応
- Python（周辺ツールが多い）・sh（Windows 非ネイティブ）・PowerShell（YAML パーサー非標準）を退けた

### 冪等性の実装方針

| CLI | 挙動 | 実装 |
|---|---|---|
| Claude | 同スコープ同名はエラー | `mcp list` で確認 → 存在すれば `remove` → `add` |
| Copilot | 同名はエラー | 同上 |
| Codex | 同名は上書き | `add` 再実行のみでよい |

---

## 7. 未確認事項

- [ ] Claude: `--scope user` で登録した場合の `~/.claude.json` への書き込み確認（local との違い）
- [ ] Copilot: `microsoft-enterprise` サーバーの由来（自動追加か手動か）
- [ ] Codex: `--bearer-token-env-var` の実際の動作確認（トークンをヘッダに自動付与するか）
- [x] 各 CLI: 既存サーバー名で `add` を再実行した場合のエラー挙動 → Claude/Copilot はエラー拒否、Codex のみ上書き
