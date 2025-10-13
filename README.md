# MCP Docker - Docker統合管理システム

Model Context Protocol (MCP) サーバーとDevOpsツールのプロダクション対応Docker統合環境

[![CI Status](https://github.com/scottlz0310/mcp-docker/workflows/CI/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Security Scan](https://github.com/scottlz0310/mcp-docker/workflows/Security/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)

## 概要

MCP Dockerは、複数のMCPサーバーとDevOpsツールを統合管理するDocker環境です。GitHub MCP Server、DateTime Validator、Actions Simulator、GitHub Release Watcherなど、複数のサービスを簡単にデプロイ・管理できます。

## 🎯 提供サービス

### 1. GitHub MCP Server
GitHub公式のModel Context Protocolサーバー。リポジトリ管理、Issue/PR操作、GitHub Actions連携などを提供。

### 2. DateTime Validator
ワークスペース内のファイルのタイムスタンプを検証し、一貫性をチェックするサービス。

### 3. GitHub Actions Simulator
GitHub Actionsワークフローのローカルシミュレーター。Dockerコンテナ内でactを使用した高速シミュレーション。

### 4. GitHub Release Watcher 🆕
任意のGitHubリポジトリの新しいリリースを監視し、複数の通知チャネル（Native/Discord/Slack/Email）で通知するサービス。

[→ GitHub Release Watcher 詳細ドキュメント](./examples/github-release-watcher/README.md)

## 主要機能

### 🚀 統合管理
- **マルチサービス**: 複数のMCPサーバーとツールを一元管理
- **Docker Compose**: シンプルな設定で全サービスをデプロイ
- **環境変数管理**: .envファイルによる統一的な設定管理

### 🔔 GitHub Release Watcher（新機能）
- **マルチチャネル通知**: Native/Discord/Slack/Email/Webhook/File出力
- **非同期処理**: 高速な並列リポジトリチェック
- **バージョン比較**: セマンティックバージョニング対応
- **フィルタリング**: 安定版/プレリリース/カスタムパターン

### 🎭 Actions Simulator
- **ワンショット実行**: 複雑な設定不要、単一コマンドで即座に開始
- **軽量actベース**: Dockerコンテナ内でactを使用した高速シミュレーション
- **自動依存関係管理**: Docker、uv、gitの自動チェックとガイダンス
- **包括的診断**: 実行前チェック、エラー検出、自動復旧機能

## クイックスタート

### 前提条件
- Docker 20.10+
- Python 3.13+
- Git

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 環境設定
cp .env.example .env
# .envファイルを編集してGitHubトークンを設定

# 依存関係のインストール
uv sync
```

## 使用方法

### 全サービスの起動

```bash
# 全サービスを起動
docker compose up -d

# 特定のサービスのみ起動
docker compose up -d github-mcp
docker compose up -d datetime-validator
docker compose up -d actions-simulator
docker compose up -d github-release-watcher
```

### GitHub Release Watcher

```bash
# サービスを起動
./examples/github-release-watcher/scripts/start.sh

# ログをフォロー
./examples/github-release-watcher/scripts/start.sh --follow

# サービスを停止
./examples/github-release-watcher/scripts/stop.sh
```

詳細は [GitHub Release Watcher ドキュメント](./examples/github-release-watcher/README.md) を参照。

### Actions Simulator

```bash
# ワークフローの実行
make actions-run WORKFLOW=.github/workflows/ci.yml

# 対話モードでの実行
make actions

# CI互換モードで実行（推奨）
make actions-ci WORKFLOW=.github/workflows/ci.yml
```

## 📦 バージョン情報

- **現在のバージョン**: v1.2.0
- **最終更新**: 2025年10月05日
- **サポート**: Python 3.13+、Docker 20.10+、act 0.2.40+

## 📁 軽量アーキテクチャ構成

```text
github-actions-simulator/
├── scripts/
│   └── run-actions.sh     # ワンショット実行スクリプト（メインエントリーポイント）
├── src/                   # 軽量シミュレーターコア
│   ├── diagnostic_service.py    # 診断・トラブルシューティング
│   ├── execution_tracer.py      # 実行トレース機能
│   └── performance_monitor.py   # パフォーマンス監視
├── main.py               # CLI エントリーポイント
├── Dockerfile            # 統合マルチステージビルド（MCP、Validator、Actions）
├── docker-compose.yml    # シンプルなサービス定義
├── Makefile             # 開発者向けコマンド
└── .env.template        # 設定テンプレート
```

## ✨ 軽量actベースアーキテクチャの利点

**🎯 シンプルで高速**

- **最小限の依存関係**: Docker + act のみでフル機能
- **高速起動**: 軽量コンテナで数秒での実行開始
- **メモリ効率**: 必要最小限のリソース使用

**🔧 開発者フレンドリー**

- **ゼロ設定**: 依存関係の自動チェックと環境セットアップ
- **インテリジェントエラー処理**: プラットフォーム別の詳細ガイダンス
- **段階的復旧**: 自動復旧提案と手動修正支援

**🚀 プロダクション対応**

- **CI/CD統合**: 非対話モードでの自動化対応
- **包括的診断**: システム健康状態の詳細チェック
- **セキュリティ強化**: 非root実行、最小権限の原則

## 🚀 5分クイックスタート

### ステップ1: 前提条件の確認（1分）

```bash
# 必要なツールの確認（自動チェック機能付き）
./scripts/run-actions.sh --check-deps
```

**必要な環境:**

- Docker 20.10+ & Docker Compose 2.0+
- Git 2.20+
- uv（推奨、なくても動作）

### ステップ2: ワンショット実行（30秒）

```bash
# 最もシンプルな実行方法
./scripts/run-actions.sh

# または特定のワークフローを直接実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

### ステップ3: 高度な機能を試す（3分）

```bash
# 診断機能付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose --enhanced

# 自動復旧機能を有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery

# パフォーマンス監視付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics
```

## 🎯 即座に使える実行パターン

```bash
# 🔍 対話的選択（初心者向け）
./scripts/run-actions.sh

# 🤖 非対話モード（CI/CD向け）
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 📊 包括的診断付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --enhanced --auto-recovery --show-performance-metrics

# ⚡ 高速実行（最小オプション）
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test
```

## 🎛️ 使用方法

### メイン実行方式

**1. ワンショットスクリプト（推奨）**

```bash
# 基本実行
./scripts/run-actions.sh [ワークフローファイル] [-- <追加オプション>]

# 例：対話的選択
./scripts/run-actions.sh

# 例：特定ワークフロー実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 例：高度なオプション付き
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --enhanced
```

**2. Make コマンド（開発者向け）**

```bash
# 対話的ワークフロー選択
make actions

# 特定ワークフロー実行
make actions WORKFLOW=.github/workflows/ci.yml

# 環境変数付き実行
ENV_VARS="NODE_ENV=dev" make actions WORKFLOW=.github/workflows/test.yml
```

**3. 直接CLI（上級者向け）**

```bash
# Docker コンテナ内でCLI実行
uv run python main.py actions simulate .github/workflows/ci.yml

# 利用可能なオプション確認
uv run python main.py actions --help
```

## 🔧 軽量actベースの強化機能

**インテリジェント診断システム**

```bash
# 包括的システム診断
./scripts/run-actions.sh --check-deps

# 実行前診断付きシミュレーション
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose
```

**自動復旧機能**

```bash
# Docker再接続・プロセス再起動・バッファクリア
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery

# 段階的タイムアウト管理
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced
```

**リアルタイム監視**

```bash
# パフォーマンス監視
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics

# 実行トレース
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-execution-trace
```

## 📋 実用的な使用例

**基本的なワークフロー実行**

```bash
# 最もシンプルな実行（対話的選択）
./scripts/run-actions.sh

# 特定のワークフローを直接実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 特定のジョブのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test

# 複数ワークフローの実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --event pull_request --ref refs/pull/42/head
```

**診断・トラブルシューティング**

```bash
# 依存関係チェックのみ実行
./scripts/run-actions.sh --check-deps

# 実行前診断付きシミュレーション
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose

# 包括的診断（パフォーマンス・トレース含む）
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --show-performance-metrics --show-execution-trace
```

**自動化・CI/CD統合**

```bash
# 非対話モード（CI/CD環境向け）
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# インデックス指定で自動選択
INDEX=1 ./scripts/run-actions.sh

# 環境変数付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --env GITHUB_ACTOR=ci-bot --env NODE_ENV=test

# JSON出力でレポート生成
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --output-format json --output-file output/simulation-report.json
```

**高度な機能**

```bash
# 自動復旧機能付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery

# 強化されたプロセス監視
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced

# 全機能を有効化した包括的実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --enhanced --diagnose --auto-recovery \
  --show-performance-metrics --show-execution-trace
```

## 🛠️ 開発者向けMakeコマンド

```bash
# 対話的ワークフロー選択
make actions

# 特定ワークフロー実行
make actions WORKFLOW=.github/workflows/ci.yml

# 環境変数付き実行
ENV_VARS="NODE_ENV=dev" make actions WORKFLOW=.github/workflows/test.yml

# 追加CLI引数の指定
make actions WORKFLOW=.github/workflows/ci.yml CLI_ARGS="--job test --enhanced"
```

**利用可能な変数**: `WORKFLOW`, `INDEX`, `JOB`, `ENV_VARS`, `CLI_ARGS`など

### 利用可能コマンド

**メインコマンド**

```bash
make actions          - GitHub Actions Simulator（対話的）
make actions-ci       - CI互換モードでワークフロー実行
make build           - Docker イメージのビルド
make test            - 統合テスト実行
make clean           - 環境のクリーンアップ
```

**開発・保守コマンド**

```bash
make test-all        - 全テストスイート実行
make security        - セキュリティスキャン
make version         - バージョン情報表示
make version-sync    - バージョン同期
make sbom           - SBOM生成
make audit-deps     - 依存関係監査
```

**レガシーサービス（参考）**

```bash
make github         - GitHub MCP server
make datetime       - DateTime validator
make start/stop/logs - サービス管理
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

### クイックリリース実行

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

### 詳細ドキュメント

完全なリリースシステムの詳細については、**[📚 リリース自動化システム完全ガイド](docs/RELEASE_SYSTEM.md)**を参照してください。

## 📚 ドキュメント

### ユーザー向けドキュメント
- **[Actions Simulator ドキュメント](docs/actions/)** - 使用方法、インストール、トラブルシューティング
- **[クイックスタート](docs/actions/QUICK_START.md)** - 5分で始めるガイド
- **[インストールガイド](docs/actions/INSTALLATION.md)** - 詳細なセットアップ手順
- **[ユーザーガイド](docs/actions/USER_GUIDE.md)** - 基本的な使用方法
- **[CLIリファレンス](docs/actions/CLI_REFERENCE.md)** - 全コマンドとオプション
- **[トラブルシューティング](docs/actions/TROUBLESHOOTING.md)** - 問題解決ガイド
- **[FAQ](docs/actions/FAQ.md)** - よくある質問と回答

### 開発・設計ドキュメント
- **[実装ルール](.kiro/steering/)** - Docker特化の実装・品質ルール
- **[設計仕様](.kiro/specs/)** - アーキテクチャ・実装・品質ゲート仕様
- **[プロジェクトガイドライン](.kiro/steering/project-guidelines.md)** - ドキュメント構造とルール

### アーカイブ

- **🗂️ Sphinx ドキュメント**: `archive/docs/sphinx/` - HTML生成用
- **🛡️ CodeQL 設定**: `archive/services/codeql/` - 旧静的解析設定

## 🔧 軽量アーキテクチャの詳細

### GitHub Actions Simulator（メインサービス）

**軽量actベースエンジン**

- **実行環境**: Docker コンテナ内でact実行
- **依存関係**: Docker + act のみ
- **起動時間**: 数秒での高速起動
- **メモリ使用量**: 最小限のリソース消費

**主要機能**

- ワークフローシミュレーション
- リアルタイム診断・監視
- 自動復旧機能
- プラットフォーム別エラーガイダンス

**API エンドポイント**（オプション）

- ポート: 8000
- `GET /actions/healthz` - ヘルスチェック
- `POST /actions/simulate` - ワークフロー実行

```bash
# REST API使用例
curl -X POST http://localhost:8000/actions/simulate \
  -H "Content-Type: application/json" \
  -d '{"workflow_file": ".github/workflows/ci.yml"}'
```

### 補助サービス（レガシー）

**GitHub MCP Server** (ポート: 8080)

- GitHub API連携のMCPサーバー
- 環境変数: 以下のいずれかを設定（優先順位順）
  - `GITHUB_PERSONAL_ACCESS_TOKEN`
  - `GITHUB_TOKEN`
  - `GH_TOKEN`

**DateTime Validator**

- ファイル監視による日付自動修正
- 疑わしい日付パターンの検出・修正

## 🛡️ セキュリティ

### 軽量アーキテクチャのセキュリティ機能

- **最小権限の原則**: 非root実行、必要最小限の権限
- **コンテナ分離**: Docker による安全な実行環境
- **依存関係管理**: 自動的な脆弱性チェック
- **秘密情報保護**: 環境変数の適切な取り扱い

### セキュリティスキャン

```bash
make security     # 包括的セキュリティスキャン（Trivy統合）
make audit-deps   # 依存関係の脆弱性監査
make sbom        # SBOM（Software Bill of Materials）生成
```

### セキュリティベストプラクティス

- 環境変数ファイル（`.env`）をコミットしない
- 定期的な依存関係更新
- Docker イメージの定期的な更新

## 🧪 テスト

### テストスイート構成

テストは以下の3層に分類されています：

```bash
# すべてのテスト実行
make test

# ユニットテストのみ（外部依存なし、高速）
make test-unit

# 統合テスト（Docker操作含む）
make test-integration

# E2Eテスト（完全なシナリオ、時間がかかる）
make test-e2e

# 高速テスト（ユニット+統合のみ）
make test-quick
```

### テスト範囲

- **ユニットテスト** (`tests/unit/`): ロジック単体の検証（外部依存なし）
- **統合テスト** (`tests/integration/`): Docker環境での動作確認、サービス連携
- **E2Eテスト** (`tests/e2e/`): 実際のワークフロー実行、パフォーマンス検証

### その他の品質チェック

```bash
make lint             # コード品質チェック
make format           # コードフォーマット
make type-check       # 型チェック
make security-check   # セキュリティスキャン
```

## 🤝 開発・貢献

### 軽量開発環境セットアップ

```bash
# 1. GitHub Personal Access Token設定（GitHub MCP Server用）
export GITHUB_TOKEN="your_token_here"
# または
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"

# 2. Docker環境自動セットアップ
./scripts/setup-docker-env.sh

# 3. 依存関係の確認
./scripts/run-actions.sh --check-deps

# 4. 開発依存関係インストール
uv sync --group dev

# 5. Pre-commitフック設定（GitHub Actions Simulator統合）
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml  # テンプレートをコピー
pre-commit install                                          # フックをインストール

# 6. 開発用Docker環境構築
make build
```

### WSL環境での追加セットアップ（オプション）

WSL環境でWindows Toast通知機能を使用する場合は、以下の手順を実行してください：

```bash
# 1. WSL環境のセットアップ
make setup-wsl

# 2. .envファイルにWindows通知パスを設定
echo "WINDOWS_NOTIFICATION_PATH=/mnt/c/path/to/windows-notifications" >> .env

# 3. サービス起動（自動的にoverride.ymlが適用されます）
make start
```

**注意**:
- `make setup-wsl`はWSL環境でのみ実行できます
- WSL以外の環境では通常の`make start`で問題なく動作します
- Windows通知機能はGitHub Release Watcherサービスで使用されます

### 開発ワークフロー

```bash
# 開発サーバー起動
make actions

# 品質チェック（pre-commit統合）
make pre-commit              # 全品質チェック実行
pre-commit run --all-files   # 全ファイルでチェック

# テスト実行
make test                    # 基本テスト
make test-hangup-quick      # 高速ハングアップテスト

# セキュリティチェック
make security

# クリーンアップ
make clean
```

**Pre-commit統合による段階的品質ゲート**

GitHub Actions Simulatorは段階的な品質レベルを提供します:

- **🟢 Basic**: 基本的なファイル品質チェック
- **🟡 Standard**: コード品質 + Actions Simulator統合テスト（推奨）
- **🔴 Strict**: 全品質チェック + セキュリティスキャン（CI/CD向け）

詳細は [Pre-commit統合ガイド](docs/PRE_COMMIT_INTEGRATION.md) をご覧ください。

### 貢献方法

1. **フォーク**: リポジトリをフォーク
2. **ブランチ作成**: `git checkout -b feature/lightweight-improvement`
3. **開発**: 軽量アーキテクチャの原則に従って開発
4. **テスト**: `make test-all` で全テスト実行
5. **プルリクエスト**: 変更内容を説明してPR作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 🌍 プラットフォーム対応

### サポートプラットフォーム

| プラットフォーム | 対応状況 | 推奨度 | 自動インストール |
|----------------|----------|--------|------------------|
| **Linux** (Ubuntu/Debian) | ✅ フル対応 | ⭐⭐⭐ | `./scripts/install.sh` |
| **Linux** (Fedora/RHEL) | ✅ フル対応 | ⭐⭐⭐ | `./scripts/install.sh` |
| **macOS** (12.0+) | ✅ フル対応 | ⭐⭐ | `./scripts/install.sh` |
| **Windows** (WSL2) | ✅ フル対応 | ⭐⭐ | PowerShell スクリプト |

### 自動インストール

```bash
# 統合インストーラー（推奨）
./scripts/install.sh

# 依存関係チェック
./scripts/run-actions.sh --check-deps

# 拡張チェック（プラットフォーム最適化情報を含む）
./scripts/run-actions.sh --check-deps-extended
```

### プラットフォーム別インストール

```bash
# Linux
./scripts/install-linux.sh

# macOS
./scripts/install-macos.sh

# Windows (PowerShell を管理者として実行)
.\scripts\install-windows.ps1
```

詳細なプラットフォームガイド: **[docs/PLATFORM_SUPPORT.md](docs/PLATFORM_SUPPORT.md)**

## 🚀 次のステップ

### 初回利用者向け

1. **依存関係確認**: `./scripts/run-actions.sh --check-deps`
2. **基本実行**: `./scripts/run-actions.sh`
3. **ドキュメント確認**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### 既存ユーザー向け

1. **高度な機能**: `./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced`
2. **CI/CD統合**: `NON_INTERACTIVE=1 ./scripts/run-actions.sh`
3. **カスタマイズ**: `.env.template` をコピーして設定

### 開発者向け

1. **開発環境**: `uv sync --group dev && pre-commit install`
2. **貢献**: [CONTRIBUTING.md](CONTRIBUTING.md) を参照
3. **拡張**: 軽量アーキテクチャの原則に従って機能追加

## 📞 サポート・コミュニティ

### 問題報告・質問

- **GitHub Issues**: [バグ報告・機能要望](https://github.com/scottlz0310/mcp-docker/issues) - 構造化されたテンプレート付き
- **GitHub Discussions**: [質問・アイデア共有](https://github.com/scottlz0310/mcp-docker/discussions) - コミュニティサポート
- **包括的サポートガイド**: [docs/SUPPORT.md](docs/SUPPORT.md) - 全サポートチャネルの詳細
- **問題報告ガイド**: [docs/PROBLEM_REPORTING_GUIDE.md](docs/PROBLEM_REPORTING_GUIDE.md) - 効果的な報告方法
- **コミュニティガイド**: [docs/COMMUNITY_SUPPORT_GUIDE.md](docs/COMMUNITY_SUPPORT_GUIDE.md) - コミュニティ活用方法

### 自動診断・トラブルシューティング

```bash
# 包括的診断情報収集（問題報告時に便利）
./scripts/collect-support-info.sh

# 自動トラブルシューティング付き診断
./scripts/collect-support-info.sh --auto-troubleshoot

# 特定問題の診断と自動修復
./scripts/diagnostic-helper.sh --fix all

# 手動での基本情報収集
./scripts/run-actions.sh --check-deps
make version
```

### アップグレード・保守

- **アップグレードガイド**: [docs/UPGRADE_GUIDE.md](docs/UPGRADE_GUIDE.md)
- **自動アップグレード**: `./scripts/upgrade.sh`
- **価値提案詳細**: [docs/VALUE_PROPOSITION.md](docs/VALUE_PROPOSITION.md)

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。

---

**GitHub Actions Simulator** - 軽量で使いやすいローカルワークフローシミュレーション 🚀
