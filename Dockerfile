FROM node:18-alpine

# 必要なパッケージをインストール
RUN apk add --no-cache curl unzip python3 py3-pip git

# GitHub MCP Server
RUN npm install -g @modelcontextprotocol/server-github

# Python依存関係（datetime validator用）
RUN pip install --no-cache-dir watchdog --break-system-packages

# CodeQL CLI
RUN curl -L -o codeql.zip https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip \
    && unzip codeql.zip -d /opt/codeql \
    && rm codeql.zip
ENV PATH="/opt/codeql/codeql:$PATH"

WORKDIR /app

# スクリプトをコピー
COPY services/datetime/datetime_validator.py /app/
COPY services/datetime/get_date.py /app/

# デフォルトはGitHub MCPサーバー
CMD ["mcp-server-github"]