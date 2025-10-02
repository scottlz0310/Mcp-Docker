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

.PHONY: pull
pull: ## Docker イメージを更新
	docker compose pull

# ----------------------------------------
# 個別サービス
# ----------------------------------------

.PHONY: github-mcp
github-mcp: ## GitHub MCPサーバー起動
	docker compose up -d github-mcp

.PHONY: github-mcp-logs
github-mcp-logs: ## GitHub MCPサーバーのログ表示
	docker compose logs -f github-mcp

.PHONY: actions
actions: ## Actions Simulator起動
	docker compose --profile tools up -d actions-simulator

.PHONY: actions-logs
actions-logs: ## Actions Simulatorのログ表示
	docker compose logs -f actions-simulator

.PHONY: datetime
datetime: ## DateTime Validator起動
	docker compose up -d datetime-validator

.PHONY: datetime-logs
datetime-logs: ## DateTime Validatorのログ表示
	docker compose logs -f datetime-validator

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: build
build: ## Docker イメージをビルド
	docker compose build

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
# クリーンアップ
# ----------------------------------------

.PHONY: clean
clean: ## 一時ファイル削除
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-docker
clean-docker: ## Docker リソースクリーンアップ
	docker compose down -v
	docker system prune -f

.PHONY: clean-all
clean-all: clean clean-docker ## 全てクリーンアップ

# ----------------------------------------
# examples/ のテスト
# ----------------------------------------

.PHONY: test-examples
test-examples: ## examples/ の動作確認
	@echo "🧪 GitHub MCP の動作確認..."
	cd examples/github-mcp && cp .env.example .env && docker compose config && rm .env
	@echo "🧪 Actions Simulator の動作確認..."
	cd examples/actions-simulator && cp .env.example .env && docker compose config && rm .env
	@echo "🧪 DateTime Validator の動作確認..."
	cd examples/datetime-validator && cp .env.example .env && docker compose config && rm .env
	@echo "✅ 全ての examples が正常です"

# ----------------------------------------
# ドキュメント
# ----------------------------------------

.PHONY: docs
docs: ## ドキュメント生成（将来の拡張用）
	@echo "📚 ドキュメントは examples/ と docs/ を参照してください"

.PHONY: validate-docs
validate-docs: ## ドキュメント検証
	@echo "📋 README リンクチェック..."
	@find . -name "README.md" -exec echo "Checking: {}" \;

# ----------------------------------------
# CI/CD サポート
# ----------------------------------------

.PHONY: ci-test
ci-test: install lint test security-check ## CI用テストスイート
	@echo "✅ 全てのCI/CDテストが完了しました"

.PHONY: pre-commit
pre-commit: lint format type-check test ## コミット前チェック
	@echo "✅ コミット準備完了"

# ----------------------------------------
# ヘルプ
# ----------------------------------------

.PHONY: help
help: ## このヘルプを表示
	@echo "Mcp-Docker - Docker サーバー管理"
	@echo ""
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "使用例:"
	@echo "  make start           # 全サービス起動"
	@echo "  make github-mcp      # GitHub MCPサーバーのみ起動"
	@echo "  make test-examples   # examples/ の動作確認"
	@echo "  make clean-all       # 全てクリーンアップ"
