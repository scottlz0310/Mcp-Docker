# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2025-10-06

### ✨ 新機能

- **🔔 GitHub Release Watcher サービス追加**
  - 任意のGitHubリポジトリの新しいリリースを監視
  - マルチチャネル通知対応（Native/Discord/Slack/Email/Webhook/File）
  - 非同期処理による高速な並列リポジトリチェック
  - セマンティックバージョニング対応のバージョン比較
  - 安定版/プレリリース/カスタムパターンによる柔軟なフィルタリング
  - TTLキャッシュによるGitHub APIレート制限対策
  - スレッドセーフな状態管理とJSON永続化
  - 環境変数展開対応のTOML設定ファイル
  - Docker統合とdocker-compose対応

- **📄 README更新**
  - MCP Dockerを統合管理システムとして再定義
  - 全サービス（GitHub MCP、DateTime Validator、Actions Simulator、GitHub Release Watcher）の統一的な説明
  - サービス別の使用方法セクション追加
  - WSL環境セットアップ手順を追加

### 🐛 バグ修正

- **🔧 CI環境でのdocker-compose.yml構文エラーを修正**
  - `WINDOWS_NOTIFICATION_PATH`環境変数未設定時のボリュームマウントエラーを解決
  - docker-compose.override.ymlパターンで環境依存設定を分離
  - WSL環境用の`docker-compose.override.yml.example`テンプレートを作成
  - Makefileに環境自動検出と`make setup-wsl`コマンドを追加

### 🧪 テスト

- **GitHub Release Watcher ユニットテスト追加**
  - comparator モジュールテスト（10テスト、全パス）
  - notification モジュールテスト（5テスト、全パス）
  - scheduler モジュールテスト（新規リリース検知、状態管理）
  - pytest モックフィクスチャ追加（GitHub API、Discord、Slack、Native通知）

- **テストタイムアウトの最適化**
  - conftest.pyでslowマーカー用タイムアウトを600秒に一元管理
  - Dockerビルドが必要なテストにslowマーカーを付与

### 📚 ドキュメント

- **GitHub Release Watcher ドキュメント追加**
  - サービス設計ドキュメント（docs/services/github-release-watcher.md）
  - 実装計画ドキュメント（docs/analysis/github-release-watcher-implementation-plan.md）
  - 使用ガイド（examples/github-release-watcher/README.md）
  - サンプル設定ファイル（config.toml）
  - 起動/停止スクリプト

### 🐳 Docker

- **GitHub Release Watcher Docker統合**
  - Dockerfile に github-release-watcher ターゲット追加
  - docker-compose.yml にサービス定義追加
  - .env.example に環境変数設定追加

### 🧹 リファクタリング

- 重複するdocker-compose.override.ymlテンプレートを削除
  - docker-compose.override.yml.sample (17KB) 削除
  - docker-compose.override.yml.simple (2.4KB) 削除
  - WSL環境専用のexampleテンプレートのみ保持

### 🔧 改善

- **依存関係追加**
  - aiohttp >= 3.9.0 (非同期HTTP)
  - cachetools >= 5.3.0 (TTLキャッシュ)
  - packaging >= 23.0 (セマンティックバージョニング)
  - python-dotenv >= 1.0.0 (環境変数管理)
  - プラットフォーム別通知ライブラリ（win10toast、pync、plyer）

### 🐛 修正

- **モジュール名の修正**
  - `services/github-release-watcher` → `services/github_release_watcher` (Pythonモジュール規約に準拠)

## [1.2.0] - 2025-10-05


### ✨ 新機能

