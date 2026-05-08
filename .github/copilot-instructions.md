# Mcp-Docker Project Guidelines

## Architecture

```
CLI clients (Claude CLI / GitHub Copilot CLI / Codex CLI)
  ↓ HTTP (port 8080)
Docker: ghcr.io/scottlz0310/mcp-gateway:latest  ← OAuth 2.0 ゲートウェイ（compose デフォルト）
  ↓ /mcp/github         ↓ /mcp/copilot-review
ghcr.io/github/github-mcp-server:main   copilot-review-mcp
  ↓
GitHub API (REST v3 + GraphQL v4)
```

## Build & Test Commands

```bash
# Service lifecycle
make start-gateway   # Pull + start (official image)
make stop
make restart
make logs
make status

# Testing
make test-shell      # BATS shell tests (tests/shell/)
make lint            # All linting
make lint-shell      # Shell script lint (shellcheck)

# Validation
./scripts/health-check.sh      # Checks container + HTTP endpoint + GitHub API
make register-all REGISTER_FLAGS=--dry-run

# Cleanup
make clean           # Containers + volumes (keeps images)
make clean-all       # Full cleanup including images
```

## Conventions

- **Environment-first auth**: `GITHUB_PERSONAL_ACCESS_TOKEN` env var always wins over `.env` file. Set both consistently to avoid confusion.
- **Port**: CLI clients connect to `mcp-gateway` on port `8080` (`MCP_GATEWAY_PORT`). `github-mcp-server` runs on internal port `8082` (`GITHUB_MCP_HTTP_PORT`, not exposed to host), and `copilot-review-mcp` runs on internal port `8083` (`COPILOT_REVIEW_MCP_PORT`, also not exposed to host; reachable only via the gateway).
- **Image override**: Set `GITHUB_MCP_GATEWAY_IMAGE` to swap the default `mcp-gateway` image, and set `GITHUB_MCP_IMAGE` to swap the default `github-mcp-server` image.
- **HTTP transport: supported in stable releases `v0.31.0+`**: Stable releases `v0.31.0` and later include native Streamable HTTP support (`http` subcommand). `v1.0.0` is the current latest stable. Use `main` for cutting-edge features.
- **Distroless container**: The container has no shell. Health checks are done host-side via `scripts/health-check.sh`, not inside the container.
- **Documentation language**: User-facing docs, Makefile help output, and messages are written in Japanese.
- **Registration**: Use `mcp-docker register` or `make register-*` for Claude CLI, GitHub Copilot CLI, and Codex CLI.

## Key Files

| File | Role |
|------|------|
| `docker-compose.yml` | Primary compose (official image, resource limits, log rotation) |
| `cmd/mcp-docker/` | CLI registration orchestrator |
| `scripts/health-check.sh` | Host-side container and gateway health checks |

## Gotchas

- **Timeout**: default HTTP timeout is 30 s. Complex operations may need `--timeout` tuning.
- **Stale config volume**: `./config/github-mcp` persists after `make clean`. Remove manually if reconfiguring from scratch.

## Further Reading

- [README.md](../README.md) — Quick start, token setup, CLI registration steps
- [SECURITY.md](../SECURITY.md) — Token scope requirements, fine-grained PAT guidance
- [docs/SECURITY_PATCHES.md](../docs/SECURITY_PATCHES.md) — CVE mitigation, Trivy scanning, digest pinning
- [docs/archives/](../docs/archives/) — Historical design notes and verification logs
- [CHANGELOG.md](../CHANGELOG.md) — Release history and breaking changes
