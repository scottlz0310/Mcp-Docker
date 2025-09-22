.PHONY: help build start stop logs clean datetime codeql

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