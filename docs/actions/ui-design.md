# GitHub Actions Simulator - ユーザーインターフェース設計書

## 概要

使いやすさを最重視したGitHub Actions Simulatorのインターフェース設計です。開発者が直感的に操作でき、効率的なCI事前検証を可能にすることを目標とします。

## インターフェース階層

```
GitHub Actions Simulator
├── CLI Interface (Primary)
├── Web UI (Optional, Future)
└── API Interface (Internal/External)
```

## CLI インターフェース設計

### 基本コマンド構造

```bash
python main.py actions <command> [options] <workflow>...
```

複数のワークフローを同時に指定できる点が新しい特長です。第一引数にサブコマンド（`simulate` / `validate` / `list-jobs`）を指定し、続く引数で対象ファイルやディレクトリを渡します。

### メインコマンド

#### 1. シミュレーション実行 (`simulate`)

```bash
# 単一ワークフローの実行
python main.py actions simulate .github/workflows/ci.yml

# 特定ジョブのみ実行
python main.py actions simulate .github/workflows/ci.yml --job test

# 複数ワークフローを連続実行（fail-fast対応）
python main.py actions simulate \
  .github/workflows/ci.yml workflows/security.yml --fail-fast
```

#### 2. ワークフロー検証 (`validate`)

```bash
# ファイル単位で検証
python main.py actions validate .github/workflows/ci.yml --strict

# ディレクトリ配下を再帰的に検証
python main.py actions validate .github/workflows
```

#### 3. ジョブ一覧表示 (`list-jobs`)

```bash
python main.py actions list-jobs .github/workflows/ci.yml --format json
```

### Makefile 連携 (`make actions`)

```bash
# 対話モード（Enter=1 で先頭を実行）
make actions

# 非対話モード（CI/AI向け）
make actions WORKFLOW=.github/workflows/ci.yml

# インデックス指定
INDEX=2 make actions

# 追加オプションをCLIに渡す
make actions WORKFLOW=.github/workflows/ci.yml \
  CLI_ARGS="--event pull_request --ref refs/pull/42/head --output-format json"
```

| 変数        | 役割                                     |
|-------------|------------------------------------------|
| `WORKFLOW`  | 実行するワークフローファイルパス         |
| `INDEX`     | 一覧の番号指定（1始まり）               |
| `JOB`       | 特定ジョブのみ実行                      |
| `DRY_RUN`   | 1 を指定するとプランのみ表示            |
| `ENGINE`    | `builtin` / `act` の切り替え             |
| `VERBOSE` / `QUIET` / `DEBUG` | CLIの出力量を制御        |
| `CONFIG`    | TOML 設定ファイルを指定                 |
| `ENV_FILE`  | 追加の環境変数ファイル                  |
| `EVENT` / `REF` / `ACTOR` | GitHub コンテキストの上書き |
| `ENV_VARS`  | `KEY=VALUE` 形式を空白区切りで複数指定  |
| `CLI_ARGS`  | その他の CLI オプションを丸ごと連結     |

人間は `make actions` の番号選択だけで操作でき、AI や自動化ツールは変数指定で即時にワークフローを走らせられるよう設計している。

### オプション設計

#### グローバルオプション

```bash
-v, --verbose        # 詳細ログ表示
-q, --quiet          # 最小限の出力
  --debug          # デバッグモード（verboseを内包）
  --config PATH    # TOML設定ファイルを読み込む
  --version        # CLIバージョン表示
```

#### 実行オプション

```bash
# イベント・トリガー指定
  --event EVENT            # GitHubイベント名（例: push, pull_request）
  --ref REF                # Gitリファレンス（例: refs/heads/main）
  --actor NAME             # 実行ユーザー

# 実行制御
  --job JOB_ID             # 特定ジョブのみ実行
  --dry-run                # 実際のコマンド実行は行わずプランのみ表示
  --engine builtin|act     # 実行エンジンの切り替え
  --fail-fast              # 最初の失敗で残りのワークフローをスキップ

# 環境設定
  --env-file PATH          # .env 互換ファイルから読み込み
  --env KEY=VALUE          # 追加の環境変数指定（複数可）

# 出力制御
  --output-format console|json  # 実行サマリーの形式
  --output-file PATH            # サマリーをJSONとして保存
```

### 使用例

```bash
# 🎯 開発中の一般的な使用パターン

# 1. 基本的なワークフロー実行
mcp-docker sim ci.yml

# 2. プルリクエストイベントでの実行
mcp-docker sim ci.yml --event pull_request --ref refs/pull/123/head

# 3. 特定ジョブのみ実行（高速フィードバック）
mcp-docker sim ci.yml --job test

# 4. 環境変数付きで実行
mcp-docker sim ci.yml --env NODE_ENV=development --env-file .env.test

# 5. 詳細レポート付き実行
mcp-docker sim ci.yml --output-format html --output-file ci-report.html

# 6. デバッグモードでの実行
mcp-docker sim ci.yml --job build --debug --verbose

# 7. 複数ワークフロー実行（統合テスト）
mcp-docker sim run ci.yml security.yml --fail-fast
```

