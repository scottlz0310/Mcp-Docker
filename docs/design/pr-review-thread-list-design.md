# PRレビュースレッド一覧取得ツール 設計ドキュメント

**作成日**: 2026-03-17  
**バージョン**: 1.0.0  
**ステータス**: Approved  
**対象**: `github-mcp-server` カスタムビルド（方式C: ソースパッチビルド）

---

## 1. 背景と課題

### 1.1 現状の「片手落ち」問題

`github-mcp-server` には `resolve_pull_request_review_thread` ツールが実装されている。
しかし、このツールの必須引数 `thread_id` に渡す `PRRT_xxxx` 形式の **node ID** は、
GitHub REST API では取得できない。GraphQL API (`pullRequest.reviewThreads.nodes[].id`) にしか存在しない。

```
■ 問題のあるワークフロー (現状)
  [AI] → list_pull_requests  OK: PR一覧取得
  [AI] → ??? スレッド一覧?   ← ツールが存在しない
  [AI] → resolve_pull_request_review_thread(thread_id="PRRT_???")
                              ← PRRT_ の ID をどこで入手する？
```

### 1.2 解決方針

`list_pull_request_review_threads` ツールを追加し、以下のフローを成立させる:

```
■ 解決後のワークフロー (一気通貫)
  [AI] → list_pull_request_review_threads(owner, repo, pull_number)
         → [{id: "PRRT_xxx", isResolved: false, path: "src/foo.go", body: "この実装は..."}]
  [AI] → (コメント内容を見てどのスレッドを解決すべきか判断)
  [AI] → resolve_pull_request_review_thread(owner, repo, pull_number, thread_id: "PRRT_xxx")
         → 解決完了
```

---

## 2. 決定事項（合意済み）

| # | 項目 | 決定内容 | 理由 |
|---|------|----------|------|
| Q1 | 実装場所 | **方式C: ソースパッチビルド** | 既存 `Dockerfile.github-mcp-server` の COPY/sed パッチ方式を拡張して Go ファイルを注入する。単一コンテナで完結。上流が追いついたら公式イメージに乗り換える一時つなぎ。 |
| Q2 | ツールスコープ | **`list_pull_request_review_threads` のみ追加** | unresolve は不要。resolve フローの一気通貫を目的とする。 |
| Q3 | 返却フィールド | **全フィールド** (id, isResolved, isOutdated, path, line, comments[0]) | AIが「何についてのスレッドか」を判断するために全フィールドが必要。 |
| Q4 | フィルタ/ページネーション | **`is_resolved` オプション引数（デフォルト: null=全件）、最大100件** | 1PRのスレッドは多くても数十件が通常。 |
| Q5 | PAT スコープ | **既存スコープのまま変更なし** | Fine-grained token の `Pull requests: Read and write` で GraphQL API の読み取りが可能。 |
| Q6 | フォールバック | **方式C 優先、難しければ方式B（サイドカー）** | 方式Cが技術的に困難な場合のみサイドカーへ移行。 |

---

## 3. アーキテクチャ

### 3.1 方式C: ソースパッチビルド の仕組み

```
Dockerfile.github-mcp-server ビルドフロー (変更後)
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2: builder (golang:1.26-bookworm)                          │
│                                                                  │
│  1. git fetch github/github-mcp-server@main              (既存)  │
│  2. sed パッチ (Capabilities.Extensions → Experimental)   (既存)  │
│  3. go mod edit -require=go-sdk@v1.3.1                   (既存)  │
│  ↓                                                               │
│  4. COPY patches/github/ → /src/pkg/github/              (追加)  │
│     - list_pr_review_threads.go  ← 新ツール実装                  │
│  5. RUN patch コマンドで server.go にツール登録を追記    (追加)  │
│  ↓                                                               │
│  6. go build                                             (既存)  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼ バイナリに新ツールが含まれる
┌──────────────────────────────────────────────────────────────────┐
│ Stage 3: distroless runtime                              (既存)  │
│  COPY --from=builder /server/github-mcp-server .                 │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 追加ファイル構成

```
Mcp-Docker/
├── Dockerfile.github-mcp-server   (変更: COPY/patch ステップ追加)
├── patches/
│   └── github/
│       └── list_pr_review_threads.go   (新規: Goパッチファイル)
└── docs/design/
    └── pr-review-thread-list-design.md  (本ドキュメント)
