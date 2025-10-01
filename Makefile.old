.PHONY: help build start stop logs clean datetime actions actions-auto actions-list actions-run test test-bats test-docker test-services test-security test-integration test-all test-hangup test-hangup-unit test-hangup-integration test-hangup-e2e test-hangup-all test-hangup-bats security lint pre-commit setup-branch-protection release-check version version-sync sbom audit-deps validate-security install-bats check-bats setup-docker health-check verify-containers docker-setup docker-health actions-setup actions-verify test-hangup-ci test-hangup-ci-full test-hangup-ci-matrix test-hangup-regression check-docs docs-consistency docker-override-setup docker-override-validate docker-override-dev docker-override-prod docker-override-monitoring docker-override-security validate-templates validate-templates-syntax validate-templates-functionality validate-templates-ci validate-templates-report test-comprehensive test-comprehensive-quick test-comprehensive-full test-comprehensive-report test-comprehensive-ci

help:
	@echo "MCP Docker Environment Commands:"
	@echo "  make build     - Build all Docker images (main + actions)"
	@echo "  make build-main - Build main services only (github-mcp + datetime)"
	@echo "  make build-actions - Build actions-simulator only"
	@echo "  make start     - Start all MCP services (GitHub MCP + DateTime validator)"
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
	@echo "Docker Customization:"
	@echo "  make docker-override-setup      - Setup Docker override configuration"
	@echo "  make docker-override-validate   - Validate Docker override settings"
	@echo "  make docker-override-dev        - Start development environment"
	@echo "  make docker-override-prod       - Start production environment"
	@echo "  make docker-override-monitoring - Start with monitoring stack"
	@echo "  make docker-override-security   - Run security scanning"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run integration tests"
	@echo "  make test-all  - Run all test suites"
	@echo "  make test-bats - Run Bats test suite"
	@echo "  make install-bats - Install Bats testing framework"
	@echo ""
	@echo "Hangup Scenario Testing:"
	@echo "  make test-hangup           - Run comprehensive hangup scenario tests"
	@echo "  make test-hangup-unit      - Run hangup unit tests only"
	@echo "  make test-hangup-integration - Run hangup integration tests only"
	@echo "  make test-hangup-e2e       - Run hangup end-to-end tests only"
	@echo "  make test-hangup-all       - Run all hangup tests with detailed reporting"
	@echo "  make test-hangup-bats      - Run hangup BATS tests"
	@echo "  make test-hangup-ci        - Run CI-optimized hangup tests"
	@echo "  make test-hangup-ci-full   - Run complete CI hangup test suite"
	@echo "  make test-hangup-regression - Run hangup regression tests"
	@echo ""
	@echo "Security & Quality:"
	@echo "  make security  - Run security scan"
	@echo "  make sbom      - Generate SBOM"
	@echo "  make audit-deps - Audit dependencies"
	@echo "  make check-docs - Check documentation consistency"
	@echo "  make validate-templates - Validate all template files"
	@echo "  make test-comprehensive - Run comprehensive test suite"
	@echo ""
	@echo "Release Management:"
	@echo "  make version           - Show current version"
	@echo "  make version-sync      - Sync versions between pyproject.toml and main.py"
	@echo "  make release-check     - Check release readiness"
	@echo "  make setup-branch-protection - Setup branch protection"
	@echo ""
	@echo "CHANGELOG Management:"
	@echo "  make changelog-add TYPE=<type> DESC='<description>' - Add new entry"
	@echo "  make changelog-release VERSION=<version>           - Prepare release"
	@echo "  make changelog-validate                            - Validate format"
	@echo "  make changelog-show                                - Show unreleased"
	@echo "  make changelog-generate FROM=<ref> TO=<ref>        - Generate from commits"
	@echo ""
	@echo "GitHub Actions Simulator:"
	@echo "  make actions             - Interactive workflow selection (Docker)"
	@echo "  make actions-auto        - Run default CI workflow (Docker)"
	@echo "  make actions-list        - List available workflows"
	@echo "  make actions-run         - Run workflow: WORKFLOW=path [JOB=job] [VERBOSE=1]"
	@echo "  make actions-validate    - Validate workflows: [WORKFLOW=path]"
	@echo "  make actions-dry-run     - Dry run workflow: WORKFLOW=path [VERBOSE=1]"
	@echo ""
	@echo "GitHub MCP Server:"
	@echo "  Use: docker run -e GITHUB_PERSONAL_ACCESS_TOKEN=\$GITHUB_PERSONAL_ACCESS_TOKEN mcp-docker-github-mcp"

build:
	@echo "🔨 Building all Docker images..."
	docker compose build
	docker compose --profile tools build actions-simulator
	@echo "✅ All images built successfully"

build-main:
	@echo "🔨 Building main services (github-mcp + datetime)..."
	docker compose build
	@echo "✅ Main services built successfully"

build-actions:
	@echo "🔨 Building actions-simulator..."
	docker compose --profile tools build actions-simulator
	@echo "✅ Actions simulator built successfully"

start:
	docker compose up -d github-mcp datetime-validator

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
actions:
	@echo "🎭 GitHub Actions Simulator - インタラクティブ実行"
	@workflows=$$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null); \
	if [ -z "$$workflows" ]; then \
		echo "❌ ワークフローファイルが見つかりません"; \
		exit 1; \
	fi; \
	default_selection=".github/workflows/ci.yml"; \
	echo "📋 使用可能なワークフロー:"; \
	echo "$$workflows" | nl -w2 -s') '; \
	echo ""; \
	echo "🚀 デフォルト実行: CI ワークフロー"; \
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
	echo "🔧 Preparing environment..."; \
	./scripts/fix-permissions.sh; \
	USER_ID=$(id -u) GROUP_ID=$(id -g) docker compose --profile tools run --rm \
		-e WORKFLOW_FILE="$$selected" \
		-e ACT_LOG_LEVEL=info \
		-e ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest \
		-e DOCKER_HOST=unix:///var/run/docker.sock \
		actions-simulator \
		uv run python main.py actions simulate "$$selected" $(if $(VERBOSE),--verbose,) $(if $(JOB),--job $(JOB),)

