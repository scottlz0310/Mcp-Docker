.PHONY: help build start stop logs clean datetime codeql test test-bats test-docker test-services test-security test-integration test-all security lint pre-commit

help:
	@echo "MCP Docker Environment Commands:"
	@echo "  make build     - Build unified image"
	@echo "  make start     - Start DateTime validator"
	@echo "  make stop      - Stop all services"
	@echo "  make logs      - Show logs"
	@echo "  make clean     - Clean up containers and images"
	@echo ""
	@echo "Services:"
	@echo "  make datetime  - Start DateTime validator"
	@echo "  make codeql    - Run CodeQL analysis"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run integration tests"
	@echo "  make test-all  - Run all test suites"
	@echo "  make test-bats - Run Bats test suite"
	@echo "  make security  - Run security scan"
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
