# GitHub Actions Simulator - ドキュメント案内

## 🎯 概要

GitHub Actions Simulatorは、軽量で使いやすいローカルワークフローシミュレーターです。Docker + actベースの軽量アーキテクチャにより、複雑な設定なしに5分でGitHub Actionsワークフローの事前チェックが可能です。

## 🚀 クイックスタート

### 最も簡単な使い方

```bash
# 対話的ワークフロー選択
./scripts/run-actions.sh

# 特定ワークフローの実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 開発者向けMakeコマンド
make actions
```

### 高度な機能

```bash
# 診断機能付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose --enhanced

# 自動復旧機能付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery

# パフォーマンス監視付き実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics
```

## 📚 ドキュメント体系

### 🎯 ユーザー向けガイド

| ファイル | 内容 | 対象者 |
| --- | --- | --- |
| **[../CLI_REFERENCE.md](../CLI_REFERENCE.md)** | 全コマンドとオプションの完全リファレンス | 全ユーザー |
| **[../COMMAND_USAGE_GUIDE.md](../COMMAND_USAGE_GUIDE.md)** | Make・スクリプト・CLIの使い分けガイド | 全ユーザー |
| **[../API_REFERENCE.md](../API_REFERENCE.md)** | 詳細なAPIドキュメント | 開発者・上級者 |
| **[../SCRIPT_OPTIONS_REFERENCE.md](../SCRIPT_OPTIONS_REFERENCE.md)** | 全スクリプトのオプション詳細 | 開発者・上級者 |
| **[USER_GUIDE.md](USER_GUIDE.md)** | 詳細な利用方法とベストプラクティス | 全ユーザー |
| **[FAQ.md](FAQ.md)** | よくある質問と回答 | 初心者〜中級者 |

### 🛠️ 技術ドキュメント

| ファイル | 内容 | 対象者 |
| --- | --- | --- |
| [github-actions-simulator-summary.md](github-actions-simulator-summary.md) | プロジェクト概要とアーキテクチャ | 開発者・アーキテクト |
| [implementation-plan.md](implementation-plan.md) | 軽量actベース実装計画 | 開発者 |
| [github-actions-simulator-design.md](github-actions-simulator-design.md) | 技術設計詳細 | 開発者・アーキテクト |
| [ui-design.md](ui-design.md) | CLI・UX設計 | 開発者・デザイナー |

### 🔧 参考資料

| ファイル | 内容 | 用途 |
| --- | --- | --- |
| [act-integration-design.md](act-integration-design.md) | act統合の詳細設定 | 軽量化・カスタマイズ |

## 📖 推奨学習パス

### 🔰 初心者向け

1. **[USER_GUIDE.md](USER_GUIDE.md)** - 基本的な使い方を学ぶ
2. **[FAQ.md](FAQ.md)** - よくある問題の解決方法を確認
3. 実際に `./scripts/run-actions.sh` を試してみる

### 🚀 中級者向け

1. **[github-actions-simulator-summary.md](github-actions-simulator-summary.md)** - アーキテクチャを理解
2. **[USER_GUIDE.md](USER_GUIDE.md)** の高度な機能を試す
3. CI/CD統合やカスタマイズを実践

### 🛠️ 開発者向け

1. **[implementation-plan.md](implementation-plan.md)** - 実装方針を理解
2. **[github-actions-simulator-design.md](github-actions-simulator-design.md)** - 技術詳細を確認
3. **[ui-design.md](ui-design.md)** - UX設計思想を学ぶ
4. **[act-integration-design.md](act-integration-design.md)** - カスタマイズ方法を習得

## 🎛️ 主要機能

### ✨ 軽量actベースアーキテクチャ

- **高速起動**: 数秒でのワークフロー実行開始
- **最小依存**: Docker + act のみでフル機能
- **メモリ効率**: 必要最小限のリソース使用

### 🔧 インテリジェント機能

- **自動依存関係チェック**: Docker、uv、gitの自動確認
- **プラットフォーム別ガイダンス**: OS固有のインストール手順
- **自動復旧機能**: エラー時の自動修復提案
- **リアルタイム診断**: 実行中の包括的監視

### 🚀 開発者体験

- **対話モード**: 初心者向けの簡単操作
- **非対話モード**: CI/CD統合対応
- **豊富なオプション**: 詳細なカスタマイズ可能
- **包括的エラーハンドリング**: 分かりやすいエラーメッセージ

## 🛠️ 利用可能なコマンド

### メインエントリーポイント

```bash
# ワンショット実行スクリプト（推奨）
./scripts/run-actions.sh [ワークフローファイル] [-- <追加オプション>]

# 開発者向けMakeコマンド
make actions [WORKFLOW=<ファイル>] [CLI_ARGS=<オプション>]

# 直接CLI実行（上級者向け）
uv run python main.py actions simulate <ワークフローファイル>
```

### 診断・トラブルシューティング

```bash
# 依存関係チェック
./scripts/run-actions.sh --check-deps

# システム診断
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose

# 包括的診断
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --show-performance-metrics --show-execution-trace
```

## 🔗 関連リソース

### 📄 プロジェクトドキュメント

- **[メインREADME](../../README.md)** - プロジェクト全体の概要
- **[トラブルシューティング](../TROUBLESHOOTING.md)** - 一般的な問題と解決方法
- **[診断コマンド](../DIAGNOSTIC_COMMANDS.md)** - 診断機能の詳細
- **[API仕様](../API.md)** - REST APIリファレンス

### 🛡️ セキュリティ・品質

- **[権限・セキュリティ](../PERMISSION_SOLUTIONS.md)** - 権限問題の解決
- **[ハングアップ対応](../HANGUP_TROUBLESHOOTING.md)** - 実行停止時の対処法

### 🚀 開発・運用

- **[リリースシステム](../RELEASE_SYSTEM.md)** - 自動リリース管理
- **[Docker統合](../docker-integration-implementation-summary.md)** - Docker統合の詳細
- **[自動復旧](../auto_recovery_implementation_summary.md)** - 自動復旧機能の実装
- **[パフォーマンス監視](../performance_monitoring_implementation.md)** - 監視機能の詳細

## 📞 サポート

### 問題が発生した場合

1. **[FAQ.md](FAQ.md)** でよくある問題を確認
2. **[USER_GUIDE.md](USER_GUIDE.md)** のトラブルシューティングセクションを参照
3. `./scripts/run-actions.sh --check-deps` で診断情報を収集
4. GitHub Issuesで問題を報告

### 診断情報の収集

```bash
# 基本診断情報
./scripts/run-actions.sh --check-deps

# バージョン情報
make version

# 詳細ログ
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose --show-execution-trace
```

## 📝 更新履歴

- **2025-09-28**: Phase C対応 - ドキュメント体系を刷新、USER_GUIDE.mdとFAQ.mdを新設
- **2025-09-27**: Phase B施策を反映 - pre-commit品質ゲート、セキュリティスキャン、サマリー閲覧コマンドを追加
- **2025-09-26**: 軽量act方針に合わせて目次を刷新
- **2025-09-25**: 旧ロードマップ向けドキュメントを追加