actions-auto:
	@echo "🎭 GitHub Actions Simulator - 自動実行 (CI)"
	@echo "📋 使用可能なワークフロー:"
	@find .github/workflows -name "*.yml" -o -name "*.yaml" | head -5
	@echo ""
	@echo "🚀 デフォルト実行: CI ワークフロー"
	docker compose --profile tools run --rm \
		-e ACT_LOG_LEVEL=info \
		-e ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest \
		-e DOCKER_HOST=unix:///var/run/docker.sock \
		actions-simulator \
		uv run python main.py actions simulate .github/workflows/ci.yml --fail-fast

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
		echo "✅ Bats $$(bats --version) is available"; \
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
	uv run pre-commit run --all-files

validate-precommit:
	@echo "🔍 Pre-commit設定検証"
	@./scripts/validate-precommit-config.sh

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
	@echo "Version: $$(grep '^version = ' pyproject.toml | sed 's/version = \"\(.*\)\"/\1/')"
	@echo "Git status:"
	@git status --porcelain
	@echo "Last commit:"
	@git log -1 --oneline
	@echo "Documentation:"
	@make check-docs
	@echo "Tests:"
	@make test-all
	@echo "Security:"
	@make security
	@echo "✅ リリース準備完了"

setup-branch-protection:
	@echo "🛡️ ブランチ保護設定"
	@./scripts/setup-branch-protection.sh

# CHANGELOG管理
changelog-add:
	@if [ -z "$(TYPE)" ] || [ -z "$(DESC)" ]; then \
		echo "使用方法: make changelog-add TYPE=<type> DESC='<description>'"; \
		echo "例: make changelog-add TYPE=added DESC='新しい診断機能を追加'"; \
		echo "TYPE: added, changed, deprecated, removed, fixed, security"; \
		exit 1; \
	fi
	@./scripts/manage-changelog.sh add-entry $(TYPE) "$(DESC)"

changelog-release:
	@if [ -z "$(VERSION)" ]; then \
		echo "使用方法: make changelog-release VERSION=<version>"; \
		echo "例: make changelog-release VERSION=1.2.0"; \
		exit 1; \
	fi
	@./scripts/manage-changelog.sh prepare-release $(VERSION)

changelog-validate:
	@./scripts/manage-changelog.sh validate

changelog-show:
	@./scripts/manage-changelog.sh show-unreleased

changelog-generate:
	@if [ -z "$(FROM)" ] || [ -z "$(TO)" ]; then \
		echo "使用方法: make changelog-generate FROM=<ref> TO=<ref>"; \
		echo "例: make changelog-generate FROM=v1.1.0 TO=HEAD"; \
		exit 1; \
	fi
	@./scripts/manage-changelog.sh generate-from-commits $(FROM) $(TO)

sbom:
	@echo "📋 SBOM生成"
	uv run python scripts/generate-sbom.py --format cyclonedx --output sbom-cyclonedx.json
	uv run python scripts/generate-sbom.py --format spdx --output sbom-spdx.json
	@echo "✅ SBOM生成完了: sbom-cyclonedx.json, sbom-spdx.json"

audit-deps:
	@echo "🔍 依存関係監査"
	uv run python scripts/audit-dependencies.py --output audit-report.json || echo "⚠️  監査完了（一部ツール不可）"
	@echo "✅ 監査レポート: audit-report.json"

check-docs:
	@echo "📚 ドキュメント整合性チェック"
	uv run python scripts/check-docs-consistency.py --verbose
	@echo "✅ ドキュメント整合性チェック完了"

docs-consistency: check-docs

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
	@docker compose --profile tools up -d actions-simulator
	@echo "⏳ コンテナの起動を待機中..."
	@sleep 10
	@./scripts/verify-container-startup.sh --actions-simulator
	@echo "✅ Actions Simulator準備完了"

actions-verify:
	@echo "🔍 Actions Simulatorコンテナ検証"
	@./scripts/verify-container-startup.sh --actions-simulator
	@echo "✅ Actions Simulator検証完了"

# Actions Simulator - デバッグ用常駐サーバー
actions-server:
	@echo "🚀 Actions Simulator - 常駐サーバーモード起動"
	@echo "📋 デバッグ用HTTPサーバーを起動します"
	@echo "   - ポート: http://localhost:8000"
	@echo "   - ログレベル: DEBUG"
	@echo "   - ホットリロード: 有効"
	@echo ""
	@./scripts/fix-permissions.sh
	USER_ID=$(id -u) GROUP_ID=$(id -g) docker compose --profile debug up -d actions-server
	@echo ""
	@echo "✅ Actions Simulatorサーバーが起動しました"
	@echo "📋 アクセス方法:"
	@echo "   - HTTP API: http://localhost:8000"
	@echo "   - ログ確認: make actions-server-logs"
	@echo "   - シェル接続: make actions-shell"
	@echo "   - 停止: make actions-server-stop"

actions-server-logs:
	@echo "📋 Actions Simulatorサーバーログ"
	docker compose --profile debug logs -f actions-server

actions-server-stop:
	@echo "🛑 Actions Simulatorサーバー停止"
	docker compose --profile debug stop actions-server
	docker compose --profile debug rm -f actions-server

actions-server-restart:
	@echo "🔄 Actions Simulatorサーバー再起動"
	@make actions-server-stop
	@make actions-server

# Actions Simulator - インタラクティブシェル
actions-shell:
	@echo "🐚 Actions Simulator - インタラクティブシェル"
	@echo "📋 デバッグ用シェルに接続します"
	@echo ""
	@./scripts/fix-permissions.sh
	USER_ID=$(id -u) GROUP_ID=$(id -g) docker compose --profile debug run --rm actions-shell

actions-shell-exec:
	@echo "🐚 Actions Simulator - 既存コンテナにシェル接続"
	docker compose --profile debug exec actions-server bash

