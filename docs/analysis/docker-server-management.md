# Docker サーバー管理のシンプル化提案

**作成日:** 2025-09-30
**目的:** Dockerサーバーをローカルで管理し、他リポジトリから利用しやすくする

---

## プロジェクトの正しい理解

### 実際の目的
1. **Dockerサーバーをローカルで管理** - 各種MCPサーバーやツールをコンテナで統一管理
2. **他の自分のリポジトリから簡単に利用** - 設定ファイルや起動スクリプトをコピーして使用
3. **サービスは今後も増やす** - GitHub MCP、DateTime、Actions など、必要に応じて追加
4. **管理をシンプルに** - 増えても管理しやすい構造

### やらないこと
- ❌ PyPI公開（ライブラリではない）
- ❌ Python API提供（サーバー管理が目的）
- ❌ uvの廃止（モダンで高速、継続使用）
- ❌ Python 3.9へのダウングレード（最新版を使うべき）
- ❌ サービスの削減（増やす予定）

---

## 現状の問題点（再分析）

### 1. 他リポジトリから使いにくい

#### GitHub MCP サーバー
**問題:**
- 設定方法が不明確
- どのファイルをコピーすればいいか分からない
- 起動方法が複雑

**あるべき姿:**
```bash
# 他リポジトリで
cp /path/to/Mcp-Docker/examples/github-mcp/* .
docker compose up github-mcp
```

#### Actions Simulator
**問題:**
- リポジトリにコピーする想定だが、何をコピーすればいいか不明
- 起動スクリプトの場所が分かりにくい
- 依存関係の管理が複雑

**あるべき姿:**
```bash
# 他リポジトリで
cp /path/to/Mcp-Docker/examples/actions-simulator/* .
./run-actions.sh .github/workflows/ci.yml
```

### 2. ドキュメントの問題

**現状:**
- 100以上のファイルで情報が散在
- 「どのサービスをどう使うか」が見つけにくい
- 内部開発用のレポートが混在

**必要なドキュメント:**
- 各サービスの使用方法（1サービス1ファイル）
- 他リポジトリへの導入手順
- トラブルシューティング

### 3. Makefile の複雑さ

**問題:**
- 55,311行、300以上のターゲット
- 重複する機能が多数
- どのターゲットを使えばいいか不明

**必要な機能:**
```makefile
# サービス管理
make start          # 全サービス起動
make stop           # 全サービス停止
make restart        # 再起動
make logs           # ログ表示
make status         # 状態確認

# 開発用
make test           # テスト実行
make lint           # Lint実行
make format         # フォーマット

# 個別サービス
make github-mcp     # GitHub MCPサーバー起動
make actions        # Actions Simulator起動
make datetime       # DateTime Validator起動
```

### 4. 設定ファイルの散在

**問題:**
- `.env.example` が360行で複雑
- `docker-compose.yml` が複数存在
- どれを使えばいいか不明

**必要な構造:**
```
examples/
├── github-mcp/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
├── actions-simulator/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── run-actions.sh
│   └── README.md
└── datetime-validator/
    ├── docker-compose.yml
    ├── .env.example
    └── README.md
```

---

## シンプル化の提案

### 提案1: examples/ ディレクトリの新設

**目的:** 他リポジトリで使うファイルを明確に分離

```
examples/
├── README.md                          # 各サービスの概要と選び方
├── github-mcp/
│   ├── README.md                      # GitHub MCPサーバーの使い方
│   ├── docker-compose.yml             # このサービスだけのCompose
│   ├── .env.example                   # 必要な環境変数のみ
│   └── config.json.example            # MCP設定例
├── actions-simulator/
│   ├── README.md                      # Actions Simulatorの使い方
│   ├── docker-compose.yml             # このサービスだけのCompose
│   ├── .env.example                   # 必要な環境変数のみ
│   ├── run-actions.sh                 # 起動スクリプト
│   └── Makefile                       # よく使うコマンド
└── datetime-validator/
    ├── README.md                      # DateTime Validatorの使い方
    ├── docker-compose.yml             # このサービスだけのCompose
    └── .env.example                   # 必要な環境変数のみ
```

**使用方法:**
```bash
# 例: GitHub MCPサーバーを他リポジトリで使う
cd ~/my-other-project
cp -r ~/workspace/Mcp-Docker/examples/github-mcp ./mcp-server
cd mcp-server
cp .env.example .env
vim .env  # GITHUB_TOKENを設定
docker compose up -d

# 例: Actions Simulatorを他リポジトリで使う
cd ~/my-workflow-project
cp ~/workspace/Mcp-Docker/examples/actions-simulator/run-actions.sh .
./run-actions.sh .github/workflows/ci.yml
```

### 提案2: ドキュメント構造の整理

**削除対象:**
- 開発プロセスのレポート（50以上のFINAL、UPDATED、COMPARISONファイル）
- 内部議論の記録
- 重複するドキュメント