## コンソール出力設計

### 実行中の表示

```bash
🚀 GitHub Actions Simulator v1.0.0
📄 Workflow: .github/workflows/ci.yml
🎯 Event: push
🌿 Ref: refs/heads/main

⏱️  Parsing workflow... ✅ Done (0.1s)
🔍 Validating dependencies... ✅ Done (0.2s)
🐳 Preparing Docker environment... ✅ Done (1.2s)

📋 Execution Plan:
  └── Job: lint (ubuntu-latest)
      ├── Checkout code
      ├── Lint Dockerfile
      └── Lint Shell scripts
  └── Job: build (ubuntu-latest, needs: lint)
      ├── Checkout code
      ├── Set up Docker Buildx
      └── Build Docker image

🏃 Starting execution...

┌─ Job: lint ─────────────────────────────────────────┐
│ 🐳 Container: ubuntu:latest                        │
│ ⏱️  Started: 2025-01-15 10:30:15                   │
├─────────────────────────────────────────────────────┤
│ 📥 Step 1/3: Checkout code                         │
│ ✅ actions/checkout@v4 completed (2.1s)            │
│                                                     │
│ 🔍 Step 2/3: Lint Dockerfile                       │
│ ✅ hadolint completed successfully (1.8s)          │
│                                                     │
│ 🧹 Step 3/3: Lint Shell scripts                    │
│ ✅ shellcheck completed successfully (3.2s)        │
├─────────────────────────────────────────────────────┤
│ ✅ Job completed successfully (7.1s)                │
└─────────────────────────────────────────────────────┘

┌─ Job: build ────────────────────────────────────────┐
│ 🐳 Container: ubuntu:latest                        │
│ ⏱️  Started: 2025-01-15 10:30:22                   │
├─────────────────────────────────────────────────────┤
│ 📥 Step 1/3: Checkout code                         │
│ ✅ actions/checkout@v4 completed (1.9s)            │
│                                                     │
│ 🔧 Step 2/3: Set up Docker Buildx                  │
│ ✅ docker/setup-buildx-action@v3 completed (4.5s)  │
│                                                     │
│ 🏗️  Step 3/3: Build Docker image                   │
│ ✅ Docker build completed successfully (45.2s)     │
├─────────────────────────────────────────────────────┤
│ ✅ Job completed successfully (51.6s)               │
└─────────────────────────────────────────────────────┘

🎉 Workflow completed successfully!
⏱️  Total execution time: 58.7s
📊 Jobs: 2 completed, 0 failed
📈 Success rate: 100%
```

### エラー表示

```bash
❌ Job: test failed

┌─ Job: test ─────────────────────────────────────────┐
│ 🐳 Container: ubuntu:latest                        │
│ ⏱️  Started: 2025-01-15 10:35:10                   │
├─────────────────────────────────────────────────────┤
│ 📥 Step 1/2: Checkout code                         │
│ ✅ actions/checkout@v4 completed (2.0s)            │
│                                                     │
│ 🧪 Step 2/2: Run tests                             │
│ ❌ pytest failed with exit code 1                  │
│                                                     │
│ 📋 Error Details:                                  │
│ ═══════════════════════════════════════════════════  │
│ FAILED tests/test_main.py::test_version - Assert... │
│ AssertionError: assert '1.0.0' == '1.0.1'         │
│   - 1.0.1                                          │
│   + 1.0.0                                          │
│ ═══════════════════════════════════════════════════  │
├─────────────────────────────────────────────────────┤
│ ❌ Job failed (12.3s)                              │
└─────────────────────────────────────────────────────┘

💡 Suggestions:
  • Check test expectations in tests/test_main.py
  • Verify version number in main.py matches expected value
  • Run tests locally: pytest tests/test_main.py::test_version

📊 Summary:
  ✅ 1 job completed successfully
  ❌ 1 job failed
  ⏱️  Total time: 14.3s
  🔗 Detailed logs: ./output/simulation-20250115-103510.log
```

## 設定ファイル設計

### メイン設定ファイル (simulator.toml)

