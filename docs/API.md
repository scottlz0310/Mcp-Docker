# API仕様書

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

## DateTime Validator

### 機能
- Markdownファイルの日付自動修正
- 監視対象: `~/workspace/*.md`

### 検出パターン
- `2025-01-XX` → 現在日付に修正
- `2024-12-XX` → 現在日付に修正

### バックアップ
修正前ファイルは `.bak_YYYYMMDD_HHMMSS` 形式で保存

## CodeQL

### 実行方法
```bash
make codeql
```

### 対象言語
- Python
- JavaScript/TypeScript
- Java
- C/C++

### 出力形式
- SARIF形式
- GitHub Security tab連携