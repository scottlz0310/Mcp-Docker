# API仕様書

## GitHub Actions Simulator CLI API

### 診断・トラブルシューティング API

#### システム診断

```bash
# 基本診断
uv run python main.py actions diagnose

# 詳細診断
uv run python main.py actions diagnose --include-performance --include-trace

# JSON出力
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json
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
        "docker_path": "/usr/bin/docker"
      },
      "recommendations": [],
      "timestamp": "2025-09-28T12:00:00Z"
    }
  ],
  "summary": "全6項目の診断を実行しました。正常: 5項目、警告: 1項目、エラー: 0項目",
  "potential_hangup_causes": [
    "Docker socket権限の問題",
    "メモリ不足による応答遅延"
  ]
}
```

#### ワークフロー実行 API

```bash
# 基本実行
uv run python main.py actions simulate <workflow_file>

# 診断付き実行
uv run python main.py actions simulate <workflow_file> --diagnose

# 強化機能付き実行
uv run python main.py actions simulate <workflow_file> --enhanced --auto-recovery

# デバッグバンドル作成
uv run python main.py actions simulate <workflow_file> --create-debug-bundle
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
  "engine": "builtin",
  "job": "test",
  "event": "push",
  "enable_diagnostics": true,
  "auto_recovery": true
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
      "message": "正常"
    }
  ],
  "performance_metrics": {
    "cpu_usage": 15.2,
    "memory_usage": 256.5,
    "docker_operations": 12
  }
}
```

## DateTime Validator

### 機能

- Markdownファイルの日付自動修正
- 監視対象: `~/workspace/*.md`

### 検出パターン

- `2025-01-XX` → 現在日付に修正
- `2024-12-XX` → 現在日付に修正

### バックアップ

修正前ファイルは `.bak_YYYYMMDD_HHMMSS` 形式で保存
