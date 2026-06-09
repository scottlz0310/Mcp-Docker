# Review Platform における Mcp-Docker の責務

本ドキュメントは、レビュー基盤（review platform）における `Mcp-Docker` の位置づけと責務境界を定義する。
`Mcp-Docker` を **MCP container orchestration / configuration automation layer** として明確化し、
他コンポーネント（Thread Owl / review-raven / mcp-resource-subscriber / mcp-gateway）との責務分担を文書化する。

関連: [Issue #158](https://github.com/scottlz0310/Mcp-Docker/issues/158)

## 1. Review Platform の全体像

レビュー基盤は、単一のアプリケーションではなく、責務の異なる複数の MCP / CLI コンポーネントの組み合わせで構成される。

| コンポーネント | 役割 |
|---|---|
| `thread-owl` | review する側 / subscribe される側。GitHub App 認証・webhook handling・review queue 管理 |
| `review-raven` | review を受けて直す側 / reviewed-side operations。review thread の reply / resolve |
| `mcp-resource-subscriber` | subscribe する側 / agent workflow bridge。resource subscription の待機 |
| `mcp-gateway` | 複数 MCP server を束ねる reverse proxy / routing / auth boundary |
| `Mcp-Docker` | MCP server 群の container 管理と CLI agent 設定自動化（**本リポジトリ**） |

このうち `Mcp-Docker` は、review platform を実際にローカル・半ローカル環境で運用するための
**orchestration layer** に位置づけられる。個々の MCP server を手作業で起動し、各 CLI agent に
個別設定する運用は server 数の増加に伴い破綻しやすい。`Mcp-Docker` は container lifecycle・compose・
gateway config・CLI agent config を束ねることで、レビュー基盤を再現可能な形で立ち上げる。

```text
Mcp-Docker
  ├─ thread-owl container
  ├─ review-raven container
  ├─ mcp-gateway container
  ├─ optional github-mcp / other MCP containers
  ├─ generated gateway routes
  └─ generated client config
```

## 2. Mcp-Docker の定義

`Mcp-Docker` は **MCP container orchestration / configuration automation layer** である。

- review platform を構成する MCP server 群を再現可能な形で起動・管理する
- domain logic（認証・review・protocol 実装）は各 repo に残し、`Mcp-Docker` には取り込まない
- orchestration（container lifecycle）と configuration automation（gateway route / CLI agent config 生成）に集中する

## 3. 責務境界

### Mcp-Docker が担うこと

- review platform を構成する MCP server 群の container lifecycle 管理
- Docker Compose / container definitions の提供
- compose profiles による optional component の選択的有効化
- `mcp-gateway` の upstream route config 生成・配置
- Claude Code / Claude Desktop / Codex CLI など CLI agent / desktop client 向け MCP 設定生成
- environment variable / secrets mount policy の整理
- local development / semi-local operation の bootstrap scripts / docs
- health check / status aggregation / logs への導線

### Mcp-Docker が担わないこと（委譲先）

| 担わないこと | 委譲先 |
|---|---|
| GitHub App 認証ロジック | Thread Owl |
| webhook event handling | Thread Owl |
| review queue 管理 | Thread Owl |
| MCP protocol の tool/resource 実装 | 各 MCP server |
| reverse proxy runtime logic | mcp-gateway |
| resource subscription の待機 CLI | mcp-resource-subscriber |
| review thread の reply / resolve 実装 | review-raven |
| LLM / AI review logic | agent skill / LLM client |

## 4. mcp-gateway との関係

`mcp-gateway` は runtime の reverse proxy / auth boundary として動作する。
`Mcp-Docker` はその gateway を含む MCP server 群を起動し、gateway が参照する upstream route config を生成または配置する。

両者は **生成（Mcp-Docker）と実行（mcp-gateway）** で責務が分かれる。

```text
Mcp-Docker
  ├─ containers を起動
  ├─ gateway routes を生成
  ├─ CLI agent config を生成
  └─ health/logs/status を提供

mcp-gateway
  ├─ generated routes を読み込む
  ├─ /mcp/thread-owl などを upstream へ route
  └─ auth / token mediation を担当
```

## 5. Configuration automation の方針

### gateway route config 生成

- route 定義は `docker-compose.yml` の `mcp-gateway.environment.ROUTE_*` を単一の source of truth とする
- 外部 Remote MCP サーバーは `config/mcp-external.yml` に定義し、route config へ反映する
- `ROUTE_GITHUB` → `github`、`ROUTE_PLAYWRIGHT` → `playwright` のように route 名を server 名へ変換する

### CLI agent config 生成

- CLI agent（Claude Code / Claude Desktop / Codex CLI 等）向けの MCP 設定を生成する
- 生成される設定には token 値を含めず、`http://127.0.0.1:8080/<path>` の gateway URL のみを記載する
- agent ごとの設定差分は template / profile として扱い、生成ロジックを共通化する

## 6. Compose profile / optional component 管理

- review platform の中核コンポーネントと optional component を compose profile で分離する
- optional component（github-mcp / playwright / Remote MCP プロバイダー等）は profile により選択的に有効化する
- profile 単位で「最小構成」「フル構成」を切り替えられるようにし、運用者が必要なものだけ起動できるようにする

## 7. Bootstrap フロー

review platform の立ち上げは、運用者の単一コマンド / compose profile を起点とする。

```text
Developer / operator
  ↓ setup command / compose profile
Mcp-Docker
  ├─ starts MCP servers
  ├─ starts mcp-gateway
  ├─ writes gateway config
  ├─ writes agent config
  └─ exposes operational status
      ↓
CLI agents / Desktop clients
  ↓ generated config
mcp-gateway
  ↓ routes
Thread Owl / review-raven / other MCP servers
```

## 8. 設計原則

- MCP server 実装を `Mcp-Docker` に取り込まない
- Gateway runtime logic を `Mcp-Docker` に取り込まない
- `Mcp-Docker` は orchestration / configuration automation に集中する
- agent ごとの設定差分は template / profile として扱う
- secrets は container image に焼き込まず、env / mounted file / secret store から注入する
- local-first / semi-local operation を優先し、remote hosting は別設計として扱う
- review platform 全体を再現可能にするが、domain logic は各 repo に残す

## 関連 Issue

- Thread Owl responsibility boundary: [scottlz0310/thread-owl#75](https://github.com/scottlz0310/thread-owl/issues/75)
- mcp-resource-subscriber JSON output: [scottlz0310/mcp-resource-subscriber#86](https://github.com/scottlz0310/mcp-resource-subscriber/issues/86)
- review-raven reviewed-side redefinition: [scottlz0310/review-raven#63](https://github.com/scottlz0310/review-raven/issues/63)
- mcp-gateway routing gateway definition: [scottlz0310/mcp-gateway#92](https://github.com/scottlz0310/mcp-gateway/issues/92)
