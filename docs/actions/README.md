# GitHub Actions Simulator - ドキュメント

GitHub Actions ワークフローをローカル環境でシミュレート・検証するためのツールのドキュメント集です。

## 📚 ドキュメント一覧

### 🚀 はじめに
- **[クイックスタート](QUICK_START.md)** - 5分で始めるGitHub Actions Simulator
- **[インストールガイド](INSTALLATION.md)** - 詳細なインストール手順
- **[ユーザーガイド](USER_GUIDE.md)** - 基本的な使用方法

### 📖 リファレンス
- **[CLIリファレンス](CLI_REFERENCE.md)** - 全コマンドとオプション
- **[APIリファレンス](API_REFERENCE.md)** - REST API仕様
- **[プラットフォーム対応](PLATFORM_SUPPORT.md)** - OS別対応状況

### 🛠️ トラブルシューティング
- **[トラブルシューティング](TROUBLESHOOTING.md)** - 一般的な問題と解決方法
- **[ハングアップ対応](HANGUP_TROUBLESHOOTING.md)** - ハングアップ問題の診断と修復
- **[診断コマンド](DIAGNOSTIC_COMMANDS.md)** - 診断・デバッグ用コマンド
- **[権限問題解決](PERMISSION_SOLUTIONS.md)** - 権限関連の問題解決

### 📋 その他
- **[FAQ](FAQ.md)** - よくある質問と回答
- **[アップグレードガイド](UPGRADE_GUIDE.md)** - バージョンアップ手順
- **[サポート](SUPPORT.md)** - サポート情報とコミュニティ

## 🎯 目的別ガイド

### 初めて使う方
1. [クイックスタート](QUICK_START.md) で基本的な使い方を学ぶ
2. [インストールガイド](INSTALLATION.md) で詳細なセットアップを行う
3. [ユーザーガイド](USER_GUIDE.md) で機能を詳しく理解する

### 問題が発生した方
1. [FAQ](FAQ.md) でよくある問題を確認
2. [トラブルシューティング](TROUBLESHOOTING.md) で解決方法を探す
3. [診断コマンド](DIAGNOSTIC_COMMANDS.md) で詳細な診断を実行

### 開発者・上級者
1. [CLIリファレンス](CLI_REFERENCE.md) で全機能を把握
2. [APIリファレンス](API_REFERENCE.md) でプログラマティックな使用方法を学ぶ
3. [プラットフォーム対応](PLATFORM_SUPPORT.md) で環境固有の情報を確認

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

## 🛠️ 基本的な使用方法

### メインエントリーポイント

```bash
# ワンショット実行スクリプト（推奨）
./scripts/run-actions.sh [ワークフローファイル]

# 開発者向けMakeコマンド
make actions

# 特定ワークフローの実行
make actions-run WORKFLOW=.github/workflows/ci.yml
```

### 診断・トラブルシューティング

```bash
# 依存関係チェック
./scripts/run-actions.sh --check-deps

# システム診断
make health-check

# 包括的診断
make test-hangup
```

## 📞 サポート

### 問題が発生した場合
1. [FAQ](FAQ.md) でよくある問題を確認
2. [トラブルシューティング](TROUBLESHOOTING.md) で解決方法を探す
3. [診断コマンド](DIAGNOSTIC_COMMANDS.md) で詳細な診断を実行
4. GitHub Issuesで問題を報告

### 診断情報の収集

```bash
# 基本診断情報
./scripts/run-actions.sh --check-deps

# バージョン情報
make version

# 詳細ログ
make actions-debug
```
