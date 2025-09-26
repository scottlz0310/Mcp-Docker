.PHONY: help build start stop logs clean datetime codeql actions actions-auto actions-list actions-run actions-api test test-bats test-docker test-services test-security test-integration test-all security lint pre-commit setup-branch-protection release-check version version-sync sbom audit-deps validate-security docs docs-serve docs-clean install-bats check-bats

help:
	@echo "MCP Docker Environment Commands:"
	@echo "  make build     - Build unified image"
	@echo "  make start     - Start DateTime validator"
	@echo "  make stop      - Stop all services"
	@echo "  make logs      - Show logs"
	@echo "  make clean     - Clean up containers and images"
	@echo ""
	@echo "Services:"
	@echo "  make github    - Start GitHub MCP server"
	@echo "  make datetime  - Start DateTime validator"
	@echo "  make codeql    - Run CodeQL analysis"
	@echo "  make actions   - Interactive GitHub Actions Simulator (Docker)"
	@echo "  make actions-api - Launch Actions REST API (uvicorn)"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run integration tests"
	@echo "  make test-all  - Run all test suites"
	@echo "  make test-bats - Run Bats test suite"
	@echo "  make install-bats - Install Bats testing framework"
	@echo "  make security  - Run security scan"
	@echo "  make sbom      - Generate SBOM"
	@echo "  make audit-deps - Audit dependencies"
	@echo ""
	@echo "Release Management:"
	@echo "  make version           - Show current version"
	@echo "  make version-sync      - Sync versions between pyproject.toml and main.py"
	@echo "  make release-check     - Check release readiness"
	@echo "  make setup-branch-protection - Setup branch protection"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs              - Generate documentation"
	@echo "  make docs-serve        - Serve documentation locally"
	@echo "  make docs-clean        - Clean documentation build"
	@echo ""
	@echo "GitHub Actions Simulator:"
	@echo "  make actions             - Interactive workflow selection (Docker)"
	@echo "  make actions-auto        - Run default CI workflow (Docker)"
	@echo "  make actions-list        - List available workflows"
	@echo "  make actions-run         - Run workflow: WORKFLOW=path [JOB=job] [VERBOSE=1]"
	@echo "  make actions-simulate    - Legacy: Run custom workflow: WORKFLOW=path [JOB=job] [VERBOSE=1]"
	@echo "  make actions-validate    - Validate workflows: [WORKFLOW=path]"
	@echo "  make actions-dry-run     - Dry run workflow: WORKFLOW=path [VERBOSE=1]"
	@echo ""
	@echo "GitHub MCP Server:"
	@echo "  Use: docker run -e GITHUB_PERSONAL_ACCESS_TOKEN=\$$GITHUB_PERSONAL_ACCESS_TOKEN mcp-docker-github-mcp"

build:
	docker compose build

start:
	docker compose up -d datetime-validator

stop:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v --rmi all

github:
	docker compose up -d github-mcp

datetime:
	docker compose up -d datetime-validator

codeql:
	docker compose --profile tools run --rm codeql

# GitHub Actions Simulator（Docker版）
actions:
	@echo "🎭 GitHub Actions Simulator (Docker) 起動"
	@echo ""
	@echo "📋 使用可能なワークフロー:"
	@workflows=$$(find .github/workflows -name "*.yml" -o -name "*.yaml" | sort); \
	if [ -z "$$workflows" ]; then \
		echo "❌ ワークフローファイルが見つかりません"; \
		exit 1; \
	fi; \
	echo "$$workflows" | nl -w2 -s') '; \
	echo ""; \
	echo "🎯 実行するワークフローを選択してください (番号入力):"; \
	read -p "選択 [1-$$(echo "$$workflows" | wc -l)]: " choice; \
	if ! echo "$$choice" | grep -q '^[0-9]\+$$'; then \
		echo "❌ 無効な選択です"; \
		exit 1; \
	fi; \
	selected=$$(echo "$$workflows" | sed -n "$${choice}p"); \
	if [ -z "$$selected" ]; then \
		echo "❌ 無効な番号です"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "🚀 実行ワークフロー: $$selected"; \
	echo ""; \
	docker compose --profile tools run --rm -e WORKFLOW_FILE="$$selected" actions-simulator \
		python main.py actions simulate "$$selected"

