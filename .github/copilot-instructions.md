# Mcp-Docker Project Guidelines

## Architecture

```
CLI clients (Claude CLI / GitHub Copilot CLI / Codex CLI)
  ↓ HTTP (port 8080)
Docker: ghcr.io/scottlz0310/mcp-gateway:latest  ← OAuth 2.0 ゲートウェイ（compose デフォルト）
  ↓ /mcp/review-raven   ↓ /mcp/thread-owl
review-raven            thread-owl
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
make health-check             # コンテナ・HTTP endpoint を確認
make mcp-conformance          # 実routeのMCP 2026-07-28契約を確認（MCP_E2E_BEARER_TOKENが必要）
make register-all REGISTER_FLAGS=--dry-run

# Cleanup
make clean           # Containers + volumes (keeps images)
make clean-all       # Full cleanup including images
```

## Conventions

- **GitHub MCP は撤去済み**: gateway の `/mcp/github` route と `github-mcp` サービスは無い。gateway は GitHub App の installation token を使わないので、`GITHUB_APP_*`・`GITHUB_APP_PRIVATE_KEY_B64`・`MCP_GATEWAY_INTERNAL_SECRET` を gateway へ渡さない。GPAT を構成や各コンテナへ渡さない。
- **Port**: CLI clients connect to `mcp-gateway` on port `8080` (`MCP_GATEWAY_PORT`). `review-raven` runs on internal port `8083` (`REVIEW_RAVEN_PORT`, also not exposed to host; reachable only via the gateway).
- **Image override**: Set `GITHUB_MCP_GATEWAY_IMAGE` to swap the default `mcp-gateway` image.
- **Documentation language**: User-facing docs, Makefile help output, and messages are written in Japanese.
- **Registration**: Use `mcp-docker register` or `make register-*` for Claude CLI, GitHub Copilot CLI, and Codex CLI.

## Key Files

| File | Role |
|------|------|
| `docker-compose.yml` | Primary compose (official image, resource limits, log rotation) |
| `cmd/mcp-docker/` | CLI registration orchestrator |
| `scripts/health-check.sh` | Host-side container and gateway health checks |
| `internal/conformance/` | MCP 2026-07-28 HTTP/SSE conformance client and tests |

## Gotchas

- **Timeout**: default HTTP timeout is 30 s. Complex operations may need `--timeout` tuning.

## Further Reading

- [README.md](../README.md) — Quick start, token setup, CLI registration steps
- [SECURITY.md](../SECURITY.md) — Token scope requirements, fine-grained PAT guidance
- [docs/SECURITY_PATCHES.md](../docs/SECURITY_PATCHES.md) — CVE mitigation, Trivy scanning, digest pinning
- [docs/archives/](../docs/archives/) — Historical design notes and verification logs
- [CHANGELOG.md](../CHANGELOG.md) — Release history and breaking changes
