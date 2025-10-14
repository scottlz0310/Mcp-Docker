# uv tool install ガイド

MCP Dockerを`uv tool`として他のプロジェクトで使用する方法を説明します。

## クイックスタート

### インストール

```bash
# GitHubから直接インストール
uv tool install git+https://github.com/scottlz0310/mcp-docker.git

# または、特定のバージョンをインストール
uv tool install git+https://github.com/scottlz0310/mcp-docker.git@v1.3.0
```

### 使用方法

```bash
# GitHub Actions Simulatorを実行
mcp-docker actions simulate .github/workflows/ci.yml

# CI互換性検証
mcp-docker actions verify-ci .github/workflows/basic-test.yml <run-id>

# バージョン確認
mcp-docker --version
```

## uvxで直接実行（インストール不要）

```bash
# インストールせずに直接実行
uvx --from git+https://github.com/scottlz0310/mcp-docker.git mcp-docker actions simulate .github/workflows/ci.yml

# 短縮形
uvx --from git+https://github.com/scottlz0310/mcp-docker.git mcp-docker --version
```

## 利用可能なコマンド

### actions サブコマンド

```bash
# ワークフローシミュレーション
mcp-docker actions simulate <workflow-file>

# 特定のジョブのみ実行
mcp-docker actions simulate <workflow-file> --job <job-name>

# CI互換性検証
mcp-docker actions verify-ci <workflow-file> <run-id>

# ヘルプ表示
mcp-docker actions --help
```

### その他のサブコマンド

```bash
# GitHub MCP Server（将来実装予定）
mcp-docker github

# バージョン情報
mcp-docker --version
```

## 他のプロジェクトでの使用例

### プロジェクトAでの使用

```bash
cd /path/to/project-a

# インストール（初回のみ）
uv tool install git+https://github.com/scottlz0310/mcp-docker.git

# ワークフローを実行
mcp-docker actions simulate .github/workflows/test.yml
```

### プロジェクトBでの使用（uvx）

```bash
cd /path/to/project-b

# インストール不要で直接実行
uvx --from git+https://github.com/scottlz0310/mcp-docker.git \
  mcp-docker actions simulate .github/workflows/deploy.yml
```

## アップグレード

```bash
# 最新版にアップグレード
uv tool upgrade mcp-docker

# または、再インストール
uv tool uninstall mcp-docker
uv tool install git+https://github.com/scottlz0310/mcp-docker.git
```

## アンインストール

```bash
uv tool uninstall mcp-docker
```

## トラブルシューティング

### インストールエラー

```bash
# キャッシュをクリアして再インストール
uv cache clean
uv tool install git+https://github.com/scottlz0310/mcp-docker.git
```

### コマンドが見つからない

```bash
# uvのツールパスを確認
uv tool list

# パスが通っているか確認
which mcp-docker

# パスを追加（必要に応じて）
export PATH="$HOME/.local/bin:$PATH"
```

## 制限事項

- Docker環境が必要です（Docker 20.10+）
- Python 3.13+が必要です
- actコマンドが必要です（GitHub Actions Simulator使用時）

## 関連ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [Actions Simulator ドキュメント](./actions/) - 詳細な使用方法
- [インストールガイド](./actions/INSTALLATION.md) - 完全なセットアップ手順