actions-auto:
	@echo "🎭 GitHub Actions Simulator - 自動実行 (CI)"
	@echo "📋 使用可能なワークフロー:"
	@find .github/workflows -name "*.yml" -o -name "*.yaml" | head -5
	@echo ""
	@echo "🚀 デフォルト実行: CI ワークフロー"
	docker compose --profile tools run --rm actions-simulator

actions-list:
	@echo "🎭 GitHub Actions Simulator - ワークフローリスト"
	@echo ""
	@echo "📋 使用可能なワークフロー:"
	@find .github/workflows -name "*.yml" -o -name "*.yaml" | sort | nl -w2 -s') '
	@echo ""
	@echo "💡 使用方法:"
	@echo "  make actions-run WORKFLOW=.github/workflows/ci.yml"
	@echo "  make actions-run WORKFLOW=.github/workflows/security.yml JOB=scan"
	@echo "  make actions-dry-run WORKFLOW=.github/workflows/docs.yml"

actions-run:
	@echo "🎭 GitHub Actions Simulator - ワークフロー実行"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "❌ WORKFLOW パラメーターが必要です"; \
		echo ""; \
		echo "📋 使用可能なワークフロー:"; \
		find .github/workflows -name "*.yml" -o -name "*.yaml" | sort | nl -w2 -s') '; \
		echo ""; \
		echo "💡 使用例:"; \
		echo "  make actions-run WORKFLOW=.github/workflows/ci.yml"; \
		echo "  make actions-run WORKFLOW=.github/workflows/security.yml JOB=scan"; \
		exit 1; \
	fi
	@echo "🚀 実行ワークフロー: $(WORKFLOW)"
	@if [ -n "$(JOB)" ]; then \
		echo "🎯 ジョブ: $(JOB)"; \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) -e JOB_NAME=$(JOB) actions-simulator \
			python main.py actions simulate $(WORKFLOW) --job $(JOB) $(if $(VERBOSE),--verbose,); \
	else \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) actions-simulator \
			python main.py actions simulate $(WORKFLOW) $(if $(VERBOSE),--verbose,); \
	fi
	@echo "🎭 GitHub Actions Simulator - カスタムワークフロー"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "❌ WORKFLOW パラメーターが必要です"; \
		echo "使用例: make actions-simulate WORKFLOW=.github/workflows/ci.yml"; \
		echo "使用例: make actions-simulate WORKFLOW=.github/workflows/ci.yml JOB=test"; \
		exit 1; \
	fi
	@echo "📝 ワークフロー: $(WORKFLOW)"
	@if [ -n "$(JOB)" ]; then \
		echo "🎯 ジョブ: $(JOB)"; \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) -e JOB_NAME=$(JOB) actions-simulator \
			python main.py actions simulate $(WORKFLOW) --job $(JOB) $(if $(VERBOSE),--verbose,); \
	else \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) actions-simulator \
			python main.py actions simulate $(WORKFLOW) $(if $(VERBOSE),--verbose,); \
	fi

actions-validate:
	@echo "✅ GitHub Actions ワークフロー検証"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "📋 全ワークフローを検証"; \
		docker compose --profile tools run --rm actions-simulator \
			python main.py actions validate .github/workflows/; \
	else \
		echo "📝 検証対象: $(WORKFLOW)"; \
		docker compose --profile tools run --rm actions-simulator \
			python main.py actions validate $(WORKFLOW); \
	fi

actions-dry-run:
	@echo "🧪 GitHub Actions ドライラン実行"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "❌ WORKFLOW パラメーターが必要です"; \
		echo "使用例: make actions-dry-run WORKFLOW=.github/workflows/ci.yml"; \
		exit 1; \
	fi
	docker compose --profile tools run --rm actions-simulator \
		python main.py actions simulate $(WORKFLOW) --dry-run $(if $(VERBOSE),--verbose,)

actions-api:
	@echo "☁️  GitHub Actions Simulator REST API サーバー起動"
	@echo "   HOST=$${HOST:-0.0.0.0} PORT=$${PORT:-8000}"
	./scripts/start-actions-api.sh

test:
	./tests/integration_test.sh

# Bats管理
check-bats:
	@if ! which bats > /dev/null 2>&1; then \
		echo "❌ Bats testing framework not found"; \
		echo "Installing Bats via Homebrew..."; \
		$(MAKE) install-bats; \
	else \
		echo "✅ Bats $(shell bats --version) is available"; \
	fi

