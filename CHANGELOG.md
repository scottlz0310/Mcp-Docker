# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ⚠️ 破壊的変更

- `github-oauth-proxy` を `mcp-gateway` に置き換え (#107)
  - **ポート変更**: `8084` → `8080`（`MCP_GATEWAY_PORT`）
  - **環境変数変更**:
    - `GITHUB_OAUTH_PROXY_BASE_URL` → `MCP_GATEWAY_BASE_URL`
    - `GITHUB_OAUTH_PROXY_PORT` → `MCP_GATEWAY_PORT`
    - `GITHUB_MCP_UPSTREAM_URL` を削除（`ROUTE_*` 環境変数に置き換え）
  - `copilot-review-mcp` のホスト公開ポート（8083）を廃止し、mcp-gateway 経由のみに変更
  - Makefile: `start-oauth` → `start-gateway`、`logs-oauth` → `logs-gateway`、`status-oauth` → `status-gateway`
  - IDE設定スクリプト: `--service github-oauth-proxy` → `--service mcp-gateway`

### ✨ 新機能

- `mcp-gateway`（`ghcr.io/scottlz0310/mcp-gateway:latest`）をルーティングゲートウェイとして追加
  - `ROUTE_GITHUB=/mcp/github|http://github-mcp:8082`
  - `ROUTE_COPILOT_REVIEW=/mcp/copilot-review|http://copilot-review-mcp:8083`
  - `github-mcp` と `copilot-review-mcp` の両サービスを単一ポートから提供
  - OAuth 2.0 認証フローを gateway に一元化

## [2.5.0] - 2026-04-24

### 🗑️ 削除

- `mcp-http-bridge` を削除（#90）
  - 全 IDE が OAuth プロキシ / HTTP 直接接続に移行済みで bridge は不要に
  - `bin/mcp-http-bridge.js`・`src/mcp-http-bridge.js`・`tests/node/mcp-http-bridge.test.js`・`scripts/verify-bridge-e2e.js`・`package.json` を削除
  - `lint-test.yml` の `test-node` ジョブを削除（Node.js テスト消滅のため）
- `github-mcp-server(patched)` カスタムビルドを削除（#89）
  - `copilot-review-mcp` の `get_review_threads` ツールが `PRRT_xxx` node ID 取得を完全に代替するため不要に
  - `Dockerfile.github-mcp-server`・`docker-compose.custom.yml`・`patches/` ディレクトリを削除
  - `docs/design/pr-review-thread-list-design.md` を削除
  - Makefile の `build-custom` / `start-custom` / `start-custom-oauth` ターゲットを削除
  - Security Scan ワークフローのパッチビルドスキャンジョブを削除

### 📝 ドキュメント

- README に設計思想セクションを追加（Docker ランタイムへの GitHub 認証一元化の背景）

## [2.4.0] - 2026-04-24

### ✨ 新機能

- `copilot-review-mcp`: Copilot review 非同期 Watch フローを追加
  - `start_copilot_review_watch` / `get_copilot_review_watch_status` / `list_copilot_review_watches` / `cancel_copilot_review_watch` ツールを追加（#75）
  - watch state を SQLite で永続化（セッション再起動後も watch を引き継ぎ可能に）（#74）
  - `get_pr_review_cycle_status` / `get_review_threads` / `reply_to_review_thread` / `reply_and_resolve_review_thread` / `resolve_review_thread` ツールを追加（#75）
  - MCP Watch resource（`copilot-review://watch/{watch_id}`）と `notifications/resources/updated` 通知を追加（#77）
  - サーバーを stateful session 管理（セッション単位で watch manager を保持）へリファクタリング（#76）

### 🔧 改善

- `copilot-review-mcp`: スレッド分類ロジックをMCPサーバーから削除し、LLMルールファイルベースへ移行（#55 #58 #62）
  - MCP が分類を担う設計をやめ、LLM がルールファイルを参照して自律分類する方式に変更
  - `get_review_threads` はフィルタなし全件返却に変更
- `docs`: `pr-review-cycle` スキルテンプレートを `docs/skills/pr-review-cycle.md` に追加（#78）

### 🐛 Fix

- `copilot-review-mcp`: `RequestCopilotReview` を REST API から GraphQL mutation へ移行（#52 #53）
  - `POST /repos/{owner}/{repo}/pulls/{pr}/requested_reviewers` は bot actor を黙って無視する（#47 の根本原因）
  - GitHub CLI と同じロジック（`requestReviewsByLogin` mutation + `botLogins`）で実装し直し
  - `union: true` で既存の human reviewer を保持したまま Copilot を追加
  - PR の GraphQL node ID を取得する際に空チェックを追加（PR 不存在・権限不足の検知）
  - `copilotBotLogin` 定数と `buildCopilotReviewInput` 関数を分離し、typo ガードのユニットテストを追加
- `copilot-review-mcp`: GraphQL input type エラーを修正（#73）
  - `requestReviewsByLogin` mutation の input フィールド名ミスを修正
- `copilot-review-mcp`: `wait_for_copilot_review` の TIMEOUT 後の余分な API コールと CANCEL 時の情報欠落を修正（#60）
- `copilot-review-mcp`: CI 環境での自動取得と `last_comment_at` 自動算出を実装（#61）
- `copilot-review-mcp`: stale-guard の誤発火とキャンセル時 `completed_at` 未更新を修正（#80）
- `auth`: GitHub トークン認証切れの原因 3 件（`expires_in` 秒計算誤り・レスポンス欠落・キャッシュ即時無効化）を修正（#51）
- `ci`: Security Scan ワークフローで `github-mcp-server` の ref をピン固定しセキュリティを強化（#70）

### 📦 依存関係更新

- `copilot-review-mcp`: `modernc.org/sqlite` を v1.48.2 へ更新（#50）
- `copilot-review-mcp`: `github.com/modelcontextprotocol/go-sdk` を v1.5.0 へ更新（#49）
- `copilot-review-mcp`: Go を v1.26.2 へ更新（#48）

### 📌 その他

- `.claude/` ディレクトリを `.gitignore` へ追加（#54）

## [2.3.0] - 2026-04-06

### ✨ 新機能

- `github-oauth-proxy` サービスを新設（`services/github-oauth-proxy/`）
  - mcp-remote 経由で Claude Desktop から github-mcp-server へ OAuth 認証付き接続が可能に（ISSUE #41）
  - RFC 8414 discovery / RFC 7591 Dynamic Client Registration (疑似) / Authorization Code + PKCE フローを実装
  - Bearer トークンを GitHub API（`GET /user`）で検証しキャッシュ。upstream (github-mcp-server) が HTTP 401 を返した際はキャッシュを即時無効化
  - `httputil.ReverseProxy.Rewrite` による厳格なヘッダーサニタイズ（`X-Forwarded-For` 等除去・`X-GitHub-Login` 注入）
  - 監査ログ: login / path / upstream_status / token_hash (SHA-256 前 8 桁) を `slog` で出力
  - `distroless/static-debian12:nonroot` ベースの最小イメージ。外部依存ライブラリなし（標準ライブラリのみ）

- `docker-compose.yml` に `github-oauth-proxy` サービスを追加
  - `github-mcp` のホスト公開ポートを廃止し Docker ネットワーク内に閉じ込め（セキュリティ向上）
  - `github-oauth-proxy` はポート 8084 でホスト公開

- `config/ide-configs/github-oauth-proxy/` に各クライアント向け設定を追加
  - `claude-desktop/`: mcp-remote 経由 stdio ブリッジ設定
  - `vscode/`: HTTP 直接接続設定
  - `codex/`: TOML 形式設定

## [2.2.0] - 2026-03-17

### ✨ 新機能

- `list_pull_request_review_threads` ツールを追加（Goソースパッチビルド方式）
  - `resolve_pull_request_review_thread` との一気通貫フローを実現
  - GraphQL API 経由でレビュースレッドの node ID（`PRRT_xxx`）を取得可能に
  - `is_resolved` 引数で解決済み/未解決フィルタが可能（省略時は全件）
  - `patches/github/list_pr_review_threads.go` を `Dockerfile.github-mcp-server` で注入するソースパッチ方式
  - カスタムイメージのビルド・起動は `make build-custom` / `make start-custom`

### 🐛 Fixes

- `generate-ide-config.sh --ide claude-desktop` の設定を HTTP から stdio（`docker run -i`）へ修正
  - Claude Desktop は HTTP transport 非対応のため、`docker run --rm -i` でバイナリを直接 stdio 起動する設定に変更
  - `GITHUB_MCP_IMAGE` 環境変数でカスタムビルドイメージも指定可能

## [2.1.0] - 2026-02-07

### 🚨 Breaking Changes

- Docker運用を `stdio` 前提から HTTP transport 前提へ変更
- `docker-compose.yml` とサンプルの既定イメージを `ghcr.io/github/github-mcp-server:main` に変更
- IDE設定生成スクリプトが `docker exec ... stdio` ではなく HTTP接続設定を出力するよう変更

### 🔧 Improvements

- `setup.sh` を「build中心」から「pull中心」に更新
- `health-check.sh` に MCP HTTPエンドポイント疎通チェックを追加
- `security.yml` のコンテナスキャン対象を pull した公式イメージに変更
- `docker-compose.yml` とサンプルのHTTPポートを `GITHUB_MCP_HTTP_PORT`（未設定時 `8082`）で一元化
- IDE設定生成スクリプトに `Codex CLI` / `Copilot CLI` 向けTOML出力を追加
- ドキュメントを HTTP運用・認証ヘッダー方式・最新イメージ方針に合わせて更新
- MCPサーバー手動テストの成功サマリーを追加（`docs/MCP_MANUAL_TEST_SUMMARY_2026-02-07.md`）

## [2.0.2] - 2026-02-05

### 🔐 Security

- **Critical Security Update**: Updated GitHub MCP Server from v0.24.1 to v0.30.2 to address multiple security vulnerabilities
  - Fixed CVE-2025-15467 (Critical): OpenSSL CMS parsing vulnerability - stack buffer overflow allowing remote code execution
  - Fixed CVE-2025-69419 (High): OpenSSL PKCS#12 vulnerability - out-of-bounds write
  - Fixed CVE-2025-61728 (High): Go archive/zip excessive CPU consumption (Go 1.25.6)
  - Fixed CVE-2025-61726 (High): Go net/url query parameter limit vulnerability (Go 1.25.6)
- Updated all docker-compose.yml files to use `ghcr.io/github/github-mcp-server:v0.30.2`
- Updated security scanning workflow to use the new image version

### 🔧 Improvements
- Documentation updated to reflect the new image version and security patches

## [2.0.1] - 2025-12-13

### 🔐 Security
- Re-introduced the `Security Scan` workflow (CodeQL + Trivy) so alerts are regenerated on every push/PR and during weekly scheduled runs.
- Filesystem and container scans now upload SARIF results with `aquasecurity/trivy-action@0.33.1`, matching the simplified MCP-only codebase.

### 🔧 Improvements
- `docker-compose.yml` とサンプル構成が `GITHUB_MCP_IMAGE` 変数を参照し、デフォルトで `ghcr.io/github/github-mcp-server:v0.24.1` に固定。
- `.env.template` に `GITHUB_MCP_IMAGE` のオーバーライドを追加し、READMEへ利用手順を追記。

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

[Unreleased]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.5.0...HEAD
[2.5.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.0.2...v2.1.0
[2.0.2]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/scottlz0310/Mcp-Docker/releases/tag/v1.0.1