# Actions Simulator - デバッグ用ユーティリティ
actions-debug:
	@echo "🐛 Actions Simulator - デバッグ情報"
	@echo ""
	@echo "📋 コンテナ状態:"
	@docker compose --profile debug ps actions-server actions-shell 2>/dev/null || echo "  デバッグコンテナは起動していません"
	@echo ""
	@echo "📋 ログファイル:"
	@ls -la logs/ 2>/dev/null || echo "  ログディレクトリが見つかりません"
	@echo ""
	@echo "📋 出力ファイル:"
	@ls -la output/actions/ 2>/dev/null || echo "  出力ディレクトリが見つかりません"
	@echo ""
	@echo "📋 利用可能なコマンド:"
	@echo "  make actions-server      - 常駐サーバー起動"
	@echo "  make actions-shell       - インタラクティブシェル"
	@echo "  make actions-server-logs - サーバーログ表示"
	@echo "  make actions-debug       - デバッグ情報表示"

actions-test-server:
	@echo "🧪 Actions Simulatorサーバーテスト"
	@echo "📋 HTTPサーバーの動作確認"
	@if curl -s http://localhost:8000/health >/dev/null 2>&1; then \
		echo "✅ サーバーは正常に動作しています"; \
		echo "📋 ヘルスチェック:"; \
		curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health; \
	else \
		echo "❌ サーバーに接続できません"; \
		echo "💡 サーバーを起動してください: make actions-server"; \
	fi

# Actions Simulator - デバッグスクリプトエイリアス
actions-debug-script:
	@./scripts/actions-debug.sh $(ARGS)

actions-status:
	@./scripts/actions-debug.sh status

actions-clean:
	@./scripts/actions-debug.sh clean

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

# Hangup Scenario Testing Targets
test-hangup:
	@echo "🔧 ハングアップシナリオテスト実行"
	@echo "📋 包括的なハングアップ条件をテストし、修正を検証します"
	@echo ""
	uv run python tests/run_hangup_tests.py --verbose

test-hangup-unit:
	@echo "🧪 ハングアップ単体テスト実行"
	@echo "📋 DiagnosticService、ProcessMonitor、ExecutionTracerの単体テスト"
	@echo ""
	uv run python tests/run_hangup_tests.py --unit-only --verbose

test-hangup-integration:
	@echo "🔗 ハングアップ統合テスト実行"
	@echo "📋 様々なハングアップ条件をシミュレートする統合テスト"
	@echo ""
	uv run python tests/run_hangup_tests.py --integration-only --verbose

test-hangup-e2e:
	@echo "🎯 ハングアップエンドツーエンドテスト実行"
	@echo "📋 実際のワークフローファイルでの信頼性テスト"
	@echo ""
	uv run python tests/run_hangup_tests.py --e2e-only --verbose

test-hangup-all:
	@echo "🚀 全ハングアップテスト実行（詳細レポート付き）"
	@echo "📋 単体・統合・E2E・パフォーマンス・ストレステストを実行"
	@echo ""
	uv run python tests/run_hangup_tests.py --verbose
	@echo ""
	@echo "📊 テスト結果サマリー:"
	@echo "  - 単体テスト: DiagnosticService, ProcessMonitor, ExecutionTracer"
	@echo "  - 統合テスト: ハングアップシナリオシミュレーション"
	@echo "  - E2Eテスト: 実ワークフローファイルでの動作確認"
	@echo "  - パフォーマンステスト: 応答時間とメモリ使用量"
	@echo "  - ストレステスト: 並行実行時の安定性"

test-hangup-bats: check-bats
	@echo "🧪 ハングアップシナリオ BATS テスト実行"
	@echo "📋 シェル環境でのハングアップ条件テスト"
	@echo ""
	bats tests/test_hangup_scenarios.bats

test-hangup-quick:
	@echo "⚡ ハングアップクイックテスト実行"
	@echo "📋 主要なハングアップシナリオのみを高速実行"
	@echo ""
	uv run python -m pytest tests/test_hangup_scenarios_comprehensive.py::TestHangupScenariosComprehensive::test_docker_socket_hangup_scenario -v
	uv run python -m pytest tests/test_hangup_scenarios_comprehensive.py::TestHangupScenariosComprehensive::test_subprocess_deadlock_hangup_scenario -v
	uv run python -m pytest tests/test_hangup_scenarios_comprehensive.py::TestHangupScenariosComprehensive::test_auto_recovery_fallback_mode_scenario -v

# 簡潔なPythonスクリプト実行ターゲット
test-hangup-performance:
	@echo "⚡ ハングアップパフォーマンステスト実行"
	@echo "📋 診断・検出・復旧機能のパフォーマンス測定"
	@echo ""
	@uv run python -c "from tests.run_hangup_tests import HangupTestRunner; runner = HangupTestRunner(verbose=True); runner.run_performance_tests()"

test-hangup-stress:
	@echo "💪 ハングアップストレステスト実行"
	@echo "📋 高負荷・並行実行時の安定性テスト"
	@echo ""
	@uv run python -c "from tests.run_hangup_tests import HangupTestRunner; runner = HangupTestRunner(verbose=True); runner.run_stress_tests()"

test-hangup-docker:
	@echo "🐳 Docker環境ハングアップテスト実行"
	@echo "📋 Docker統合環境でのハングアップシナリオテスト"
	@echo ""
	@echo "🔍 Docker環境チェック"
	@make health-check
	@echo ""
	@echo "🧪 Docker環境でのハングアップテスト実行"
	docker compose --profile tools run --rm actions-simulator \
		uv run python tests/run_hangup_tests.py --verbose

test-hangup-ci:
	@echo "🤖 CI環境ハングアップテスト実行"
	@echo "📋 CI/CD環境に適したハングアップテスト"
	@echo ""
	PYTEST_TIMEOUT=180 uv run python tests/run_hangup_tests.py