```

---

## 4. 追加MCPツール仕様

### 4.1 `list_pull_request_review_threads`

#### 概要

指定したPRのレビュースレッド一覧をGraphQL APIで取得する。
`resolve_pull_request_review_thread` と組み合わせて使う前段ツール。

#### 引数

| 引数名 | 型 | 必須 | デフォルト | 説明 |
|--------|-----|------|-----------|------|
| `owner` | string | ✓ | - | リポジトリオーナー名 |
| `repo` | string | ✓ | - | リポジトリ名 |
| `pull_number` | int | ✓ | - | PRの番号 |
| `is_resolved` | bool/null | - | `null` | `true`: 解決済みのみ, `false`: 未解決のみ, `null` (省略): 全件 |

#### 返却値（スレッド配列）

```json
[
  {
    "id": "PRRT_kwDOxxxxxxxxxxxxxxxx",
    "isResolved": false,
    "isOutdated": false,
    "path": "src/foo.go",
    "line": 42,
    "startLine": 40,
    "firstComment": {
      "body": "この処理はエラーハンドリングが必要では？",
      "author": "reviewer",
      "createdAt": "2026-03-15T10:00:00Z"
    }
  }
]
```

| フィールド | 説明 |
|------------|------|
| `id` | `PRRT_` プレフィックスの node ID（`resolve_pull_request_review_thread` の `thread_id` に渡す値） |
| `isResolved` | スレッドが解決済みかどうか |
| `isOutdated` | コードの変更で該当行が古くなったかどうか |
| `path` | 対象ファイルのパス |
| `line` | 対象行番号（末尾行） |
| `startLine` | 対象行番号（開始行）。単一行コメントの場合は `line` と同じ |
| `firstComment.body` | 最初のコメント本文（AIが内容を判断するために使用） |
| `firstComment.author` | コメントしたユーザー名 |
| `firstComment.createdAt` | コメント日時（ISO 8601） |

#### エラーパターン

| 状況 | 返却 |
|------|------|
| PR が存在しない | `404 Not Found` エラー |
| 権限不足 | `403 Forbidden` エラー |
| スレッドが0件 | 空配列 `[]` |

---

## 5. GraphQL クエリ設計

### 5.1 使用するクエリ

```graphql
query ListPRReviewThreads($owner: String!, $repo: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          comments(first: 1) {
            nodes {
              body
              author {
                login
              }
              createdAt
            }
          }
        }
      }
    }
  }
}
```

### 5.2 APIエンドポイント

- URL: `${GITHUB_API_URL}/graphql` (デフォルト: `https://api.github.com/graphql`)
- 認証: `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`
- メソッド: `POST`
- 依存ライブラリ: 追加なし（Go標準の `net/http` + `encoding/json` で実装）

### 5.3 ページネーション

初期実装は `first: 100` 固定。100件を超えるケースは現実的に稀なため、
`pageInfo.hasNextPage` が `true` の場合は最初の100件を返し、警告メッセージを付加する。

---

## 6. AIワークフロー設計（一気通貫フロー）

### 6.1 基本フロー：未解決スレッドを一括確認して対応

```
[ユーザー] 「PR #42 の未解決レビューを全部確認して解決してほしい」

[AI]
  Step 1: list_pull_request_review_threads(
            owner="org", repo="repo", pull_number=42, is_resolved=false
          )
  → 3件の未解決スレッドを取得
    - PRRT_aaa: src/foo.go:42 「エラーハンドリングが必要」
    - PRRT_bbb: src/bar.go:15 「変数名が不明瞭」
    - PRRT_ccc: README.md:8  「リンクが切れている」

  Step 2: (AIが各スレッドへの対応を実施)
    → コードを修正し、コメントに返信

  Step 3: resolve_pull_request_review_thread(
            owner="org", repo="repo", pull_number=42, thread_id="PRRT_aaa"
          )
  Step 4: resolve_pull_request_review_thread(..., thread_id="PRRT_bbb")
  Step 5: resolve_pull_request_review_thread(..., thread_id="PRRT_ccc")

[ユーザー] 全スレッド解決完了
```

### 6.2 ツール引数の統一性

`list` と `resolve` が同じコンテキスト引数 (`owner`, `repo`, `pull_number`) を持つことで、
AIがステップ間でコンテキストを再利用しやすい設計になっている。

```
list_pull_request_review_threads(owner, repo, pull_number [, is_resolved])
                  ↕ id を引き継ぐ
resolve_pull_request_review_thread(owner, repo, pull_number, thread_id)
```

---

## 7. Go実装設計

### 7.1 ファイル: `patches/github/list_pr_review_threads.go`

```
パッケージ: package github
```

#### 実装構造

```go
// GraphQL リクエスト構造体
type listPRReviewThreadsInput struct { ... }

// GraphQL レスポンス構造体
type prReviewThreadsResponse struct { ... }

// ツール実装関数
func ListPullRequestReviewThreads(client *github.Client, t translations.TranslationHelperFunc) (tool mcp.Tool, handler server.ToolHandlerFunc)

// GraphQL 実行ヘルパー（net/http で実装、外部依存なし）
func executeGraphQL(ctx context.Context, token, apiURL, query string, variables map[string]interface{}, result interface{}) error
```