- **🧪 テストインフラの完全再構築** (#17)
  - pytest-xdist並列実行完全対応（worker_idベース）
  - Actions SimulatorとDateTime Validatorの統合テスト追加
  - コンテナ名のユニーク化により並列実行時の競合を完全解消
  - 31/31テスト全てパス（100%成功率）

- **🤖 Actions Simulator機能強化**
  - ハングアップ検出機能実装
  - EnhancedActWrapper統合
  - システムヘルスチェック機能追加
  - 自動復旧メカニズム実装
  - Docker統合とコンテナ通信の修正機能

- **📋 AI開発支援体制の確立**
  - プロジェクト分析ドキュメント追加
  - AI開発支援ルールの策定と遵守事項の明確化
  - ドキュメント構造の整理とガイドライン策定

### 🔧 改善

- **CI/CDワークフローの最適化**
  - テスト実行タイムアウトの適切な設定
  - GitHub Actions実行の安定性向上
  - プロファイル指定によるサービス起動方式の改善

- **依存関係の更新**
  - setup-uv: 3 → 6 (#16)
  - build-push-action: 5 → 6 (#15)
  - github-script: 7 → 8 (#14)

### 🐛 修正

- Docker権限問題の完全解決とGPAT環境変数フォールバック機能
- Actions Simulatorパス解決問題の根本修正
- 品質ゲート失敗問題の修正
- pre-commit設定の引数整形とコメントの調整
- GitHub Actionsワークフロー入力パラメータ修正

### 🔬 テスト

- テストスイート全体の並列実行対応
- テスト実行時間の短縮（初回186秒、キャッシュ有効時47秒）
- テストの堅牢性向上（フレーキーテスト解消）

### 📝 ドキュメント

- プロジェクト分析ドキュメントの追加
- 使用ガイドの整備
- API仕様書の更新

### 📋 詳細機能説明

### ✨ 新機能
- **🧪 テストインフラの完全再構築** (#17)
  - pytest-xdist並列実行完全対応（worker_idベース）
  - Actions SimulatorとDateTime Validatorの統合テスト追加
  - コンテナ名のユニーク化により並列実行時の競合を完全解消
  - 31/31テスト全てパス（100%成功率）
- **🤖 Actions Simulator機能強化**
  - ハングアップ検出機能実装
  - EnhancedActWrapper統合
  - システムヘルスチェック機能追加
  - 自動復旧メカニズム実装
  - Docker統合とコンテナ通信の修正機能
- **📋 AI開発支援体制の確立**
  - プロジェクト分析ドキュメント追加
  - AI開発支援ルールの策定と遵守事項の明確化
  - ドキュメント構造の整理とガイドライン策定
### 🔧 改善
- **CI/CDワークフローの最適化**
  - テスト実行タイムアウトの適切な設定
  - GitHub Actions実行の安定性向上
  - プロファイル指定によるサービス起動方式の改善
- **依存関係の更新**
  - setup-uv: 3 → 6 (#16)
  - build-push-action: 5 → 6 (#15)
  - github-script: 7 → 8 (#14)
### 🐛 修正
- Docker権限問題の完全解決とGPAT環境変数フォールバック機能
- Actions Simulatorパス解決問題の根本修正
- 品質ゲート失敗問題の修正
- pre-commit設定の引数整形とコメントの調整
- GitHub Actionsワークフロー入力パラメータ修正
### 🔬 テスト
- テストスイート全体の並列実行対応
- テスト実行時間の短縮（初回186秒、キャッシュ有効時47秒）
- テストの堅牢性向上（フレーキーテスト解消）
### 📝 ドキュメント
- プロジェクト分析ドキュメントの追加
- 使用ガイドの整備
- API仕様書の更新

<!-- リリースページ統合済み: 2025-10-05 -->

## [1.1.0] - 2025-09-24

### ✨ 新機能

- Improve testing infrastructure and package management
- integrate documentation auto-update with release workflow
- 包括的なドキュメント自動生成システムを実装
- 🚀 **完全自動化リリースシステム**: GitHub Actions 5段階ジョブ構成による完全自動化
- 🧠 **スマートバージョン管理**: pyproject.toml ↔ main.py 自動同期・バージョン後退禁止
- 📝 **インテリジェントCHANGELOG**: Git履歴からConventional Commits解析・自動分類
- 🏗️ **統合ドキュメント**: Sphinx + GitHub Pages 完全自動デプロイ
- 🎛️ **多様なトリガー**: 手動実行・タグプッシュ・ドキュメント連動
- 🛡️ **セキュリティ保証**: バージョン後退禁止・権限管理・品質保証統合

### � 修正

- resolve CI test failure in UID validation
- 自動修正時のコミットメッセージの取り扱いを変更
- resolve CI test failures with dynamic UID/GID validation

### �📝 ドキュメント

- enable GitHub Pages integration
- **📚 リリース自動化システム完全ガイド**: 包括的な13,000文字超ドキュメント作成
- **🔄 美しいフローチャート**: Mermaidダイアグラムによる視覚化
- **🎢 処理シーケンス**: 開発者・GitHub Actions・リポジトリの相互作用図
- **📋 ステップバイステップガイド**: 実行手順・デバッグ方法完全解説
- **🌐 Sphinxドキュメント統合**: GitHub Pagesへの完全統合

### 🔧 その他

- chore: bump version to 1.1.0

### 🔧 システム強化

- **5段階ジョブ**: version-check → quality-check → prepare-release → create-release → post-release
- **repository_dispatch**: リリース連動ドキュメント自動更新
- **マトリクステスト**: OS × Dockerバージョン対応
- **ブランチ保護**: 自動設定・必須チェック統合
- **CODEOWNERS**: 自動レビュー設定

### 🧪 CI/CD改善

- **UID検証テスト**: docker-compose警告対策・stderr処理改善
- **環境変数管理**: GITHUB_PERSONAL_ACCESS_TOKEN設定
- **デバッグ出力強化**: 包括的エラーハンドリング
- **GitHub Pages**: repository設定・workflow権限最適化

## [0.1.0] - 2025-09-24

### ✨ 初期機能

- MCP Docker環境の初期実装
- GitHub/DateTime/CodeQL MCPサービス統合
- 包括的テストスイート（Bats）
- セキュリティスキャン（Trivy）統合
- CI/CDパイプライン実装

### 📝 初期ドキュメント

- API仕様書作成
- トラブルシューティングガイド
- 開発者向けドキュメント整備

### 🔧 基盤整備

- Phase 1-5完了
- プロダクション品質達成
