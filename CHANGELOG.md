# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
