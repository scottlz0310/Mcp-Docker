# 他リポジトリからの利用ガイド

**作成日:** 2025-09-30
**目的:** Mcp-Dockerのサービスを他のリポジトリから簡単に利用する方法

---

## 3つの利用パターン

### パターン1: Dockerイメージを直接使用（推奨）
**メリット:** 最もシンプル、ビルド不要、すぐ使える

### パターン2: 設定ファイルをコピー
**メリット:** カスタマイズしやすい、独立して管理

### パターン3: Git Submodule
**メリット:** 最新版を追跡、アップデート容易

---

## サービス別利用方法

### GitHub MCPサーバー

#### 1. Dockerイメージで使用
```yaml
# ~/my-project/docker-compose.yml
services:
  app:
    build: .
    environment:
      - MCP_SERVER_URL=http://github-mcp:3000

  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    ports:
      - "3000:3000"
    restart: unless-stopped
```

```bash
# セットアップ
cd ~/my-project
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
docker compose up -d github-mcp

# 使用
curl http://localhost:3000/repositories
```

#### 2. 設定ファイルをコピー
```bash
# セットアップ
cd ~/my-project
mkdir -p mcp/github
cp ~/workspace/Mcp-Docker/examples/github-mcp/* mcp/github/
cd mcp/github
cp .env.example .env
vim .env  # GITHUB_TOKENを設定

# 起動
docker compose up -d
```

**ファイル構成:**
```
~/my-project/
├── mcp/
│   └── github/
│       ├── docker-compose.yml
│       ├── .env
│       ├── config.json
│       └── README.md
└── docker-compose.yml  # メインプロジェクト
```

#### 3. Claude Desktopでの設定
```json
// ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "GITHUB_TOKEN",
        "ghcr.io/your-username/mcp-docker-github:latest"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

---

### Actions Simulator

#### 1. スクリプトをコピー（推奨）
```bash
# セットアップ
cd ~/my-workflow-project
cp ~/workspace/Mcp-Docker/examples/actions-simulator/run-actions.sh .
chmod +x run-actions.sh

# 使用
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
./run-actions.sh .github/workflows/ci.yml
./run-actions.sh .github/workflows/ci.yml test  # 特定のジョブ
./run-actions.sh .github/workflows/ci.yml test pull_request  # イベント指定
```

#### 2. Dockerコマンドで直接使用
```bash
# 1回限りの実行
docker run --rm \
  -v "$PWD:/workspace" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  ghcr.io/your-username/mcp-docker-actions:latest \
  act push -W .github/workflows/ci.yml
```

#### 3. Makefileに統合
```makefile
# ~/my-workflow-project/Makefile

.PHONY: test-workflows
test-workflows: ## GitHub Actionsワークフローをローカルでテスト
	docker run --rm \
		-v $(PWD):/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e GITHUB_TOKEN=$(GITHUB_TOKEN) \
		ghcr.io/your-username/mcp-docker-actions:latest \
		act push -W .github/workflows/ci.yml

.PHONY: test-workflow-job
test-workflow-job: ## 特定のジョブをテスト (例: make test-workflow-job JOB=test)
	docker run --rm \
		-v $(PWD):/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e GITHUB_TOKEN=$(GITHUB_TOKEN) \
		ghcr.io/your-username/mcp-docker-actions:latest \
		act push -W .github/workflows/ci.yml -j $(JOB)
```

#### 4. CI/CDパイプラインで使用

**GitHub Actionsで検証:**
```yaml
# .github/workflows/validate-workflows.yml
name: Validate Workflows

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test workflows locally with act
        run: |
          docker run --rm \
            -v $PWD:/workspace \
            -v /var/run/docker.sock:/var/run/docker.sock \
            ghcr.io/your-username/mcp-docker-actions:latest \
            act --list
```

**pre-commitフックで使用:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-github-actions
        name: Validate GitHub Actions
        entry: bash -c 'docker run --rm -v $PWD:/workspace ghcr.io/your-username/mcp-docker-actions:latest act --list'
        language: system
        files: ^\.github/workflows/.*\.yml$
        pass_filenames: false
```

---

### DateTime Validator

#### 1. Dockerイメージで使用
```yaml
# ~/my-docs-project/docker-compose.yml
services:
  datetime-validator:
    image: ghcr.io/your-username/mcp-docker-datetime:latest
    environment:
      - WATCH_DIRECTORY=/workspace/docs
      - CHECK_INTERVAL=60
    volumes:
      - ./docs:/workspace/docs
    restart: unless-stopped
```

```bash
# 起動
cd ~/my-docs-project
docker compose up -d datetime-validator

# ログ確認
docker compose logs -f datetime-validator
```

#### 2. 設定ファイルをコピー
```bash
cd ~/my-docs-project
mkdir -p tools/datetime-validator
cp ~/workspace/Mcp-Docker/examples/datetime-validator/* tools/datetime-validator/
cd tools/datetime-validator
cp .env.example .env
vim .env  # WATCH_DIRECTORYを設定
docker compose up -d
```

---

## 実践例

### 例1: 新しいプロジェクトでGitHub MCPサーバーを使う

```bash
# 1. 新プロジェクト作成
mkdir ~/my-new-project
cd ~/my-new-project

# 2. Dockerイメージを使う設定
cat > docker-compose.yml <<EOF
services:
  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    environment:
      - GITHUB_TOKEN=\${GITHUB_TOKEN}
    ports:
      - "3000:3000"
    restart: unless-stopped
EOF

# 3. 環境変数設定
cat > .env <<EOF
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
EOF

# 4. 起動
docker compose up -d

# 5. 確認
curl http://localhost:3000/repositories
```

**所要時間:** 3分

---

### 例2: 既存プロジェクトのワークフローをテスト

