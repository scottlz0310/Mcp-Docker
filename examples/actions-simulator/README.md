# Actions Simulator

GitHub Actions ワークフローをローカル環境で実行・テストするためのツールです。

## 概要

- **用途**: CI/CD ワークフローのローカルテスト、デバッグ
- **基盤**: nektos/act を使用
- **導入時間**: 約5分

## クイックスタート

### 1. ファイルをコピー

```bash
# 他のプロジェクトで使用する場合
cd ~/your-workflow-project
cp ~/workspace/Mcp-Docker/examples/actions-simulator/run-actions.sh .
chmod +x run-actions.sh
```

### 2. 環境変数を設定

```bash
# GitHub Token を設定（必要に応じて）
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### 3. ワークフローを実行

```bash
# デフォルトワークフローを実行
./run-actions.sh

# 特定のワークフローを実行
./run-actions.sh .github/workflows/ci.yml

# 特定のジョブのみ実行
./run-actions.sh .github/workflows/ci.yml test

# 特定のイベントでトリガー
./run-actions.sh .github/workflows/deploy.yml "" release
```

## Docker Compose での使用

### 1. 設定ファイルをコピー

```bash
cd ~/your-project
cp -r ~/workspace/Mcp-Docker/examples/actions-simulator ./actions
cd actions
```

### 2. 環境変数を設定

```bash
cp .env.example .env
vim .env
```

`.env` ファイルで以下を設定：

```bash
# 必須: GitHub Token（プライベートリポジトリや API アクセスが必要な場合）
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# オプション
ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest
ACT_TIMEOUT=600
LOG_LEVEL=info
DOCKER_HOST=unix:///var/run/docker.sock
```

### 3. Docker Compose で実行

```bash
# ワークフローを実行
docker compose run actions-simulator act
```

## 使用例

### 基本的な CI テスト

```bash
# プッシュイベントでの CI 実行
./run-actions.sh .github/workflows/ci.yml "" push

# プルリクエストイベントでの CI 実行
./run-actions.sh .github/workflows/ci.yml "" pull_request
```

### 特定のジョブのみテスト

```bash
# test ジョブのみ実行
./run-actions.sh .github/workflows/ci.yml test

# build と deploy ジョブを順次実行
./run-actions.sh .github/workflows/ci.yml build
./run-actions.sh .github/workflows/ci.yml deploy
```

### デバッグモード

```bash
# 詳細なログ出力
RUNNER_DEBUG=1 ./run-actions.sh .github/workflows/ci.yml
```

## 対応プラットフォーム

| プラットフォーム | Docker イメージ | 説明 |
|----------------|----------------|------|
| `ubuntu-latest` | `catthehacker/ubuntu:act-latest` | 最新の Ubuntu（推奨） |
| `ubuntu-20.04` | `catthehacker/ubuntu:act-20.04` | Ubuntu 20.04 LTS |
| `ubuntu-18.04` | `catthehacker/ubuntu:act-18.04` | Ubuntu 18.04 LTS |

## 制限事項

### サポートされていない機能

- GitHub-hosted runners の一部機能
- Marketplace actions の一部
- GitHub API への直接アクセス（Token が必要）
- Secrets の自動注入（環境変数で代替）

### ワークアラウンド

#### Secrets の設定

```bash
# .secrets ファイルを作成
echo "MY_SECRET=secret_value" > .secrets

# act 実行時に指定
docker run --rm -v "$PWD:/workspace" -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/scottlz0310/mcp-docker-actions:latest \
  act --secret-file .secrets
```

#### カスタム環境変数

```bash
# 環境変数を直接指定
docker run --rm -v "$PWD:/workspace" -v /var/run/docker.sock:/var/run/docker.sock \
  -e CUSTOM_VAR=value \
  ghcr.io/scottlz0310/mcp-docker-actions:latest \
  act
```

## トラブルシューティング

### Docker の権限エラー

```bash
# Docker グループにユーザーを追加
sudo usermod -aG docker $USER
# ログアウト・ログインして再試行
```

### メモリ不足エラー

```bash
# Docker のメモリ制限を増やす
# Docker Desktop の Settings → Resources → Memory
```

### Act が見つからない

```bash
# Docker イメージを直接使用
docker run --rm -v "$PWD:/workspace" -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/scottlz0310/mcp-docker-actions:latest \
  act --help
```

## 高度な使用方法

### カスタム Dockerfile

```yaml
# .github/workflows/custom.yml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: your-custom-image:latest
    steps:
      - uses: actions/checkout@v3
      - run: make test
```

### Matrix ビルド

```yaml
strategy:
  matrix:
    node-version: [14, 16, 18]
steps:
  - uses: actions/setup-node@v3
    with:
      node-version: ${{ matrix.node-version }}
```

### 条件付き実行

```bash
# 特定の条件でのみ実行
./run-actions.sh .github/workflows/deploy.yml "" push
```

## 設定オプション

| 環境変数 | 必須 | デフォルト | 説明 |
|---------|------|----------|------|
| `GITHUB_TOKEN` | ❌ | - | GitHub Personal Access Token |
| `ACT_PLATFORM` | ❌ | `ubuntu-latest=catthehacker/ubuntu:act-latest` | 使用するプラットフォーム |
| `ACT_TIMEOUT` | ❌ | `600` | タイムアウト（秒） |
| `LOG_LEVEL` | ❌ | `info` | ログレベル |
| `DOCKER_HOST` | ❌ | `unix:///var/run/docker.sock` | Docker ホスト |

## パフォーマンス最適化

### Docker イメージのキャッシュ

```bash
# よく使うイメージを事前にプル
docker pull catthehacker/ubuntu:act-latest
docker pull node:16
docker pull python:3.9
```

### 並列実行

```bash
# 複数のジョブを並列実行
./run-actions.sh .github/workflows/ci.yml test &
./run-actions.sh .github/workflows/ci.yml lint &
wait
```
