# Pre-commit Integration Guide

GitHub Actions Simulator の pre-commit 統合ガイド

## 概要

このドキュメントでは、GitHub Actions Simulator と pre-commit フックの統合方法について説明します。段階的な品質ゲート設定により、開発ワークフローに適した品質チェックを実現できます。

## 設定レベル

### Basic レベル（基本）

最小限のファイル品質チェックのみを実行します。既存プロジェクトへの導入や、軽量な開発環境に適しています。

**含まれるチェック:**
- ファイル形式の基本チェック（末尾空白、改行コード等）
- YAML/JSON 構文チェック
- 大容量ファイルの検出
- マージコンフリクトの検出

**使用例:**
```yaml
CONFIG_LEVEL: "basic"
```

### Standard レベル（標準・推奨）

コード品質チェックを含む包括的なチェックを実行します。通常の開発作業に推奨されるレベルです。

**含まれるチェック:**
- Basic レベルの全チェック
- Docker/Shell/YAML の静的解析
- Python コード品質チェック（Ruff）
- GitHub Actions Simulator 単体テスト
- ワークフロー構文検証

**使用例:**
```yaml
CONFIG_LEVEL: "standard"
```

### Strict レベル（厳格）

全ての品質チェックを含む最も厳格なレベルです。CI/CD 環境や本格的な開発に適しています。

**含まれるチェック:**
- Standard レベルの全チェック
- Python 型チェック（MyPy）
- 統合テスト実行
- ドキュメント整合性チェック
- セキュリティスキャン

**使用例:**
```yaml
CONFIG_LEVEL: "strict"
```

## GitHub Actions Simulator 統合機能

### 1. ワークフロー事前検証

GitHub Actions ワークフローファイルをコミット前に検証します。

```bash
# 自動実行される検証内容
- YAML 構文チェック
- Actions Simulator での実行可能性確認
- 必須フィールドの存在確認
```

### 2. Docker 環境整合性チェック

Docker 関連ファイルの品質と整合性を確認します。

```bash
# チェック対象
- Dockerfile のベストプラクティス準拠
- docker-compose.yml の構文検証
- Docker 環境の基本動作確認
```

### 3. 設定ファイル検証

Actions Simulator の設定ファイルを検証します。

```bash
# 検証内容
- .env.example の存在確認
- pyproject.toml の整合性チェック
- バージョン情報の同期確認
```

### 4. 単体テスト統合

Actions Simulator の核心機能をテストします。

```bash
# テスト対象
- DiagnosticService の初期化
- ProcessMonitor の動作確認
- ExecutionTracer の機能テスト
```

## セットアップ手順

### 1. 新規プロジェクトでのセットアップ

```bash
# 1. テンプレートをコピー
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml

# 2. 設定レベルを選択（推奨: standard）
# CONFIG_LEVEL: "standard" に設定

# 3. pre-commit をインストール
pre-commit install

# 4. 初回実行
pre-commit run --all-files
```

### 2. 既存プロジェクトへの導入

```bash
# 1. 段階的導入のため basic レベルから開始
# CONFIG_LEVEL: "basic" に設定

# 2. pre-commit をインストール
pre-commit install

# 3. 全ファイルでチェック実行
pre-commit run --all-files

# 4. 問題を修正後、standard レベルに移行
# CONFIG_LEVEL: "standard" に変更

# 5. 再度チェック実行
pre-commit run --all-files
```

### 3. CI/CD 環境での設定

```bash
# 1. 厳格レベルに設定
# CONFIG_LEVEL: "strict" に設定

# 2. GitHub Actions での実行例
- name: Run pre-commit
  run: |
    pre-commit run --all-files
```

## カスタマイズ方法

### 1. 特定のチェックを無効化

```yaml
# 例: hadolint を無効化
# - repo: https://github.com/hadolint/hadolint
#   rev: v2.12.0
#   hooks:
#     - id: hadolint-docker
```

### 2. 除外パターンの追加

```yaml
exclude: |
  (?x)^(
    # 既存のパターン
    \.git/.*|
    # プロジェクト固有の除外パターンを追加
    vendor/.*|
    generated/.*|
  )$
```

### 3. プロジェクト固有のチェック追加

