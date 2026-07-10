# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ✨ 機能追加

- ローカル HTTPS (TLS) 接続のための自動セットアップ機能を追加 — #202
  - `make setup-tls`（`scripts/setup-tls.ps1`）: winget による mkcert の非対話インストール、ローカル CA の信頼登録（`mkcert -install` のみ局所 UAC 昇格）、`./config/certs/` への localhost / 127.0.0.1 宛て証明書生成、`.env` の自動構成（`MCP_GATEWAY_PUBLIC_URL` / `MCP_GATEWAY_TLS_CERT_PATH` / `MCP_GATEWAY_TLS_KEY_PATH` / `NODE_EXTRA_CA_CERTS`）を実施
  - `docker-compose.yml`: `./config/certs` を `/data/certs` として読み取り専用マウントし、TLS 環境変数を mcp-gateway に受け渡し（未設定時は従来どおり HTTP）
  - `scripts/health-check.sh`: gateway URL が `https://localhost` / `https://127.0.0.1` の場合に curl へ `-k` を自動付与（mkcert ローカル CA 未信頼環境での疎通確認失敗を防止。それ以外のホストでは証明書検証を維持）
  - `mcp-docker register`: 登録 URL・prune 判定の origin を `MCP_GATEWAY_PUBLIC_URL`（旧名 `MCP_GATEWAY_BASE_URL`）に追従させ、TLS 有効時に HTTPS エンドポイントが登録されるよう変更（未設定時は従来どおり `http://127.0.0.1:<port>`）
  - `setup-tls.ps1` は証明書生成時の CA fingerprint を `config/certs/.ca-fingerprint` に記録し、CA 再生成後の旧証明書再利用を防止
  - mcp-gateway 側の TLS 終端実装（mcp-gateway#201）とペアで機能

- `ROUTE_REVIEW_RAVEN` に `upstream_provider_token=true` を追加 — #197
  - `OAUTH_PROVIDER=builtin` モードで gateway JWT の代わりに GitHub provider token が review-raven upstream に注入されるようになる
  - gateway が独自 JWT を発行して provider token を破棄することで発生していた GitHub API 401 / `REAUTH_REQUIRED` を解消（mcp-gateway#186 の根本修正）

### 🐛 バグ修正

- Windows で `TestRegisterTimeoutOnAddCommand` / `TestRegisterTimeoutOnPruneCommand` が cmd.exe の起動オーバーヘッドにより `claude list` 段階で誤ってタイムアウトする flaky を修正（タイムアウトを 100ms から 2s に緩和）
- `thread-owl` サービスの起動モードを実体に合わせて修正 — #199
  - `command` を `--webhook-mcp-http` から `--mcp-http` に変更（Webhook 受信経路が存在しないため）
  - 未使用の `GITHUB_WEBHOOK_SECRET` 環境変数を削除（Webhook 受信を再導入する際に thread-owl#112 / Mcp-Docker#195 側で改めて追加）
- Windows 版 GNU Make からシェルスクリプトを実行した際、`/bin/bash` が WSL の `bash.exe` に誤解決される問題を修正
  - Windows では検出済みの Git for Windows Bash を明示し、`make lint-shell` と `make rotate-secret` を安定して実行可能に変更
  - `rotate-secret.sh` では Git Bash のパス変換を無効化し、永続 `config.yaml` の削除結果を検証

### 🔐 セキュリティ

- `ROUTE_GITHUB` / `ROUTE_REVIEW_RAVEN` / `ROUTE_THREAD_OWL` の `auth=none` を削除し、gateway OAuth 認証を必須化 — mcp-gateway#184
  - `ROUTE_GITHUB`: オーナーの PAT を注入する `upstream_bearer_token_env` は引き続き機能する。認証なしで 44 ツールが公開されていたリスクを解消
  - `ROUTE_REVIEW_RAVEN`: `auth=none` は review-raven が `X-Authenticated-User` ヘッダーを期待する設計と不整合であり、MCP 認証が機能しない状態だった
  - `ROUTE_THREAD_OWL`: GitHub App トークンによる高権限操作（Issue / PR / レビュー書き込み）が認証なしで露出していたリスクを解消
  - `ROUTE_PLAYWRIGHT` は認証不要な設計のまま維持（ローカルブラウザ制御専用）

## [2.15.0] - 2026-06-21

### ✨ 機能追加