test-hangup-ci-full:
	@echo "🚀 CI環境完全ハングアップテスト実行"
	@echo "📋 CI/CDパイプライン用の包括的ハングアップテスト"
	@echo ""
	@echo "🔍 1. 基本診断テスト"
	@make test-hangup-unit
	@echo ""
	@echo "🔗 2. 統合テスト"
	@make test-hangup-integration
	@echo ""
	@echo "⚡ 3. パフォーマンステスト（軽量版）"
	@make test-hangup-performance
	@echo ""
	@echo "🔄 4. リグレッションテスト"
	@uv run python -c "from services.actions.diagnostic import DiagnosticService; from services.actions.hangup_detector import HangupDetector; from services.actions.logger import ActionsLogger; logger = ActionsLogger(verbose=True); print('🔍 CI環境リグレッションテスト'); service = DiagnosticService(logger=logger); detector = HangupDetector(logger=logger); docker_result = service.check_docker_connectivity(); assert docker_result.status != 'ERROR', f'Docker接続回帰: {docker_result.message}'; print('✅ Docker接続回帰テスト完了'); process_issues = detector.detect_subprocess_deadlock(); critical_issues = [i for i in process_issues if i.severity.value >= 3]; assert len(critical_issues) == 0, f'プロセス監視回帰: {len(critical_issues)}件'; print('✅ プロセス監視回帰テスト完了'); print('✅ CI環境リグレッションテスト完了')"
	@echo ""
	@echo "✅ CI環境完全ハングアップテスト完了"

test-hangup-ci-matrix:
	@echo "🎯 CI環境マトリクステスト実行"
	@echo "📋 複数環境でのハングアップテスト"
	@echo ""
	@echo "🐍 Python環境情報:"
	@python --version
	@echo "🐳 Docker環境情報:"
	@docker --version
	@docker system info | head -10
	@echo ""
	@echo "🧪 環境固有テスト実行"
	@uv run python -c "import os; import platform; import psutil; from services.actions.diagnostic import DiagnosticService; from services.actions.hangup_detector import HangupDetector; from services.actions.logger import ActionsLogger; logger = ActionsLogger(verbose=True); print(f'🔍 環境情報'); print(f'OS: {platform.system()} {platform.release()}'); print(f'Python: {platform.python_version()}'); print(f'CPU: {psutil.cpu_count()} cores'); print(f'Memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB'); service = DiagnosticService(logger=logger); detector = HangupDetector(logger=logger); health_report = service.run_comprehensive_health_check(); print(f'システムヘルス: {health_report.get(\"status\", \"unknown\")}'); analysis = detector.analyze_hangup_conditions(); print(f'検出された問題: {len(analysis.issues)}件'); env_issues = []; docker_issues = detector.detect_docker_socket_issues() if platform.system() == 'Linux' else []; permission_issues = detector.detect_permission_issues() if platform.system() == 'Darwin' else []; env_issues.extend(docker_issues); env_issues.extend(permission_issues); critical_env_issues = [i for i in env_issues if i.severity.value >= 3]; assert len(critical_env_issues) == 0, f'環境固有の重大な問題: {len(critical_env_issues)}件'; print('✅ CI環境マトリクステスト完了')"

test-hangup-regression:
	@echo "🔄 ハングアップリグレッションテスト実行"
	@echo "📋 自動化されたリグレッション検出とパフォーマンス監視"
	@echo ""
	@./scripts/run-hangup-regression-tests.sh --verbose

test-hangup-debug:
	@echo "🐛 ハングアップデバッグモードテスト実行"
	@echo "📋 詳細なデバッグ情報付きでハングアップテストを実行"
	@echo ""
	ACTIONS_SIMULATOR_VERBOSE=true \
	ACTIONS_SIMULATOR_DEBUG=true \
	uv run python tests/run_hangup_tests.py --verbose

test-hangup-mock:
	@echo "🎭 モックモードハングアップテスト実行"
	@echo "📋 モックエンジンを使用したハングアップシナリオテスト"
	@echo ""
	ACTIONS_SIMULATOR_ENGINE=mock \
	uv run python tests/run_hangup_tests.py --verbose

test-hangup-report:
	@echo "📊 ハングアップテストレポート生成"
	@echo "📋 詳細なテスト結果レポートを生成"
	@echo ""
	@mkdir -p output/test-reports
	uv run python tests/run_hangup_tests.py --verbose > output/test-reports/hangup-test-report.txt 2>&1
	@echo "✅ テストレポートを生成しました: output/test-reports/hangup-test-report.txt"
	@echo ""
	@echo "📋 レポート内容:"
	@echo "  - 全テストカテゴリの実行結果"
	@echo "  - パフォーマンスメトリクス"
	@echo "  - エラー詳細とトラブルシューティング情報"
	@echo "  - 推奨改善事項"

# ハングアップテスト環境セットアップ
setup-hangup-test-env:
	@echo "🔧 ハングアップテスト環境セットアップ"
	@echo "📋 テスト実行に必要な環境を準備"
	@echo ""
	@echo "🐍 Python依存関係チェック"
	uv sync
	@echo ""
	@echo "🐳 Docker環境チェック"
	@make health-check
	@echo ""
	@echo "🧪 テストフレームワーク確認"
	@make check-bats
	@echo ""
	@echo "📁 テスト出力ディレクトリ作成"
	@mkdir -p output/test-reports
	@mkdir -p output/debug-bundles
	@echo ""
	@echo "✅ ハングアップテスト環境準備完了"