```yaml
- repo: local
  hooks:
    - id: custom-check
      name: "カスタムチェック"
      entry: ./scripts/custom-check.sh
      language: system
      files: ^src/
```

### 4. GitHub Actions Simulator 統合のカスタマイズ

```yaml
# テストファイルパスの調整
- id: actions-simulator-unit-tests
  files: ^(src/|tests/custom_test\.py)

# タイムアウト値の変更
  entry: >
    uv run pytest ... --timeout=60

# 追加の検証ルール
- id: custom-workflow-check
  entry: ./scripts/validate-workflows.sh
```

## 段階的品質ゲート

### Phase 1: 基本品質（緑）

```bash
# 自動修正可能な問題の解決
- 末尾空白の削除
- ファイル末尾の改行修正
- 改行コードの統一
```

### Phase 2: コード品質（黄）

```bash
# 静的解析による品質向上
- Dockerfile のベストプラクティス
- Shell スクリプトの潜在的問題検出
- Python コードスタイルの統一
```

### Phase 3: 統合品質（橙）

```bash
# 機能レベルでの品質確認
- 単体テストの実行
- ワークフロー構文の検証
- Docker 環境の動作確認
```

### Phase 4: 配布品質（赤）

```bash
# リリース準備の品質確認
- 包括的テストスイート
- ドキュメント整合性チェック
- セキュリティスキャン
```

## Make コマンド統合

### 基本的な使用方法

```bash
# pre-commit の実行
make pre-commit

# 全ファイルでの実行
pre-commit run --all-files

# 特定のフックのみ実行
pre-commit run actions-simulator-unit-tests
```

### 開発ワークフローとの統合

```bash
# 開発サイクル例
make build                    # Docker イメージビルド
make test-hangup-quick       # 高速テスト実行
make pre-commit              # 品質チェック実行
git commit -m "feat: 新機能追加"  # コミット（自動でpre-commit実行）
```

## トラブルシューティング

### 1. Docker 関連エラー

```bash
# Docker 環境の確認
make docker-health

# Docker サービスの再起動
docker system prune -f
make build
```

### 2. Python 環境エラー

```bash
# 依存関係の更新
uv sync

# 仮想環境の再作成
rm -rf .venv
uv sync
```

### 3. テストタイムアウト

```bash
# システムリソースの確認
docker system df
docker system prune -f

# 軽量テストの実行
make test-hangup-quick
```

### 4. 権限エラー

```bash
# 権限の修正
./scripts/fix-permissions.sh

# Docker rootless モードの確認
docker context ls
```

### 5. 設定ファイルエラー

```bash
# 設定の検証
pre-commit validate-config

# キャッシュのクリア
pre-commit clean
pre-commit install --install-hooks
```

## ベストプラクティス

### 1. 段階的導入

```bash
# 推奨導入順序
1. basic レベルで開始
2. 問題を修正しながら standard レベルに移行
3. 安定後に strict レベルを検討
```

### 2. チーム開発での運用

```bash
# チーム設定の統一
- .pre-commit-config.yaml をリポジトリに含める
- README にセットアップ手順を記載
- CI/CD で pre-commit チェックを実行
```

### 3. パフォーマンス最適化

```bash
# 高速化のコツ
- 必要最小限のチェックを選択
- 除外パターンを適切に設定
- Docker イメージのキャッシュを活用
```

### 4. 継続的改善

```bash
# 定期的なメンテナンス
- pre-commit フックのバージョン更新
- 新しいチェックルールの評価
- チーム内でのフィードバック収集
```

## 関連ドキュメント

- [GitHub Actions Simulator ユーザーガイド](./actions/USER_GUIDE.md)
- [Docker 統合ガイド](./CONTAINER_SETUP.md)
- [トラブルシューティング](./TROUBLESHOOTING.md)
- [開発者向けガイド](../CONTRIBUTING.md)

## サポート

問題が発生した場合は以下を確認してください:

1. [トラブルシューティングガイド](./TROUBLESHOOTING.md)
2. [FAQ](./actions/FAQ.md)
3. [GitHub Issues](https://github.com/your-repo/issues)
4. [診断ツール](./DIAGNOSTIC_COMMANDS.md)
