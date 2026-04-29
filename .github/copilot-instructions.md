# Mcp-Docker Project Guidelines

## Architecture

```
IDEs (VS Code / Cursor / Kiro / Amazon Q / Copilot CLI)
  ↓ HTTP (port 8080)
Docker: ghcr.io/scottlz0310/mcp-gateway:latest  ← OAuth 2.0 ゲートウェイ（compose デフォルト）
  ↓ /mcp/github         ↓ /mcp/copilot-review
ghcr.io/github/github-mcp-server:main   copilot-review-mcp
  ↓
GitHub API (REST v3 + GraphQL v4)

Claude Desktop (stdio only)
  ↓ stdio
docker run -i --rm <image> stdio
```

## Build & Test Commands

```bash
# Setup (first run — creates .env, validates Docker)
./scripts/setup.sh

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
./scripts/generate-ide-config.sh  # Prints IDE-specific MCP configs (VS Code, Claude Desktop, Kiro, Codex…)

# Cleanup
make clean           # Containers + volumes (keeps images)
make clean-all       # Full cleanup including images
```

## Conventions

- **Environment-first auth**: `GITHUB_PERSONAL_ACCESS_TOKEN` env var always wins over `.env` file. Set both consistently to avoid confusion.
- **Port**: IDEs connect to `mcp-gateway` on port `8080` (`MCP_GATEWAY_PORT`). `github-mcp-server` runs on internal port `8082` (`GITHUB_MCP_HTTP_PORT`, not exposed to host), and `copilot-review-mcp` runs on internal port `8083` (`COPILOT_REVIEW_MCP_PORT`, also not exposed to host; reachable only via the gateway).
- **Image override**: Set `GITHUB_MCP_GATEWAY_IMAGE` to swap the default `mcp-gateway` image, and set `GITHUB_MCP_IMAGE` to swap the default `github-mcp-server` image.
- **HTTP transport: supported in stable releases `v0.31.0+`**: Stable releases `v0.31.0` and later include native Streamable HTTP support (`http` subcommand). `v1.0.0` is the current latest stable. Use `main` for cutting-edge features.
- **Claude Desktop exception**: HTTP transport 非対応のため、`docker run -i --rm <image> stdio` で直接起動する。VS Code/Cursor/Kiro/Amazon Q/Codex/Copilot CLI は HTTP (port 8080, mcp-gateway 経由) に接続する。
- **Distroless container**: The container has no shell. Health checks are done host-side via `scripts/health-check.sh`, not inside the container.
- **Documentation language**: User-facing docs, Makefile help output, and messages are written in Japanese.
- **MCP server key**: Always use `github-mcp-server-docker` as the server identifier in IDE configs.

## Key Files

| File | Role |
|------|------|
| `docker-compose.yml` | Primary compose (official image, resource limits, log rotation) |
| `scripts/setup.sh` | First-run: creates `.env`, validates environment |
| `scripts/generate-ide-config.sh` | Generates per-IDE MCP JSON/TOML configs |

## Gotchas

- **Timeout**: default HTTP timeout is 30 s. Complex operations may need `--timeout` tuning.
- **Stale config volume**: `./config/github-mcp` persists after `make clean`. Remove manually if reconfiguring from scratch.
- **v2.1.0 breaking change**: transport changed from stdio to HTTP. Pre-2.1.0 IDE configs will fail.

## Further Reading

- [README.md](../README.md) — Quick start, token setup, per-IDE configuration steps
- [SECURITY.md](../SECURITY.md) — Token scope requirements, fine-grained PAT guidance
- [docs/SECURITY_PATCHES.md](../docs/SECURITY_PATCHES.md) — CVE mitigation, Trivy scanning, digest pinning
- [docs/simplification/github-mcp-server-design.md](../docs/simplification/github-mcp-server-design.md) — Detailed system design
- [CHANGELOG.md](../CHANGELOG.md) — Release history and breaking changes
