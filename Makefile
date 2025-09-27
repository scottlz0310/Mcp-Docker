.PHONY: help build start stop logs clean datetime actions actions-auto actions-list actions-run test test-bats test-docker test-services test-security test-integration test-all security lint pre-commit setup-branch-protection release-check version version-sync sbom audit-deps validate-security install-bats check-bats setup-docker health-check verify-containers docker-setup docker-health actions-setup actions-verify

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
	@echo "  make actions   - Interactive GitHub Actions Simulator (Docker)"
	@echo ""
	@echo "Docker Setup & Health:"
	@echo "  make setup-docker      - Setup Docker integration environment"
	@echo "  make health-check      - Run comprehensive Docker health check"
	@echo "  make verify-containers - Verify container startup and configuration"
	@echo "  make docker-setup      - Alias for setup-docker"
	@echo "  make docker-health     - Alias for health-check"
	@echo "  make actions-setup     - Setup Actions Simulator environment"
	@echo "  make actions-verify    - Verify Actions Simulator container"
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

# GitHub Actions Simulator（Docker版）
	if [ -z "$$workflows" ]; then \
		echo "❌ ワークフローファイルが見つかりません"; \
		exit 1; \
	@find .github/workflows -name "*.yml" -o -name "*.yaml" | head -5
	@echo ""
	@echo "🚀 デフォルト実行: CI ワークフロー"
	docker compose --profile tools run --rm actions-simulator \
		uv run python main.py actions simulate .github/workflows/ci.yml --fail-fast
	echo ""; \
	selected=""; \
	if [ -n "$(WORKFLOW)" ]; then \
		if [ -f "$(WORKFLOW)" ]; then \
			selected="$(WORKFLOW)"; \
		else \
			match=$$(echo "$$workflows" | grep -Fx "$(WORKFLOW)"); \
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
		selected=$$(echo "$$workflows" | sed -n "$(INDEX)p"); \
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
		selected=$$(echo "$$workflows" | sed -n "$${choice}p"); \
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
	set -- uv run python main.py actions; \
	if [ -n "$(VERBOSE)" ]; then \
		set -- "$$@" --verbose; \
	fi; \
	if [ -n "$(QUIET)" ]; then \
		set -- "$$@" --quiet; \
	fi; \
	if [ -n "$(DEBUG)" ]; then \
		set -- "$$@" --debug; \
	fi; \
	if [ -n "$(CONFIG)" ]; then \
		set -- "$$@" --config "$(CONFIG)"; \
	fi; \
	set -- "$$@" simulate "$$selected"; \
	if [ -n "$(JOB)" ]; then \
		set -- "$$@" --job "$(JOB)"; \
	fi; \
	if [ -n "$(DRY_RUN)" ]; then \
		set -- "$$@" --dry-run; \
	fi; \
	if [ -n "$(ENV_FILE)" ]; then \
		set -- "$$@" --env-file "$(ENV_FILE)"; \
	fi; \
	if [ -n "$(EVENT)" ]; then \
		set -- "$$@" --event "$(EVENT)"; \
	fi; \
	if [ -n "$(REF)" ]; then \
		set -- "$$@" --ref "$(REF)"; \
	fi; \
	if [ -n "$(ACTOR)" ]; then \
		set -- "$$@" --actor "$(ACTOR)"; \
	fi; \
	if [ -n "$(ENV_VARS)" ]; then \
		for kv in $(ENV_VARS); do \
			set -- "$$@" --env "$$kv"; \
		done; \
	fi; \
	if [ -n "$(CLI_ARGS)" ]; then \
		set -- "$$@" $(CLI_ARGS); \
	fi; \
	docker compose --profile tools run --rm -e WORKFLOW_FILE="$$selected" actions-simulator "$$@"

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
			uv run python main.py actions simulate $(WORKFLOW) --job $(JOB) $(if $(VERBOSE),--verbose,); \
	else \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) actions-simulator \
			uv run python main.py actions simulate $(WORKFLOW) $(if $(VERBOSE),--verbose,); \
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
			uv run python main.py actions simulate $(WORKFLOW) --job $(JOB) $(if $(VERBOSE),--verbose,); \
	else \
		docker compose --profile tools run --rm -e WORKFLOW_FILE=$(WORKFLOW) actions-simulator \
			uv run python main.py actions simulate $(WORKFLOW) $(if $(VERBOSE),--verbose,); \
	fi

