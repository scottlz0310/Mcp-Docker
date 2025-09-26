# MCP Docker Environment

Model Context Protocol（MCP）サーバーのためのプロダクション対応Docker環境

[![CI Status](https://github.com/scottlz0310/mcp-docker/workflows/CI/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Security Scan](https://github.com/scottlz0310/mcp-docker/workflows/Security/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Documentation](https://github.com/scottlz0310/mcp-docker/workflows/Documentation/badge.svg)](https://scottlz0310.github.io/mcp-docker)

### 📦 バージョン情報

- **現在のバージョン**: v1.0.1
- **最終更新**: 2025年09月24日
- **サポート**: Python 3.13+

### 📊 プロジェクト統計

- **ファイル数**: 1313個のソースファイル
- **テスト数**: 4個のテストファイル
- **Dockerサービス**: 4個の定義済みサービス
- **最新コミット**: `bbbef3e chore: bump version to 1.0.1...`

## 📁 構成

```
mcp-docker/
├── services/           # サービス別設定
│   ├── github/         # GitHub MCP設定
│   ├── datetime/       # 日付検証スクリプト
│   └── codeql/         # CodeQL設定
├── scripts/            # 管理スクリプト
├── docs/              # ドキュメント
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
| CodeQL | - | 静的コード分析ツール |
| Actions Simulator API | 8000 | FastAPI ベースのワークフローシミュレーター REST サービス |

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

### 📋 利用可能コマンド

```bash
  make build     - Build unified image
  make start     - Start DateTime validator
  make stop      - Stop all services
  make logs      - Show logs
  make clean     - Clean up containers and images
  make github    - Start GitHub MCP server
  make datetime  - Start DateTime validator
  make codeql    - Run CodeQL analysis
  make actions   - Interactive GitHub Actions Simulator (Docker)
  make actions-api - Launch Actions REST API (uvicorn)
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
  make docs              - Generate documentation
  make docs-serve        - Serve documentation locally
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

### � 詳細ドキュメント

完全なリリースシステムの詳細については、**[�📚 リリース自動化システム完全ガイド](docs/RELEASE_SYSTEM.md)**を参照してください。

## 📚 ドキュメント体系

### 🏗️ ドキュメント生成

```bash
make docs              # Sphinx + GitHub Pages自動ドキュメント生成
make docs-serve        # ローカルでドキュメント表示
make docs-clean        # ドキュメントビルドクリーンアップ
```

### 🌐 オンラインリソース

- **🏠 メインドキュメント**: <https://scottlz0310.github.io/Mcp-Docker/>
- **📋 API リファレンス**: 自動生成Sphinxドキュメント
- **🚀 リリースシステム**: [docs/RELEASE_SYSTEM.md](docs/RELEASE_SYSTEM.md)
- **🔧 トラブルシューティング**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **🔒 セキュリティ**: [docs/PERMISSION_SOLUTIONS.md](docs/PERMISSION_SOLUTIONS.md)

## 🔧 サービス詳細

### GitHub MCP Server

- ポート: 8080
- GitHub API連携
- 環境変数: `GITHUB_PERSONAL_ACCESS_TOKEN`

### DateTime Validator

- ファイル監視による日付自動修正
- 2025-01, 2024-12などの疑わしい日付を検出

### CodeQL

- 静的コード分析
- オンデマンド実行

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
uv sync --group dev --group docs

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
