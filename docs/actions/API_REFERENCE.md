# GitHub Actions Simulator - API リファレンス

## 概要

このドキュメントでは、GitHub Actions Simulator の全APIエンドポイント、CLIコマンド、および設定オプションについて詳細に説明します。

## 目次

- [CLI API](#cli-api)
- [Python API](#python-api)
- [HTTP API](#http-api)
- [設定ファイル](#設定ファイル)
- [環境変数](#環境変数)
- [エラーコード](#エラーコード)

## CLI API

### メインエントリーポイント

#### `main.py`

```bash
python main.py <service> [options]
```

**パラメーター:**

| パラメーター | 型 | 必須 | 説明 | デフォルト |
|-------------|----|----|------|-----------|
| `service` | string | ✅ | 起動するサービス (`github`, `datetime`, `actions`) | - |
| `--version` | flag | ❌ | バージョン情報を表示 | false |

**戻り値:**
- 成功時: 0
- エラー時: 1-255

**例:**
```bash
python main.py actions simulate .github/workflows/ci.yml
python main.py --version
```

### Actions Simulator CLI

#### グローバルオプション

```bash
python -m services.actions.main [global-options] <command> [command-options]
```

**グローバルオプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--verbose`, `-v` | boolean | false | 詳細ログを有効化 |
| `--quiet`, `-q` | boolean | false | 最小限の出力 |
| `--debug` | boolean | false | デバッグログを有効化 |
| `--config` | path | `actions.toml` | 設定ファイルのパス |
| `--help`, `-h` | flag | - | ヘルプを表示 |
| `--version` | flag | - | バージョン情報を表示 |

#### `simulate` コマンド

ワークフローファイルを実行します。

```bash
python -m services.actions.main simulate [options] <workflow-file>
```

**パラメーター:**

| パラメーター | 型 | 必須 | 説明 |
|-------------|----|----|------|
| `workflow-file` | path | ✅ | 実行するワークフローファイル |

**オプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--job` | string | null | 実行する特定のジョブID |
| `--dry-run` | boolean | false | 実行計画のみを表示 |
| `--env-file` | path | null | 環境変数ファイル |
| `--env` | key=value | [] | 環境変数（複数指定可能） |
| `--diagnose` | boolean | false | 実行前にシステム診断 |
| `--enhanced` | boolean | false | 拡張機能を有効化 |
| `--show-performance-metrics` | boolean | false | パフォーマンス情報を表示 |
| `--show-execution-trace` | boolean | false | 実行トレースを表示 |
| `--create-debug-bundle` | boolean | false | エラー時にデバッグバンドル作成 |
| `--debug-bundle-dir` | path | `output/debug-bundles` | デバッグバンドル出力先 |

**戻り値:**
- 成功時: 0
- ワークフローエラー: 1
- システムエラー: 2

**例:**
```bash
# 基本実行
python -m services.actions.main simulate .github/workflows/ci.yml

# 特定ジョブの実行
python -m services.actions.main simulate .github/workflows/ci.yml --job test

# 環境変数付き実行
python -m services.actions.main simulate .github/workflows/ci.yml --env NODE_ENV=test --env DEBUG=true

# 詳細診断付き実行
python -m services.actions.main --verbose simulate .github/workflows/ci.yml --diagnose --enhanced
```

#### `validate` コマンド

ワークフローファイルの構文を検証します。

```bash
python -m services.actions.main validate [options] <workflow-file-or-directory>
```

**パラメーター:**

| パラメーター | 型 | 必須 | 説明 |
|-------------|----|----|------|
| `workflow-file-or-directory` | path | ✅ | 検証するファイルまたはディレクトリ |

**オプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--strict` | boolean | false | 厳密な検証を実行 |

**戻り値:**
- 成功時: 0
- 検証エラー: 1

**例:**
```bash
# 単一ファイルの検証
python -m services.actions.main validate .github/workflows/ci.yml

# ディレクトリ全体の検証
python -m services.actions.main validate .github/workflows/

# 厳密な検証
python -m services.actions.main validate --strict .github/workflows/ci.yml
```

#### `list-jobs` コマンド

ワークフローファイル内のジョブ一覧を表示します。

```bash
python -m services.actions.main list-jobs [options] <workflow-file>
```

**パラメーター:**

| パラメーター | 型 | 必須 | 説明 |
|-------------|----|----|------|
| `workflow-file` | path | ✅ | 対象のワークフローファイル |

**オプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--format` | enum | `table` | 出力形式 (`table`, `json`) |

**戻り値:**
- 成功時: 0
- エラー時: 1

**例:**
```bash
# テーブル形式で表示
python -m services.actions.main list-jobs .github/workflows/ci.yml

# JSON形式で表示
python -m services.actions.main list-jobs --format json .github/workflows/ci.yml
```

#### `diagnose` コマンド

システムのヘルスチェックを実行します。

```bash
python -m services.actions.main diagnose [options]
```

**オプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--format` | enum | `table` | 出力形式 (`table`, `json`) |
| `--output` | path | null | 結果をファイルに保存 |
| `--include-performance` | boolean | false | パフォーマンス分析を含める |
| `--include-trace` | boolean | false | トレース分析を含める |

**戻り値:**
- 正常時: 0
- 警告あり: 2
- エラーあり: 1

**例:**
```bash
# 基本診断
python -m services.actions.main diagnose

# 詳細診断（JSON出力）
python -m services.actions.main diagnose --format json --include-performance --include-trace

# ファイル出力
python -m services.actions.main diagnose --output diagnostic-report.json
```

#### `create-debug-bundle` コマンド

デバッグバンドルを作成します。

```bash
python -m services.actions.main create-debug-bundle [options]
```

**オプション:**

| オプション | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--output-dir` | path | `output/debug-bundles` | 出力ディレクトリ |
| `--include-logs` | boolean | true | ログファイルを含める |
| `--include-config` | boolean | true | 設定ファイルを含める |

**戻り値:**
- 成功時: 0
- エラー時: 1

**例:**
```bash
# デバッグバンドル作成
python -m services.actions.main create-debug-bundle

# 出力先指定
python -m services.actions.main create-debug-bundle --output-dir /tmp/debug
```

### Make コマンド API

#### Actions 関連コマンド

| コマンド | パラメーター | 説明 |
|---------|-------------|------|
| `make actions` | `INDEX`, `WORKFLOW`, `JOB`, `VERBOSE` | インタラクティブ実行 |
| `make actions-auto` | - | デフォルトワークフロー自動実行 |
| `make actions-list` | - | ワークフロー一覧表示 |
| `make actions-run` | `WORKFLOW` (必須), `JOB`, `VERBOSE` | 指定ワークフロー実行 |
| `make actions-validate` | `WORKFLOW` | ワークフロー検証 |
| `make actions-dry-run` | `WORKFLOW` (必須), `VERBOSE` | ドライラン実行 |

**パラメーター詳細:**

| パラメーター | 型 | 説明 | 例 |
|-------------|----|----|-----|
| `WORKFLOW` | path | ワークフローファイルパス | `WORKFLOW=.github/workflows/ci.yml` |
| `JOB` | string | 実行するジョブID | `JOB=test` |
| `VERBOSE` | boolean | 詳細ログ有効化 | `VERBOSE=1` |
| `INDEX` | integer | ワークフロー選択番号 | `INDEX=1` |

**例:**
```bash
# インタラクティブ実行
make actions

# 特定ワークフロー実行
make actions-run WORKFLOW=.github/workflows/ci.yml

# 特定ジョブ実行
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test VERBOSE=1

# 自動選択実行
INDEX=1 make actions
```

> `make actions-run` ファミリーは Phase1 の `act` ブリッジモードを既定で使用します。ブリッジが未対応の機能では自動的に従来実装にフォールバックし、ログで警告します。

### 配布スクリプト API

#### `run-actions.sh`

```bash
./scripts/run-actions.sh [options] [workflow-file] [-- <additional-args>]
```

**オプション:**

| オプション | 型 | 説明 |
|-----------|----|----|
| `--help`, `-h` | flag | ヘルプを表示 |
| `--check-deps` | flag | 依存関係チェックのみ |
| `--non-interactive` | flag | 非対話モード |
| `--timeout=<seconds>` | integer | タイムアウト設定 |
| `--act-timeout=<seconds>` | integer | actタイムアウト設定 |

**環境変数:**

| 環境変数 | 型 | 説明 |
|---------|----|----|
| `NON_INTERACTIVE` | boolean | 非対話モード有効化 |
| `INDEX` | integer | ワークフロー自動選択 |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | integer | タイムアウト時間（秒） |

**戻り値:**
- 成功時: 0
- 依存関係エラー: 2
- 権限エラー: 126
- コマンド未発見: 127
- 中断: 130

**例:**
```bash
# 対話的実行
./scripts/run-actions.sh

# 非対話モード
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# 依存関係チェック
./scripts/run-actions.sh --check-deps

# タイムアウト設定
./scripts/run-actions.sh --timeout=600 .github/workflows/ci.yml
```

## Python API

### SimulationService クラス

```python
from services.actions.service import SimulationService, SimulationParameters

service = SimulationService()
```

#### `run_simulation` メソッド

```python
def run_simulation(
    self,
    params: SimulationParameters,
    logger: ActionsLogger | None = None,
    capture_output: bool = False
) -> SimulationResult
```

**パラメーター:**

| パラメーター | 型 | 必須 | 説明 |
|-------------|----|----|------|
| `params` | SimulationParameters | ✅ | シミュレーションパラメーター |
| `logger` | ActionsLogger | ❌ | ロガーインスタンス |
| `capture_output` | bool | ❌ | 出力をキャプチャするか |

**戻り値:** `SimulationResult`

### SimulationParameters クラス

```python
@dataclass
class SimulationParameters:
    workflow_file: Path
    job: str | None = None
    dry_run: bool = False
    env_file: Path | None = None
    verbose: bool = False
    env_vars: Dict[str, str] | None = None
```

### SimulationResult クラス

```python
@dataclass
class SimulationResult:
    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    detailed_result: DetailedSimulationResult | None = None
```

### DiagnosticService クラス

```python
from services.actions.diagnostic import DiagnosticService

service = DiagnosticService(logger=logger)
```

#### `run_comprehensive_health_check` メソッド

```python
def run_comprehensive_health_check(self) -> HealthCheckReport
```

**戻り値:** `HealthCheckReport`

#### `identify_hangup_causes` メソッド

```python
def identify_hangup_causes(self) -> List[str]
```

**戻り値:** `List[str]` - ハングアップの潜在的原因リスト

### 使用例

```python
from pathlib import Path
from services.actions.service import SimulationService, SimulationParameters
from services.actions.logger import ActionsLogger

# ロガーの初期化
logger = ActionsLogger(verbose=True)

# サービスの初期化
service = SimulationService()

# パラメーターの設定
params = SimulationParameters(
    workflow_file=Path(".github/workflows/ci.yml"),
    job="test",
    env_vars={"NODE_ENV": "test", "DEBUG": "true"}
)

# シミュレーション実行
result = service.run_simulation(params, logger=logger, capture_output=True)

if result.success:
    print("シミュレーション成功")
    print(result.stdout)
else:
    print("シミュレーション失敗")
    print(result.stderr)
```

## HTTP API

### サーバーモード

Actions Simulator はHTTPサーバーモードでも動作可能です。

#### 起動方法

```bash
# サーバーモード起動
make actions-server

# または直接起動
python -m services.actions.main server --host 0.0.0.0 --port 8000
```

#### エンドポイント

##### `GET /health`

ヘルスチェックエンドポイント

**レスポンス:**
```json
{
  "status": "ok",
  "version": "1.2.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

##### `POST /simulate`

ワークフローシミュレーション実行

**リクエスト:**
```json
{
  "workflow_file": ".github/workflows/ci.yml",
  "job": "test",
  "env_vars": {
    "NODE_ENV": "test"
  },
  "dry_run": false
}
```

**レスポンス:**
```json
{
  "success": true,
  "return_code": 0,
  "stdout": "...",
  "stderr": "",
  "execution_time_ms": 1234.5
}
```

##### `POST /validate`

ワークフロー検証

**リクエスト:**
```json
{
  "workflow_file": ".github/workflows/ci.yml",
  "strict": true
}
```

**レスポンス:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

##### `GET /diagnose`

システム診断

**レスポンス:**
```json
{
  "overall_status": "OK",
  "summary": "All systems operational",
  "results": [
    {
      "component": "Docker",
      "status": "OK",
      "message": "Docker is running",
      "recommendations": []
    }
  ]
}
```

## 設定ファイル

### `actions.toml`

Actions Simulator の設定ファイル（TOML形式）

```toml
[simulator]
# 基本設定
engine = "act"  # "act" または "mock"
timeout_seconds = 300
verbose = false
debug = false

[docker]
# Docker設定
platform = "ubuntu-latest=catthehacker/ubuntu:act-latest"
socket_path = "/var/run/docker.sock"
network_name = "actions-simulator"

[act]
# act固有設定
log_level = "info"
use_gitignore = true
reuse_containers = false
pull_images = true

[output]
# 出力設定
directory = "output/actions"
format = "json"
include_logs = true
include_artifacts = false

[diagnostics]
# 診断設定
enable_performance_monitoring = false
enable_hangup_detection = true
auto_create_debug_bundle = false

[environment]
# 環境変数設定
default_env_file = ".env"
preserve_env = ["PATH", "HOME", "USER"]
```

### 設定項目詳細

| セクション | キー | 型 | デフォルト | 説明 |
|-----------|-----|----|---------|----|
| `simulator` | `engine` | string | `"act"` | 実行エンジン |
| `simulator` | `timeout_seconds` | integer | `300` | タイムアウト時間 |
| `simulator` | `verbose` | boolean | `false` | 詳細ログ |
| `docker` | `platform` | string | `"ubuntu-latest=..."` | Dockerプラットフォーム |
| `docker` | `socket_path` | string | `"/var/run/docker.sock"` | Dockerソケットパス |
| `act` | `log_level` | string | `"info"` | actのログレベル |
| `act` | `reuse_containers` | boolean | `false` | コンテナ再利用 |
| `output` | `directory` | string | `"output/actions"` | 出力ディレクトリ |
| `output` | `format` | string | `"json"` | 出力形式 |

## 環境変数

### システム環境変数

| 環境変数 | 型 | デフォルト | 説明 |
|---------|----|---------|----|
| `ACTIONS_SIMULATOR_VERBOSE` | boolean | `false` | 詳細ログ有効化 |
| `ACTIONS_SIMULATOR_DEBUG` | boolean | `false` | デバッグモード有効化 |
| `ACTIONS_SIMULATOR_ENGINE` | string | `"act"` | 実行エンジン選択 |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | integer | `300` | actタイムアウト |
| `ACTIONS_SIMULATOR_CONFIG_PATH` | path | `"actions.toml"` | 設定ファイルパス |

### Docker関連環境変数

| 環境変数 | 型 | デフォルト | 説明 |
|---------|----|---------|----|
| `DOCKER_HOST` | string | `"unix:///var/run/docker.sock"` | Dockerホスト |
| `ACT_PLATFORM` | string | `"ubuntu-latest=..."` | actプラットフォーム |
| `ACT_LOG_LEVEL` | string | `"info"` | actログレベル |

### CI/CD環境変数

| 環境変数 | 型 | 説明 |
|---------|----|----|
| `CI` | boolean | CI環境フラグ |
| `GITHUB_ACTIONS` | boolean | GitHub Actions環境フラグ |
| `NON_INTERACTIVE` | boolean | 非対話モードフラグ |

## エラーコード

### 終了コード

| コード | 名前 | 説明 |
|-------|------|------|
| 0 | SUCCESS | 正常終了 |
| 1 | GENERAL_ERROR | 一般的なエラー |
| 2 | DEPENDENCY_ERROR | 依存関係エラー |
| 126 | PERMISSION_ERROR | 権限エラー |
| 127 | COMMAND_NOT_FOUND | コマンド未発見 |
| 130 | INTERRUPTED | 中断（Ctrl+C） |

### HTTP ステータスコード

| コード | 説明 |
|-------|------|
| 200 | 成功 |
| 400 | 不正なリクエスト |
| 404 | リソースが見つからない |
| 500 | 内部サーバーエラー |
| 503 | サービス利用不可 |

### エラーレスポンス形式

```json
{
  "error": {
    "code": "WORKFLOW_NOT_FOUND",
    "message": "指定されたワークフローファイルが見つかりません",
    "details": {
      "workflow_file": ".github/workflows/missing.yml"
    },
    "suggestions": [
      "ファイルパスを確認してください",
      "make actions-list でワークフロー一覧を確認してください"
    ]
  }
}
```

## 関連ドキュメント

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) - CLIリファレンス
- [COMMAND_USAGE_GUIDE.md](./COMMAND_USAGE_GUIDE.md) - コマンド使い分けガイド
- [docs/actions/USER_GUIDE.md](./actions/USER_GUIDE.md) - ユーザーガイド
