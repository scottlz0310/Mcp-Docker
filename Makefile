.PHONY: help build start stop logs clean datetime codeql test test-bats test-docker test-services test-security test-integration test-all security lint pre-commit setup-branch-protection release-check version

help:
	@echo "MCP Docker Environment Commands:"
	@echo "  make build     - Build unified image"
	@echo "  make start     - Start DateTime validator"
	@echo "  make stop      - Stop all services"
	@echo "  make logs      - Show logs"
	@echo "  make clean     - Clean up containers and images"
	@echo ""
	@echo "Services:"
	@echo "  make datetime          - Start DateTime validator (normal mode)"
	@echo "  make datetime-readonly - Run DateTime validator (read-only mode)"
	@echo "  make datetime-fix      - Run DateTime validator (fix mode)"
	@echo "  make codeql            - Run CodeQL analysis"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run integration tests"
	@echo "  make test-all      - Run all test suites"
	@echo "  make test-bats     - Run Bats test suite"
	@echo ""
	@echo "Security:"
	@echo "  make security         - Run basic security scan"
	@echo "  make security-full    - Run comprehensive security scan"
	@echo "  make security-secrets - Run secret scanning"
	@echo "  make security-deps    - Run dependency security scan"
	@echo "  make security-metrics  - Collect security metrics"
	@echo "  make security-monitor  - Start continuous security monitoring"
	@echo "  make security-report   - Generate security report"
	@echo "  make security-validate - Validate Phase 7 exit criteria"
	@echo ""
	@echo "Release Management:"
	@echo "  make version           - Show current version"
	@echo "  make release-check     - Check release readiness"
	@echo "  make setup-branch-protection - Setup branch protection"
	@echo ""
	@echo "GitHub MCP Server:"
	@echo "  Use: docker run -e GITHUB_PERSONAL_ACCESS_TOKEN=\$$GITHUB_PERSONAL_ACCESS_TOKEN mcp-docker-github-mcp"

build:
	docker compose build

start:
	UID=$(shell id -u) GID=$(shell id -g) docker compose up -d datetime-validator

stop:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v --rmi all

datetime:
	UID=$(shell id -u) GID=$(shell id -g) docker compose up -d datetime-validator

datetime-readonly:
	@echo "🔍 読み取り専用モードでDateTime Validatorを起動"
	docker compose run --rm datetime-validator python datetime_validator.py --directory /workspace --read-only

datetime-fix:
	@echo "🔧 修正モードでDateTime Validatorを起動"
	UID=$(shell id -u) GID=$(shell id -g) docker compose run --rm datetime-validator python datetime_validator.py --directory /workspace

codeql:
	docker compose --profile tools run --rm codeql

test:
	./tests/integration_test.sh

test-bats:
	@echo "🧪 Bats テストスイート実行"
	bats tests/test_*.bats

test-docker:
	@echo "🐳 Docker ビルドテスト"
	bats tests/test_docker_build.bats

test-services:
	@echo "🚀 サービステスト"
	bats tests/test_services.bats

test-security:
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

security-full:
	@echo "🔍 包括的セキュリティスキャン実行"
	make security
	@echo "🔍 SBOM生成"
	docker run --rm -v "$$(pwd)":/workspace anchore/syft:latest /workspace -o spdx-json=sbom.spdx.json
	@echo "🔍 脆弱性スキャン"
	docker run --rm -v "$$(pwd)":/workspace anchore/grype:latest sbom:sbom.spdx.json

security-secrets:
	@echo "🔍 シークレットスキャン実行"
	docker run --rm -v "$$(pwd)":/workspace trufflesecurity/trufflehog:latest filesystem /workspace --only-verified

security-deps:
	@echo "🔍 Python依存関係スキャン"
	pip freeze | docker run --rm -i pyupio/safety:latest check --stdin

security-metrics:
	@echo "📊 セキュリティメトリクス収集"
	./scripts/security-metrics.sh

security-monitor:
	@echo "🔍 継続的セキュリティ監視開始"
	@echo "ℹ️ メトリクスは security-reports/ ディレクトリに保存されます"
	make security-metrics
	@echo "✅ セキュリティ監視完了"

security-report:
	@echo "📄 セキュリティレポート生成"
	make security-metrics
	@echo "📁 レポートは security-reports/ ディレクトリを確認してください"

security-validate:
	@echo "🔍 Phase 7 Exit Criteria検証"
	./scripts/security-validation.sh

lint:
	docker run --rm -i hadolint/hadolint < Dockerfile
	shellcheck scripts/*.sh tests/*.sh
	pipx run uv run yamllint -c .yamllint.yml docker-compose.yml

pre-commit:
	pipx run uv run pre-commit run --all-files

version:
	@echo "Current version: $(shell grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"
	@uv run python main.py --version

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
