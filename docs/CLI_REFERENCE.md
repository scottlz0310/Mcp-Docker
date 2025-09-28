# GitHub Actions Simulator - CLI リファレンス

## 概要

GitHub Actions Simulator は、GitHub Actions ワークフローをローカル環境でシミュレート・検証するためのCLIツールです。このドキュメントでは、利用可能なすべてのコマンド、オプション、使用例について詳しく説明します。

## 目次

- [基本的な使用方法](#基本的な使用方法)
- [メインエントリーポイント](#メインエントリーポイント)
- [Actions Simulator CLI](#actions-simulator-cli)
- [Make コマンド](#make-コマンド)
- [配布スクリプト](#配布スクリプト)
- [環境変数](#環境変数)
- [使用例](#使用例)
- [トラブルシューティング](#トラブルシューティング)

## 基本的な使用方法

GitHub Actions Simulator には3つの主要なインターフェースがあります：

1. **Python メインエントリーポイント** (`python main.py`)
2. **Actions Simulator CLI** (`python -m services.actions.main`)
3. **Make コマンド** (`make actions`)
4. **配布スクリプト** (`./scripts/run-actions.sh`)

## メインエントリーポイント

### `python main.py`

MCP Docker Environment のメインエントリーポイントです。

#### 構文
```bash
python main.py <service> [options]
```

#### サービス

| サービス | 説明 | 例 |
|---------|------|-----|
| `github` | GitHub MCP サーバーを起動 | `python main.py github` |
| `datetime` | DateTime Validator を起動 | `python main.py datetime` |
| `actions` | GitHub Actions Simulator を起動 | `python main.py actions simulate .github/workflows/ci.yml` |

#### オプション

| オプション | 説明 |
|-----------|------|
| `--version` | バージョン情報を表示 |

#### 使用例

```bash
# バージョン情報を表示
python main.py --version

# GitHub MCP サーバーを起動
python main.py github

# DateTime Validator を起動
python main.py datetime

# GitHub Actions Simulator でワークフローを実行
python main.py actions simulate .github/workflows/ci.yml

# GitHub Actions Simulator でジョブを指定して実行
python main.py actions simulate .github/workflows/ci.yml --job test

# GitHub Actions Simulator でドライランを実行
python main.py actions simulate .github/workflows/ci.yml --dry-run
```

## Actions Simulator CLI

### `python -m services.actions.main`

GitHub Actions Simulator の詳細なCLIインターフェースです。

#### 基本構文
```bash
python -m services.actions.main [global-options] <command> [command-options] [arguments]
```

#### グローバルオプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--verbose` | `-v` | 詳細ログを表示 |
| `--quiet` | `-q` | 最小限の出力に切り替える |
| `--debug` | | デバッグレベルのログを表示 |
| `--config <path>` | | 設定ファイル (TOML) を指定 |
| `--help` | `-h` | ヘルプを表示 |
| `--version` | | バージョン情報を表示 |

### サブコマンド

#### `simulate` - ワークフローを実行

ワークフローファイルを実行します。

##### 構文
```bash
python -m services.actions.main simulate [options] <workflow-file>
```

##### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--job <job-id>` | 特定のジョブのみを実行 | 全ジョブ |
| `--dry-run` | 実際には実行せず、計画のみを表示 | false |
| `--env-file <path>` | 環境変数ファイルを指定 | なし |
| `--env <KEY=VALUE>` | 環境変数を設定（複数指定可能） | なし |
| `--diagnose` | 実行前にシステム診断を実行 | false |
| `--enhanced` | 拡張機能を有効化 | false |
| `--show-performance-metrics` | パフォーマンスメトリクスを表示 | false |
| `--show-execution-trace` | 実行トレースを表示 | false |
| `--create-debug-bundle` | エラー時にデバッグバンドルを作成 | false |
| `--debug-bundle-dir <path>` | デバッグバンドルの出力ディレクトリ | `output/debug-bundles` |

##### 使用例

```bash
# 基本的なワークフロー実行
python -m services.actions.main simulate .github/workflows/ci.yml

# 特定のジョブのみを実行
python -m services.actions.main simulate .github/workflows/ci.yml --job test

# ドライランで実行計画を確認
python -m services.actions.main simulate .github/workflows/ci.yml --dry-run

# 環境変数を指定して実行
python -m services.actions.main simulate .github/workflows/ci.yml --env NODE_ENV=test --env DEBUG=true

# 環境変数ファイルを使用
python -m services.actions.main simulate .github/workflows/ci.yml --env-file .env.test

# 詳細ログと診断を有効化
python -m services.actions.main --verbose simulate .github/workflows/ci.yml --diagnose

# 拡張機能とパフォーマンス監視を有効化
python -m services.actions.main simulate .github/workflows/ci.yml --enhanced --show-performance-metrics

# デバッグバンドル作成を有効化
python -m services.actions.main simulate .github/workflows/ci.yml --create-debug-bundle
```

#### `validate` - ワークフローを検証

ワークフローファイルの構文をチェックします。

##### 構文
```bash
python -m services.actions.main validate [options] <workflow-file-or-directory>
```

##### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--strict` | 厳密な検証を実行 | false |

##### 使用例

```bash
# 単一ファイルの検証
python -m services.actions.main validate .github/workflows/ci.yml

# ディレクトリ内の全ワークフローを検証
python -m services.actions.main validate .github/workflows/

# 厳密な検証を実行
python -m services.actions.main validate --strict .github/workflows/ci.yml
```

#### `list-jobs` - ジョブ一覧を表示

ワークフローファイル内のジョブ一覧を表示します。

##### 構文
```bash
python -m services.actions.main list-jobs [options] <workflow-file>
```

##### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--format <format>` | 出力形式 (table/json) | table |

##### 使用例

```bash
# テーブル形式でジョブ一覧を表示
python -m services.actions.main list-jobs .github/workflows/ci.yml

# JSON形式でジョブ一覧を表示
python -m services.actions.main list-jobs --format json .github/workflows/ci.yml
```

#### `diagnose` - システム診断

システムのヘルスチェックを実行します。

##### 構文
```bash
python -m services.actions.main diagnose [options]
```

##### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--format <format>` | 出力形式 (table/json) | table |
| `--output <path>` | 結果をファイルに保存 | なし |
| `--include-performance` | パフォーマンス分析を含める | false |
| `--include-trace` | トレース分析を含める | false |

##### 使用例

```bash
# 基本的なシステム診断
python -m services.actions.main diagnose

# JSON形式で診断結果を出力
python -m services.actions.main diagnose --format json

# 診断結果をファイルに保存
python -m services.actions.main diagnose --output diagnostic-report.json

# パフォーマンス分析を含めた詳細診断
python -m services.actions.main diagnose --include-performance --include-trace
```

#### `create-debug-bundle` - デバッグバンドルを作成

トラブルシューティング用のデバッグバンドルを作成します。

##### 構文
```bash
python -m services.actions.main create-debug-bundle [options]
```

##### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--output-dir <path>` | 出力ディレクトリ | `output/debug-bundles` |
| `--include-logs` | ログファイルを含める | true |
| `--include-config` | 設定ファイルを含める | true |

##### 使用例

```bash
# デバッグバンドルを作成
python -m services.actions.main create-debug-bundle

# 出力ディレクトリを指定してデバッグバンドルを作成
python -m services.actions.main create-debug-bundle --output-dir /tmp/debug
```

## Make コマンド

Makefile を通じて提供される便利なコマンドです。

### GitHub Actions Simulator 関連

#### 基本コマンド

| コマンド | 説明 | 使用例 |
|---------|------|--------|
| `make actions` | インタラクティブなワークフロー選択 | `make actions` |
| `make actions-auto` | デフォルトCIワークフローを自動実行 | `make actions-auto` |
| `make actions-list` | 利用可能なワークフロー一覧を表示 | `make actions-list` |
| `make actions-run` | 指定したワークフローを実行 | `make actions-run WORKFLOW=.github/workflows/ci.yml` |
| `make actions-validate` | ワークフローを検証 | `make actions-validate WORKFLOW=.github/workflows/ci.yml` |
| `make actions-dry-run` | ドライランを実行 | `make actions-dry-run WORKFLOW=.github/workflows/ci.yml` |

#### パラメーター

| パラメーター | 説明 | 例 |
|-------------|------|-----|
| `WORKFLOW` | 実行するワークフローファイル | `WORKFLOW=.github/workflows/ci.yml` |
| `JOB` | 実行する特定のジョブ | `JOB=test` |
| `VERBOSE` | 詳細ログを有効化 | `VERBOSE=1` |
| `INDEX` | ワークフロー選択の自動化 | `INDEX=1` |

#### 使用例

```bash
# インタラクティブにワークフローを選択して実行
make actions

# 特定のワークフローを実行
make actions-run WORKFLOW=.github/workflows/ci.yml

# 特定のジョブのみを実行
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test

# 詳細ログを有効にして実行
make actions-run WORKFLOW=.github/workflows/ci.yml VERBOSE=1

# ワークフローの検証のみを実行
make actions-validate WORKFLOW=.github/workflows/ci.yml

# ドライランを実行
make actions-dry-run WORKFLOW=.github/workflows/ci.yml

# 非対話モードで最初のワークフローを自動選択
INDEX=1 make actions
```

### Docker 関連コマンド

| コマンド | 説明 |
|---------|------|
| `make build` | 全Dockerイメージをビルド |
| `make build-actions` | Actions Simulatorイメージのみをビルド |
| `make start` | MCPサービスを起動 |
| `make stop` | サービスを停止 |
| `make logs` | ログを表示 |
| `make clean` | コンテナとイメージをクリーンアップ |

### テスト関連コマンド

| コマンド | 説明 |
|---------|------|
| `make test` | 統合テストを実行 |
| `make test-all` | 全テストスイートを実行 |
| `make test-bats` | Batsテストスイートを実行 |
| `make test-hangup` | ハングアップシナリオテストを実行 |

### セキュリティ・品質関連コマンド

| コマンド | 説明 |
|---------|------|
| `make security` | セキュリティスキャンを実行 |
| `make lint` | MegaLinterを実行 |
| `make sbom` | SBOM（Software Bill of Materials）を生成 |
| `make audit-deps` | 依存関係監査を実行 |

### バージョン・リリース関連コマンド

| コマンド | 説明 |
|---------|------|
| `make version` | 現在のバージョンを表示 |
| `make version-sync` | バージョン情報を同期 |
| `make release-check` | リリース準備状況をチェック |

## 配布スクリプト

### `./scripts/run-actions.sh`

ワンショット実行用の配布スクリプトです。依存関係の自動チェックと環境セットアップを行います。

#### 構文
```bash
./scripts/run-actions.sh [options] [workflow-file] [-- <additional-cli-args>]
```

#### オプション

| オプション | 説明 |
|-----------|------|
| `--help`, `-h` | ヘルプを表示 |
| `--check-deps` | 依存関係のみをチェック（実行はしない） |
| `--non-interactive` | 非対話モード（CI/CD環境用） |
| `--timeout=<秒数>` | actのタイムアウト時間を設定 |
| `--act-timeout=<秒数>` | 同上 |

#### 環境変数

| 環境変数 | 説明 | 例 |
|---------|------|-----|
| `NON_INTERACTIVE` | 非対話モードを有効化 | `NON_INTERACTIVE=1` |
| `INDEX` | ワークフロー選択を自動化 | `INDEX=1` |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | タイムアウト設定 | `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=300` |

#### 使用例

```bash
# 対話的にワークフローを選択
./scripts/run-actions.sh

# 特定のワークフローを実行
./scripts/run-actions.sh .github/workflows/ci.yml

# 依存関係のみをチェック
./scripts/run-actions.sh --check-deps

# 非対話モードで実行
NON_INTERACTIVE=1 ./scripts/run-actions.sh

# 最初のワークフローを自動選択
INDEX=1 ./scripts/run-actions.sh

# タイムアウトを設定して実行
./scripts/run-actions.sh --timeout=600 .github/workflows/ci.yml

# 追加のCLI引数を渡す
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --verbose
```

## 環境変数

### 共通環境変数

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `ACTIONS_SIMULATOR_VERBOSE` | 詳細ログを有効化 | `false` |
| `ACTIONS_SIMULATOR_DEBUG` | デバッグモードを有効化 | `false` |
| `ACTIONS_SIMULATOR_ENGINE` | 実行エンジンを指定 (act/mock) | `act` |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | actのタイムアウト時間（秒） | `300` |

### Docker関連環境変数

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `DOCKER_HOST` | Docker デーモンのホスト | `unix:///var/run/docker.sock` |
| `ACT_PLATFORM` | actで使用するプラットフォーム | `ubuntu-latest=catthehacker/ubuntu:act-latest` |
| `ACT_LOG_LEVEL` | actのログレベル | `info` |

### CI/CD環境変数

| 環境変数 | 説明 |
|---------|------|
| `CI` | CI環境であることを示す |
| `GITHUB_ACTIONS` | GitHub Actions環境であることを示す |
| `NON_INTERACTIVE` | 非対話モードを有効化 |

## 使用例

### 基本的なワークフロー実行

```bash
# 最もシンプルな実行方法
make actions

# 特定のワークフローを直接実行
python main.py actions simulate .github/workflows/ci.yml

# 配布スクリプトを使用
./scripts/run-actions.sh .github/workflows/ci.yml
```

### 詳細な診断とデバッグ

```bash
# システム診断を実行
python -m services.actions.main diagnose --include-performance --include-trace

# 診断付きでワークフローを実行
python -m services.actions.main --verbose simulate .github/workflows/ci.yml --diagnose --enhanced

# デバッグバンドルを作成
python -m services.actions.main create-debug-bundle --include-logs --include-config
```

### CI/CD環境での使用

```bash
# 非対話モードで実行
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 特定のジョブのみを実行
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test

# タイムアウトを設定
ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=600 make actions-auto
```

### 開発・テスト環境での使用

```bash
# ドライランで実行計画を確認
python -m services.actions.main simulate .github/workflows/ci.yml --dry-run

# 環境変数を設定して実行
python -m services.actions.main simulate .github/workflows/ci.yml --env NODE_ENV=development --env DEBUG=true

# パフォーマンス監視を有効化
python -m services.actions.main simulate .github/workflows/ci.yml --show-performance-metrics --show-execution-trace
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. Docker関連の問題

```bash
# Docker サービスが起動していない
sudo systemctl start docker  # Linux
# または Docker Desktop を起動  # macOS/Windows

# Docker 権限の問題
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. 依存関係の問題

```bash
# 依存関係をチェック
./scripts/run-actions.sh --check-deps

# 自動診断を実行
python -m services.actions.main diagnose
```

#### 3. ワークフロー実行の問題

```bash
# ワークフローの構文をチェック
python -m services.actions.main validate .github/workflows/ci.yml --strict

# ドライランで問題を特定
python -m services.actions.main simulate .github/workflows/ci.yml --dry-run --verbose
```

#### 4. パフォーマンスの問題

```bash
# パフォーマンス分析を実行
python -m services.actions.main diagnose --include-performance

# タイムアウトを調整
ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=900 make actions-run WORKFLOW=.github/workflows/ci.yml
```

### ログとデバッグ情報

#### ログファイルの場所

- エラーログ: `logs/error.log`
- 診断ログ: `logs/diagnostic.log`
- 実行ログ: `output/actions/`

#### デバッグバンドルの作成

```bash
# 自動的にデバッグバンドルを作成
python -m services.actions.main simulate .github/workflows/ci.yml --create-debug-bundle

# 手動でデバッグバンドルを作成
python -m services.actions.main create-debug-bundle --output-dir /tmp/debug
```

### サポート情報

詳細なトラブルシューティング情報については、以下のドキュメントを参照してください：

- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 一般的なトラブルシューティング
- [docs/actions/FAQ.md](./actions/FAQ.md) - よくある質問
- [HANGUP_TROUBLESHOOTING.md](./HANGUP_TROUBLESHOOTING.md) - ハングアップ問題の解決

## 関連ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [docs/actions/USER_GUIDE.md](./actions/USER_GUIDE.md) - ユーザーガイド
- [docs/actions/README.md](./actions/README.md) - Actions Simulator 詳細
- [CONTAINER_SETUP.md](./CONTAINER_SETUP.md) - Docker環境セットアップ
