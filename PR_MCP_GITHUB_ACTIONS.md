# GitHub Actions ワークフローログ取得MCPサーバー

## 📋 概要

GitHub REST APIを使用してGitHub Actionsのワークフロー実行ログを取得する新しいMCPサーバーを実装しました。

**⚠️ 重要**: このブランチは `services/actions` (Actions Simulator) 削除計画完了後にマージすることを想定しています。

## 🎯 実装内容

### 新規ファイル

```
src/mcp_github_actions/
├── __init__.py           # パッケージ初期化
├── server.py             # MCPサーバー本体
├── github_api.py         # GitHub REST API クライアント
├── test_api.py           # テストスクリプト
└── README.md             # 使用方法ドキュメント

.mcp-github-actions.json  # MCP設定ファイル例
```

### 変更ファイル

- `pyproject.toml`
  - 依存関係追加: `mcp>=1.0.0`, `requests>=2.31.0`, `pydantic>=2.0.0`
  - コマンド追加: `mcp-github-actions`

## 🚀 提供機能

MCPツールとして以下の5つの機能を提供：

1. **`list_workflow_runs`** - ワークフロー実行一覧取得
   - ワークフローID、ブランチ、ステータスでフィルタリング可能

2. **`get_workflow_run`** - 特定のワークフロー実行情報取得
   - Run IDを指定して詳細情報を取得

3. **`get_workflow_run_logs`** - ワークフロー実行ログ取得
   - すべてのジョブのログを一括取得

4. **`list_workflow_jobs`** - ジョブ一覧取得
   - 各ジョブの実行状況を確認

5. **`get_latest_workflow_logs`** ⭐ **推奨**
   - 指定ワークフローの最新ログを即座に取得
   - 最も簡単な使用方法

## ✅ テスト結果

```bash
$ uv run python src/mcp_github_actions/test_api.py

============================================================
GitHub Actions API テスト
============================================================

1. APIクライアント初期化...
✅ APIクライアント初期化成功

2. ワークフロー実行一覧取得...
✅ 5 件のワークフロー実行を取得

最新の実行:
  - Run ID: 18515963008
  - Name: 🛡️ Quality Gates
  - Status: completed
  - Conclusion: success
  - Branch: main
  - Created: 2025-10-15 02:35:38+00:00

3. ジョブ一覧取得 (Run ID: 18515963008)...
✅ 8 件のジョブを取得

4. ログ取得 (Run ID: 18515963008)...
✅ 8 件のログファイルを取得

============================================================
✅ すべてのテスト成功
============================================================
```

## 💡 使用例

### MCPクライアントでの使用

Claude DesktopなどのMCPクライアントで以下のように質問：

```
MCPサーバーを使用して、scottlz0310/Mcp-Dockerリポジトリの
最新のActionsログを取得してみて
```

または具体的に：

```
get_latest_workflow_logsツールを使用して、
owner: scottlz0310
repo: Mcp-Docker
workflow_id: ci.yml
のログを取得してください
```

### コマンドラインでの使用

```bash
# 依存関係インストール
uv sync

# MCPサーバー起動
uv run mcp-github-actions

# テスト実行
export GITHUB_TOKEN="your_token_here"
uv run python src/mcp_github_actions/test_api.py
```

## 🔧 セットアップ

### 1. GitHub Personal Access Token

必要な権限：
- `repo` - リポジトリへのアクセス
- `actions:read` - GitHub Actionsへの読み取りアクセス

### 2. MCP設定（Claude Desktopなど）

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

## 📦 依存関係

新規追加：
- `mcp>=1.0.0` - Model Context Protocol SDK
- `requests>=2.31.0` - HTTP クライアント
- `pydantic>=2.0.0` - データバリデーション

## 🔒 セキュリティ

- GitHub Personal Access Tokenは環境変数で管理
- 読み取り専用アクセスのみ使用
- ログは必要に応じてファイルに保存可能

## 🎨 特徴

- ✅ **独立実装**: `services/actions` とは完全に独立
- ✅ **シンプル**: 5つの明確なツール
- ✅ **テスト済み**: 動作確認完了
- ✅ **ドキュメント完備**: README.md 付属
- ✅ **型安全**: Pydantic モデル使用

## 📝 マージ計画

### タイミング

**以下の条件が満たされた後にマージ**：

1. ✅ `services/actions` (Actions Simulator) 削除計画の完了
2. ✅ 関連する依存関係の整理
3. ✅ ドキュメントの更新

### マージ手順

```bash
# 1. mainブランチを最新化
git checkout main
git pull origin main

# 2. フィーチャーブランチをリベース
git checkout feature/mcp-github-actions-logs
git rebase main

# 3. 競合があれば解決

# 4. プルリクエスト作成
# GitHub UIで Draft → Ready for review に変更

# 5. レビュー・承認後マージ
```

## 🔍 レビューポイント

- [ ] コード品質（型チェック、リント）
- [ ] テストカバレッジ
- [ ] ドキュメントの完全性
- [ ] セキュリティ（トークン管理）
- [ ] `services/actions` との競合がないこと

## 📚 参考資料

- [GitHub Actions API Documentation](https://docs.github.com/en/rest/actions)
- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [プロジェクトREADME](src/mcp_github_actions/README.md)

## 👥 レビュワー

@scottlz0310

---

**Status**: 🚧 Draft - Actions Simulator 削除待ち
