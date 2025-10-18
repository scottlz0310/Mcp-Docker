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
# GitHub Actions Simulatorを実行（ワークフロー指定）
mcp-docker actions .github/workflows/ci.yml

# 対話的にワークフローを選択
mcp-docker actions

# 依存関係チェック
mcp-docker actions --check-deps

# バージョン確認
mcp-docker --version
```

## uvxで直接実行（インストール不要）

```bash
# インストールせずに直接実行
uvx --from git+https://github.com/scottlz0310/mcp-docker.git mcp-docker actions .github/workflows/ci.yml

# バージョン確認
uvx --from git+https://github.com/scottlz0310/mcp-docker.git mcp-docker --version
```

## 利用可能なコマンド

### actions サブコマンド

```bash
# ワークフローシミュレーション
mcp-docker actions <workflow-file>

# 対話的にワークフローを選択
mcp-docker actions

# 依存関係チェック
mcp-docker actions --check-deps

# 拡張依存関係チェック
mcp-docker actions --check-deps-extended

# 非対話モード
mcp-docker actions --non-interactive <workflow-file>

# タイムアウト設定
mcp-docker actions --timeout=60 <workflow-file>

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
mcp-docker actions .github/workflows/test.yml
```

### プロジェクトBでの使用（uvx）

```bash
cd /path/to/project-b

# インストール不要で直接実行
uvx --from git+https://github.com/scottlz0310/mcp-docker.git \
  mcp-docker actions .github/workflows/deploy.yml
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

- **Docker環境が必須**: Docker 20.10+ と Docker Compose 2.0+ が必要です
- **Python 3.13+が必要**: uv tool install時に自動的にインストールされます
- **Gitリポジトリ内で実行**: `mcp-docker actions`はGitリポジトリのルートディレクトリで実行する必要があります
- **初回実行時**: Docker イメージのビルドまたはプルが必要です（`docker compose build actions-simulator`）

### 重要な注意事項

`uv tool install`でインストールした場合、以下の準備が必要です:

1. **Docker環境のセットアップ**: Docker と Docker Compose をインストール
2. **プロジェクトのクローン**: MCP Dockerリポジトリをクローン（初回のみ）
3. **イメージのビルド**: `docker compose build actions-simulator`を実行

または、プロジェクトをクローンして直接使用することを推奨します:

```bash
# 推奨: プロジェクトをクローンして使用
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker
uv sync
./scripts/run-actions.sh .github/workflows/basic-test.yml
```

## 関連ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [Actions Simulator ドキュメント](./actions/) - 詳細な使用方法
- [インストールガイド](./actions/INSTALLATION.md) - 完全なセットアップ手順