install-bats:
	@echo "📦 Installing Bats testing framework..."
	@if which brew > /dev/null 2>&1; then \
		brew install bats-core && \
		echo "✅ Bats installed successfully via Homebrew"; \
	else \
		echo "❌ Homebrew not found. Please install Homebrew first"; \
		echo "Or install Bats manually from: https://github.com/bats-core/bats-core"; \
		exit 1; \
	fi

test-bats: check-bats
	@echo "🧪 Bats テストスイート実行"
	bats tests/test_*.bats

test-docker: check-bats
	@echo "🐳 Docker ビルドテスト"
	bats tests/test_docker_build.bats

test-services: check-bats
	@echo "🚀 サービステスト"
	bats tests/test_services.bats

test-security: check-bats
	@echo "🔒 セキュリティテスト"
	bats tests/test_security.bats

test-integration:
	@echo "🔗 統合テスト"
	bats tests/test_integration.bats

test-all:
	@echo "🎯 全テスト実行"
	make test-docker
	make test-services
	make test-security
	make test-integration
	make test

security:
	@echo "🔒 セキュリティスキャン実行"
	docker build -t mcp-docker:latest . || (echo "❌ Build失敗"; exit 1)
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image mcp-docker:latest

lint:
	docker run --rm -i hadolint/hadolint < Dockerfile
	shellcheck scripts/*.sh tests/*.sh
	pipx run uv run yamllint -c .yamllint.yml docker-compose.yml

pre-commit:
	pipx run uv run pre-commit run --all-files

version:
	@./scripts/get-current-version.sh
	@echo ""
	@echo "💻 Application Version:"
	@uv run python main.py --version

version-sync:
	@echo "🔄 Synchronizing versions..."
	@PYPROJECT_VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	if [ -f "main.py" ]; then \
		MAIN_PY_VERSION=$$(grep '^__version__ = ' main.py | sed 's/__version__ = "\(.*\)"/\1/'); \
		if [ "$$PYPROJECT_VERSION" != "$$MAIN_PY_VERSION" ]; then \
			echo "📝 Updating main.py version: $$MAIN_PY_VERSION → $$PYPROJECT_VERSION"; \
			sed -i "s/__version__ = \"$$MAIN_PY_VERSION\"/__version__ = \"$$PYPROJECT_VERSION\"/" main.py; \
			echo "✅ Version synchronized: $$PYPROJECT_VERSION"; \
		else \
			echo "✅ Versions already synchronized: $$PYPROJECT_VERSION"; \
		fi; \
	else \
		echo "❌ main.py not found"; \
	fi

release-check:
	@echo "🔍 リリース準備状況チェック"
	@echo "Version: $(shell grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"
	@echo "Git status:"
	@git status --porcelain
	@echo "Last commit:"
	@git log -1 --oneline
	@echo "Tests:"
	@make test-all
	@echo "Security:"
	@make security
	@echo "✅ リリース準備完了"

setup-branch-protection:
	@echo "🛡️ ブランチ保護設定"
	@./scripts/setup-branch-protection.sh

sbom:
	@echo "📋 SBOM生成"
	uv run python scripts/generate-sbom.py --format cyclonedx --output sbom-cyclonedx.json
	uv run python scripts/generate-sbom.py --format spdx --output sbom-spdx.json
	@echo "✅ SBOM生成完了: sbom-cyclonedx.json, sbom-spdx.json"

audit-deps:
	@echo "🔍 依存関係監査"
	uv run python scripts/audit-dependencies.py --output audit-report.json || echo "⚠️  監査完了（一部ツール不可）"
	@echo "✅ 監査レポート: audit-report.json"

validate-security:
	@echo "🛡️  セキュリティバリデーション"
	./scripts/validate-user-permissions.sh
	@echo "✅ セキュリティ検証完了"

docs:
	@echo "📚 ドキュメント生成"
	./scripts/generate-docs.sh all
	@echo "✅ ドキュメント生成完了: docs/_build/html/index.html"

docs-serve:
	@echo "🌐 ドキュメントサーバー起動"
	@if [ -d "docs/_build/html" ]; then \
		echo "📍 http://localhost:8000 でドキュメントを確認できます"; \
		echo "Ctrl+C で停止"; \
		cd docs/_build/html && python3 -m http.server 8000; \
	else \
		echo "❌ ドキュメントがビルドされていません"; \
		echo "最初に 'make docs' を実行してください"; \
	fi

docs-clean:
	@echo "🧹 ドキュメントビルドをクリア"
	rm -rf docs/_build docs/api
	@echo "✅ クリーンアップ完了"
