# マルチステージビルド: ベースイメージ（Windows互換性対応）
FROM --platform=$BUILDPLATFORM node:18-alpine AS base

# セキュリティ: 非rootユーザー作成（ホストユーザーIDに合わせる）
RUN (addgroup -g 1000 -S mcp 2>/dev/null || addgroup -S mcp) && \
    (adduser -S mcp -u 1000 -G mcp 2>/dev/null || adduser -S mcp -G mcp)

# 必要なパッケージをインストール
RUN apk add --no-cache \
    curl \
    unzip \
    python3 \
    py3-pip \
    git && \
    apk cache clean

# ビルドステージ: 依存関係インストール
FROM --platform=$BUILDPLATFORM base AS builder

# GitHub MCP Server & Python依存関係
RUN npm install -g @modelcontextprotocol/server-github@latest && \
    pip install --no-cache-dir --user --break-system-packages watchdog==4.0.0

# CodeQL CLI
RUN curl -L -o codeql.zip https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip && \
    unzip codeql.zip -d /opt/codeql && \
    rm codeql.zip && \
    chmod +x /opt/codeql/codeql/codeql

# プロダクションステージ
FROM --platform=$TARGETPLATFORM base AS production

# ビルドステージから必要なファイルをコピー
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/mcp-server-github /usr/local/bin/
COPY --from=builder /root/.local /home/mcp/.local
COPY --from=builder /opt/codeql /opt/codeql

# 権限設定（rootで実行）
RUN chown -R mcp:mcp /home/mcp

# 環境変数設定
ENV PATH="/opt/codeql/codeql:/home/mcp/.local/bin:$PATH"
ENV PYTHONPATH="/home/mcp/.local/lib/python3.12/site-packages"

# 作業ディレクトリ設定
WORKDIR /app

# スクリプトをコピーして権限設定
COPY --chown=mcp:mcp main.py /app/
COPY --chown=mcp:mcp services/datetime/datetime_validator.py /app/
COPY --chown=mcp:mcp services/datetime/get_date.py /app/
RUN chmod +x /app/main.py /app/datetime_validator.py /app/get_date.py

# mcpユーザーでPython依存関係を再インストール
USER mcp
RUN pip install --no-cache-dir --user --break-system-packages watchdog==4.0.0

# ヘルスチェック追加（プロセス確認ベース）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python" || exit 1

# デフォルトはGitHub MCPサーバー
CMD ["mcp-server-github"]
