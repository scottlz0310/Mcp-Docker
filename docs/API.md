# API仕様書

> **注意**: このドキュメントは簡易版です。完全なAPIリファレンスについては以下をご参照ください：
> - [CLI_REFERENCE.md](./CLI_REFERENCE.md) - 完全なCLIリファレンス
> - [API_REFERENCE.md](./API_REFERENCE.md) - 詳細なAPIドキュメント
> - [COMMAND_USAGE_GUIDE.md](./COMMAND_USAGE_GUIDE.md) - コマンド使い分けガイド

## GitHub Actions Simulator CLI API

### 診断・トラブルシューティング API

#### システム診断

```bash
# 包括的システム診断
uv run python main.py actions diagnose

# 詳細診断（パフォーマンス分析・実行トレース含む）
uv run python main.py actions diagnose --include-performance --include-trace

# JSON形式での診断結果出力
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json

# デバッグバンドル作成付き診断
uv run python main.py actions diagnose --create-debug-bundle --debug-bundle-dir ./debug_output

# 詳細ログ付き診断
uv run python main.py actions diagnose --verbose
```

#### 診断結果の構造

```json
{
  "overall_status": "OK|WARNING|ERROR",
  "results": [
    {
      "component": "Docker接続性",
      "status": "OK",
      "message": "Docker接続は正常です",
      "details": {
        "version": "Docker version 24.0.0",
        "docker_path": "/usr/bin/docker",
        "socket_accessible": true,
        "daemon_responsive": true
      },
      "recommendations": [],
      "timestamp": "2025-09-28T12:00:00Z"
    },
    {
      "component": "actバイナリ",
      "status": "OK",
      "message": "actバイナリは正常に動作しています",
      "details": {
        "version": "act version 0.2.50",
        "path": "/usr/local/bin/act",
        "executable": true
      },
      "recommendations": [],
      "timestamp": "2025-09-28T12:00:00Z"
    }
  ],
  "summary": "全7項目の診断を実行しました。正常: 6項目、警告: 1項目、エラー: 0項目",
  "potential_hangup_causes": [
    "Docker socket権限の問題",
    "メモリ不足による応答遅延"
  ],
  "performance_metrics": {
    "cpu_usage_percent": 15.2,
    "memory_usage_mb": 256.5,
    "disk_io_mb": 12.3,
    "docker_response_time_ms": 150.2
  },
  "execution_trace": {
    "total_stages": 5,
    "completed_stages": 5,
    "failed_stages": 0,
    "total_execution_time_seconds": 2.3
  }
}
```

#### ワークフロー実行 API

```bash
# 基本実行
uv run python main.py actions simulate <workflow_file>

# 事前診断付き実行
uv run python main.py actions simulate <workflow_file> --diagnose

# 強化されたプロセス監視とデッドロック検出
uv run python main.py actions simulate <workflow_file> --enhanced

# 自動復旧機能付き実行
uv run python main.py actions simulate <workflow_file> --enhanced --auto-recovery

# デバッグバンドル自動作成
uv run python main.py actions simulate <workflow_file> --create-debug-bundle

# パフォーマンス監視付き実行
uv run python main.py actions simulate <workflow_file> --show-performance-metrics

# 実行トレース表示付き実行
uv run python main.py actions simulate <workflow_file> --show-execution-trace

# 包括的機能を有効化した実行
uv run python main.py actions simulate <workflow_file> \
  --enhanced --diagnose --auto-recovery --create-debug-bundle \
  --show-performance-metrics --show-execution-trace
```

## GitHub MCP Server

### エンドポイント

- **ベースURL**: `http://localhost:8080`
- **プロトコル**: HTTP/JSON-RPC 2.0

### 認証

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
```

### 利用可能なツール

#### 1. リポジトリ情報取得

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_repository",
    "arguments": {
      "owner": "username",
      "repo": "repository-name"
    }
  }
}
```

#### 2. Issue一覧取得

```json
{
  "method": "tools/call",
  "params": {
    "name": "list_issues",
    "arguments": {
      "owner": "username",
      "repo": "repository-name",
      "state": "open"
    }
  }
}
```

## Actions Simulator API (REST)

### エンドポイント

- **ベースURL**: `http://localhost:8000`
- **プロトコル**: HTTP/REST

### 利用可能なエンドポイント

#### ヘルスチェック

```bash
GET /actions/healthz
```

レスポンス:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-28T12:00:00Z",
  "version": "1.0.1"
}
```

#### ワークフローシミュレーション

```bash
POST /actions/simulate
Content-Type: application/json

{
  "workflow_file": ".github/workflows/ci.yml",
  "engine": "enhanced",
  "job": "test",
  "event": "push",
  "enable_diagnostics": true,
  "auto_recovery": true,
  "create_debug_bundle": true,
  "show_performance_metrics": true,
  "show_execution_trace": true
}
```

レスポンス:
```json
{
  "success": true,
  "execution_time": 45.2,
  "exit_code": 0,
  "output": "ワークフロー実行結果...",
  "diagnostic_results": [
    {
      "component": "Docker接続性",
      "status": "OK",
      "message": "正常",
      "details": {
        "response_time_ms": 120.5
      }
    },
    {
      "component": "actバイナリ",
      "status": "OK",
      "message": "正常",
      "details": {
        "version": "0.2.50"
      }
    }
  ],
  "performance_metrics": {
    "cpu_usage_percent": 15.2,
    "memory_usage_mb": 256.5,
    "disk_io_mb": 12.3,
    "docker_operations": 12,
    "docker_response_time_ms": 150.2,
    "bottlenecks": [
      {
        "component": "Docker Image Pull",
        "time_seconds": 23.4,
        "percentage": 51.1
      }
    ]
  },
  "execution_trace": {
    "stages": [
      {
        "name": "Workflow Parsing",
        "start_time": "2025-09-28T12:00:00Z",
        "end_time": "2025-09-28T12:00:02Z",
        "status": "COMPLETED",
        "duration_seconds": 2.1
      },
      {
        "name": "Docker Setup",
        "start_time": "2025-09-28T12:00:02Z",
        "end_time": "2025-09-28T12:00:25Z",
        "status": "COMPLETED",
        "duration_seconds": 23.4
      }
    ],
    "total_stages": 5,
    "completed_stages": 5
  },
  "recovery_statistics": {
    "total_recovery_attempts": 2,
    "successful_recoveries": 2,
    "recovery_types": {
      "docker_reconnections": 1,
      "buffer_clears": 1
    }
  },
  "debug_bundle_path": "/tmp/debug_bundle_20250928_120000.tar.gz"
}
```

## DateTime Validator

### 機能

- Markdownファイルの日付自動修正
- 監視対象: `~/workspace/*.md`

### 検出パターン

- `2025-10-XX` → 現在日付に修正
- `2024-12-XX` → 現在日付に修正

### バックアップ

修正前ファイルは `.bak_YYYYMMDD_HHMMSS` 形式で保存