#### 実装の注意点

- `GITHUB_PERSONAL_ACCESS_TOKEN` 環境変数は既存のコンテキスト経由で取得可能
- `GITHUB_API_URL` もコンテキストまたは環境変数から取得
- Go標準ライブラリのみ使用し、`go.mod` の変更を最小化する

### 7.2 ツール登録の注入方法

上流の `pkg/github/server.go` (またはそれに相当するファイル) において、
既存のツール登録パターン（例: `s.RegisterTool("resolve_pull_request_review_thread", ...)`）の
直後に以下を追記するパッチを Dockerfile で適用する:

```
# Dockerfile での sed/patch による登録行の追加イメージ
RUN grep -n "resolve_pull_request_review_thread" /src/pkg/github/server.go | head -1
RUN sed -i '/registerTool.*resolve_pull_request_review_thread/a\\t\tregisterTool(s, ListPullRequestReviewThreads(s.client, s.t))' /src/pkg/github/server.go
```

> **実装前確認事項**: 上流の `server.go` の実際のツール登録パターン（関数名・書き方）を
> `git fetch` 後に確認してから正確な sed コマンドを決定する。

---

## 8. Dockerfile 変更設計

### 8.1 変更差分（概要）

```dockerfile
# [既存] ソース取得・パッチ適用
RUN git init . && git remote add origin ... && git fetch ...
RUN sed -i 's/Capabilities.Extensions/Capabilities.Experimental/g' ...
RUN go mod edit -require=... && go mod tidy

# [追加] ここから
# 新ツールの Go ファイルをソースツリーに注入
COPY patches/github/list_pr_review_threads.go /src/pkg/github/

# ツール登録を server.go に追記（実際の関数名は上流を確認して確定）
RUN REGISTER_LINE=$(grep -n "resolve_pull_request_review_thread" /src/pkg/github/server.go | \
      grep -i "register\|add\|tool" | head -1 | cut -d: -f1) && \
    sed -i "${REGISTER_LINE}a\\$(printf '\t\t')listPRReviewThreadsTool" /src/pkg/github/server.go
# [追加] ここまで

# [既存] ビルド
RUN CGO_ENABLED=0 ... go build ...
```

### 8.2 方式Bへの切り替え条件

方式Cでの実装が以下のいずれかに該当する場合、方式B（サイドカー）に切り替える:

- 上流の登録パターンが複雑で `sed` による注入が現実的でない
- `go.mod` への外部ライブラリ追加が必要になった
- 上流の構造変更で毎ビルドのたびにパッチが壊れる頻度が高い

---

## 9. テスト計画

### 9.1 手動スモークテスト

1. `make build-custom`（カスタムイメージのビルド）後に起動
2. `list_pull_request_review_threads` がツール一覧に表示されることを確認
3. 実際のPRに対して呼び出し、`PRRT_` 形式の ID が返ることを確認
4. 返却された ID を使って `resolve_pull_request_review_thread` を呼び出し、解決できることを確認
5. `is_resolved=false` フィルタで既解決スレッドが除外されることを確認

### 9.2 CI への組み込み

- 既存の `shellcheck` / `bats` テストの範囲外（Go コード）なので、
  手動テストサマリー（`docs/MCP_MANUAL_TEST_SUMMARY_*.md`）として記録する。

---

## 10. 上流移行・撤退計画

### 上流が追いついたときの移行手順

1. `github/github-mcp-server` の公式リリースノートで `list_pull_request_review_threads` の追加を確認
2. `docker-compose.yml` の `GITHUB_MCP_IMAGE` を公式イメージに戻す
3. `Dockerfile.github-mcp-server` のパッチ追加ステップを削除（または Dockerfile 自体の使用を停止）
4. `patches/github/` ディレクトリを削除

### CHANGELOG への反映

```markdown
## [Unreleased]
### ✨ 新機能
- `list_pull_request_review_threads` ツールを追加（Goソースパッチビルド方式）
  - resolve_pull_request_review_thread との一気通貫フローを実現
  - GraphQL API 経由でスレッドのnode ID（PRRT_）を取得可能に
```

---

## 付録A: `resolve_pull_request_review_thread` 現状確認

上流に実装済みのツールのシグネチャ（参考）:

```
resolve_pull_request_review_thread(
  owner:       string,  // リポジトリオーナー
  repo:        string,  // リポジトリ名
  pull_number: int,     // PR番号
  thread_id:   string   // PRRT_xxxx (今回追加するツールで取得する値)
)
```

今回追加する `list_pull_request_review_threads` はこのシグネチャと**同じコンテキスト引数** (`owner`, `repo`, `pull_number`) を持つように設計し、AIが自然につなげられるようにする。