```bash
# 1. 既存プロジェクトへ移動
cd ~/existing-project

# 2. run-actions.sh をダウンロード
curl -O https://raw.githubusercontent.com/your-username/Mcp-Docker/main/examples/actions-simulator/run-actions.sh
chmod +x run-actions.sh

# 3. 実行
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
./run-actions.sh .github/workflows/ci.yml

# 4. 特定のジョブだけテスト
./run-actions.sh .github/workflows/ci.yml test
```

**所要時間:** 2分

---

### 例3: マルチサービス構成

```bash
# 複数のサービスを同時に使用
cd ~/complex-project

cat > docker-compose.yml <<EOF
services:
  # アプリケーション
  app:
    build: .
    depends_on:
      - github-mcp
    environment:
      - MCP_SERVER_URL=http://github-mcp:3000

  # GitHub MCPサーバー
  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    environment:
      - GITHUB_TOKEN=\${GITHUB_TOKEN}
    ports:
      - "3000:3000"

  # DateTime Validator
  datetime-validator:
    image: ghcr.io/your-username/mcp-docker-datetime:latest
    environment:
      - WATCH_DIRECTORY=/workspace/docs
    volumes:
      - ./docs:/workspace/docs
EOF

# 起動
docker compose up -d

# 確認
docker compose ps
docker compose logs
```

---

## トラブルシューティング

### Dockerイメージが見つからない

**問題:**
```
Error response from daemon: manifest for ghcr.io/your-username/mcp-docker-github:latest not found
```

**解決策:**
```bash
# 1. イメージが公開されているか確認
# GitHub Container Registryで確認

# 2. ローカルでビルド
cd ~/workspace/Mcp-Docker
docker build -t ghcr.io/your-username/mcp-docker-github:latest .
```

### GitHub Tokenが無効

**問題:**
```
Error: Bad credentials
```

**解決策:**
```bash
# 1. トークンの権限を確認
# GitHub Settings > Developer settings > Personal access tokens
# 必要な権限: repo, read:user

# 2. トークンを再生成
# 環境変数を更新
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 3. コンテナ再起動
docker compose restart
```

### Docker in Dockerの権限エラー

**問題:**
```
permission denied while trying to connect to the Docker daemon socket
```

**解決策:**
```bash
# 1. Dockerソケットのマウントを確認
# docker-compose.ymlに以下があることを確認:
volumes:
  - /var/run/docker.sock:/var/run/docker.sock

# 2. ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
newgrp docker

# 3. コンテナ再起動
docker compose restart
```

### ポートが既に使用されている

**問題:**
```
Error: bind: address already in use
```

**解決策:**
```bash
# 1. 使用中のプロセスを確認
sudo lsof -i :3000

# 2. ポートを変更
# docker-compose.ymlで:
ports:
  - "3001:3000"  # 3001に変更
```

---

## ベストプラクティス

### 1. 環境変数の管理

```bash
# .env.example を用意（リポジトリにコミット）
cat > .env.example <<EOF
# GitHub Token (必須)
GITHUB_TOKEN=

# ログレベル (オプション)
LOG_LEVEL=info
EOF

# .env は .gitignore に追加
echo ".env" >> .gitignore
```

### 2. Docker Composeでの依存関係

```yaml
services:
  app:
    depends_on:
      github-mcp:
        condition: service_healthy
    environment:
      - MCP_SERVER_URL=http://github-mcp:3000

  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### 3. バージョン管理

```yaml
# latestではなく特定のバージョンを使用
services:
  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:v1.1.0
    # 理由: 予期しない変更を防ぐ
```

### 4. ログの永続化

```yaml
services:
  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    volumes:
      - ./logs:/app/logs
    environment:
      - LOG_FILE=/app/logs/github-mcp.log
```

---

## FAQ

### Q1: どのサービスを使えばいい？

**A:**
- **GitHub MCPサーバー** - Claude DesktopからGitHub操作したい
- **Actions Simulator** - GitHub Actionsをローカルでテストしたい
- **DateTime Validator** - ドキュメントの日付を自動チェックしたい

### Q2: Dockerイメージとソースコピーどちらが良い？

**A:**
- **Dockerイメージ**: すぐ使える、メンテナンス不要、推奨
- **ソースコピー**: カスタマイズしたい場合のみ

### Q3: 複数のプロジェクトで同じサービスを使える？

**A:** はい、各プロジェクトで独立したコンテナを起動できます。

```bash
# プロジェクト1
cd ~/project1
docker compose up -d  # ポート3000で起動

# プロジェクト2（ポート変更）
cd ~/project2
# docker-compose.ymlでポートを3001に変更
docker compose up -d  # ポート3001で起動
```

### Q4: アップデート方法は？

**A:**
```bash
# Dockerイメージの場合
docker compose pull
docker compose up -d

# Git Submoduleの場合
cd tools/mcp-docker
git pull origin main
cd ../..
docker compose build
docker compose up -d
```

### Q5: オフラインでも使える？

**A:** はい、事前にイメージをpullしておけば可能。

```bash
# 事前にpull
docker pull ghcr.io/your-username/mcp-docker-github:latest

# オフラインで起動
docker compose up -d  # キャッシュされたイメージを使用
```

---

## まとめ

### 推奨フロー

1. **examples/ を確認** - 使いたいサービスの例を見る
2. **Dockerイメージを使用** - 最も簡単
3. **環境変数を設定** - .envファイルを作成
4. **docker compose up** - 起動
5. **動作確認** - curl やブラウザで確認

### 所要時間
- 初回セットアップ: 5〜10分
- 2回目以降: 1分以内

### サポート
- ドキュメント: `docs/services/`
- 例: `examples/`
- Issue: GitHub Issues

---

**作成日:** 2025-09-30
**更新日:** -
