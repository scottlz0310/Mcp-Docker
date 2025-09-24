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
mcp-docker actions-simulator <command> [options] [workflow-file]
```

### メインコマンド

#### 1. シミュレーション実行
```bash
# 基本実行
mcp-docker actions-simulator run .github/workflows/ci.yml

# エイリアス（短縮形）
mcp-docker sim run ci.yml
mcp-docker sim ci.yml  # runは省略可能

# 複数ワークフロー同時実行
mcp-docker sim run ci.yml security.yml release.yml
```

#### 2. ワークフロー検証
```bash
# 文法チェック
mcp-docker sim validate .github/workflows/ci.yml

# 全ワークフローの一括検証
mcp-docker sim validate .github/workflows/

# 詳細検証（依存関係、セキュリティ等）
mcp-docker sim validate ci.yml --strict --security
```

#### 3. ワークフロー情報表示
```bash
# ワークフロー構造表示
mcp-docker sim info ci.yml

# ジョブ一覧表示
mcp-docker sim jobs ci.yml

# 実行履歴表示
mcp-docker sim history
```

### オプション設計

#### グローバルオプション
```bash
--verbose, -v         # 詳細ログ表示
--quiet, -q          # 最小限の出力
--debug              # デバッグモード
--config CONFIG      # 設定ファイル指定
--help, -h          # ヘルプ表示
--version           # バージョン表示
```

#### 実行オプション
```bash
# イベント・トリガー指定
--event push                    # push イベントをシミュレート
--event pull_request           # PR イベントをシミュレート
--ref refs/heads/main          # ブランチ指定
--actor username               # 実行ユーザー指定

# 実行制御
--job JOB_NAME                 # 特定ジョブのみ実行
--skip-job JOB_NAME           # 特定ジョブをスキップ
--fail-fast                   # 最初の失敗で停止
--continue-on-error           # エラー時も続行

# 環境設定
--env-file .env.local         # 環境変数ファイル
--secret-file .secrets        # シークレットファイル
--env KEY=VALUE              # 環境変数直接指定

# 出力制御
--output-format json|html|text # 出力形式
--output-file report.html     # 出力ファイル
--no-cleanup                 # 一時ファイル保持
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

```
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

```
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

1. **インタラクティブモード**
   ```bash
   mcp-docker sim
   # 対話式でワークフロー選択・オプション設定
   ```

2. **オートコンプリート**
   ```bash
   # Bash/Zsh completion
   mcp-docker sim <TAB>
   # → run validate info jobs history
   ```

3. **進捗表示**
   - プログレスバー
   - 残り時間推定
   - リアルタイム統計

4. **カラー出力**
   - 成功（緑）、エラー（赤）、警告（黄）
   - `--no-color`オプション対応

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

2. **修正提案**
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
