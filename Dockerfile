# syntax=docker/dockerfile:1.7
# =============================================================================
# Unified Dockerfile for MCP Docker Services
# =============================================================================
# This Dockerfile consolidates Dockerfile and Dockerfile.actions into a single
# multi-stage build with multiple targets:
# - mcp-server: GitHub MCP Server
# - datetime-validator: DateTime validation service
# - actions-simulator: GitHub Actions Simulator
#
# Build examples:
#   docker build --target mcp-server -t mcp-server:latest .
#   docker build --target actions-simulator -t actions-simulator:latest .
# =============================================================================

ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=20
ARG ACT_VERSION=v0.2.82

# =============================================================================
# Base Stage: Python + Essential Tools
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install essential system packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        jq \
        tini \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Node.js Stage: Add Node.js to base
# =============================================================================
FROM base AS base-with-node

ARG NODE_VERSION

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Node.js using official NodeSource setup
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# =============================================================================
# Builder Stage: Install Python dependencies
# =============================================================================
FROM base AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
COPY LICENSE ./
COPY README.md ./

# Copy source code
COPY services ./services
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
COPY main.py ./

# Install Python and dependencies
RUN uv python install "${PYTHON_VERSION}" \
    && uv sync \
    && uv cache prune --ci

# =============================================================================
# Act CLI Installer Stage
# =============================================================================
FROM base AS act-installer

ARG ACT_VERSION
ARG TARGETARCH

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN case "${TARGETARCH}" in \
        "arm64")   ACT_ARCH="arm64" ;; \
        "aarch64") ACT_ARCH="arm64" ;; \
        "amd64")   ACT_ARCH="x86_64" ;; \
        "x86_64")  ACT_ARCH="x86_64" ;; \
        *)         ACT_ARCH="x86_64" ;; \
    esac \
    && curl -fsSL "https://github.com/nektos/act/releases/download/${ACT_VERSION}/act_Linux_${ACT_ARCH}.tar.gz" -o /tmp/act.tgz \
    && tar -xzf /tmp/act.tgz -C /usr/local/bin act \
    && rm /tmp/act.tgz \
    && chmod +x /usr/local/bin/act

# =============================================================================
# MCP Server Target: GitHub MCP Server
# =============================================================================
FROM base-with-node AS mcp-server

# Install GitHub MCP server
RUN npm install -g @modelcontextprotocol/server-github@latest

# Copy Python environment from builder
COPY --from=builder /opt/uv /opt/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Copy act CLI
COPY --from=act-installer /usr/local/bin/act /usr/local/bin/act

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}"
ENV NODE_PATH="/usr/local/lib/node_modules"

WORKDIR /app

# Create non-root user
RUN groupadd -g 1001 mcp \
    && useradd -l -u 1001 -g 1001 --create-home --shell /bin/bash mcp \
    && chown -R mcp:mcp /app /opt/uv

USER mcp

ENTRYPOINT ["tini", "--"]
CMD ["node", "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"]

# =============================================================================
# DateTime Validator Target: DateTime validation service
# =============================================================================
FROM base AS datetime-validator

# Copy Python environment from builder
COPY --from=builder /opt/uv /opt/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}"

WORKDIR /app

# Create non-root user (matches docker-compose user specification)
RUN groupadd -g 1000 validator \
    && useradd -l -u 1000 -g 1000 --create-home --shell /bin/bash validator \
    && chown -R validator:validator /app /opt/uv

USER validator

ENTRYPOINT ["tini", "--"]
CMD ["python", "services/datetime/datetime_validator.py", "--directory", "/workspace"]

# =============================================================================
# GitHub Release Watcher Target: Monitor GitHub releases
# =============================================================================
FROM base AS github-release-watcher

# Copy Python environment from builder
COPY --from=builder /opt/uv /opt/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}"

WORKDIR /app

# Create non-root user
RUN groupadd -g 1000 watcher \
    && useradd -l -u 1000 -g 1000 --create-home --shell /bin/bash watcher \
    && mkdir -p /app/data /app/logs \
    && chown -R watcher:watcher /app /opt/uv

USER watcher

ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "services.github_release_watcher", "--config", "/app/data/config.toml", "--state", "/app/data/state.json"]

# =============================================================================
# Actions Simulator Target: GitHub Actions Simulator
# =============================================================================
FROM base AS actions-simulator

ARG USER_ID=1000
ARG GROUP_ID=1000

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install uv in runtime
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && rm -rf /root/.local/share/uv

# Copy Python environment from builder
COPY --from=builder /opt/uv /opt/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Copy act CLI
COPY --from=act-installer /usr/local/bin/act /usr/local/bin/act

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}"
ENV ACT_CACHE_DIR=/opt/act/cache
ENV ACT_LOG_LEVEL=info
ENV ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:runner-latest

WORKDIR /app

# Create actions user with configurable UID/GID
RUN install -d -m 0755 /opt/uv \
    && groupadd -g "${GROUP_ID}" actions \
    && useradd -l -u "${USER_ID}" -g "${GROUP_ID}" --create-home --shell /bin/bash actions \
    && install -d -m 0755 -o actions -g actions /opt/act/cache /app/output /app/.cache/uv \
    && chown -R actions:actions /app /opt/uv

# Copy act configuration
COPY .actrc /home/actions/.actrc
RUN chown actions:actions /home/actions/.actrc

USER actions

ENTRYPOINT ["tini", "--"]
CMD ["uv", "run", "python", "main.py", "actions", "--help"]

# =============================================================================
# Default Target: MCP Server (for backward compatibility)
# =============================================================================
FROM mcp-server AS default
