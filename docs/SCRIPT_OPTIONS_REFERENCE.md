# スクリプトオプション完全リファレンス

## 概要

GitHub Actions Simulator プロジェクトで提供される全スクリプトのオプションと使用方法について詳細に説明します。

## 目次

- [配布スクリプト](#配布スクリプト)
- [セットアップスクリプト](#セットアップスクリプト)
- [診断・ヘルスチェックスクリプト](#診断ヘルスチェックスクリプト)
- [テストスクリプト](#テストスクリプト)
- [セキュリティスクリプト](#セキュリティスクリプト)
- [ユーティリティスクリプト](#ユーティリティスクリプト)

## 配布スクリプト

### `scripts/run-actions.sh`

GitHub Actions Simulator のメイン配布スクリプトです。

#### 構文
```bash
./scripts/run-actions.sh [options] [workflow-file] [-- <additional-args>]
```

#### オプション

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|----|---------|----|
| `--help` | `-h` | flag | - | ヘルプメッセージを表示 |
| `--check-deps` | - | flag | false | 依存関係チェックのみ実行 |
| `--non-interactive` | - | flag | false | 非対話モードで実行 |
| `--timeout=<seconds>` | - | integer | 300 | actのタイムアウト時間を設定 |
| `--act-timeout=<seconds>` | - | integer | 300 | 同上（エイリアス） |

#### 環境変数

| 環境変数 | 型 | デフォルト | 説明 |
|---------|----|---------|----|
| `NON_INTERACTIVE` | boolean | false | 非対話モードを有効化 |
| `INDEX` | integer | - | ワークフロー選択を自動化（1から開始） |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | integer | 300 | actのタイムアウト時間 |

#### 機能

1. **依存関係チェック**
   - Docker (最小バージョン: 20.10.0)
   - Docker Compose (最小バージョン: 2.0.0)
   - Git (最小バージョン: 2.20.0)
   - uv (オプション)

2. **プラットフォーム検出**
   - Ubuntu/Debian
   - Fedora/RHEL/CentOS
   - macOS
   - Windows (WSL)

3. **エラーハンドリング**
   - 詳細なエラーメッセージ
   - プラットフォーム固有のインストールガイダンス
   - 自動復旧提案
   - 診断情報収集

4. **ログ機能**
   - エラーログ: `logs/error.log`
   - 診断ログ: `logs/diagnostic.log`

#### 使用例

```bash
# 基本実行（対話的）
./scripts/run-actions.sh

# 特定ワークフローを実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 依存関係チェックのみ
./scripts/run-actions.sh --check-deps

# 非対話モードで実行
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 最初のワークフローを自動選択
INDEX=1 ./scripts/run-actions.sh

# タイムアウトを10分に設定
./scripts/run-actions.sh --timeout=600 .github/workflows/ci.yml

# 追加のCLI引数を渡す
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --verbose
```

#### 終了コード

| コード | 説明 |
|-------|------|
| 0 | 正常終了 |
| 1 | 一般的なエラー |
| 2 | 依存関係エラー |
| 126 | 権限エラー |
| 127 | コマンド未発見 |
| 130 | 中断（Ctrl+C） |

## セットアップスクリプト

### `scripts/setup-docker-integration.sh`

Docker統合環境のセットアップを行います。

#### 構文
```bash
./scripts/setup-docker-integration.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--force` | 既存設定を強制上書き |
| `--skip-network` | ネットワーク作成をスキップ |
| `--skip-volumes` | ボリューム作成をスキップ |

#### 機能

1. **Docker ネットワーク作成**
   - `actions-simulator-network`
   - `mcp-network`

2. **Docker ボリューム作成**
   - `actions-simulator-cache`
   - `docker-socket-proxy`

3. **権限設定**
   - Docker グループへのユーザー追加
   - ファイル権限の調整

#### 使用例

```bash
# 基本セットアップ
./scripts/setup-docker-integration.sh

# 強制セットアップ（既存設定を上書き）
./scripts/setup-docker-integration.sh --force

# ネットワーク作成をスキップ
./scripts/setup-docker-integration.sh --skip-network
```

### `scripts/setup.sh`

プロジェクト全体の初期セットアップを行います。

#### 構文
```bash
./scripts/setup.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--dev` | 開発環境用セットアップ |
| `--prod` | 本番環境用セットアップ |
| `--minimal` | 最小限のセットアップ |

#### 機能

1. **依存関係インストール**
   - Python パッケージ (uv)
   - Node.js パッケージ (npm)
   - システムパッケージ

2. **設定ファイル作成**
   - `.env` ファイル
   - 設定テンプレートのコピー

3. **ディレクトリ構造作成**
   - `logs/`
   - `output/`
   - `cache/`

#### 使用例

```bash
# 基本セットアップ
./scripts/setup.sh

# 開発環境用セットアップ
./scripts/setup.sh --dev

# 最小限のセットアップ
./scripts/setup.sh --minimal
```

## 診断・ヘルスチェックスクリプト

### `scripts/docker-health-check.sh`

Docker環境の包括的なヘルスチェックを実行します。

#### 構文
```bash
./scripts/docker-health-check.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--comprehensive` | 包括的なチェックを実行 |
| `--daemon-only` | Docker デーモンのみをチェック |
| `--socket-only` | Docker ソケットのみをチェック |
| `--container-test-only` | コンテナテストのみを実行 |
| `--network-only` | ネットワークのみをチェック |
| `--act-only` | act関連のみをチェック |
| `--json` | JSON形式で結果を出力 |
| `--output <file>` | 結果をファイルに保存 |

#### チェック項目

1. **Docker デーモン**
   - サービス状態
   - バージョン情報
   - 応答時間

2. **Docker ソケット**
   - アクセス権限
   - 接続性
   - パフォーマンス

3. **コンテナ環境**
   - イメージの可用性
   - ネットワーク設定
   - ボリューム設定

4. **act 統合**
   - バイナリの存在
   - 実行権限
   - 動作確認

#### 使用例

```bash
# 基本ヘルスチェック
./scripts/docker-health-check.sh

# 包括的チェック
./scripts/docker-health-check.sh --comprehensive

# JSON形式で出力
./scripts/docker-health-check.sh --json --output health-report.json

# Docker デーモンのみをチェック
./scripts/docker-health-check.sh --daemon-only
```

### `scripts/verify-container-startup.sh`

コンテナの起動と設定を検証します。

#### 構文
```bash
./scripts/verify-container-startup.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--all` | 全コンテナを検証 |
| `--actions-simulator` | Actions Simulator コンテナのみ |
| `--github-mcp` | GitHub MCP コンテナのみ |
| `--datetime-validator` | DateTime Validator コンテナのみ |
| `--timeout <seconds>` | タイムアウト時間を設定 |
| `--retry <count>` | リトライ回数を設定 |

#### 検証項目

1. **コンテナ状態**
   - 起動状態
   - ヘルス状態
   - リソース使用量

2. **ネットワーク接続**
   - ポート開放状態
   - 内部通信
   - 外部接続

3. **ボリュームマウント**
   - マウント状態
   - 権限設定
   - データ永続化

#### 使用例

```bash
# 全コンテナを検証
./scripts/verify-container-startup.sh --all

# Actions Simulator のみを検証
./scripts/verify-container-startup.sh --actions-simulator

# タイムアウトとリトライを設定
./scripts/verify-container-startup.sh --all --timeout 60 --retry 3
```

## テストスクリプト

### `scripts/run-hangup-regression-tests.sh`

ハングアップ問題のリグレッションテストを実行します。

#### 構文
```bash
./scripts/run-hangup-regression-tests.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--verbose` | 詳細ログを出力 |
| `--quick` | 高速テストのみを実行 |
| `--full` | 完全なテストスイートを実行 |
| `--report <file>` | テスト結果をファイルに保存 |
| `--timeout <seconds>` | テストタイムアウトを設定 |

#### テスト項目

1. **Docker ソケットハングアップ**
   - 接続タイムアウト
   - 応答遅延
   - デッドロック状態

2. **プロセス監視**
   - プロセスハング検出
   - リソース枯渇
   - メモリリーク

3. **自動復旧機能**
   - 復旧メカニズム
   - フォールバック動作
   - エラーハンドリング

#### 使用例

```bash
# 基本リグレッションテスト
./scripts/run-hangup-regression-tests.sh

# 詳細ログ付きで実行
./scripts/run-hangup-regression-tests.sh --verbose

# 高速テストのみ
./scripts/run-hangup-regression-tests.sh --quick

# 結果をファイルに保存
./scripts/run-hangup-regression-tests.sh --report regression-report.json
```

### `scripts/run_bats.py`

Bats テストフレームワークを使用したテストを実行します。

#### 構文
```bash
python scripts/run_bats.py [options] [test-files...]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--verbose` | 詳細出力を有効化 |
| `--parallel <count>` | 並列実行数を指定 |
| `--filter <pattern>` | テストフィルターを指定 |
| `--output <format>` | 出力形式を指定 (tap, junit, json) |
| `--report <file>` | レポートファイルを指定 |

#### 使用例

```bash
# 全Batsテストを実行
python scripts/run_bats.py

# 特定のテストファイルを実行
python scripts/run_bats.py tests/test_docker_build.bats

# 並列実行
python scripts/run_bats.py --parallel 4

# JUnit形式でレポート出力
python scripts/run_bats.py --output junit --report test-results.xml
```

## セキュリティスクリプト

### `scripts/run_security_scan.py`

セキュリティスキャンを実行します。

#### 構文
```bash
python scripts/run_security_scan.py [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--image <name>` | スキャン対象のDockerイメージ |
| `--fail-on <severity>` | 指定した重要度以上で失敗 |
| `--skip-build` | ビルドをスキップ |
| `--severity <level>` | 最小重要度レベル |
| `--format <format>` | 出力形式 (table, json, sarif) |
| `--output <file>` | 結果をファイルに保存 |

#### スキャン項目

1. **コンテナイメージ**
   - 脆弱性スキャン (Trivy)
   - 設定チェック
   - シークレット検出

2. **依存関係**
   - Python パッケージ
   - Node.js パッケージ
   - システムパッケージ

3. **設定ファイル**
   - Dockerfile
   - Docker Compose
   - 環境変数

#### 使用例

```bash
# 基本セキュリティスキャン
python scripts/run_security_scan.py

# 特定イメージをスキャン
python scripts/run_security_scan.py --image actions-simulator:latest

# 高重要度以上で失敗
python scripts/run_security_scan.py --fail-on HIGH

# JSON形式で結果を保存
python scripts/run_security_scan.py --format json --output security-report.json
```

### `scripts/validate-user-permissions.sh`

ユーザー権限を検証します。

#### 構文
```bash
./scripts/validate-user-permissions.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--fix` | 権限問題を自動修正 |
| `--docker-only` | Docker権限のみをチェック |
| `--file-only` | ファイル権限のみをチェック |
| `--report` | 詳細レポートを出力 |

#### 検証項目

1. **Docker 権限**
   - Docker グループメンバーシップ
   - ソケットアクセス権限
   - コンテナ実行権限

2. **ファイル権限**
   - プロジェクトディレクトリ
   - ログディレクトリ
   - 出力ディレクトリ

3. **実行権限**
   - スクリプト実行権限
   - バイナリアクセス権限

#### 使用例

```bash
# 権限検証
./scripts/validate-user-permissions.sh

# 権限問題を自動修正
./scripts/validate-user-permissions.sh --fix

# Docker権限のみをチェック
./scripts/validate-user-permissions.sh --docker-only
```

## ユーティリティスクリプト

### `scripts/fix-permissions.sh`

ファイル・ディレクトリの権限を修正します。

#### 構文
```bash
./scripts/fix-permissions.sh [options] [paths...]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--recursive` | 再帰的に権限を修正 |
| `--docker-only` | Docker関連ファイルのみ |
| `--logs-only` | ログファイルのみ |
| `--output-only` | 出力ファイルのみ |
| `--dry-run` | 実際には変更せず、計画のみを表示 |

#### 修正対象

1. **プロジェクトファイル**
   - 実行可能スクリプト: 755
   - 設定ファイル: 644
   - ディレクトリ: 755

2. **ログファイル**
   - ログディレクトリ: 755
   - ログファイル: 644

3. **出力ファイル**
   - 出力ディレクトリ: 755
   - 出力ファイル: 644

#### 使用例

```bash
# 全体の権限を修正
./scripts/fix-permissions.sh

# ドライランで確認
./scripts/fix-permissions.sh --dry-run

# ログファイルのみを修正
./scripts/fix-permissions.sh --logs-only

# 特定のパスを修正
./scripts/fix-permissions.sh --recursive /path/to/directory
```

### `scripts/get-current-version.sh`

現在のプロジェクトバージョンを取得します。

#### 構文
```bash
./scripts/get-current-version.sh [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--format <format>` | 出力形式 (simple, json, yaml) |
| `--source <source>` | バージョンソース (pyproject, git, main) |
| `--check-consistency` | バージョン整合性をチェック |

#### バージョンソース

1. **pyproject.toml**
   - プロジェクト設定ファイル
   - 公式バージョン

2. **Git タグ**
   - 最新のGitタグ
   - リリースバージョン

3. **main.py**
   - アプリケーション内バージョン
   - 実行時バージョン

#### 使用例

```bash
# 現在のバージョンを表示
./scripts/get-current-version.sh

# JSON形式で出力
./scripts/get-current-version.sh --format json

# バージョン整合性をチェック
./scripts/get-current-version.sh --check-consistency
```

### `scripts/version-manager.py`

バージョン管理を行います。

#### 構文
```bash
python scripts/version-manager.py [command] [options]
```

#### コマンド

| コマンド | 説明 |
|---------|------|
| `show` | 現在のバージョンを表示 |
| `bump` | バージョンを更新 |
| `sync` | バージョンを同期 |
| `validate` | バージョン整合性を検証 |

#### オプション

| オプション | 説明 |
|-----------|------|
| `--type <type>` | バージョン更新タイプ (major, minor, patch) |
| `--version <version>` | 特定のバージョンを設定 |
| `--dry-run` | 実際には変更せず、計画のみを表示 |
| `--force` | 強制的に更新 |

#### 使用例

```bash
# 現在のバージョンを表示
python scripts/version-manager.py show

# パッチバージョンを更新
python scripts/version-manager.py bump --type patch

# 特定のバージョンを設定
python scripts/version-manager.py bump --version 1.2.0

# バージョンを同期
python scripts/version-manager.py sync
```

### `scripts/generate-sbom.py`

SBOM (Software Bill of Materials) を生成します。

#### 構文
```bash
python scripts/generate-sbom.py [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--format <format>` | 出力形式 (cyclonedx, spdx) |
| `--output <file>` | 出力ファイル |
| `--include-dev` | 開発依存関係を含める |
| `--include-docker` | Dockerイメージ情報を含める |

#### 生成内容

1. **Python 依存関係**
   - パッケージ名とバージョン
   - ライセンス情報
   - 脆弱性情報

2. **Docker イメージ**
   - ベースイメージ
   - レイヤー情報
   - インストールされたパッケージ

3. **システム依存関係**
   - OS パッケージ
   - バイナリファイル

#### 使用例

```bash
# CycloneDX形式でSBOMを生成
python scripts/generate-sbom.py --format cyclonedx --output sbom-cyclonedx.json

# SPDX形式でSBOMを生成
python scripts/generate-sbom.py --format spdx --output sbom-spdx.json

# 開発依存関係を含めて生成
python scripts/generate-sbom.py --include-dev --include-docker
```

### `scripts/audit-dependencies.py`

依存関係の監査を実行します。

#### 構文
```bash
python scripts/audit-dependencies.py [options]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--output <file>` | 監査結果をファイルに保存 |
| `--format <format>` | 出力形式 (json, csv, html) |
| `--severity <level>` | 最小重要度レベル |
| `--fix` | 修正可能な問題を自動修正 |

#### 監査項目

1. **脆弱性チェック**
   - 既知の脆弱性
   - セキュリティアドバイザリ
   - CVE データベース

2. **ライセンスチェック**
   - ライセンス互換性
   - 制限事項
   - コンプライアンス

3. **依存関係分析**
   - 循環依存
   - 未使用依存関係
   - バージョン競合

#### 使用例

```bash
# 依存関係監査を実行
python scripts/audit-dependencies.py

# 結果をJSONファイルに保存
python scripts/audit-dependencies.py --output audit-report.json

# 高重要度以上の問題のみを表示
python scripts/audit-dependencies.py --severity HIGH

# 修正可能な問題を自動修正
python scripts/audit-dependencies.py --fix
```

## 共通オプション

多くのスクリプトで共通して使用されるオプション：

| オプション | 説明 |
|-----------|------|
| `--help`, `-h` | ヘルプメッセージを表示 |
| `--verbose`, `-v` | 詳細ログを有効化 |
| `--quiet`, `-q` | 最小限の出力 |
| `--dry-run` | 実際には実行せず、計画のみを表示 |
| `--force` | 強制実行（確認をスキップ） |
| `--output <file>` | 結果をファイルに保存 |
| `--format <format>` | 出力形式を指定 |
| `--timeout <seconds>` | タイムアウト時間を設定 |

## 環境変数

スクリプト実行時に使用される共通環境変数：

| 環境変数 | 説明 | デフォルト |
|---------|----|---------|
| `VERBOSE` | 詳細ログを有効化 | false |
| `DEBUG` | デバッグモードを有効化 | false |
| `NON_INTERACTIVE` | 非対話モードを有効化 | false |
| `FORCE` | 強制実行を有効化 | false |
| `TIMEOUT` | デフォルトタイムアウト時間 | 300 |

## 関連ドキュメント

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) - CLIコマンドリファレンス
- [COMMAND_USAGE_GUIDE.md](./COMMAND_USAGE_GUIDE.md) - コマンド使い分けガイド
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - トラブルシューティング
- [CONTAINER_SETUP.md](./CONTAINER_SETUP.md) - Docker環境セットアップ
