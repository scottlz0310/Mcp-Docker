# Multi-stage build for the MCP Docker environment
FROM node:24-alpine AS base

# Security: create non-root user early to avoid UID reuse surprises
RUN addgroup -S docker && \
    addgroup -g 1001 -S mcp && \
    adduser -S mcp -u 1001 -G mcp && \
    addgroup mcp docker

# Install required system packages
RUN apk add --no-cache \
    bash \
    curl \
    git \
    python3 \
    py3-pip \
    docker-cli && \
    apk cache clean

# Builder stage: install tooling and Python dependencies via uv
FROM base AS builder

# Install GitHub MCP server and helper script
RUN npm install -g @modelcontextprotocol/server-github@latest && \
    echo '#!/bin/sh' > /usr/local/bin/mcp-server-github-direct && \
    echo 'exec node /usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js "$@"' >> /usr/local/bin/mcp-server-github-direct && \
    chmod +x /usr/local/bin/mcp-server-github-direct

# Install act CLI (GitHub Actions local runner)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -L -o act_Linux_x86_64.tar.gz https://github.com/nektos/act/releases/latest/download/act_Linux_x86_64.tar.gz && \
    tar xzf act_Linux_x86_64.tar.gz && \
    mv act /usr/local/bin/act && \
    rm act_Linux_x86_64.tar.gz && \
    chmod +x /usr/local/bin/act

# Install uv and pre-sync Python dependencies
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/opt/uv

RUN mkdir -p /opt/uv

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock ./
RUN uv python install 3.13 && \
    uv sync --locked --no-install-project && \
    uv cache prune --ci

# Production stage
FROM base AS production

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/opt/uv
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}"
ENV NODE_PATH="/usr/local/lib/node_modules"
ENV PYTHONUNBUFFERED=1

# Copy tooling from builder
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/mcp-server-github-direct /usr/local/bin/
COPY --from=builder /usr/local/bin/act /usr/local/bin/
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder /opt/uv /opt/uv
COPY --from=builder /app/.venv /app/.venv

# Application files
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY LICENSE ./
COPY README.md ./
COPY main.py ./
COPY services/actions ./services/actions
COPY services/datetime ./services/datetime
COPY scripts ./scripts

# Permissions
RUN chown -R mcp:mcp /app /opt/uv /usr/local/lib/node_modules

USER mcp

# Default command: GitHub MCP server
CMD ["mcp-server-github-direct"]