**保持・整理:**
```
docs/
├── README.md                          # プロジェクト概要
├── services/
│   ├── github-mcp.md                  # GitHub MCPサーバー詳細
│   ├── actions-simulator.md           # Actions Simulator詳細
│   └── datetime-validator.md          # DateTime Validator詳細
├── guides/
│   ├── getting-started.md             # 初めての人向け
│   ├── usage-in-other-repos.md        # 他リポジトリでの使用方法
│   └── adding-new-service.md          # 新サービスの追加方法
├── development/
│   ├── CONTRIBUTING.md                # コントリビューションガイド
│   └── ARCHITECTURE.md                # アーキテクチャ設計
├── troubleshooting/
│   └── common-issues.md               # よくある問題
└── analysis/                          # この分析（参考資料）
    └── ...
```

**合計:** 約15ファイル（現在100以上から大幅削減）

### 提案3: Makefile の大幅簡素化

**現在:** 55,311行 → **目標:** <200行

**新しい構造:**
```makefile
# ========================================
# Mcp-Docker - サービス管理
# ========================================

.DEFAULT_GOAL := help

# ----------------------------------------
# サービス管理
# ----------------------------------------

.PHONY: start
start: ## 全サービス起動
	docker compose up -d

.PHONY: stop
stop: ## 全サービス停止
	docker compose down

.PHONY: restart
restart: stop start ## 再起動

.PHONY: logs
logs: ## ログ表示
	docker compose logs -f

.PHONY: status
status: ## 状態確認
	docker compose ps

# ----------------------------------------
# 個別サービス
# ----------------------------------------

.PHONY: github-mcp
github-mcp: ## GitHub MCPサーバー起動
	docker compose up -d github-mcp

.PHONY: actions
actions: ## Actions Simulator起動
	docker compose --profile tools up -d actions-simulator

.PHONY: datetime
datetime: ## DateTime Validator起動
	docker compose up -d datetime-validator

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: test
test: ## テスト実行
	uv run pytest

.PHONY: lint
lint: ## Lint実行
	uv run ruff check .

.PHONY: format
format: ## フォーマット
	uv run ruff format .

.PHONY: clean
clean: ## クリーンアップ
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# ----------------------------------------
# ヘルプ
# ----------------------------------------

.PHONY: help
help: ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

**削除するもの:**
- 重複するactionsターゲット（50以上）
- 詳細な診断ターゲット
- レポート生成ターゲット
- ドキュメント検証ターゲット

### 提案4: 環境変数の整理

**現在:** 50以上の環境変数 → **目標:** サービスごとに5〜10個

#### GitHub MCP サーバー
```bash
# examples/github-mcp/.env.example
# 必須
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# オプション
LOG_LEVEL=info
PORT=3000
```

#### Actions Simulator
```bash
# examples/actions-simulator/.env.example
# 必須
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# オプション
ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest
ACT_TIMEOUT=600
LOG_LEVEL=info
DOCKER_HOST=unix:///var/run/docker.sock
```

#### DateTime Validator
```bash
# examples/datetime-validator/.env.example
# 必須
WATCH_DIRECTORY=./docs

# オプション
LOG_LEVEL=info
CHECK_INTERVAL=60
```

### 提案5: Docker Compose の整理

#### ルートの docker-compose.yml
```yaml
# 開発用: 全サービスを管理
services:
  github-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    env_file: .env
    volumes:
      - ./services/github:/app/services/github
    ports:
      - "3000:3000"

  datetime-validator:
    build:
      context: .
      dockerfile: Dockerfile
    env_file: .env
    volumes:
      - ./services/datetime:/app/services/datetime
      - ./docs:/workspace/docs

  actions-simulator:
    build:
      context: .
      dockerfile: Dockerfile.actions
    env_file: .env
    volumes:
      - ./services/actions:/app/services/actions
      - /var/run/docker.sock:/var/run/docker.sock
    profiles:
      - tools
```

#### examples/*/docker-compose.yml
```yaml
# 他リポジトリでコピーして使う用
# 例: examples/github-mcp/docker-compose.yml
services:
  github-mcp:
    image: ghcr.io/your-username/mcp-docker:latest
    env_file: .env
    ports:
      - "3000:3000"
    restart: unless-stopped
```

---

## 他リポジトリからの利用パターン

### パターン1: Docker Compose で参照

**他リポジトリの構成:**
```yaml
# ~/my-project/docker-compose.yml
services:
  app:
    build: .
    depends_on:
      - github-mcp

  github-mcp:
    image: ghcr.io/your-username/mcp-docker-github:latest
    env_file: ./mcp/.env
    ports:
      - "3000:3000"
```

**セットアップ:**
```bash
cd ~/my-project
mkdir mcp
cp ~/workspace/Mcp-Docker/examples/github-mcp/.env.example mcp/.env
vim mcp/.env  # GITHUB_TOKENを設定
docker compose up -d
```

### パターン2: スクリプトをコピーして使用

**Actions Simulator の場合:**
```bash
cd ~/my-workflow-project

# スクリプトコピー
cp ~/workspace/Mcp-Docker/examples/actions-simulator/run-actions.sh .
chmod +x run-actions.sh

