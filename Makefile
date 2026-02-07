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