```toml
[simulator]
version = "1.0.0"
default_event = "push"
default_runner = "ubuntu-latest"
cleanup_after_run = true
max_parallel_jobs = 4

[docker]
network = "actions-simulator"
image_cache = true
pull_policy = "if-not-present"

[runners]
"ubuntu-latest" = "ghcr.io/catthehacker/ubuntu:act-latest"
"ubuntu-22.04" = "ghcr.io/catthehacker/ubuntu:act-22.04"
"ubuntu-20.04" = "ghcr.io/catthehacker/ubuntu:act-20.04"

[actions]
allowed_actions = [
  "actions/checkout@*",
  "actions/setup-python@*",
  "actions/setup-node@*",
  "docker/setup-buildx-action@*"
]

[security]
network_access = false
allow_privileged = false
secret_masking = true

[output]
default_format = "console"
log_level = "info"
color = true
```

### 環境変数ファイル (.env.simulator)

```bash
# GitHub関連
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_ACTOR=testuser
GITHUB_REPOSITORY=owner/repo

# アプリケーション固有
NODE_ENV=test
DATABASE_URL=sqlite:///test.db
API_KEY=test-api-key

# Docker関連
DOCKER_BUILDKIT=1
BUILDX_EXPERIMENTAL=1
```

### シークレットファイル (.secrets.json)

```json
{
  "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx",
  "DOCKER_PASSWORD": "supersecret123",
  "API_SECRET_KEY": "secret-key-value",
  "DATABASE_PASSWORD": "db-password"
}
```

## API インターフェース設計

### REST API エンドポイント

```yaml
# OpenAPI 3.0 specification
openapi: 3.0.0
info:
  title: GitHub Actions Simulator API
  version: 1.0.0

paths:
  /api/v1/simulate:
    post:
      summary: ワークフロー実行開始
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [workflow_path]
              properties:
                workflow_path:
                  type: string
                  example: ".github/workflows/ci.yml"
                event:
                  type: string
                  enum: [push, pull_request, schedule]
                  default: push
                environment:
                  type: object
                  additionalProperties:
                    type: string

  /api/v1/simulate/{run_id}:
    get:
      summary: 実行状況取得
      parameters:
        - name: run_id
          in: path
          required: true
          schema:
            type: string

  /api/v1/workflows:
    get:
      summary: 利用可能ワークフロー一覧
      responses:
        '200':
          description: ワークフロー一覧
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Workflow'

components:
  schemas:
    Workflow:
      type: object
      properties:
        name:
          type: string
        path:
          type: string
        jobs:
          type: array
          items:
            $ref: '#/components/schemas/Job'

    Job:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        runs-on:
          type: string
        needs:
          type: array
          items:
            type: string
```

## Web UI 設計 (Future Phase)

### ダッシュボード画面

```text
┌─────────────────────────────────────────────────────────────┐
│ 🚀 GitHub Actions Simulator                   [Settings] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📊 実行統計 (過去30日)                                        │
│ ┌─────────────┬─────────────┬─────────────┬─────────────┐     │
│ │ 総実行回数    │ 成功率      │ 平均実行時間   │ 最終実行      │     │
│ │ 247回       │ 94.3%      │ 3m 42s     │ 2分前       │     │
│ └─────────────┴─────────────┴─────────────┴─────────────┘     │
│                                                             │
│ 🔄 最近の実行                                               │
│ ┌───────────────────────────────────────────────────────┐     │
│ │ ✅ ci.yml          │ 3m 21s │ 2分前   │ [ログ] [再実行] │     │
│ │ ❌ security.yml    │ 1m 45s │ 15分前  │ [ログ] [再実行] │     │
│ │ ✅ release.yml     │ 8m 12s │ 1時間前 │ [ログ] [再実行] │     │
│ └───────────────────────────────────────────────────────┘     │
│                                                             │
│ 🎯 クイック実行                                              │
│ ┌─ ワークフロー選択 ─────────┐ ┌─ オプション ─────────┐        │
│ │ ○ ci.yml                │ │ Event: [push ▼]    │        │
│ │ ○ security.yml          │ │ Branch: [main]     │        │
│ │ ○ release.yml           │ │ Job: [全て ▼]       │        │
│ │ ○ docs.yml              │ │                   │        │
│ └─────────────────────────┘ └─────────────────────┘        │
│                                                             │
│                              [🚀 実行開始]                 │
└─────────────────────────────────────────────────────────────┘
```

### 実行詳細画面

