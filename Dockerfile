# マルチステージビルド: ベースイメージ
FROM node:24-alpine AS base

# セキュリティ: 非rootユーザー作成
RUN addgroup -g 1001 -S mcp && \
    adduser -S mcp -u 1001 -G mcp

# 必要なパッケージをインストール
RUN apk add --no-cache \
    curl \
    unzip \
    python3 \
    py3-pip \
    git && \
    apk cache clean

# ビルドステージ: 依存関係インストール
FROM base AS builder

# GitHub MCP Server & Python依存関係
RUN npm install -g @modelcontextprotocol/server-github@latest && \
    pip install --no-cache-dir --user --break-system-packages watchdog==4.0.0

# CodeQL CLI
RUN curl -L -o codeql.zip https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip && \
    unzip codeql.zip -d /opt/codeql && \
    rm codeql.zip && \
    chmod +x /opt/codeql/codeql/codeql

# プロダクションステージ
FROM base AS production

# ビルドステージから必要なファイルをコピー
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/mcp-server-github /usr/local/bin/
COPY --from=builder /root/.local /home/mcp/.local
COPY --from=builder /opt/codeql /opt/codeql

# 環境変数設定
ENV PATH="/opt/codeql/codeql:/home/mcp/.local/bin:$PATH"
ENV PYTHONPATH="/home/mcp/.local/lib/python3.12/site-packages"

# 作業ディレクトリ設定
WORKDIR /app

# アプリケーションファイルをコピー
COPY main.py /app/
COPY pyproject.toml /app/
COPY services/datetime/datetime_validator.py /app/
COPY services/datetime/get_date.py /app/

# 権限設定
RUN chown -R mcp:mcp /app /home/mcp

# 非rootユーザーに切り替え
USER mcp

# ヘルスチェックはサービス固有の設定で実装
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8080/health || exit 1

# デフォルトはGitHub MCPサーバー
CMD ["mcp-server-github"]
