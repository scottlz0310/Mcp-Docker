.PHONY: help build start stop logs clean datetime codeql test test-bats test-docker test-services test-security test-integration test-all security lint pre-commit setup-branch-protection release-check version version-sync sbom audit-deps validate-security docs docs-serve docs-clean

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
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run integration tests"
	@echo "  make test-all  - Run all test suites"
	@echo "  make test-bats - Run Bats test suite"
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
