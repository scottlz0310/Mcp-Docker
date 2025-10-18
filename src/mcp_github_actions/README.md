# GitHub Actions MCP Server

GitHub REST APIを使用してGitHub Actionsのワークフロー実行ログを取得するMCPサーバーです。

## 機能

- ワークフロー実行一覧の取得
- 特定のワークフロー実行の詳細取得
- ワークフロー実行ログの取得
- ジョブ一覧の取得
- 最新のワークフローログの取得（最も簡単な方法）

## セットアップ

### 1. 依存関係のインストール

```bash
# プロジェクトルートで実行
uv sync
```

### 2. GitHub Personal Access Tokenの設定

GitHub Personal Access Tokenを取得し、環境変数に設定します：

```bash
export GITHUB_TOKEN="your_github_token_here"
# または
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token_here"
```

必要な権限：
- `repo`: リポジトリへのアクセス
- `actions:read`: GitHub Actionsへの読み取りアクセス

### 3. MCPクライアントでの設定

Claude DesktopなどのMCPクライアントの設定ファイルに追加：

```json
{
  "mcpServers": {
    "github-actions": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/Mcp-Docker",
        "run",
        "mcp-github-actions"
      ],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

## 使用方法

MCPクライアント（Claude Desktopなど）を通じて以下のツールが利用可能です：

### 1. 最新のワークフローログを取得（推奨）

最も簡単な方法です：

```
MCPサーバーを使用して、scottlz0310/Mcp-Dockerリポジトリの
ci.ymlワークフローの最新ログを取得してください
```

ツール: `get_latest_workflow_logs`
パラメータ:
- `owner`: リポジトリオーナー（例: "scottlz0310"）
- `repo`: リポジトリ名（例: "Mcp-Docker"）
- `workflow_id`: ワークフローID（例: "ci.yml"）
- `branch`: ブランチ名（オプション）

### 2. ワークフロー実行一覧を取得

```
scottlz0310/Mcp-Dockerの最近のワークフロー実行を10件取得してください
```

ツール: `list_workflow_runs`
パラメータ:
- `owner`: リポジトリオーナー
- `repo`: リポジトリ名
- `workflow_id`: ワークフローID（オプション）
- `branch`: ブランチ名（オプション）
- `status`: ステータス（オプション: queued, in_progress, completed）
- `per_page`: 取得件数（デフォルト: 10）

### 3. 特定の実行IDのログを取得

```
run_id 12345678のログを取得してください
```

ツール: `get_workflow_run_logs`
パラメータ:
- `owner`: リポジトリオーナー
- `repo`: リポジトリ名
- `run_id`: ワークフロー実行ID

### 4. ジョブ一覧を取得

```
run_id 12345678のジョブ一覧を取得してください
```

ツール: `list_workflow_jobs`
パラメータ:
- `owner`: リポジトリオーナー
- `repo`: リポジトリ名
- `run_id`: ワークフロー実行ID

## 開発

### テスト実行

```bash
# 単体テストの実行（予定）
uv run pytest tests/unit/test_mcp_github_actions.py

# MCPサーバーをローカルで起動してテスト
uv run mcp-github-actions
```

### デバッグ

ログレベルを設定してデバッグ情報を表示：

```bash
export LOG_LEVEL=DEBUG
uv run mcp-github-actions
```

## トラブルシューティング

### 認証エラー

```
GitHub API エラー: 401 - Bad credentials
```

**解決策**: GitHub Personal Access Tokenが正しく設定されているか確認してください。

### リポジトリが見つからない

```
GitHub API エラー: 404 - Not Found
```

**解決策**:
- リポジトリオーナーとリポジトリ名が正しいか確認
- トークンに適切な権限があるか確認

### ログが取得できない

**原因**: ワークフローが実行中または失敗している場合、ログが利用できないことがあります。

**解決策**: `list_workflow_runs`でステータスを確認してください。

## ライセンス

MIT License
