# Mcp-Docker Project Guidelines

## Architecture

```
IDEs (VS Code / Cursor / Kiro / Amazon Q / Copilot CLI)
  ↓ HTTP (port 8082)
Docker: ghcr.io/github/github-mcp-server  ← official image (default)
  ↓
GitHub API (REST v3 + GraphQL v4)

Claude Desktop (stdio only)
  ↓ stdio
mcp-http-bridge (Node.js)  →  HTTP (port 8082)  →  same container above
```

Two image modes:
- **Official** (`docker-compose.yml`): pulls `ghcr.io/github/github-mcp-server:main` — use `make start`
- **Custom/Patched** (`docker-compose.custom.yml`): builds from source with Go patches in `patches/github/` — use `make build-custom && make start-custom`

## Build & Test Commands

```bash
# Setup (first run — creates .env, validates Docker)
./scripts/setup.sh

# Service lifecycle
make start           # Pull + start (official image)
make stop
make restart
make logs
make status

# Custom patched image
make build-custom
make start-custom

# Testing
npm test             # Node.js unit tests (tests/node/)
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
- **Port**: Default MCP HTTP port is `8082`. Override with `GITHUB_MCP_HTTP_PORT`.
- **Image override**: Set `GITHUB_MCP_IMAGE` to swap the default container image.
- **HTTP transport only in `main` tag**: Using a pinned release (e.g. `v0.30.3`) will silently fall back to stdio-only mode and break.
- **Claude Desktop exception**: Requires the `mcp-http-bridge` Node.js process (`bin/mcp-http-bridge.js`) to translate between stdio MCP and HTTP. All other IDEs connect directly to port 8082.
- **Distroless container**: The container has no shell. Health checks are done host-side via `scripts/health-check.sh`, not inside the container.
- **Go patches**: Source patches for the custom build live in `patches/github/`. They are copied into the builder stage in `Dockerfile.github-mcp-server`. Add new `.go` files there and reference them in the Dockerfile.
- **Documentation language**: User-facing docs, Makefile help output, and messages are written in Japanese.
- **MCP server key**: Always use `github-mcp-server-docker` as the server identifier in IDE configs.

## Key Files

| File | Role |
|------|------|
| `bin/mcp-http-bridge.js` | stdio↔HTTP bridge for Claude Desktop |
| `Dockerfile.github-mcp-server` | 3-stage build: OpenSSL refresh → Go builder (injects patches) → distroless runtime |
| `patches/github/list_pr_review_threads.go` | Custom GraphQL tool: `list_pull_request_review_threads` |
| `docker-compose.yml` | Primary compose (official image, resource limits, log rotation) |
| `docker-compose.custom.yml` | Override file for custom patched builds |
| `scripts/setup.sh` | First-run: creates `.env`, validates environment |
| `scripts/generate-ide-config.sh` | Generates per-IDE MCP JSON/TOML configs |

## Gotchas

- **Frame size** (`mcp-http-bridge`): default max frame is 1 MB. Large GitHub responses need `--max-frame-size`.
- **Timeout**: default HTTP timeout is 30 s. Complex operations may need `--timeout` tuning.
- **GraphQL rate limits**: the custom `list_pull_request_review_threads` tool uses GraphQL (not REST), which has separate rate limits. Paginates at 100 threads/query.
- **Stale config volume**: `./config/github-mcp` persists after `make clean`. Remove manually if reconfiguring from scratch.
- **v2.1.0 breaking change**: transport changed from stdio to HTTP. Pre-2.1.0 IDE configs will fail.

## Further Reading

- [README.md](../README.md) — Quick start, token setup, per-IDE configuration steps
- [SECURITY.md](../SECURITY.md) — Token scope requirements, fine-grained PAT guidance
- [docs/SECURITY_PATCHES.md](../docs/SECURITY_PATCHES.md) — CVE mitigation, Trivy scanning, digest pinning
- [docs/simplification/github-mcp-server-design.md](../docs/simplification/github-mcp-server-design.md) — Detailed system design
- [CHANGELOG.md](../CHANGELOG.md) — Release history and breaking changes