actions-validate:
	@echo "✅ GitHub Actions ワークフロー検証"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "📋 全ワークフローを検証"; \
		docker compose --profile tools run --rm actions-simulator \
			uv run python main.py actions validate .github/workflows/; \
	else \
		echo "📝 検証対象: $(WORKFLOW)"; \
		docker compose --profile tools run --rm actions-simulator \
			uv run python main.py actions validate $(WORKFLOW); \
	fi

actions-dry-run:
	@echo "🧪 GitHub Actions ドライラン実行"
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "❌ WORKFLOW パラメーターが必要です"; \
		echo "使用例: make actions-dry-run WORKFLOW=.github/workflows/ci.yml"; \
		exit 1; \
	fi
	docker compose --profile tools run --rm actions-simulator \
		uv run python main.py actions simulate $(WORKFLOW) --dry-run $(if $(VERBOSE),--verbose,)

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
	uv run security-scan $(if $(IMAGE),--image $(IMAGE),) $(if $(FAIL_ON),--fail-on $(FAIL_ON),) $(if $(SKIP_BUILD),--skip-build,) $(if $(SEVERITY),--severity $(SEVERITY),)
	@echo "✅ セキュリティサマリーは output/security/trivy に保存されました"

lint:
	@echo "🧹 Running MegaLinter (Docker)..."
	docker run --rm \
		-u $$(id -u):$$(id -g) \
		-e APPLY_FIXES=none \
		-e DEFAULT_WORKSPACE=/tmp/lint \
		-e REPORT_OUTPUT_FOLDER=/tmp/lint/megalinter-reports \
		-e HOME=/tmp/lint \
		-v "$(CURDIR)":/tmp/lint \
		oxsecurity/megalinter:v7
	@echo "✅ MegaLinter completed. Reports (if any) are stored in ./megalinter-reports"

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

# Docker Setup & Health Check Targets
setup-docker:
	@echo "🐳 Docker統合環境セットアップ"
	@./scripts/setup-docker-integration.sh
	@echo "✅ Docker統合セットアップ完了"

health-check:
	@echo "🏥 Docker統合ヘルスチェック"
	@./scripts/docker-health-check.sh --comprehensive
	@echo "✅ ヘルスチェック完了"

verify-containers:
	@echo "🔍 コンテナ起動検証"
	@./scripts/verify-container-startup.sh --all
	@echo "✅ コンテナ検証完了"

docker-setup: setup-docker

docker-health: health-check

# Actions Simulator specific targets
actions-setup:
	@echo "🎭 Actions Simulator環境セットアップ"
	@./scripts/setup-docker-integration.sh
	@echo "🚀 Actions Simulatorコンテナを起動中..."
	@docker-compose --profile tools up -d actions-simulator
	@echo "⏳ コンテナの起動を待機中..."
	@sleep 10
	@./scripts/verify-container-startup.sh --actions-simulator
	@echo "✅ Actions Simulator準備完了"

actions-verify:
	@echo "🔍 Actions Simulatorコンテナ検証"
	@./scripts/verify-container-startup.sh --actions-simulator
	@echo "✅ Actions Simulator検証完了"

# Quick health check targets
health-daemon:
	@./scripts/docker-health-check.sh --daemon-only

health-socket:
	@./scripts/docker-health-check.sh --socket-only

health-container:
	@./scripts/docker-health-check.sh --container-test-only

health-network:
	@./scripts/docker-health-check.sh --network-only

health-act:
	@./scripts/docker-health-check.sh --act-only
