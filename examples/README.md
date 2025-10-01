# Mcp-Docker 使用例

このディレクトリには、Mcp-Docker のサービスを他のプロジェクトで使用するための設定例が含まれています。

## 利用可能なサービス

| サービス | 用途 | 導入時間 |
|---------|------|---------|
| **[github-mcp](./github-mcp/)** | GitHub リポジトリの MCP サーバー | ~5分 |
| **[actions-simulator](./actions-simulator/)** | GitHub Actions のローカル実行 | ~5分 |
| **[datetime-validator](./datetime-validator/)** | ドキュメントの日付検証 | ~3分 |

## クイックスタート

### 1. サービスを選択

使いたいサービスのディレクトリを確認してください：

```bash
ls examples/
# github-mcp/  actions-simulator/  datetime-validator/
```

### 2. 設定ファイルをコピー

他のプロジェクトで使用したいサービスの設定をコピーします：

```bash
# 例: GitHub MCP サーバーを使用する場合
cd ~/my-project
cp -r ~/workspace/Mcp-Docker/examples/github-mcp ./mcp-server
cd mcp-server
```

### 3. 環境変数を設定

```bash
cp .env.example .env
vim .env  # 必要な値を設定
```

### 4. サービス起動

```bash
docker compose up -d
```

## 各サービスの詳細

各サービスのディレクトリには、詳細な使用方法を説明した `README.md` があります。

- **[GitHub MCP](./github-mcp/README.md)** - GitHub リポジトリの情報取得・操作
- **[Actions Simulator](./actions-simulator/README.md)** - CI/CD ワークフローのローカルテスト
- **[DateTime Validator](./datetime-validator/README.md)** - マークダウンファイルの日付形式チェック

## サポート

- 各サービスの設定については、該当ディレクトリの `README.md` を参照
- 問題が発生した場合は、[プロジェクトのトラブルシューティング](../docs/TROUBLESHOOTING.md) を確認
- より詳細なドキュメントは [docs/](../docs/) ディレクトリを参照