# ハングアップテスト環境クリーンアップ
cleanup-hangup-test-env:
	@echo "🧹 ハングアップテスト環境クリーンアップ"
	@echo "📋 テスト実行で生成されたファイルを削除"
	@echo ""
	@rm -rf output/test-reports/hangup-*
	@rm -rf output/debug-bundles/*
	@rm -rf /tmp/hangup_test_*
	@echo "✅ ハングアップテスト環境クリーンアップ完了"
# =============================================================================
# Docker Customization Targets
# =============================================================================

# Docker Override Setup
docker-override-setup:
	@echo "🐳 Docker Override設定セットアップ"
	@echo "📋 カスタマイズテンプレートから設定ファイルを作成します"
	@echo ""
	@if [ ! -f docker-compose.override.yml ]; then \
		echo "📄 docker-compose.override.yml を作成中..."; \
		if [ "$(FULL)" = "1" ]; then \
			cp docker-compose.override.yml.sample docker-compose.override.yml; \
			echo "✅ フル機能Override設定ファイルを作成しました"; \
		else \
			cp docker-compose.override.yml.simple docker-compose.override.yml; \
			echo "✅ シンプルOverride設定ファイルを作成しました"; \
			echo "💡 フル機能版が必要な場合: make docker-override-setup FULL=1"; \
		fi; \
	else \
		echo "ℹ️  docker-compose.override.yml は既に存在します"; \
	fi
	@echo ""
	@if [ ! -f .env ]; then \
		echo "📄 .env ファイルを作成中..."; \
		cp .env.example .env; \
		echo "✅ 環境変数ファイルを作成しました"; \
		echo "⚠️  .env ファイルの設定を確認してください"; \
	else \
		echo "ℹ️  .env ファイルは既に存在します"; \
	fi
	@echo ""
	@echo "📚 次のステップ:"
	@echo "  1. vi docker-compose.override.yml  # 設定をカスタマイズ"
	@echo "  2. vi .env                          # 環境変数を設定"
	@echo "  3. make docker-override-validate    # 設定を検証"
	@echo "  4. make docker-override-dev         # 開発環境で起動"

# Docker Override Validation
docker-override-validate:
	@echo "🔍 Docker Override設定検証"
	@echo "📋 設定ファイルの妥当性をチェックします"
	@echo ""
	@./scripts/validate-docker-override.sh --verbose
	@echo ""
	@echo "📊 設定サマリー:"
	@docker-compose config --services | sed 's/^/  - /'
	@echo ""
	@echo "💡 ヒント:"
	@echo "  - 詳細な検証: make docker-override-validate VERBOSE=1"
	@echo "  - 自動修正: ./scripts/validate-docker-override.sh --fix"

# Development Environment
docker-override-dev:
	@echo "🚀 開発環境起動 (Docker Override)"
	@echo "📋 開発用設定でサービスを起動します"
	@echo ""
	@echo "🔧 起動するサービス:"
	@echo "  - actions-simulator (開発モード)"
	@echo "  - actions-shell (デバッグシェル)"
	@echo ""
	@docker-compose up -d actions-simulator actions-shell
	@echo ""
	@echo "✅ 開発環境が起動しました"
	@echo ""
	@echo "📋 利用可能なコマンド:"
	@echo "  - ログ確認: docker-compose logs -f actions-simulator"
	@echo "  - シェル接続: docker-compose exec actions-shell bash"
	@echo "  - サービス停止: docker-compose down"
	@echo "  - 状態確認: docker-compose ps"

# Production Environment
docker-override-prod:
	@echo "🏭 本番環境起動 (Docker Override)"
	@echo "📋 本番用設定でサービスを起動します"
	@echo ""
	@echo "🔧 起動するサービス:"
	@echo "  - actions-server (本番モード)"
	@echo ""
	@docker-compose up -d actions-server
	@echo ""
	@echo "✅ 本番環境が起動しました"
	@echo ""
	@echo "📋 利用可能なコマンド:"
	@echo "  - ヘルスチェック: curl http://localhost:8000/health"
	@echo "  - メトリクス確認: curl http://localhost:8000/metrics"
	@echo "  - ログ確認: docker-compose logs -f actions-server"
	@echo "  - サービス停止: docker-compose down"

# Monitoring Stack
docker-override-monitoring:
	@echo "📊 監視スタック起動 (Docker Override)"
	@echo "📋 Prometheus + Grafana 監視環境を起動します"
	@echo ""
	@echo "🔧 起動するサービス:"
	@echo "  - actions-server (メトリクス有効)"
	@echo "  - prometheus (メトリクス収集)"
	@echo "  - grafana (ダッシュボード)"
	@echo ""
	@docker-compose --profile monitoring up -d
	@echo ""
	@echo "✅ 監視スタックが起動しました"
	@echo ""
	@echo "📋 アクセス情報:"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Actions Server: http://localhost:8000"
	@echo ""
	@echo "📊 監視コマンド:"
	@echo "  - リソース監視: docker stats"
	@echo "  - ログ監視: docker-compose logs -f"
	@echo "  - 停止: docker-compose --profile monitoring down"

# =============================================================================
# Quality Gates Integration (Task 19)
# =============================================================================

# 品質ゲート関連
quality-gates: quality-check-docs quality-check-templates quality-check-distribution quality-check-comprehensive

quality-check: automated-quality-check

automated-quality-check:
	@echo "🛡️ 自動品質チェックを実行中..."
	./scripts/automated-quality-check.sh

quality-check-quick:
	@echo "⚡ クイック品質チェックを実行中..."
	./scripts/automated-quality-check.sh --quick

quality-check-strict:
	@echo "🔒 厳格品質チェックを実行中..."
	./scripts/automated-quality-check.sh --strict

quality-check-docs:
	@echo "📚 ドキュメント品質チェックを実行中..."
	./scripts/automated-quality-check.sh --docs-only

quality-check-templates:
	@echo "📋 テンプレート品質チェックを実行中..."
	./scripts/automated-quality-check.sh --templates-only

quality-check-distribution:
	@echo "📦 配布スクリプト品質チェックを実行中..."
	uv run pytest tests/test_comprehensive_distribution.py -v

quality-check-comprehensive:
	@echo "🧪 包括的品質チェックを実行中..."
	./scripts/run-comprehensive-tests.sh

quality-report:
	@echo "📊 品質レポートを生成中..."
	./scripts/automated-quality-check.sh --output-format json --output-file quality-report.json
	@echo "📄 品質レポートが生成されました: quality-report.json"

quality-ci:
	@echo "🤖 CI環境での品質チェックを実行中..."
	./scripts/automated-quality-check.sh --ci --output-format json --output-file ci-quality-report.json

# CI/CD品質ゲート統合
ci-quality-gates:
	@echo "🛡️ CI/CD品質ゲート統合実行中..."
	@echo "📋 配布品質チェック、ドキュメント検証、テンプレート検証を実行"
	@echo ""
	@echo "1️⃣ 配布スクリプト品質チェック"
	@make quality-check-distribution
	@echo ""
	@echo "2️⃣ ドキュメント整合性検証"
	@make quality-check-docs
	@echo ""
	@echo "3️⃣ テンプレート検証"
	@make quality-check-templates
	@echo ""
	@echo "4️⃣ 包括的品質検証"
	@make quality-check-comprehensive
	@echo ""
	@echo "✅ CI/CD品質ゲート統合完了"

# リリース品質確認
release-quality-gates:
	@echo "🚀 リリース品質ゲート実行中..."
	@echo "📋 リリース前の厳格な品質確認を実行"
	@echo ""
	@echo "🔒 厳格モードで品質チェック実行"
	@make quality-check-strict
	@echo ""
	@echo "🧪 包括的テストスイート実行"
	@make test-comprehensive-full
	@echo ""
	@echo "🔒 セキュリティ検証"
	@make security
	@echo ""
	@echo "📊 品質レポート生成"
	@make quality-report
	@echo ""
	@echo "✅ リリース品質ゲート完了"

# 品質メトリクス収集
quality-metrics:
	@echo "📊 品質メトリクス収集中..."
	@mkdir -p output/quality-metrics
	@echo "📈 配布スクリプトメトリクス"
	@find scripts/ -name "*.sh" -exec wc -l {} + > output/quality-metrics/script-lines.txt
	@echo "📈 ドキュメントメトリクス"
	@find . -name "*.md" -not -path "./.git/*" -exec wc -l {} + > output/quality-metrics/doc-lines.txt
	@echo "📈 テンプレートメトリクス"
	@find . \( -name "*.sample" -o -name "*.example" -o -name "*.template" \) -exec wc -l {} + > output/quality-metrics/template-lines.txt
	@echo "📈 テストカバレッジメトリクス"
	@find tests/ -name "*.py" -exec wc -l {} + > output/quality-metrics/test-lines.txt
	@echo "✅ 品質メトリクス収集完了: output/quality-metrics/"

# 品質ダッシュボード
quality-dashboard:
	@echo "📊 品質ダッシュボード表示"
	@echo "=================================="
	@echo "📦 配布スクリプト品質:"
	@find scripts/ -name "*.sh" | wc -l | xargs echo "  スクリプト数:"
	@find scripts/ -name "*.sh" -exec wc -l {} + | tail -1 | awk '{print "  総行数: " $$1}'
	@echo ""
	@echo "📚 ドキュメント品質:"
	@find . -name "*.md" -not -path "./.git/*" | wc -l | xargs echo "  ドキュメント数:"
	@find . -name "*.md" -not -path "./.git/*" -exec wc -l {} + | tail -1 | awk '{print "  総行数: " $$1}' 2>/dev/null || echo "  総行数: 0"
	@echo ""
	@echo "📋 テンプレート品質:"
	@find . \( -name "*.sample" -o -name "*.example" -o -name "*.template" \) | wc -l | xargs echo "  テンプレート数:"
	@find . \( -name "*.sample" -o -name "*.example" -o -name "*.template" \) -exec wc -l {} + | tail -1 | awk '{print "  総行数: " $$1}' 2>/dev/null || echo "  総行数: 0"
	@echo ""
	@echo "🧪 テスト品質:"
	@find tests/ -name "*.py" | wc -l | xargs echo "  テストファイル数:"
	@find tests/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print "  総行数: " $$1}' 2>/dev/null || echo "  総行数: 0"
	@echo ""
	@echo "🛡️ 品質ゲート状態:"
	@if [ -f "quality-report.json" ]; then \
		echo "  最新レポート: 利用可能"; \
		if command -v jq >/dev/null 2>&1; then \
			jq -r '"  全体品質スコア: " + (.overall_summary.quality_score | tostring) + "%"' quality-report.json 2>/dev/null || echo "  全体品質スコア: 解析不可"; \
		fi; \
	else \
		echo "  最新レポート: 未生成"; \
		echo "  💡 make quality-report で生成してください"; \
	fi
	@echo "=================================="

# Security Scanning
docker-override-security:
	@echo "🔒 セキュリティスキャン実行 (Docker Override)"
	@echo "📋 コンテナイメージのセキュリティ検査を実行します"
	@echo ""
	@echo "🔍 実行するスキャン:"
	@echo "  - Trivy (脆弱性スキャン)"
	@echo "  - Grype (依存関係スキャン)"
	@echo "  - Docker Bench (設定チェック)"
	@echo ""
	@make security
	@echo ""
	@echo "✅ セキュリティスキャン完了"

# =============================================================================
# Comprehensive Test Suite Targets (Task 18)
# =============================================================================

# Comprehensive Test Suite - Main targets
test-comprehensive:
	@echo "🚀 包括的テストスイート実行"
	@echo "📋 配布スクリプト、ドキュメント、テンプレート、エンドツーエンドテストを実行"
	@echo ""
	@./scripts/run-comprehensive-tests.sh --full --report

test-comprehensive-quick:
	@echo "⚡ 包括的テストスイート（クイック）実行"
	@echo "📋 必須テストのみを高速実行"
	@echo ""
	@./scripts/run-comprehensive-tests.sh --quick

test-comprehensive-full:
	@echo "🔍 包括的テストスイート（フル）実行"
	@echo "📋 全テストカテゴリを詳細実行"
	@echo ""
	@./scripts/run-comprehensive-tests.sh --full --verbose

test-comprehensive-report:
	@echo "📊 包括的テストレポート生成"
	@echo "📋 詳細なテスト結果レポートを生成"
	@echo ""
	@mkdir -p output/test-reports
	@./scripts/run-comprehensive-tests.sh --full --report --output output/test-reports/comprehensive-test-report.txt
	@echo ""
	@echo "✅ レポートを生成しました: output/test-reports/comprehensive-test-report.txt"

test-comprehensive-ci:
	@echo "🤖 CI環境包括的テスト実行"
	@echo "📋 CI/CD環境に適した包括的テスト"
	@echo ""
	@./scripts/run-comprehensive-tests.sh --ci --report

# Individual comprehensive test components
test-distribution-comprehensive:
	@echo "📦 配布スクリプト包括的テスト"
	@echo "📋 配布スクリプトの全機能をテスト"
	@echo ""
	uv run python -m pytest tests/test_comprehensive_distribution.py -v

test-documentation-comprehensive:
	@echo "📚 ドキュメント整合性包括的テスト"
	@echo "📋 ドキュメント間の整合性とテンプレート動作を検証"
	@echo ""
	uv run python -m pytest tests/test_documentation_consistency.py -v

test-user-experience-comprehensive:
	@echo "👤 ユーザー体験包括的テスト"
	@echo "📋 エンドツーエンドの新規ユーザー体験をテスト"
	@echo ""
	uv run python -m pytest tests/test_end_to_end_user_experience.py -v

test-integration-comprehensive:
	@echo "🔗 統合包括的テスト"
	@echo "📋 全コンポーネントの統合動作をテスト"
	@echo ""
	uv run python -m pytest tests/test_comprehensive_integration_suite.py -v

# Comprehensive test utilities
test-comprehensive-setup:
	@echo "🔧 包括的テスト環境セットアップ"
	@echo "📋 テスト実行に必要な環境を準備"
	@echo ""
	@echo "🐍 Python依存関係チェック"
	uv sync
	@echo ""
	@echo "📁 テスト出力ディレクトリ作成"
	@mkdir -p output/test-reports
	@mkdir -p logs
	@echo ""
	@echo "🧪 テストフレームワーク確認"
	@uv run python -m pytest --version
	@echo ""
	@echo "✅ 包括的テスト環境準備完了"

test-comprehensive-cleanup:
	@echo "🧹 包括的テスト環境クリーンアップ"
	@echo "📋 テスト実行で生成されたファイルを削除"
	@echo ""
	@rm -rf output/test-reports/comprehensive-*
	@rm -rf logs/comprehensive-tests.log
	@rm -rf /tmp/comprehensive_test_*
	@echo "✅ 包括的テスト環境クリーンアップ完了"

test-comprehensive-debug:
	@echo "🐛 包括的テストデバッグモード実行"
	@echo "📋 詳細なデバッグ情報付きで包括的テストを実行"
	@echo ""
	@./scripts/run-comprehensive-tests.sh --full --verbose

test-comprehensive-parallel:
	@echo "⚡ 包括的テスト並列実行"
	@echo "📋 複数のテストスイートを並列で実行"
	@echo ""
	uv run python tests/run_comprehensive_test_suite.py --full --verbose

# Comprehensive test validation
validate-comprehensive-tests:
	@echo "✅ 包括的テストスイート検証"
	@echo "📋 テストスイート自体の妥当性を確認"
	@echo ""
	@echo "🔍 テストファイル存在確認"
	@test -f tests/test_comprehensive_distribution.py || (echo "❌ 配布スクリプトテストが見つかりません" && exit 1)
	@test -f tests/test_documentation_consistency.py || (echo "❌ ドキュメント整合性テストが見つかりません" && exit 1)
	@test -f tests/test_end_to_end_user_experience.py || (echo "❌ ユーザー体験テストが見つかりません" && exit 1)
	@test -f tests/test_comprehensive_integration_suite.py || (echo "❌ 統合テストが見つかりません" && exit 1)
	@test -f tests/run_comprehensive_test_suite.py || (echo "❌ テストランナーが見つかりません" && exit 1)
	@test -f scripts/run-comprehensive-tests.sh || (echo "❌ 実行スクリプトが見つかりません" && exit 1)
	@echo "✅ 全テストファイルが存在します"
	@echo ""
	@echo "🧪 テスト構文チェック"
	@uv run python -m py_compile tests/test_comprehensive_distribution.py
	@uv run python -m py_compile tests/test_documentation_consistency.py
	@uv run python -m py_compile tests/test_end_to_end_user_experience.py
	@uv run python -m py_compile tests/test_comprehensive_integration_suite.py
	@uv run python -m py_compile tests/run_comprehensive_test_suite.py
	@echo "✅ 全テストファイルの構文が正常です"
	@echo ""
	@echo "📋 実行スクリプト権限チェック"
	@test -x scripts/run-comprehensive-tests.sh || (echo "❌ 実行スクリプトに実行権限がありません" && exit 1)
	@echo "✅ 実行スクリプトの権限が正常です"
	@echo ""
	@echo "✅ 包括的テストスイート検証完了")"
	@echo "  - 設定検証"
	@echo "  - 権限チェック"
	@echo ""
	@docker-compose --profile security up security-scanner
	@echo ""
	@echo "📋 セキュリティレポート:"
	@echo "  - 詳細レポート: ./security-reports/"
	@echo "  - 設定検証: ./scripts/validate-docker-override.sh"
	@echo ""
	@echo "🛡️  セキュリティ推奨事項:"
	@echo "  - 定期的なベースイメージ更新"
	@echo "  - 最小権限の原則遵守"
	@echo "  - シークレット管理の適切な実装"

# Docker Override Status
docker-override-status:
	@echo "📊 Docker Override環境状態"
	@echo "📋 現在の設定と実行状況を表示します"
	@echo ""
	@echo "📄 設定ファイル:"
	@if [ -f docker-compose.override.yml ]; then \
		echo "  ✅ docker-compose.override.yml"; \
	else \
		echo "  ❌ docker-compose.override.yml (未作成)"; \
	fi
	@if [ -f .env ]; then \
		echo "  ✅ .env"; \
	else \
		echo "  ❌ .env (未作成)"; \
	fi
	@echo ""
	@echo "🐳 実行中のサービス:"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (サービスが起動していません)"
	@echo ""
	@echo "💾 ボリューム使用量:"
	@docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "  (Docker情報を取得できません)"
	@echo ""
	@echo "📋 利用可能なプロファイル:"
	@echo "  - default: 基本サービス"
	@echo "  - debug: デバッグ用サービス"
	@echo "  - monitoring: 監視スタック"
	@echo "  - security: セキュリティツール"

# Docker Override Cleanup
docker-override-cleanup:
	@echo "🧹 Docker Override環境クリーンアップ"
	@echo "📋 コンテナ、ボリューム、ネットワークを削除します"
	@echo ""
	@echo "⚠️  この操作は以下を削除します:"
	@echo "  - 全てのコンテナ"
	@echo "  - 全てのボリューム"
	@echo "  - カスタムネットワーク"
	@echo "  - 未使用のイメージ"
	@echo ""
	@read -p "続行しますか? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "🗑️  クリーンアップ実行中..."; \
		docker-compose --profile monitoring --profile security --profile debug down -v --remove-orphans; \
		docker system prune -f; \
		echo "✅ クリーンアップ完了"; \
	else \
		echo "❌ クリーンアップをキャンセルしました"; \
	fi

# Docker Override Help
docker-override-help:
	@echo "🐳 Docker Override カスタマイズヘルプ"
	@echo "=================================================="
	@echo ""
	@echo "📋 基本的な使用方法:"
	@echo "  1. make docker-override-setup      # 初期設定"
	@echo "  2. vi docker-compose.override.yml  # カスタマイズ"
	@echo "  3. make docker-override-validate   # 設定検証"
	@echo "  4. make docker-override-dev        # 開発環境起動"
	@echo ""
	@echo "🚀 環境別起動コマンド:"
	@echo "  make docker-override-dev        # 開発環境"
	@echo "  make docker-override-prod       # 本番環境"
	@echo "  make docker-override-monitoring # 監視環境"
	@echo "  make docker-override-security   # セキュリティスキャン"
	@echo ""
	@echo "🔧 管理コマンド:"
	@echo "  make docker-override-status     # 状態確認"
	@echo "  make docker-override-validate   # 設定検証"
	@echo "  make docker-override-cleanup    # 環境削除"
	@echo ""
	@echo "📚 詳細ドキュメント:"
	@echo "  - カスタマイズガイド: docs/DOCKER_CUSTOMIZATION_GUIDE.md"
	@echo "  - 設定テンプレート: docker-compose.override.yml.sample"
	@echo "  - 環境変数例: .env.example"
	@echo ""
	@echo "💡 ヒント:"
	@echo "  - 設定の確認: docker-compose config"
	@echo "  - ログの監視: docker-compose logs -f"
	@echo "  - リソース監視: docker stats"
# =============================================================================
# Template Validation Targets
# =============================================================================

# Complete template validation
validate-templates:
	@echo "🔍 テンプレートファイル検証"
	@echo "📋 全テンプレートファイルの構文・機能・セキュリティチェックを実行"
	@echo ""
	@./scripts/ci-validate-templates.sh --verbose

# Syntax check only
validate-templates-syntax:
	@echo "🔍 テンプレート構文チェック"
	@echo "📋 構文エラーのみをチェック（高速実行）"
	@echo ""
	@./scripts/ci-validate-templates.sh --check-only --verbose

# Functionality test only
validate-templates-functionality:
	@echo "🧪 テンプレート機能テスト"
	@echo "📋 テンプレートの実際の動作確認"
	@echo ""
	@./scripts/ci-validate-templates.sh --test-only --verbose

# CI-optimized validation
validate-templates-ci:
	@echo "🤖 CI用テンプレート検証"
	@echo "📋 CI/CD環境に最適化された検証を実行"
	@echo ""
	@./scripts/ci-validate-templates.sh --format json --output template-validation-report.json

# Generate detailed report
validate-templates-report:
	@echo "📊 テンプレート検証レポート生成"
	@echo "📋 詳細な検証結果レポートを生成"
	@echo ""
	@mkdir -p output/validation-reports
	@./scripts/ci-validate-templates.sh --format json --output output/validation-reports/template-validation-$(shell date +%Y%m%d-%H%M%S).json --verbose
	@echo ""
	@echo "✅ 検証レポートを生成しました: output/validation-reports/"
	@echo "📋 レポート内容:"
	@echo "  - 全テンプレートファイルの検証結果"
	@echo "  - 構文エラーと機能問題の詳細"
	@echo "  - セキュリティ問題の検出結果"
	@echo "  - 推奨改善事項"

# Template validation with specific format
validate-templates-json:
	@echo "📊 JSON形式テンプレート検証"
	@./scripts/ci-validate-templates.sh --format json

validate-templates-text:
	@echo "📄 テキスト形式テンプレート検証"
	@./scripts/ci-validate-templates.sh --format text

# Quick template validation (fail-fast)
validate-templates-quick:
	@echo "⚡ クイックテンプレート検証"
	@echo "📋 最初のエラーで即座に停止する高速検証"
	@echo ""
	@./scripts/ci-validate-templates.sh --check-only --fail-fast

# Template validation with timeout
validate-templates-timeout:
	@echo "⏱️ タイムアウト付きテンプレート検証"
	@echo "📋 指定時間内での検証実行"
	@echo ""
	@TEMPLATE_VALIDATION_TIMEOUT=$(TIMEOUT) ./scripts/ci-validate-templates.sh --verbose

# Template validation test suite
test-template-validation:
	@echo "🧪 テンプレート検証システムのテスト"
	@echo "📋 検証システム自体の動作確認"
	@echo ""
	@uv run pytest tests/test_template_validation.py -v

# Template validation setup
setup-template-validation:
	@echo "🔧 テンプレート検証環境セットアップ"
	@echo "📋 検証に必要な依存関係をインストール"
	@echo ""
	@echo "🐍 Python依存関係チェック"
	@uv sync --group test --group dev
	@echo ""
	@echo "🔧 オプショナルツールチェック"
	@if ! command -v shellcheck >/dev/null 2>&1; then \
		echo "⚠️  shellcheck が見つかりません"; \
		echo "💡 インストール: sudo apt-get install shellcheck (Ubuntu) / brew install shellcheck (macOS)"; \
	fi
	@if ! command -v yamllint >/dev/null 2>&1; then \
		echo "⚠️  yamllint が見つかりません"; \
		echo "💡 インストール: pip install yamllint"; \
	fi
	@if ! command -v hadolint >/dev/null 2>&1; then \
		echo "⚠️  hadolint が見つかりません"; \
		echo "💡 インストール: https://github.com/hadolint/hadolint#install"; \
	fi
	@echo ""
	@echo "✅ テンプレート検証環境セットアップ完了"

# Template validation cleanup
cleanup-template-validation:
	@echo "🧹 テンプレート検証クリーンアップ"
	@echo "📋 検証で生成されたファイルを削除"
	@echo ""
	@rm -rf output/validation-reports/template-validation-*
	@rm -f template-validation-report.json
	@rm -f template-validation-summary.txt
	@echo "✅ テンプレート検証クリーンアップ完了"
