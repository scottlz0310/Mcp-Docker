# ========================================
# Mcp-Docker - サービス管理
# ========================================

.DEFAULT_GOAL := help

.PHONY: help
help: ## 利用可能なターゲット一覧を表示
	@echo "Available targets:\n"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':|##' '{printf "  %-20s %s\n", $$1, $$3}'
	@echo ""
	@echo "各ターゲットはコメントに記載された説明のとおりに動作します。"

ROOT_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

# ----------------------------------------
# 環境検出とDocker Composeコマンド構築
# ----------------------------------------

# WSL環境を検出
IS_WSL := $(shell grep -qi microsoft /proc/version 2>/dev/null && echo "true" || echo "false")

# docker-composeコマンドの構築
ifeq ($(IS_WSL),true)
    # WSL環境: override.ymlを使用（存在する場合）
    ifneq ($(wildcard docker-compose.override.yml),)
        COMPOSE_CMD := docker compose -f docker-compose.yml -f docker-compose.override.yml
        COMPOSE_INFO := (WSL mode with override.yml)
    else
        COMPOSE_CMD := docker compose
        COMPOSE_INFO := (WSL mode without override.yml - run 'make setup-wsl' to enable Windows notifications)
    endif
else
    # 通常環境: ベースのみ
    COMPOSE_CMD := docker compose
    COMPOSE_INFO := (standard mode)
endif

# ----------------------------------------
# サービス管理
# ----------------------------------------

.PHONY: start
start: ## 全サービス起動
	@echo "Starting services $(COMPOSE_INFO)..."
	$(COMPOSE_CMD) up -d

.PHONY: stop
stop: ## 全サービス停止
	$(COMPOSE_CMD) down

.PHONY: restart
restart: stop start ## 再起動

.PHONY: logs
logs: ## ログ表示
	$(COMPOSE_CMD) logs -f

.PHONY: status
status: ## 状態確認
	$(COMPOSE_CMD) ps

.PHONY: pull
pull: ## Docker イメージを更新
	$(COMPOSE_CMD) pull

# ----------------------------------------
# 個別サービス
# ----------------------------------------

.PHONY: github-mcp
github-mcp: ## GitHub MCPサーバー起動
	$(COMPOSE_CMD) up -d github-mcp

.PHONY: github-mcp-logs
github-mcp-logs: ## GitHub MCPサーバーのログ表示
	$(COMPOSE_CMD) logs -f github-mcp

.PHONY: actions
actions: ## Actions Simulator起動
	$(COMPOSE_CMD) --profile tools up -d actions-simulator

.PHONY: actions-logs
actions-logs: ## Actions Simulatorのログ表示
	$(COMPOSE_CMD) logs -f actions-simulator

.PHONY: release-watcher
release-watcher: ## GitHub Release Watcher起動
	$(COMPOSE_CMD) up -d github-release-watcher

.PHONY: release-watcher-logs
release-watcher-logs: ## GitHub Release Watcherのログ表示
	$(COMPOSE_CMD) logs -f github-release-watcher

.PHONY: release-watcher-stop
release-watcher-stop: ## GitHub Release Watcher停止
	$(COMPOSE_CMD) stop github-release-watcher

.PHONY: actions-run
actions-run: ## Actions Simulatorでワークフローを選択して実行
	@repo_root="$(ROOT_DIR)"; \
	cd "$$repo_root"; \
	echo "🎭 GitHub Actions Simulator - ワークフロー実行"; \
	workflows=$$(find .github/workflows -maxdepth 1 -type f \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null | sort); \
	if [ -z "$$workflows" ]; then \
		echo "❌ ワークフローファイルが見つかりません"; \
		exit 1; \
	fi; \
	default_selection=".github/workflows/ci.yml"; \
	if [ ! -f "$$default_selection" ]; then \
		default_selection=$$(echo "$$workflows" | head -n1); \
	fi; \
	echo ""; \
	echo "📋 使用可能なワークフロー:"; \
	echo "$$workflows" | nl -w2 -s') '; \
	echo ""; \
	selected=""; \
	if [ -n "$(WORKFLOW)" ]; then \
		if [ -f "$(WORKFLOW)" ]; then \
			selected="$(WORKFLOW)"; \
		else \
			match=$$(printf "%s\n" "$$workflows" | grep -Fx "$(WORKFLOW)"); \
			if [ -z "$$match" ]; then \
				echo "❌ 指定された WORKFLOW が一覧に見つかりません: $(WORKFLOW)"; \
				exit 1; \
			fi; \
			selected="$$match"; \
		fi; \
	elif [ -n "$(INDEX)" ]; then \
		if ! echo "$(INDEX)" | grep -Eq '^[0-9]+$$'; then \
			echo "❌ INDEX は数値で指定してください"; \
			exit 1; \
		fi; \
		selected=$$(printf "%s\n" "$$workflows" | sed -n "$(INDEX)p"); \
		if [ -z "$$selected" ]; then \
			echo "❌ INDEX が範囲外です: $(INDEX)"; \
			exit 1; \
		fi; \
	else \
		echo "💡 Enter だけで $$default_selection を実行します"; \
		printf "🎯 実行するワークフローを選択してください (Enter=1): "; \
		read choice; \
		if [ -z "$$choice" ]; then \
			choice=1; \
		fi; \
		if ! echo "$$choice" | grep -Eq '^[0-9]+$$'; then \
			echo "❌ 無効な選択です"; \
			exit 1; \
		fi; \
		selected=$$(printf "%s\n" "$$workflows" | sed -n "$${choice}p"); \
		if [ -z "$$selected" ]; then \
			echo "❌ 無効な番号です"; \
			exit 1; \
		fi; \
	fi; \
	if [ -z "$$selected" ]; then \
		selected="$$default_selection"; \
	fi; \
	echo ""; \
	echo "🚀 実行ワークフロー: $$selected"; \
	echo ""; \
	echo "🔧 Preparing environment..."; \
	./scripts/fix-permissions.sh >/dev/null 2>&1 || true; \
	if [ -n "$(JOB)" ]; then \
		USER_ID=$$(id -u) GROUP_ID=$$(id -g) $(COMPOSE_CMD) --profile tools run --rm \
			-e WORKFLOW_FILE="$$selected" \
			actions-simulator \
			uv run python main.py actions simulate "$$selected" --job "$(JOB)" $(if $(VERBOSE),--verbose,); \
	else \
		USER_ID=$$(id -u) GROUP_ID=$$(id -g) $(COMPOSE_CMD) --profile tools run --rm \
			-e WORKFLOW_FILE="$$selected" \
			actions-simulator \
			uv run python main.py actions simulate "$$selected" $(if $(VERBOSE),--verbose,); \
	fi