- mcp-gateway の OIDC AS（builtin）を Compose に統合 — #185
  - `GITHUB_MCP_GATEWAY_IMAGE` デフォルトを `:main` に変更（builtin AS 実装を含む main ブランチを使用）
  - `OAUTH_PROVIDER` デフォルトを `builtin` に変更（gateway 自身が OIDC AS として動作。GitHub OAuth App は social login のみに使用）

### 🔄 変更

- Cloudflare MCP を gateway 経由（`upstream_oauth=auto`）から直接接続方式に変更
  - `ROUTE_CLOUDFLARE`（upstream_oauth 委任）を docker-compose.yml から削除
  - `config/mcp-external.yml` に Cloudflare 直接接続エントリを例示（コメントアウト）
  - MCP クライアントが `https://mcp.cloudflare.com/mcp` へ直接 OAuth 認可を行う構成に統一
  - **背景**: agy（Antigravity CLI）の既知バグ [#25](https://github.com/google-antigravity/antigravity-cli/issues/25)・[#348](https://github.com/google-antigravity/antigravity-cli/issues/348) により、HTTP MCP + upstream OAuth 委任フローが動作しないため

- review-raven の `auth=none` フォールバック対応として、gateway / review-raven コンテナに必要な環境変数を注入 — #182
  - gateway: `GITHUB_PERSONAL_ACCESS_TOKEN` を環境変数として追加し、`ROUTE_GITHUB` に `upstream_bearer_token_env=GITHUB_PERSONAL_ACCESS_TOKEN` を設定
  - `ROUTE_REVIEW_RAVEN` / `ROUTE_THREAD_OWL` に `auth=none` を追加
  - review-raven: `GITHUB_PERSONAL_ACCESS_TOKEN` と `REVIEW_RAVEN_DEFAULT_USER` を注入

- MCP ゲートウェイの GitHub トークン自動ローテーションをデフォルトで有効化（`MCP_GATEWAY_GITHUB_REFRESH_ENABLED=true`） — #178
  - `docker-compose.yml` でのデフォルト値を `true` に設定
  - `.env.template` に `MCP_GATEWAY_GITHUB_REFRESH_ENABLED=true` を明記し、自動ローテーション機能の利用を推奨するドキュメントを追加

### 🐛 バグ修正

- mcp-gateway の route prefix strip 後に `review-raven` / `thread-owl` の root へ転送され、MCP initialize が 404 になる問題を修正 — #180
  - 各 route の upstream URL に内部 MCP endpoint `/mcp` を明記
  - `thread-owl` の `MCP_HTTP_PATH=/mcp/thread-owl` を削除し、外部 route prefix と内部 endpoint の責務を分離
- `mcp-docker register` コマンドでエージェント（特に Codex CLI など）の登録・登録確認を行う際、OAuth 認証のキャンセルや失敗によって外部コマンドが応答なしのままハングアップする問題を修正 — #175
  - 各エージェントに対する外部コマンド実行（登録確認 `ListEntries`、登録 `Register`、削除 `pruneAgent`）にデフォルト 3 分のタイムアウトを設定
  - タイムアウト発生時は安全にエラー終了させるとともに、OAuth認証フローの失敗やキャンセルが発生した可能性を示す親切なエラーメッセージを出力
  - タイムアウト時間は環境変数 `MCP_DOCKER_REGISTER_TIMEOUT` からカスタマイズ可能に

### 📝 ドキュメント

- mcp-gateway の GitHub App 移行に合わせ、`.env.template` / `README.md` の作成手順・callback URL・permission 設定を更新 — #183
  - `OAUTH_CLIENT_ID` の例を GitHub App Client ID の `Iv23...` 形式に更新
  - `docker-compose.yml` で OAuth 監査ログを `/data/logs/auth-audit.jsonl` に永続化


## [2.14.0] - 2026-06-12

### ✨ 機能追加

- `mcp-docker register` に stale エントリ削除（prune）を追加 — #171
  - `--prune` で、定義ファイルに含まれなくなった gateway 配下（`http://127.0.0.1:<port>/...`）の既存登録を削除候補として提示・削除
  - gateway 配下以外の URL・URL 不明のエントリ（mcp-docker 管理外の可能性があるもの）は候補に含めない
  - 対話モードでは削除候補を番号選択（既定は削除しない）し、削除実行前に対象一覧つきの最終確認を表示
  - 非対話モードでは候補一覧と y/N 確認を表示し、`--yes` 指定時のみ確認を省略
  - 選択プロンプトに複数選択の入力例（`1,3 / all / none`）を表示

### 🐛 バグ修正

- `mcp-docker register` が `ROUTE_*` の Compose 変数展開に未対応で、cloudflare の serverUrl が壊れた値のまま agent に登録される問題を修正 — #167
  - `ROUTE_*` 値に Compose 互換の変数展開（`${VAR}` / `${VAR:-default}` / `${VAR:+alternative}`）を適用
  - `${VAR:+...}` の変数未設定などで展開後に空になったルートは登録対象からスキップ（gateway 側の空 `ROUTE_*` スキップと整合）
- `scripts/verify-mcp-endpoint.js` が `Accept` ヘッダー不足で HTTP 406 エラーになる問題を修正 — #168
  - mcp-gateway が要求する `Accept: application/json, text/event-stream` を送信するように変更
  - レスポンスが `text/event-stream` (SSE フレーミング) の場合に `data:` 行を抽出して JSON パースするように変更

### 🔧 改善

- `mcp-docker register` 実行時、既存登録確認と stale 検出（prune）で重複していた `list` コマンド実行（`ListEntries`）を排除し体感遅延を低減 — #173

### 📝 ドキュメント

- `mcp-docker register` の stale エントリ削除（prune）における「登録計画」という表現を「定義ファイル」に修正し、`--server` で絞り込んだ際の安全側の挙動を明確化

## [2.13.0] - 2026-06-11

### ⚠️ 破壊的変更

- `copilot-review-mcp` を `review-raven` へリネーム — #159
  - mcp-gateway の route を `/mcp/copilot-review` → `/mcp/review-raven` に変更（**破壊的**）
  - **アップグレード手順**:
    1. `make start-gateway`（`docker compose up --remove-orphans` により旧 `copilot-review-mcp` コンテナを自动除去）
    2. 各 CLI の旧登録キーを削除: `claude mcp remove --scope user copilot-review`（Copilot CLI / Codex CLI も同様に旧 `copilot-review` キーを削除）
    3. `make register-all REGISTER_FLAGS=--yes` で新名 `review-raven` を登録
  - イメージを `ghcr.io/scottlz0310/copilot-review-mcp` → `ghcr.io/scottlz0310/review-raven` に変更
  - 環境変数を改名: `ROUTE_COPILOT_REVIEW` → `ROUTE_REVIEW_RAVEN`、`COPILOT_REVIEW_MCP_IMAGE` → `REVIEW_RAVEN_IMAGE`、`COPILOT_REVIEW_MCP_PORT` → `REVIEW_RAVEN_PORT`（旧名フォールバックなし）
  - コンテナ名 `copilot-review-mcp` → `review-raven`、ボリューム `copilot-review-data` → `review-raven-data`（watch DB は空から再生成）
  - `scripts/health-check.sh --service` の対象名も `copilot-review-mcp` → `review-raven`
  - MCP ツール名（`start_copilot_review_watch` 等）は review-raven でも同名のため変更なし

### ✨ 機能追加

- Antigravity CLI への MCP 登録サポートを追加 — #165
  - `mcp-docker register` コマンドで `antigravity` を選択し、MCP サーバー定義を Antigravity の `mcp_config.json` に追加可能に

### 🔧 改善

- `make pull-main` / `make start-main` の開発版対象に thread-owl を追加 — #163
  - thread-owl のタグ分離（`:main` = 開発ビルド / `:latest` + `:vX.Y.Z` = 安定リリース）に追従
  - `THREAD_OWL_MAIN_IMAGE ?= ghcr.io/scottlz0310/thread-owl:main` を追加し、`pull-main` / `start-main` が thread-owl も `:main` を取得・起動
  - `make start-gateway` は従来通り `:latest`（安定版）で起動

### 📝 ドキュメント

- review platform における Mcp-Docker の責務を明文化 — #158
  - `docs/architecture-review-platform.md` を新規追加（orchestration / configuration automation layer としての定義・責務境界・bootstrap フロー）
  - README の関連リソースから新ドキュメントへの導線を追加

## [2.12.0] - 2026-06-01

### 🔧 改善

- Cloudflare ルートの環境変数駆動化 — #151
  - `docker-compose.yml` の Cloudflare 設定を `:?`（必須・未設定でエラー）から `:+`（条件付き展開）に変更
  - `CLOUDFLARE_API_TOKEN` を `.env` に設定するだけで自動有効化。`docker-compose.yml` の編集不要
  - mcp-gateway v0.5.1 の空 `ROUTE_*` スキップ対応と対になる変更

### 🐛 バグ修正

- `MCP_GITHUB_PAT` のネスト変数展開バグを修正 — #151
  - Docker Compose は `${VAR:-${OTHER}}` のネストを解釈しない仕様のため、`MCP_GITHUB_PAT` 未設定時にリテラル文字列がコンテナに渡っていた
  - Makefile 側でフォールバックを解決し、`docker-compose.yml` を単純なパススルーに変更
- Makefile が `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` を `.env` から読み取らない問題を修正 — #151（#147 フォロー）
  - 新変数名 `OAUTH_*` / 旧変数名 `GITHUB_MCP_*` の双方向フォールバックを整備

### 📦 依存関係更新

- mcp-gateway v0.5.1 に対応（空 `ROUTE_*` env var スキップ）

## [2.11.0] - 2026-05-18

### ✨ 新機能

- Remote MCP プロバイダーサポート追加（Cloudflare 対応・mcp-gateway v0.5.0 連携）— #146
  - `docker-compose.yml` に Cloudflare Remote MCP プロバイダー設定（コメントアウト済み）を追加
    - `ROUTE_CLOUDFLARE=/mcp/cloudflare|https://mcp.cloudflare.com/mcp|auth=oauth|upstream_bearer_token_env=CLOUDFLARE_API_TOKEN`
  - `.env.template` に `CLOUDFLARE_API_TOKEN` セクションを追加
  - README に Remote MCP プロバイダー設定ガイドを追加（Cloudflare を第一例として横展開パターンを文書化）

### 📦 依存関係更新

- `mcp-gateway v0.5.0` に対応（`upstream_bearer_token_env` 機能）

## [2.10.0] - 2026-05-18

### 🔧 改善

- `mcp-gateway v0.4.0` の `OAUTH_*` 環境変数移行に対応
  - `GITHUB_MCP_CLIENT_ID` → `OAUTH_CLIENT_ID`（旧変数名は後方互換フォールバックとして維持）
  - `GITHUB_MCP_CLIENT_SECRET` → `OAUTH_CLIENT_SECRET`（同上）
  - `GITHUB_MCP_OAUTH_SCOPES` → `OAUTH_SCOPES`（同上）
  - `docker-compose.yml` を二重フォールバック形式 `${OAUTH_CLIENT_ID:-${GITHUB_MCP_CLIENT_ID}}` に更新し、既存の `.env` を変更せずアップグレード可能に
- `.env.template` に `OAUTH_*` 変数を推奨変数として追記し、`GITHUB_MCP_*` を非推奨レガシーフォールバックとしてマーク

### ✨ 新機能

- `MCP_GATEWAY_GITHUB_REFRESH_ENABLED`（Phase A）を `docker-compose.yml` に追加（デフォルト `false`）
  - `true` に設定すると `mcp-gateway` がアクセストークンを透過的にローテーション
- `.env.template` に Phase B 内部 API 変数（`MCP_GATEWAY_INTERNAL_SECRET` / `MCP_GATEWAY_INTERNAL_PORT`）を追記

### 📦 依存関係更新

- `mcp-gateway v0.4.0` / `copilot-review-mcp v3.2.0` に対応

## [2.9.1] - 2026-05-10

### 📝 ドキュメント

- `docs/e2e-runbook-mcp-docker-cli.md` の `mcp-docker --help` 期待出力を v2.9.0 で追加された `--server <csv>|all` / `--interactive` を含む現行 CLI 出力に整合（PR #141 review）

## [2.9.0] - 2026-05-10

### ✨ 新機能

- `mcp-docker register` を対話モード対応に拡張（#134）
  - 引数なしかつ TTY 実行時は番号入力 UI で agent / MCP サーバーを複数選択
  - `--server <csv>|all` を新規追加し、`--agent claude,codex` のようなカンマ区切り指定にも対応
  - `--interactive` を明示指定したまま非 TTY 環境で起動した場合はエラーで終了
  - `make register` ターゲットを追加（`register-*` は後方互換のため維持）

## [2.8.0] - 2026-05-09

### 🐛 修正

- Windows では Makefile 経由の `mcp-docker` 成果物を `bin/mcp-docker.exe` として扱うよう修正（#133）
- `mcp-docker register --dry-run` が `--yes` なしで入力待ちにならないよう修正（#133）
- Go モジュールパスを `github.com/scottlz0310/mcp-docker/v2` に修正し `go install` でのグローバルインストールを可能に（#138）
  - 旧パスの `/tools` サフィックスが Go プロキシに不正解釈される問題を解消
  - v2.x.x タグに対応した `/v2` サフィックスを付与し `@latest` が正しく解決されるよう修正

### 🔧 改善

- Codecov upload を OIDC 認証に切り替え、アップロード失敗を CI で検出するよう調整

### 🗑️ 削除

- `mcp-docker register` への一本化に合わせ、Legacy の IDE 設定生成スクリプトと関連テストを削除
- 古い AI ツール向けルール、旧 issue template、旧単体 compose 例、Python/ci-helper 系の残骸を削除
- 現行実装から外れた設計メモと検証ログを `docs/archives/` に退避

## [2.7.0] - 2026-05-07

### ✨ 新機能

- `pull-main` / `start-main` / `restart-main` ターゲットを追加（#126）
  - `mcp-gateway` / `copilot-review-mcp` の `:main` イメージでリリース前の安定確認が可能
- `mcp-docker version` / `mcp-docker --version` / `mcp-docker -v` を追加
  - リリースバイナリではタグ名から内部バージョンを埋め込み

### 🔧 改善

- `mcp-gateway v0.3.0` / `copilot-review-mcp v3.0.0` の起動・設定変更に対応（#130）
  - OAuth 管理を `mcp-gateway` 側へ一元化した構成に整理
  - `MCP_GATEWAY_PUBLIC_URL` / `MCP_GATEWAY_BIND_ADDR` / `MCP_GATEWAY_KEY_PATH` / `MCP_CONFIG_FILE` を compose 設定に追加
  - `MCP_GATEWAY_BASE_URL` は後方互換エイリアスとして維持
- `localhost` 表記を `127.0.0.1` に統一し、OAuth callback URL と IDE 設定例の揺れを解消（#128 #129）
- gateway E2E 確認向けに compose 設定を調整（#127）
- `generate-ide-config.sh` / `health-check.sh` / README を `MCP_GATEWAY_PUBLIC_URL` 優先の説明に更新
- README に Makefile を使わず Go ツールチェーンから `mcp-docker` CLI をビルド・実行する手順を追加

### 🗑️ 削除

- `mcp-gateway-init` コンテナを削除（#125）
  - 現行の `mcp-gateway` イメージでトークンストア用ボリューム初期化を外部 init コンテナに依存しない構成へ移行

### 🧪 テスト

- `MCP_GATEWAY_PUBLIC_URL` が IDE 設定生成に反映され、`MCP_GATEWAY_BASE_URL` より優先されることを BATS で検証
- `mcp-docker --version` の Go テストを追加
- `cmd/mcp-docker/main.go` を Codecov 対象に戻し、CLI 実装コードのカバレッジを可視化

### 📦 依存関係更新

- Go module directive を `1.26.2` に更新（#131）

## [2.6.1] - 2026-04-30

### 🐛 バグ修正・改善

- リリース配布物を生バイナリからアーカイブ形式に変更（#124）
  - Linux / macOS: `.tar.gz`
  - Windows: `.zip`
  - `checksums.txt` をアーカイブファイルの SHA256 に統一

## [2.6.0] - 2026-04-30

### ✨ 新機能

- `mcp-docker` Go CLI ツールを追加（#117）
  - `mcp-docker register [--agent claude|copilot|codex|all]` コマンドで MCP サーバーを各 IDE CLI に一括登録
  - `--dry-run` オプションで実行前に登録コマンドを確認可能
  - `--compose` / `--external` で `docker-compose.yml` および `config/mcp-external.yml` から自動的にサーバー一覧を取得
  - バイナリを GitHub Releases で配布（linux/darwin/windows, amd64/arm64）
- `.github/workflows/release.yml` を追加: タグ push で自動クロスコンパイル＆リリース作成
- CI に `go vet ./...` を追加し、Makefile に `lint-go` ターゲットを追加（#122）
- `auth=none` ルートで認証不要 MCP サーバを設定のみで追加できるパターンを追加（#109）
  - `docker-compose.yml` に `playwright-mcp` サービスをデフォルト有効化済みの設定例として追加
  - `mcp-gateway` の `environment` に `ROUTE_PLAYWRIGHT=.../auth=none` をデフォルト有効化
  - `playwright-mcp` を使用しない場合は `depends_on`・`ROUTE_PLAYWRIGHT`・サービス定義を削除してください
  - `.env.template` に `PLAYWRIGHT_MCP_IMAGE` / `PLAYWRIGHT_MCP_PORT` の説明と手順を追加
  - README に「MCPサーバの追加パターン（auth=none）」セクションを追加
  - 前提: `mcp-gateway` の `auth=none` サポート（scottlz0310/mcp-gateway#23 でマージ済み）
- `copilot-review-mcp` のイメージをローカルビルドから公開パッケージ（`ghcr.io/scottlz0310/copilot-review-mcp:latest`）に変更
  - `COPILOT_REVIEW_MCP_IMAGE` 環境変数でオーバーライド可能
- `mcp-gateway`（`ghcr.io/scottlz0310/mcp-gateway:latest`）をルーティングゲートウェイとして追加
  - `ROUTE_GITHUB=/mcp/github|http://github-mcp:8082`
  - `ROUTE_COPILOT_REVIEW=/mcp/copilot-review|http://copilot-review-mcp:8083`
  - `github-mcp` と `copilot-review-mcp` の両サービスを単一ポートから提供
  - OAuth 2.0 認証フローを gateway に一元化

### ⚠️ 破壊的変更

- Makefile ターゲットを `*-gateway` 命名に統一
  - `start` / `start-gateway` → **`start-gateway`**（単体起動廃止、gateway スタック起動が唯一の標準）
  - `stop` → **`stop-gateway`**（`stop` は後方互換エイリアスとして維持）
  - `restart` → **`restart-gateway`**（`stop-gateway` + `start-gateway`）
  - `logs-gateway` → 維持
  - `status-gateway` → 維持（`status` は後方互換エイリアス）
  - `pull` → **`pull-gateway`**（全サービスイメージを `docker compose pull` で一括取得）
- `github-oauth-proxy` を `mcp-gateway` に置き換え (#107)
  - **ポート変更**: `8084` → `8080`（`MCP_GATEWAY_PORT`）
  - **環境変数変更**:
    - `GITHUB_OAUTH_PROXY_BASE_URL` → `MCP_GATEWAY_BASE_URL`
    - `GITHUB_OAUTH_PROXY_PORT` → `MCP_GATEWAY_PORT`
    - `GITHUB_MCP_UPSTREAM_URL` を削除（`ROUTE_*` 環境変数に置き換え）
  - `copilot-review-mcp` のホスト公開ポート（8083）を廃止し、mcp-gateway 経由のみに変更
  - Makefile: `start-oauth` → `start-gateway`、`logs-oauth` → `logs-gateway`、`status-oauth` → `status-gateway`
  - IDE設定スクリプト: `--service github-oauth-proxy` → `--service mcp-gateway`

### 🗑️ 削除

- `services/copilot-review-mcp/` を削除（外部リポジトリ `ghcr.io/scottlz0310/copilot-review-mcp` に移行済み）
- `services/github-oauth-proxy/` を削除（外部リポジトリ `ghcr.io/scottlz0310/mcp-gateway` に移行済み）
- Makefile: ローカルビルド前提の `crm-*` ターゲット群を削除（`crm-build`, `crm-start`, `crm-stop`, `crm-restart`, `crm-logs`, `crm-status`, `crm-health`）
- Makefile: `start`（github-mcp 単体）、`restart`（単体）、`build`（pull エイリアス）、`gen-config-crm` を削除
- `.github/workflows/lint-test.yml`: Go テストジョブ（`test-go`）を削除
- `.github/workflows/security.yml`: `copilot-review-mcp-scan` ジョブを削除（ローカル Dockerfile 不要に）
- `.github/workflows/codeql.yml`: `go` 言語マトリックスを削除（Go コード消滅のため）
- `tasks.md`、`scripts/verify-review-status.sh`、`docs/copilot-review-mcp-tasks.md`、`docs/copilot-review-watch-tools.md`、`docs/design/copilot-review-watch-redesign.md`、`docs/observations/`、`docs/bug-reports/` を削除

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

[Unreleased]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.15.0...HEAD
[2.15.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.14.0...v2.15.0
[2.14.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.13.0...v2.14.0
[2.13.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.12.0...v2.13.0
[2.12.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.11.0...v2.12.0
[2.11.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.10.0...v2.11.0
[2.10.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.9.1...v2.10.0
[2.9.1]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.9.0...v2.9.1
[2.9.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.8.0...v2.9.0
[2.8.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.7.0...v2.8.0
[2.7.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.6.1...v2.7.0
[2.6.1]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.6.0...v2.6.1
[2.6.0]: https://github.com/scottlz0310/Mcp-Docker/compare/v2.5.0...v2.6.0
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
