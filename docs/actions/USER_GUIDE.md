# GitHub Actions Simulator - 詳細利用ガイド

## 📋 目次

- [🚀 はじめに](#-はじめに)
- [⚡ クイックスタート](#-クイックスタート)
- [🎛️ 基本的な使い方](#️-基本的な使い方)
- [🔧 高度な機能](#-高度な機能)
- [🛠️ 開発者向け機能](#️-開発者向け機能)
- [🔍 診断・トラブルシューティング](#-診断トラブルシューティング)
- [🚀 CI/CD統合](#-cicd統合)
- [⚙️ カスタマイズ](#️-カスタマイズ)
- [📊 ベストプラクティス](#-ベストプラクティス)
- [🔧 トラブルシューティング](#-トラブルシューティング)

## 🚀 はじめに

GitHub Actions Simulatorは、軽量で使いやすいローカルワークフローシミュレーターです。Docker + actベースの軽量アーキテクチャにより、複雑な設定なしに5分でGitHub Actionsワークフローの事前チェックが可能です。

### 🎯 主要な価値提案

- **⚡ 高速**: 数秒でのワークフロー実行開始
- **🪶 軽量**: Docker + actのみでフル機能
- **🔧 簡単**: ワンコマンドでの実行
- **🛡️ 安全**: コンテナ内での隔離実行
- **🔄 自動化**: CI/CD統合対応

## ⚡ クイックスタート

### ステップ1: 前提条件の確認（1分）

```bash
# 依存関係の自動チェック
./scripts/run-actions.sh --check-deps
```

**必要な環境:**
- Docker 20.10+ & Docker Compose 2.0+
- Git 2.20+
- uv（推奨、なくても動作）

### ステップ2: 最初の実行（30秒）

```bash
# 最もシンプルな実行方法（対話的選択）
./scripts/run-actions.sh

# 特定のワークフローを直接実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

### ステップ3: 結果の確認（30秒）

実行後、以下の情報が表示されます：

- ✅ 実行成功/失敗の結果
- 📊 実行時間とパフォーマンス情報
- 🔍 エラーがある場合の詳細情報
- 🚀 次のステップの提案

## 🎛️ 基本的な使い方

### 実行方式の選択

GitHub Actions Simulatorは3つの実行方式を提供します：

#### 1. ワンショットスクリプト（推奨）

```bash
# 基本構文
./scripts/run-actions.sh [ワークフローファイル] [-- <追加オプション>]

# 対話的選択（初心者向け）
./scripts/run-actions.sh

# 特定ワークフロー実行
./scripts/run-actions.sh .github/workflows/ci.yml

# オプション付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --enhanced
```

#### 2. Makeコマンド（開発者向け）

```bash
# 対話的ワークフロー選択
make actions

# 特定ワークフロー実行
make actions WORKFLOW=.github/workflows/ci.yml

# 環境変数付き実行
ENV_VARS="NODE_ENV=dev" make actions WORKFLOW=.github/workflows/test.yml

# CLI引数の指定
make actions WORKFLOW=.github/workflows/ci.yml CLI_ARGS="--job test --enhanced"
```

#### 3. 直接CLI（上級者向け）

```bash
# Docker コンテナ内でCLI実行
uv run python main.py actions simulate .github/workflows/ci.yml

# 利用可能なオプション確認
uv run python main.py actions --help
```

### 基本的な実行パターン

#### 対話的実行（初心者向け）

```bash
# ワークフローファイルを対話的に選択
./scripts/run-actions.sh

# 実行例：
# 1. .github/workflows/ci.yml
# 2. .github/workflows/test.yml
# 3. .github/workflows/deploy.yml
# 選択してください (1-3): 1
```

#### 直接実行（効率重視）

```bash
# 特定のワークフローを直接実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 特定のジョブのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test

# 複数の条件を指定
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --job test --event pull_request --ref refs/pull/42/head
```

## 🔧 高度な機能

### インテリジェント診断システム

#### 実行前診断

```bash
# 基本的な診断
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose

# 包括的診断
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --show-performance-metrics --show-execution-trace
```

診断内容：
- 🔍 Docker環境の健康状態
- 📊 システムリソースの使用状況
- 🔧 ワークフロー構文の検証
- 🛡️ セキュリティ設定の確認

#### 自動復旧機能

```bash
# 自動復旧機能を有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery

# 強化されたプロセス監視
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced
```

自動復旧機能：
- 🔄 Docker接続の自動再接続
- 🚀 プロセスの自動再起動
- 🧹 バッファとキャッシュのクリア
- ⏱️ 段階的タイムアウト管理

### リアルタイム監視

#### パフォーマンス監視

```bash
# パフォーマンス監視を有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics
```

監視項目：
- 💾 メモリ使用量
- ⚡ CPU使用率
- 🕒 実行時間
- 📊 リソース効率

#### 実行トレース

```bash
# 実行トレースを有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-execution-trace
```

トレース情報：
- 📝 詳細な実行ログ
- 🔍 ステップ別の実行時間
- 🚨 エラーの詳細情報
- 🔄 依存関係の解決過程

### 全機能を組み合わせた実行

```bash
# 全機能を有効化した包括的実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --enhanced --diagnose --auto-recovery \
  --show-performance-metrics --show-execution-trace
```

## 🛠️ 開発者向け機能

### 環境変数の設定

#### 実行時環境変数

```bash
# 環境変数を指定して実行
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --env GITHUB_ACTOR=ci-bot --env NODE_ENV=test

# Makeコマンドでの環境変数指定
ENV_VARS="NODE_ENV=dev,DEBUG=true" make actions WORKFLOW=.github/workflows/test.yml
```

#### 設定ファイルの使用

```bash
# .envファイルを作成（.env.templateをコピー）
cp .env.template .env

# 設定を編集
vim .env

# 設定ファイルを使用して実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

### 出力形式のカスタマイズ

#### JSON出力

```bash
# JSON形式でレポート生成
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --output-format json --output-file output/simulation-report.json
```

#### 詳細ログ出力

```bash
# 詳細ログを有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --verbose

# デバッグレベルのログ
./scripts/run-actions.sh .github/workflows/ci.yml -- --debug
```

### 開発用Makeターゲット

```bash
# 開発環境のセットアップ
make setup

# Docker イメージのビルド
make build

# テストの実行
make test

# セキュリティスキャン
make security

# 環境のクリーンアップ
make clean
```

## 🔍 診断・トラブルシューティング

### 依存関係の診断

```bash
# 包括的な依存関係チェック
./scripts/run-actions.sh --check-deps
```

チェック項目：
- 🐳 Docker & Docker Compose のバージョン
- 📦 uv の存在とバージョン
- 🔧 Git の設定状態
- 🔒 権限とアクセス権
- 🌐 ネットワーク接続

### システム診断

```bash
# システム健康状態の確認
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose --system-check
```

診断内容：
- 💾 利用可能メモリ
- 💿 ディスク容量
- 🔄 Docker デーモンの状態
- 🌐 ネットワーク設定

### エラー診断

```bash
# エラー発生時の詳細診断
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --show-execution-trace --debug
```

## 🚀 CI/CD統合

### 非対話モードでの実行

```bash
# 非対話モード（CI/CD環境向け）
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# インデックス指定で自動選択
INDEX=1 ./scripts/run-actions.sh

# 環境変数での制御
export NON_INTERACTIVE=1
export WORKFLOW_INDEX=1
./scripts/run-actions.sh
```

### GitHub Actionsでの使用例

```yaml
name: Local CI Simulation
on: [push, pull_request]

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Dependencies
        run: |
          # Docker は GitHub Actions ランナーに標準でインストール済み
          curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run GitHub Actions Simulation
        run: |
          NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml
        env:
          GITHUB_ACTOR: ${{ github.actor }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### pre-commitフックでの使用

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: github-actions-simulation
        name: GitHub Actions Simulation
        entry: ./scripts/run-actions.sh
        args: ['.github/workflows/ci.yml', '--', '--job', 'test']
        language: system
        pass_filenames: false
```

## ⚙️ カスタマイズ

### 設定ファイルのカスタマイズ

#### .env設定

```bash
# .env.templateをコピーして編集
cp .env.template .env

# 主要な設定項目
GITHUB_ACTOR=your-username
NODE_ENV=development
DEBUG=false
DOCKER_BUILDKIT=1
```

#### Docker設定のカスタマイズ

```bash
# docker-compose.override.ymlを作成
cp docker-compose.override.yml.sample docker-compose.override.yml

# カスタム設定を追加
vim docker-compose.override.yml
```

### ワークフロー固有の設定

#### 特定のジョブのみ実行

```bash
# 特定のジョブのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test

# 複数のジョブを実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --job lint
```

#### イベントとリファレンスの指定

```bash
# プルリクエストイベントをシミュレート
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --event pull_request --ref refs/pull/42/head

# プッシュイベントをシミュレート
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --event push --ref refs/heads/main
```

## 📊 ベストプラクティス

### 効率的な使用方法

#### 1. 段階的な実行

```bash
# 1. まず構文チェックのみ
./scripts/run-actions.sh .github/workflows/ci.yml -- --dry-run

# 2. 軽量なジョブから実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job lint

# 3. 全体を実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

#### 2. 開発ワークフローでの活用

```bash
# 開発中の継続的チェック
while inotifywait -e modify .github/workflows/; do
  ./scripts/run-actions.sh .github/workflows/ci.yml -- --job test
done
```

#### 3. パフォーマンス最適化

```bash
# キャッシュを活用した高速実行
DOCKER_BUILDKIT=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 並列実行の活用
./scripts/run-actions.sh .github/workflows/ci.yml -- --parallel
```

### セキュリティのベストプラクティス

#### 1. 秘密情報の管理

```bash
# 環境変数ファイルをコミットしない
echo ".env" >> .gitignore

# テンプレートファイルのみコミット
git add .env.template
```

#### 2. 権限の最小化

```bash
# 非root実行の確認
./scripts/run-actions.sh --check-deps | grep -i "root"

# Docker グループの確認
groups | grep docker
```

### 品質管理のベストプラクティス

#### 1. 定期的な依存関係チェック

```bash
# 週次での依存関係確認
./scripts/run-actions.sh --check-deps

# セキュリティスキャンの実行
make security
```

#### 2. ドキュメントの同期

```bash
# バージョン情報の確認
make version

# ドキュメントの整合性チェック
make test-docs
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. Docker関連の問題

**問題**: Docker デーモンに接続できない

```bash
# 解決方法1: Docker サービスの再起動
sudo systemctl restart docker

# 解決方法2: ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
newgrp docker

# 解決方法3: 権限の確認
./scripts/run-actions.sh --check-deps
```

**問題**: Docker イメージのビルドが失敗する

```bash
# 解決方法1: キャッシュのクリア
docker system prune -f

# 解決方法2: 強制リビルド
make build --no-cache

# 解決方法3: ディスク容量の確認
df -h
```

#### 2. ワークフロー関連の問題

**問題**: ワークフローファイルが見つからない

```bash
# 解決方法1: ファイルパスの確認
ls -la .github/workflows/

# 解決方法2: 対話的選択を使用
./scripts/run-actions.sh

# 解決方法3: 絶対パスで指定
./scripts/run-actions.sh $(pwd)/.github/workflows/ci.yml
```

**問題**: ワークフローの構文エラー

```bash
# 解決方法1: 構文チェックのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --dry-run

# 解決方法2: 詳細診断を実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose

# 解決方法3: YAMLリンターを使用
yamllint .github/workflows/ci.yml
```

#### 3. パフォーマンス関連の問題

**問題**: 実行が遅い

```bash
# 解決方法1: パフォーマンス監視を有効化
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics

# 解決方法2: 特定のジョブのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test

# 解決方法3: Docker BuildKitを有効化
export DOCKER_BUILDKIT=1
./scripts/run-actions.sh .github/workflows/ci.yml
```

**問題**: メモリ不足

```bash
# 解決方法1: システムリソースの確認
./scripts/run-actions.sh --check-deps

# 解決方法2: 不要なコンテナの削除
docker container prune -f

# 解決方法3: メモリ制限の調整
docker-compose --compatibility up
```

### 高度なトラブルシューティング

#### デバッグモードでの実行

```bash
# 詳細なデバッグ情報を出力
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --debug --show-execution-trace --verbose
```

#### ログの収集と分析

```bash
# ログディレクトリの確認
ls -la logs/

# エラーログの確認
tail -f logs/error.log

# 診断ログの確認
tail -f logs/diagnostic.log
```

#### サポートへの問題報告

問題を報告する際は、以下の情報を含めてください：

```bash
# 1. システム情報の収集
./scripts/run-actions.sh --check-deps > system-info.txt

# 2. バージョン情報の収集
make version > version-info.txt

# 3. エラーログの収集
cp logs/error.log error-report.log

# 4. 実行コマンドと結果
./scripts/run-actions.sh .github/workflows/ci.yml -- --debug > debug-output.txt 2>&1
```

## 📚 関連リソース

### 公式ドキュメント

- **[メインREADME](../../README.md)** - プロジェクト全体の概要
- **[FAQ](FAQ.md)** - よくある質問と回答
- **[トラブルシューティング](../TROUBLESHOOTING.md)** - 一般的な問題と解決方法

### 技術ドキュメント

- **[技術設計](github-actions-simulator-design.md)** - アーキテクチャの詳細
- **[実装計画](implementation-plan.md)** - 開発ロードマップ
- **[UI設計](ui-design.md)** - ユーザーインターフェース設計

### 外部リソース

- **[nektos/act](https://github.com/nektos/act)** - GitHub Actions ローカル実行ツール
- **[Docker Documentation](https://docs.docker.com/)** - Docker 公式ドキュメント
- **[GitHub Actions Documentation](https://docs.github.com/en/actions)** - GitHub Actions 公式ドキュメント

---

このガイドがGitHub Actions Simulatorの効果的な活用に役立つことを願っています。さらに詳しい情報や最新のアップデートについては、[プロジェクトのGitHubリポジトリ](https://github.com/scottlz0310/mcp-docker)をご確認ください。
