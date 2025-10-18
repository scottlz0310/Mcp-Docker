# コマンド使い分けガイド

## 概要

GitHub Actions Simulator では、複数のコマンドインターフェースを提供しています。このガイドでは、それぞれの特徴と適切な使い分け方法について説明します。

## 目次

- [コマンドインターフェース一覧](#コマンドインターフェース一覧)
- [使い分けの基準](#使い分けの基準)
- [シナリオ別推奨コマンド](#シナリオ別推奨コマンド)
- [パフォーマンス比較](#パフォーマンス比較)
- [機能比較表](#機能比較表)

## コマンドインターフェース一覧

### 1. Make コマンド (`make actions`)

**特徴:**
- 最もシンプルで使いやすい
- 開発者向けの便利なショートカット
- Docker環境の自動管理
- 豊富なオプションとパラメーター

**適用場面:**
- 日常的な開発作業
- ローカル環境でのテスト
- 複数のワークフローを頻繁に実行

### 2. 配布スクリプト (`./scripts/run-actions.sh`)

**特徴:**
- 依存関係の自動チェックと修復提案
- プラットフォーム固有のインストールガイダンス
- エラーハンドリングとトラブルシューティング支援
- 新規ユーザー向けの親切な設計

**適用場面:**
- 初回セットアップ
- 新しい環境での実行
- CI/CD パイプラインでの使用
- 配布・共有時の標準インターフェース

### 3. Python メインエントリーポイント (`python main.py actions`)

**特徴:**
- 軽量で高速
- 他のMCPサービスとの統一インターフェース
- 最小限の依存関係
- プログラマティックな使用に適している

**適用場面:**
- スクリプトからの呼び出し
- 他のPythonアプリケーションとの統合
- 最小限のオーバーヘッドが必要な場合

### 4. Actions Simulator CLI (`python -m services.actions.main`)

**特徴:**
- 最も詳細な制御が可能
- 豊富なオプションとサブコマンド
- 診断機能とデバッグ支援
- 高度なユーザー向け

**適用場面:**
- 詳細な設定が必要な場合
- デバッグとトラブルシューティング
- 高度な機能の使用
- カスタマイズされたワークフロー

## 使い分けの基準

### 1. ユーザーレベル別

#### 初心者・新規ユーザー
```bash
# 推奨: 配布スクリプト
./scripts/run-actions.sh

# 理由:
# - 依存関係の自動チェック
# - 詳細なエラーガイダンス
# - プラットフォーム固有のヘルプ
```

#### 日常的な開発者
```bash
# 推奨: Make コマンド (CI互換モード)
make actions-ci
make actions-ci WORKFLOW=.github/workflows/ci.yml

# 旧コマンド (Phase1 ブリッジモード、移行中)
make actions-run WORKFLOW=.github/workflows/ci.yml

# 理由:
# - シンプルで覚えやすい
# - 豊富なショートカット
# - 開発ワークフローに最適化
```

> ⚠️ **移行情報 (2025-10-15)**:
> - `make actions-ci`: CI互換モード（推奨）。`act` を直接実行し、GitHub Actions環境に近い動作。
> - `make actions-run`: Phase1 ブリッジモード（移行中）。従来の診断機能を保持しつつ `act` へ移行中。未実装機能では自動フォールバックします。
> - 今後は `make actions-ci` の使用を推奨します。Phase 2 完了後、`make actions-run` は `make actions-ci` に統合されます。

#### 上級ユーザー・DevOps エンジニア
```bash
# 推奨: Actions Simulator CLI
python -m services.actions.main simulate .github/workflows/ci.yml --diagnose --enhanced

# 理由:
# - 詳細な制御が可能
# - 高度な診断機能
# - カスタマイズ性が高い
```

### 2. 環境別

#### ローカル開発環境
```bash
# 推奨: Make コマンド
make actions                    # インタラクティブ選択
make actions-list              # ワークフロー一覧
make actions-run WORKFLOW=... JOB=...  # 特定実行
```

#### CI/CD パイプライン
```bash
# 推奨: 配布スクリプト（非対話モード）
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# または Python エントリーポイント
python main.py actions simulate .github/workflows/ci.yml --job test
```

#### Docker コンテナ内
```bash
# 推奨: Python エントリーポイント
python main.py actions simulate .github/workflows/ci.yml

# 理由:
# - 軽量で高速
# - 依存関係が最小限
# - コンテナ環境に最適化
```

#### 本番環境・自動化
```bash
# 推奨: Actions Simulator CLI
python -m services.actions.main simulate .github/workflows/deploy.yml \
  --env-file .env.production \
  --create-debug-bundle \
  --show-performance-metrics
```

### 3. 用途別

#### ワークフローの開発・テスト
```bash
# 開発中: Make コマンド（高速イテレーション）
make actions-dry-run WORKFLOW=.github/workflows/new-feature.yml
make actions-run WORKFLOW=.github/workflows/new-feature.yml JOB=test VERBOSE=1

# 検証: Actions Simulator CLI（詳細分析）
python -m services.actions.main validate .github/workflows/new-feature.yml --strict
python -m services.actions.main simulate .github/workflows/new-feature.yml --diagnose
```

#### トラブルシューティング
```bash
# 1. システム診断
python -m services.actions.main diagnose --include-performance --include-trace

# 2. 詳細実行（デバッグ情報付き）
python -m services.actions.main --debug simulate .github/workflows/problematic.yml \
  --create-debug-bundle --show-execution-trace

# 3. 依存関係チェック
./scripts/run-actions.sh --check-deps
```

#### 新環境でのセットアップ
```bash
# 1. 依存関係チェックと自動修復提案
./scripts/run-actions.sh --check-deps

# 2. 初回実行（ガイダンス付き）
./scripts/run-actions.sh

# 3. 動作確認
make actions-auto
```

## シナリオ別推奨コマンド

### シナリオ1: 新しいプロジェクトでの初回セットアップ

```bash
# ステップ1: 依存関係チェック
./scripts/run-actions.sh --check-deps

# ステップ2: 初回実行（対話的）
./scripts/run-actions.sh

# ステップ3: 動作確認
make actions-list
make actions-auto
```

### シナリオ2: 日常的な開発ワークフロー

```bash
# 朝の作業開始時
make actions-list                    # 利用可能なワークフローを確認

# 機能開発中
make actions-dry-run WORKFLOW=.github/workflows/ci.yml  # 実行計画を確認
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test  # テストのみ実行

# コミット前
make actions-run WORKFLOW=.github/workflows/ci.yml  # 全体テスト
```

### シナリオ3: CI/CD パイプラインでの使用

```bash
# GitHub Actions ワークフロー内
- name: Run GitHub Actions Simulator
  run: |
    NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# または
- name: Validate and Test Workflow
  run: |
    python -m services.actions.main validate .github/workflows/ci.yml --strict
    python main.py actions simulate .github/workflows/ci.yml --job test
```

### シナリオ4: 問題の診断とデバッグ

```bash
# ステップ1: システム全体の診断
python -m services.actions.main diagnose --format json --output diagnostic-report.json

# ステップ2: 問題のあるワークフローの詳細実行
python -m services.actions.main --debug simulate .github/workflows/failing.yml \
  --create-debug-bundle --show-performance-metrics --show-execution-trace

# ステップ3: 依存関係の再チェック
./scripts/run-actions.sh --check-deps

# ステップ4: デバッグバンドルの作成
python -m services.actions.main create-debug-bundle --include-logs --include-config
```

### シナリオ5: 複数環境での動作確認

```bash
# 開発環境
make actions-run WORKFLOW=.github/workflows/ci.yml

# ステージング環境（環境変数付き）
python -m services.actions.main simulate .github/workflows/ci.yml \
  --env-file .env.staging --env ENVIRONMENT=staging

# 本番環境（詳細監視付き）
python -m services.actions.main simulate .github/workflows/deploy.yml \
  --env-file .env.production \
  --show-performance-metrics \
  --create-debug-bundle
```

## パフォーマンス比較

### 起動時間

| コマンド | 起動時間 | 理由 |
|---------|---------|------|
| `python main.py actions` | 最速 (< 1秒) | 最小限の初期化 |
| `make actions` | 高速 (1-2秒) | Docker環境チェック |
| `python -m services.actions.main` | 中程度 (2-3秒) | 豊富な機能の初期化 |
| `./scripts/run-actions.sh` | 低速 (3-5秒) | 依存関係チェック |

### メモリ使用量

| コマンド | メモリ使用量 | 特徴 |
|---------|-------------|------|
| `python main.py actions` | 最小 (~50MB) | 軽量実装 |
| `make actions` | 小 (~100MB) | Docker オーバーヘッド |
| `python -m services.actions.main` | 中 (~150MB) | 豊富な機能 |
| `./scripts/run-actions.sh` | 大 (~200MB) | 診断機能込み |

### 機能の豊富さ

| コマンド | 機能レベル | 特徴 |
|---------|-----------|------|
| `python main.py actions` | 基本 | 最小限の機能 |
| `make actions` | 標準 | 開発に必要な機能 |
| `./scripts/run-actions.sh` | 高 | エラーハンドリング充実 |
| `python -m services.actions.main` | 最高 | 全機能利用可能 |

## 機能比較表

| 機能 | Make | スクリプト | Python main | Actions CLI |
|------|------|-----------|-------------|-------------|
| **基本実行** | ✅ | ✅ | ✅ | ✅ |
| **インタラクティブ選択** | ✅ | ✅ | ❌ | ❌ |
| **依存関係チェック** | 基本 | 詳細 | なし | 基本 |
| **エラーハンドリング** | 基本 | 詳細 | 基本 | 詳細 |
| **プラットフォーム対応** | 基本 | 詳細 | 基本 | 基本 |
| **診断機能** | ❌ | 基本 | ❌ | 詳細 |
| **デバッグ支援** | 基本 | 詳細 | 基本 | 詳細 |
| **パフォーマンス監視** | ❌ | ❌ | ❌ | ✅ |
| **カスタマイズ性** | 中 | 低 | 低 | 高 |
| **CI/CD 適性** | 中 | 高 | 高 | 高 |
| **学習コスト** | 低 | 低 | 低 | 高 |

## 推奨パターン

### 開発チーム向け標準パターン

```bash
# 新メンバーのオンボーディング
./scripts/run-actions.sh --check-deps
./scripts/run-actions.sh

# 日常的な開発作業
make actions-list
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test

# 問題発生時
python -m services.actions.main diagnose
python -m services.actions.main --debug simulate problematic-workflow.yml --create-debug-bundle
```

### DevOps チーム向け標準パターン

```bash
# 環境セットアップ
./scripts/run-actions.sh --check-deps

# 自動化スクリプト内
python main.py actions simulate .github/workflows/deploy.yml

# 詳細分析が必要な場合
python -m services.actions.main simulate .github/workflows/complex.yml \
  --diagnose --enhanced --show-performance-metrics --create-debug-bundle
```

### CI/CD パイプライン向け標準パターン

```bash
# 軽量チェック
python main.py actions validate .github/workflows/

# 実行テスト
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 詳細レポート
python -m services.actions.main diagnose --format json --output ci-diagnostic.json
```

## まとめ

適切なコマンドの選択により、効率的で安全なワークフロー開発が可能になります：

1. **初心者・新規環境**: 配布スクリプト (`./scripts/run-actions.sh`)
2. **日常開発**: Make コマンド (`make actions`)
3. **軽量実行**: Python エントリーポイント (`python main.py actions`)
4. **高度な制御**: Actions Simulator CLI (`python -m services.actions.main`)

各コマンドの特性を理解し、状況に応じて適切に使い分けることで、GitHub Actions Simulator を最大限に活用できます。
