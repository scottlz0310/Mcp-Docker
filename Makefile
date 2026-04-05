# ========================================
# GitHub MCP Server - サービス管理
# ========================================

.DEFAULT_GOAL := help

.PHONY: help
help: ## 利用可能なターゲット一覧を表示
	@echo "Available targets:\n"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':|##' '{printf "  %-20s %s\n", $$1, $$3}'

# ----------------------------------------
# サービス管理
# ----------------------------------------

.PHONY: start
start: ## GitHub MCPサーバー起動
	docker compose up -d github-mcp

.PHONY: prepare
prepare: ## 環境整備のみ実行（.env作成・事前確認）
	./scripts/setup.sh --prepare-only

.PHONY: stop
stop: ## GitHub MCPサーバー停止
	docker compose down

.PHONY: restart
restart: stop start ## 再起動

.PHONY: logs
logs: ## ログ表示
	docker compose logs -f github-mcp

.PHONY: status
status: ## 状態確認
	docker compose ps

.PHONY: pull
pull: ## Dockerイメージを取得
	docker compose pull github-mcp

.PHONY: build
build: pull ## 互換性のため pull を実行

.PHONY: build-custom
build-custom: ## カスタムビルド（list_pull_request_review_threads パッチ適用）
	GITHUB_MCP_IMAGE=mcp-github-patched:latest docker compose -f docker-compose.yml -f docker-compose.custom.yml build github-mcp

.PHONY: start-custom
start-custom: build-custom ## カスタムビルド後に起動
	GITHUB_MCP_IMAGE=mcp-github-patched:latest docker compose up -d github-mcp

# ----------------------------------------
# copilot-review-mcp (services/copilot-review-mcp)
# ----------------------------------------

CRM_IMAGE       ?= copilot-review-mcp:latest
CRM_CONTAINER   ?= copilot-review-mcp
CRM_PORT        ?= 8083
CRM_SQLITE_PATH ?= /tmp/copilot-review.db
CRM_DIR         := services/copilot-review-mcp

.PHONY: crm-build
crm-build: ## copilot-review-mcp イメージをビルド
	docker build -t $(CRM_IMAGE) $(CRM_DIR)

.PHONY: crm-start
crm-start: crm-stop ## copilot-review-mcp コンテナを起動（バックグラウンド、既存コンテナ自動削除）
	@if [ -z "$$GITHUB_CLIENT_ID" ] || [ -z "$$GITHUB_CLIENT_SECRET" ]; then \
		echo "❌ 環境変数 GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET が未設定です"; \
		exit 1; \
	fi
	docker run -d \
		--name $(CRM_CONTAINER) \
		-p $(CRM_PORT):8083 \
		-e GITHUB_CLIENT_ID \
		-e GITHUB_CLIENT_SECRET \
		-e BASE_URL=$${BASE_URL:-http://localhost:$(CRM_PORT)} \
		-e SQLITE_PATH=$(CRM_SQLITE_PATH) \
		$(if $(GITHUB_OAUTH_SCOPES),-e GITHUB_OAUTH_SCOPES=$(GITHUB_OAUTH_SCOPES)) \
		$(CRM_IMAGE)
	@echo "✅ 起動しました (port $(CRM_PORT))"
	@echo "   ヘルスチェック: curl -s http://localhost:$(CRM_PORT)/health"

.PHONY: crm-stop
crm-stop: ## copilot-review-mcp コンテナを停止・削除
	docker stop $(CRM_CONTAINER) 2>/dev/null || true
	docker rm   $(CRM_CONTAINER) 2>/dev/null || true
	@echo "✅ 停止しました"

.PHONY: crm-restart
crm-restart: crm-stop crm-start ## copilot-review-mcp を再起動

.PHONY: crm-logs
crm-logs: ## copilot-review-mcp ログを表示
	docker logs -f $(CRM_CONTAINER)

.PHONY: crm-status
crm-status: ## copilot-review-mcp コンテナの状態確認
	@docker inspect --format \
		'{{.Name}}  status={{.State.Status}}  pid={{.State.Pid}}' \
		$(CRM_CONTAINER) 2>/dev/null || echo "コンテナが見つかりません: $(CRM_CONTAINER)"

.PHONY: crm-health
crm-health: ## copilot-review-mcp ヘルスチェック
	@curl -sf http://localhost:$(CRM_PORT)/health > /dev/null || { echo "❌ ヘルスチェック失敗"; exit 1; }
	@echo ""

# ----------------------------------------
# 設定生成
# ----------------------------------------

.PHONY: gen-config
gen-config: ## IDE設定ファイルを生成 (IDE=vscode|claude-desktop|kiro|amazonq|codex|copilot-cli)
	./scripts/generate-ide-config.sh --ide $(or $(IDE),vscode)

.PHONY: gen-config-crm
gen-config-crm: ## copilot-review-mcp の IDE設定ファイルを生成 (IDE=vscode|kiro|amazonq|codex|copilot-cli)
	./scripts/generate-ide-config.sh --ide $(or $(IDE),vscode) --service copilot-review-mcp

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: lint
lint: lint-shell ## すべてのLint実行

.PHONY: lint-shell
lint-shell: ## シェルスクリプトのlint実行
	./scripts/lint-shell.sh

.PHONY: test-shell
test-shell: ## シェルスクリプトのテスト実行
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/shell/*.bats; \
	else \
		echo "❌ bats がインストールされていません"; \
		echo "   インストール: brew install bats-core"; \
		exit 1; \
	fi

# ----------------------------------------
# クリーンアップ
# ----------------------------------------

.PHONY: clean
clean: ## 一時ファイル削除
	@echo "キャッシュをクリーンアップ中..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage test-results
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "キャッシュクリーンアップ完了"

.PHONY: clean-docker
clean-docker: ## Dockerリソースクリーンアップ
	@echo "Dockerリソースをクリーンアップ中..."
	docker compose down -v
	docker system prune -f
	@echo "Dockerクリーンアップ完了"

.PHONY: clean-all
clean-all: clean clean-docker ## 全てクリーンアップ
	@echo "すべてのクリーンアップ完了"