# 実行
./run-actions.sh .github/workflows/ci.yml
```

**run-actions.sh の改善:**
```bash
#!/bin/bash
# Actions Simulator - シンプルな起動スクリプト

set -euo pipefail

WORKFLOW=${1:-.github/workflows/ci.yml}
JOB=${2:-}
EVENT=${3:-push}

# Docker イメージを使用
docker run --rm \
  -v "$PWD:/workspace" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
  ghcr.io/your-username/mcp-docker-actions:latest \
  act "$EVENT" \
  -W "$WORKFLOW" \
  ${JOB:+-j "$JOB"}
```

### パターン3: Git Submodule として管理

```bash
cd ~/my-project
git submodule add https://github.com/your-username/Mcp-Docker.git tools/mcp-docker

# 使用
cd tools/mcp-docker
docker compose up -d github-mcp
```

---

## 新サービス追加の簡易化

### サービステンプレート

**新サービス追加時のチェックリスト:**
1. `services/new-service/` ディレクトリ作成
2. `docker-compose.yml` にサービス追加
3. `examples/new-service/` に使用例作成
4. `docs/services/new-service.md` にドキュメント作成
5. `README.md` の一覧に追加

**テンプレート構造:**
```
services/new-service/
├── __init__.py
├── main.py                # エントリポイント
├── service.py             # サービスロジック
├── config.py              # 設定管理
└── README.md              # サービス説明

examples/new-service/
├── README.md              # 使用方法
├── docker-compose.yml     # 単体で使えるCompose
└── .env.example           # 環境変数テンプレート

docs/services/
└── new-service.md         # 詳細ドキュメント
```

---

## 実装計画

### フェーズ1: examples/ 作成（1日）

**タスク:**
1. `examples/` ディレクトリ作成
2. 各サービスの使用例を分離
3. 各examples/*/README.md 作成
4. 簡潔な .env.example 作成

**成果物:**
- `examples/github-mcp/`
- `examples/actions-simulator/`
- `examples/datetime-validator/`

### フェーズ2: ドキュメント整理（2日）

**タスク:**
1. 開発プロセスのレポートを削除/アーカイブ
2. `docs/services/` に各サービスのドキュメント作成
3. `docs/guides/usage-in-other-repos.md` 作成
4. ルート README.md を分かりやすく書き直し

**目標:**
- ドキュメント数: 100+ → 約15

### フェーズ3: Makefile 簡素化（1日）

**タスク:**
1. 新しいシンプルな Makefile 作成
2. 旧 Makefile を `Makefile.old` にバックアップ
3. 基本的な20ターゲットのみ実装
4. examples/ の Makefile 作成

**目標:**
- Makefile: 55,311行 → <200行

### フェーズ4: Docker イメージ公開（1日）

**タスク:**
1. GitHub Container Registry へのpush設定
2. CI/CD でイメージビルド自動化
3. タグ管理（latest, version）
4. examples/ で公開イメージを使用

**成果物:**
- `ghcr.io/your-username/mcp-docker:latest`
- `ghcr.io/your-username/mcp-docker-github:latest`
- `ghcr.io/your-username/mcp-docker-actions:latest`

### フェーズ5: 検証とドキュメント更新（1日）

**タスク:**
1. 実際に他リポジトリで試す
2. 問題点を洗い出し
3. ドキュメント修正
4. README.md に使用例を追加

**合計:** 約1週間で完了

---

## 成功指標

### 他リポジトリからの利用
- [ ] 新しいリポジトリへの導入時間: <10分
- [ ] 必要なファイルコピー: <3ファイル
- [ ] 環境変数設定: <5個
- [ ] docker compose up で起動成功

### ドキュメント
- [ ] ドキュメントファイル数: 100+ → 約15
- [ ] 各サービスの使用方法が1ページで理解可能
- [ ] examples/ を見れば使い方が分かる

### メンテナンス性
- [ ] Makefile: 55,311行 → <200行
- [ ] よく使うコマンドが20個以下
- [ ] 新サービス追加の所要時間: <1時間

### シンプルさ
- [ ] Python 3.13+ 継続使用
- [ ] uv 継続使用
- [ ] サービスは柔軟に追加可能
- [ ] 各サービスは独立して使用可能

---

## まとめ

### 現状の理解
- ✅ Dockerサーバー管理ツール
- ✅ 複数のMCPサービス・ツールを統合
- ✅ 他の自分のリポジトリから利用
- ✅ サービスは今後も増やす

### 解決策
1. **examples/ で明確な使用例** - コピーして使える構成
2. **ドキュメント整理** - 100+ → 約15ファイル
3. **Makefile簡素化** - 55,311行 → <200行
4. **Docker イメージ公開** - 他リポジトリで簡単に使える
5. **サービステンプレート** - 新サービス追加が容易

### やらないこと
- ❌ PyPI公開（目的外）
- ❌ uvの廃止（モダンで高速）
- ❌ Python古いバージョン（最新を使用）
- ❌ サービスの削減（増やす予定）

---

**次のステップ:** フェーズ1（examples/ 作成）から開始

**作成日:** 2025-09-30