.PHONY: datetime
datetime: ## DateTime Validator起動
	$(COMPOSE_CMD) up -d datetime-validator

.PHONY: datetime-logs
datetime-logs: ## DateTime Validatorのログ表示
	$(COMPOSE_CMD) logs -f datetime-validator

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: build
build: ## Docker イメージをビルド
	$(COMPOSE_CMD) build
	$(COMPOSE_CMD) --profile tools build actions-simulator
	$(COMPOSE_CMD) --profile debug build actions-server

.PHONY: build-actions
build-actions: ## GitHub Actions シミュレータのイメージをビルド
	$(COMPOSE_CMD) --profile tools build actions-simulator

.PHONY: build-actions-server
build-actions-server: ## GitHub Actions サーバーのイメージをビルド
	$(COMPOSE_CMD) --profile debug build actions-server

.PHONY: build-release-watcher
build-release-watcher: ## GitHub Release Watcherのイメージをビルド
	$(COMPOSE_CMD) build github-release-watcher

.PHONY: test
test: ## すべてのテスト実行
	uv run pytest

.PHONY: test-unit
test-unit: ## ユニットテストのみ実行
	uv run pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## 統合テストのみ実行
	uv run pytest tests/integration/ -v
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/integration/*.bats; \
	else \
		echo "⚠️  bats がインストールされていません。batsテストをスキップします。"; \
	fi

.PHONY: test-e2e
test-e2e: ## E2Eテストのみ実行（タイムアウト5分）
	uv run pytest tests/e2e/ -v --timeout=300
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/e2e/*.bats; \
	else \
		echo "⚠️  bats がインストールされていません。batsテストをスキップします。"; \
	fi

.PHONY: test-quick
test-quick: ## 高速テスト（ユニット+統合のみ）
	uv run pytest tests/unit/ tests/integration/ -v

.PHONY: lint
lint: ## Lint実行
	uv run ruff check .

.PHONY: format
format: ## フォーマット
	uv run ruff format .

.PHONY: type-check
type-check: ## 型チェック実行
	uv run mypy .

.PHONY: security-check
security-check: ## セキュリティチェック
	uv run bandit -r src/ services/

# ----------------------------------------
# 環境管理
# ----------------------------------------

.PHONY: setup-wsl
setup-wsl: ## WSL環境のセットアップ（Windows Toast通知を有効化）
	@if [ "$(IS_WSL)" != "true" ]; then \
		echo "❌ このコマンドはWSL環境でのみ使用できます"; \
		exit 1; \
	fi; \
	if [ -f docker-compose.override.yml ]; then \
		echo "✅ docker-compose.override.yml は既に存在します"; \
	else \
		echo "📝 docker-compose.override.yml を作成しています..."; \
		cp docker-compose.override.yml.example docker-compose.override.yml; \
		echo "✅ docker-compose.override.yml を作成しました"; \
	fi; \
	echo ""; \
	echo "📋 次のステップ:"; \
	echo "  1. .env ファイルに WINDOWS_NOTIFICATION_PATH を設定してください:"; \
	echo "     echo 'WINDOWS_NOTIFICATION_PATH=/mnt/c/path/to/windows-notifications' >> .env"; \
	echo "  2. make start でサービスを起動してください"; \
	echo ""

.PHONY: install
install: ## 依存関係インストール
	uv sync

.PHONY: update
update: ## 依存関係更新
	uv lock --upgrade

.PHONY: venv
venv: ## 仮想環境作成
	uv venv

# ----------------------------------------
	@echo "すべてのキャッシュをクリーンアップ完了"

# クリーンアップ
.PHONY: clean clean-docker clean-all

clean: ## 一時ファイル削除
	@echo "キャッシュをクリーンアップ中..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage test-results
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "キャッシュクリーンアップ完了"

clean-docker: ## Docker リソースクリーンアップ
	@echo "Dockerリソースをクリーンアップ中..."
	$(COMPOSE_CMD) down -v
	docker system prune -f
	@echo "Dockerクリーンアップ完了"

clean-all: clean clean-docker ## 全てクリーンアップ
	@echo "すべてのクリーンアップ完了"