```text
┌─────────────────────────────────────────────────────────────┐
│ 📋 ci.yml - 実行詳細                            [🔄] [❌]   │
├─────────────────────────────────────────────────────────────┤
│ 🎯 push event • main branch • 3m 21s • ✅ 成功              │
│                                                             │
│ 📊 進行状況                                                  │
│ ████████████████████████████████████████ 100% (2/2)       │
│                                                             │
│ 🔄 ジョブ実行フロー                                          │
│ ┌─────────┐    ┌─────────┐                                │
│ │  lint   │───▶│  build  │                                │
│ │ ✅ 1m2s  │    │ ✅ 2m19s │                                │
│ └─────────┘    └─────────┘                                │
│                                                             │
│ 📝 実行ログ                                  [ダウンロード]    │
│ ┌───────────────────────────────────────────────────────┐     │
│ │ lint                                   ▼ [展開/折畳]  │     │
│ │ ├── 📥 Checkout code (2.1s) ✅                        │     │
│ │ ├── 🔍 Lint Dockerfile (1.8s) ✅                      │     │
│ │ └── 🧹 Lint Shell scripts (3.2s) ✅                   │     │
│ │                                                       │     │
│ │ build                                  ▼ [展開/折畳]  │     │
│ │ ├── 📥 Checkout code (1.9s) ✅                        │     │
│ │ ├── 🔧 Set up Docker Buildx (4.5s) ✅                 │     │
│ │ └── 🏗️ Build Docker image (45.2s) ✅                  │     │
│ └───────────────────────────────────────────────────────┘     │
│                                                             │
│ 🎛️ アクション                                               │
│ [📋 レポート出力] [🔄 再実行] [📊 統計] [📤 共有]            │
└─────────────────────────────────────────────────────────────┘
```

## アクセシビリティ・使いやすさ

### CLI使いやすさ機能

1. **マルチワークフロー実行と fail-fast**

   ```bash
   python main.py actions simulate ci.yml security.yml --fail-fast
   ```

   1コマンドで複数ワークフローを連続実行し、`--fail-fast` が最初の失敗後に残りの処理をスキップします。

1. **JSON/コンソールの柔軟なサマリー表示**

   ```bash
   python main.py actions simulate ci.yml --output-format json --output-file summary.json
   ```

   Rich のテーブルによるカラー出力と、JSONファイル保存によるレポート自動化の両方に対応します。

1. **環境変数の上書きと設定ファイル統合**

   ```bash
   python main.py actions simulate ci.yml --config simulator.toml --env GITHUB_ACTOR=local
   ```

   TOML 設定からデフォルトのイベントやリファレンスを読み込みつつ、`--env` や `--env-file` で本番相当の環境を簡単に再現できます。

### エラーハンドリング

1. **分かりやすいエラーメッセージ**

  ```bash
   ❌ Error: Workflow file not found

   📍 Searched locations:
     • .github/workflows/ci.yml
     • ./ci.yml
     • workflows/ci.yml

   💡 Did you mean:
     • .github/workflows/ci-test.yml
     • .github/workflows/build.yml
   ```

1. **修正提案**
   - 設定ミスの自動検出
   - 具体的な修正方法の提示
   - 関連ドキュメントへのリンク

### パフォーマンス表示

```bash
📈 Performance Summary:
┌──────────────────┬──────────┬──────────────┬────────────┐
│ Job              │ Duration │ CPU Usage    │ Memory     │
├──────────────────┼──────────┼──────────────┼────────────┤
│ lint             │ 1m 02s   │ 45%          │ 512 MB     │
│ build            │ 2m 19s   │ 78%          │ 1.2 GB     │
├──────────────────┼──────────┼──────────────┼────────────┤
│ Total            │ 3m 21s   │ 62% (avg)    │ 1.7 GB     │
└──────────────────┴──────────┴──────────────┴────────────┘

💡 Performance Tips:
  • build job uses high memory - consider using smaller base images
  • Enable Docker layer caching for faster builds
  • Consider splitting build job into smaller steps
```

## 統合開発環境（IDE）連携

### VS Code Extension (Future)

```json
{
  "commands": [
    {
      "command": "github-actions-simulator.run",
      "title": "Run Workflow",
      "category": "GitHub Actions"
    },
    {
      "command": "github-actions-simulator.validate",
      "title": "Validate Workflow",
      "category": "GitHub Actions"
    }
  ],
  "keybindings": [
    {
      "command": "github-actions-simulator.run",
      "key": "ctrl+shift+a",
      "when": "editorTextFocus && resourceExtname == .yml"
    }
  ]
}
```

## まとめ

このユーザーインターフェース設計は、開発者の日常的なワークフローに自然に統合され、GitHub Actions の事前検証を効率的かつ直感的に行えることを目指しています。

**主要な特徴:**

- 🚀 **高速起動**: 1コマンドで即座に実行開始
- 🎯 **直感的操作**: 覚えやすいコマンド体系
- 📊 **豊富な情報**: 実行状況、統計、パフォーマンス情報
- 🔍 **優れたデバッグ**: 詳細ログ、エラー診断、修正提案
- ⚡ **柔軟な設定**: 環境、オプション、出力形式の自由な組み合わせ

段階的な実装により、まずは CLI インターフェースを完璧に仕上げ、その後 Web UI や IDE 統合など、より高度な機能を追加していく計画です。
