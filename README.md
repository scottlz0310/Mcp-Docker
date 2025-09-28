# MCP Docker Environment

Model Context Protocol（MCP）サーバーのためのプロダクション対応Docker環境

[![CI Status](https://github.com/scottlz0310/mcp-docker/workflows/CI/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Security Scan](https://github.com/scottlz0310/mcp-docker/workflows/Security/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)

## 📦 バージョン情報

- **現在のバージョン**: v1.0.1
- **最終更新**: 2025年09月24日
- **サポート**: Python 3.13+

## 📊 プロジェクト統計

- **ファイル数**: 1313個のソースファイル
- **テスト数**: 4個のテストファイル
- **Dockerサービス**: 3個の定義済みサービス
- **最新コミット**: `bbbef3e chore: bump version to 1.0.1...`

## 📁 構成

```text
mcp-docker/
├── services/           # サービス別設定
│   ├── github/         # GitHub MCP設定
│   ├── datetime/       # 日付検証スクリプト
│   └── (archived)      # CodeQL設定は archive/services/codeql/ へ移動
├── scripts/            # 管理スクリプト
├── docs/              # 運用ドキュメント (Markdown)
├── tests/             # テストスイート
├── Dockerfile          # 統合イメージ
├── docker-compose.yml  # サービス定義
├── Makefile           # 簡単コマンド
└── .env.template      # 環境変数テンプレート
```

## ✨ 特徴

- **統合イメージ**: 1つのDockerイメージで全機能提供
- **サービス分離**: 同じイメージから異なるコマンドで起動
- **軽量運用**: 必要なサービスのみ選択起動
- **セキュリティ強化**: 非root実行、読み取り専用マウント
- **自動化**: CI/CD、リリース管理、テスト完全自動化

### 🚀 提供サービス

| サービス名 | ポート | 説明 |
|-----------|--------|------|
| GitHub MCP | 8080 | GitHub API連携のMCPサーバー |
| DateTime Validator | - | 日付検証・自動修正サービス |
| Actions Simulator API | 8000 | FastAPI ベースのワークフローシミュレーター REST サービス |

> ℹ️ CodeQL ベースのローカル静的解析サービスは 2025-09-27 に撤去されました。過去の設定は `archive/services/codeql/` に保管されており、GitHub Actions のセキュリティワークフローでは Trivy を中心としたスキャンを継続しています。

## 🚀 クイックスタート

### 1. 初期設定

```bash
# 環境変数設定
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc

# セットアップ実行
./scripts/setup.sh
```

### 2. 使用方法

#### GitHub Actions Simulator CLI

```bash
uv run python main.py actions --help
```

グローバルオプションとして `-v/--verbose`, `-q/--quiet`, `--debug`, `--config <path>`, `--version` をサポートしています。設定ファイルは TOML 形式で、`[simulator]` や `[environment]` セクションからデフォルト値を読み込みます。

#### 🔧 診断・トラブルシューティング機能

```bash
# システム全体の健康状態チェック
uv run python main.py actions diagnose

# 詳細診断（パフォーマンス分析・実行トレース含む）
uv run python main.py actions diagnose --include-performance --include-trace

# ワークフロー実行前の事前診断
uv run python main.py actions simulate .github/workflows/ci.yml --diagnose

# 強化されたエラー検出・自動復旧機能
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery

# ハングアップ時のデバッグバンドル自動作成
uv run python main.py actions simulate .github/workflows/ci.yml --create-debug-bundle
```

代表的な実行例:

```bash
# 単一ワークフローをシミュレート
uv run python main.py actions simulate .github/workflows/ci.yml --job test

# 複数ワークフローをまとめて実行し、fail-fast で早期終了
uv run python main.py actions simulate .github/workflows/ci.yml workflows/security.yml \
  --fail-fast --event pull_request --ref refs/pull/42/head

# 実行結果のサマリーを JSON で保存
uv run python main.py actions simulate .github/workflows/ci.yml --output-format json \
  --output-file output/simulation-summary.json

# 追加の環境変数を上書きして実行
uv run python main.py actions simulate .github/workflows/ci.yml \
  --env GITHUB_ACTOR=local-dev --env NODE_ENV=development
```

検証用途には `validate`、ジョブ一覧確認には `list-jobs` サブコマンドを使用してください。複数のワークフローをまとめて検証する場合は `uv run python main.py actions validate .github/workflows --strict` のようにディレクトリを指定できます。

#### make actions ターゲットの活用

```bash
# 対話モード（番号を選択、Enter だけで先頭を実行）
make actions

# 非対話モード（AI/CI向け）
make actions WORKFLOW=.github/workflows/ci.yml

# インデックス指定で実行
INDEX=2 make actions

# 追加オプションをCLIに伝達
make actions WORKFLOW=.github/workflows/ci.yml \
  CLI_ARGS="--event pull_request --ref refs/pull/42/head --output-format json"

# 環境変数をまとめて注入
ENV_VARS="NODE_ENV=dev FEATURE_FLAG=on" make actions WORKFLOW=.github/workflows/dev.yml
```

利用可能な変数: `WORKFLOW`（パス）、`INDEX`（一覧の番号）、`JOB`、`DRY_RUN`、`VERBOSE`/`QUIET`/`DEBUG`、`CONFIG`、`ENV_FILE`、`EVENT`、`REF`、`ACTOR`、`ENV_VARS`、`CLI_ARGS` など。人間は `make actions` の番号選択だけで実行でき、AI や自動化は変数指定で即座にワークフローを走らせられます。

#### ワンショットスクリプト (`scripts/run-actions.sh`)

```bash
# 最新イメージを取得しつつワークフローをシミュレート
./scripts/run-actions.sh .github/workflows/ci.yml -- --fail-fast

# 引数なしでヘルプを確認
./scripts/run-actions.sh
```

スクリプトは Docker / Docker Compose のバージョンを確認し、`actions-simulator` コンテナで Click CLI を起動します。追加の CLI 引数は `--` 区切りで渡せます（例: `-- --job build --output-format json`）。

### 📋 利用可能コマンド

```bash
  make build     - Build unified image
  make start     - Start DateTime validator
  make stop      - Stop all services
  make logs      - Show logs
  make clean     - Clean up containers and images
  make github    - Start GitHub MCP server
  make datetime  - Start DateTime validator
  make actions   - Interactive GitHub Actions Simulator (Docker)
  make test      - Run integration tests
  make test-all  - Run all test suites
  make test-bats - Run Bats test suite
  make security  - Run security scan
  make sbom      - Generate SBOM
  make audit-deps - Audit dependencies
  make version           - Show current version
  make version-sync      - Sync versions between pyproject.toml and main.py
  make release-check     - Check release readiness
  make setup-branch-protection - Setup branch protection
```

## 📦 バージョン管理

### 現在のバージョンを確認

```bash
make version
```

このコマンドで以下の情報が表示されます：

- pyproject.tomlのバージョン
- main.pyのバージョン
- 最新のGitタグ（存在する場合）
- 推奨される次のバージョン（patch/minor/major）

### バージョンの同期

pyproject.tomlとmain.pyのバージョンが不整合の場合、自動で同期できます：

```bash
make version-sync
```

このコマンドはpyproject.tomlのバージョンをmain.pyに反映します。

### 🚀 クイックリリース実行

**GitHub ActionsのRelease Managementワークフローを使用（推奨）**:

1. **🌐 [GitHub Actions](https://github.com/scottlz0310/Mcp-Docker/actions)** → **「🚀 Release Management」**を選択
2. **「Run workflow」**をクリック
3. **バージョン指定**: 新しいバージョン (例: `1.3.7`, `2.0.0`)
4. **プレリリース**: 必要に応じて「Mark as prerelease」をチェック
5. **「Run workflow」**で完全自動化実行開始

**または、コマンドラインから**:

```bash
# タグプッシュによる自動リリース
git tag v1.3.7
git push origin v1.3.7
```

### 📄 詳細ドキュメント

完全なリリースシステムの詳細については、**[📚 リリース自動化システム完全ガイド](docs/RELEASE_SYSTEM.md)**を参照してください。

## 📚 ドキュメント体系

### 🌐 オンラインリソース

- **🚀 リリースシステム**: [docs/RELEASE_SYSTEM.md](docs/RELEASE_SYSTEM.md)
- **🔧 トラブルシューティング**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **🚨 ハングアップ問題対応**: [docs/HANGUP_TROUBLESHOOTING.md](docs/HANGUP_TROUBLESHOOTING.md)
- **🔧 診断コマンド完全ガイド**: [docs/DIAGNOSTIC_COMMANDS.md](docs/DIAGNOSTIC_COMMANDS.md)
- **🔒 セキュリティ**: [docs/PERMISSION_SOLUTIONS.md](docs/PERMISSION_SOLUTIONS.md)
- **📊 API仕様**: [docs/API.md](docs/API.md)
- **🗂️ アーカイブ済み Sphinx プロジェクト**: `archive/docs/sphinx/` (HTML 生成に再利用する場合)
- **🛡️ アーカイブ済み CodeQL 設定**: `archive/services/codeql/`

### 🔧 実装詳細ドキュメント

- **🐳 Docker統合**: [docs/docker-integration-implementation-summary.md](docs/docker-integration-implementation-summary.md)
- **🔄 自動復旧**: [docs/auto_recovery_implementation_summary.md](docs/auto_recovery_implementation_summary.md)
- **📈 パフォーマンス監視**: [docs/performance_monitoring_implementation.md](docs/performance_monitoring_implementation.md)

## 🔧 サービス詳細

### GitHub MCP Server

- ポート: 8080
- GitHub API連携
- 環境変数: `GITHUB_PERSONAL_ACCESS_TOKEN`

### DateTime Validator

- ファイル監視による日付自動修正
- 2025-01, 2024-12などの疑わしい日付を検出

### Actions Simulator API

- ポート: 8000 (`make actions-api` または `docker compose --profile tools up actions-simulator`)
- エンドポイント:
  - `GET /actions/healthz`
  - `POST /actions/simulate`
- 利用例:

```bash
curl -X POST http://localhost:8000/actions/simulate \
  -H "Content-Type: application/json" \
  -d '{"workflow_file": ".github/workflows/ci.yml", "engine": "builtin"}'
```

## 🛡️ セキュリティ

### セキュリティ機能

- **非root実行**: 動的UID/GIDマッピング
- **読み取り専用マウント**: コンテナセキュリティ強化
- **リソース制限**: メモリ・CPU使用量制限
- **自動セキュリティスキャン**: TruffleHog, Trivy統合

### セキュリティテスト

```bash
make security          # セキュリティスキャン実行
make validate-security # セキュリティ設定検証
```

## 🧪 テスト

```bash
make test              # 基本テスト
make test-all          # 全テストスイート
make test-security     # セキュリティテスト
make test-integration  # 統合テスト
```

## 🤝 開発・貢献

### 開発環境セットアップ

```bash
# 開発依存関係インストール
uv sync --group dev

# Pre-commitフック設定
pre-commit install
```

### 貢献方法

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。
