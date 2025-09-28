.PHONY: help build start stop logs clean datetime actions actions-auto actions-list actions-run test test-bats test-docker test-services test-security test-integration test-all test-hangup test-hangup-unit test-hangup-integration test-hangup-e2e test-hangup-all test-hangup-bats security lint pre-commit setup-branch-protection release-check version version-sync sbom audit-deps validate-security install-bats check-bats setup-docker health-check verify-containers docker-setup docker-health actions-setup actions-verify test-hangup-ci test-hangup-ci-full test-hangup-ci-matrix test-hangup-regression

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
