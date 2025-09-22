.PHONY: help build start stop logs clean datetime codeql test security lint pre-commit

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
	@echo "GitHub MCP Server:"
	@echo "  Use: docker run -e GITHUB_PERSONAL_ACCESS_TOKEN=\$$GITHUB_PERSONAL_ACCESS_TOKEN mcp-docker-github-mcp"

build:
	docker-compose build

start:
	docker-compose up -d datetime-validator

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --rmi all

datetime:
	docker-compose up -d datetime-validator

codeql:
	docker-compose --profile tools run --rm codeql

test:
	./tests/integration_test.sh

security:
	docker run --rm -v "$(PWD)":/app aquasec/trivy:latest image mcp-docker:latest

lint:
	docker run --rm -i hadolint/hadolint < Dockerfile
	shellcheck scripts/*.sh tests/*.sh
	pipx run uv run yamllint -c .yamllint.yml docker-compose.yml

pre-commit:
	pipx run uv run pre-commit run --all-files
