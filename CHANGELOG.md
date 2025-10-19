# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-19

### 🚨 Breaking Changes

- **プロジェクト構成の大幅な簡素化**: GitHub MCP Server専用環境に特化
- **Python関連の完全削除**: Actions Simulator、Release Watcher等を削除
- **Dockerfileの削除**: 公式イメージ(`ghcr.io/github/github-mcp-server:latest`)を使用
- **依存関係管理の削除**: pyproject.toml、uv.lock等を削除

### ✨ 新機能

- **シェルスクリプトベースの管理**: シンプルで保守しやすい構成
- **IDE設定生成スクリプト**: VS Code、Cursor、Claude Desktop、Kiro、Amazon Q対応
- **ヘルスチェックスクリプト**: サービス状態の確認を簡単に
- **自動テスト**: Batsによるシェルスクリプトテスト
- **Amazon Q Agent設定**: MCPサーバー統合設定

### 🔧 改善

- **Makefile簡素化**: MCPサーバー関連のみに絞り込み
- **CI/CD最適化**: シェルスクリプトのLint・テストのみ
- **ドキュメント整備**: README更新、セットアップガイド追加

### 🗑️ 削除

- Actions Simulator関連
- GitHub Release Watcher関連
- Python依存関係管理
- 複雑なCI/CDワークフロー (security, release, dependabot等)
- SBOM生成機能
- 不要な設定ファイル

### 📦 構成

シンプルな構成:
- `docker-compose.yml` - GitHub MCPサーバー設定
- `scripts/` - 管理スクリプト (setup, health-check, generate-ide-config, lint)
- `tests/shell/` - シェルスクリプトテスト
- `Makefile` - タスク管理

### 🔄 移行ガイド

v1.x からの移行:

1. **セットアップ方法の変更**:
   ```bash
   # 旧: 複雑なセットアップ
   # 新: シンプルなセットアップ
   ./scripts/setup.sh
   ```

2. **IDE設定生成**:
   ```bash
   ./scripts/generate-ide-config.sh --ide vscode
   ```

3. **サービス管理**:
   ```bash
   make start  # 起動
   make stop   # 停止
   make logs   # ログ確認
   ```

4. **不要なファイルの削除**:
   - Python関連ファイル
   - Actions Simulator設定
   - Release Watcher設定

## [1.3.0] - 2025-10-18

### Added
- Log analyzer for GitHub Actions
- Integration tests for GitHub Actions API

### Changed
- Updated README formatting

### Removed
- Outdated test files
- Comprehensive distribution files

## [1.2.0] - 2025-10-18

### Fixed
- Actions service directory handling
- Exit code handling

### Changed
- Documentation updates

## [1.1.0] - 2025-10-18

### Added
- Initial GitHub Actions Simulator
- GitHub Release Watcher

## [1.0.1] - 2025-10-18

### Fixed
- Initial bug fixes

[2.0.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/scottlz0310/Mcp-Docker/releases/tag/v1.0.1
