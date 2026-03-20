#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# MCP サーバー識別子（全IDE設定で統一）
MCP_SERVER_KEY="github-mcp-server-docker"

usage() {
    cat <<EOF
使用方法: $0 --ide <IDE名>

IDE名:
  vscode          VS Code / Cursor
  claude-desktop  Claude Desktop
  kiro            Kiro
  amazonq         Amazon Q
  codex           Codex CLI
  copilot-cli     GitHub Copilot CLI

例:
  $0 --ide vscode
  $0 --ide claude-desktop
  $0 --ide amazonq
  $0 --ide codex
  $0 --ide copilot-cli

環境変数:
  GITHUB_MCP_IMAGE        使用する Docker イメージ（claude-desktop では必須）
  GITHUB_MCP_SERVER_URL   HTTP 接続先 URL（未設定時は GITHUB_MCP_HTTP_PORT から生成）
  GITHUB_MCP_HTTP_PORT    HTTP ポート番号（デフォルト: 8082）
EOF
    exit 1
}

IDE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --ide)
            IDE="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

if [[ -z "$IDE" ]]; then
    usage
fi

extract_env_value() {
    local key="$1"
    if [[ ! -f "${ENV_FILE}" ]]; then
        return 0
    fi

    local line
    line="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 || true)"
    echo "${line#*=}"
}

resolve_server_url() {
    local server_url="${GITHUB_MCP_SERVER_URL:-}"
    if [[ -z "${server_url}" ]]; then
        server_url="$(extract_env_value "GITHUB_MCP_SERVER_URL")"
    fi

    if [[ -z "${server_url}" ]]; then
        local http_port="${GITHUB_MCP_HTTP_PORT:-}"
        if [[ -z "${http_port}" ]]; then
            http_port="$(extract_env_value "GITHUB_MCP_HTTP_PORT")"
        fi
        if [[ -z "${http_port}" ]]; then
            http_port="8082"
        fi
        server_url="http://127.0.0.1:${http_port}"
    fi

    # Remove trailing slash to keep host settings consistent.
    server_url="${server_url%/}"
    echo "${server_url}"
}

SERVER_URL="$(resolve_server_url)"
OUTPUT_DIR="${PROJECT_ROOT}/config/ide-configs/${IDE}"
mkdir -p "${OUTPUT_DIR}"

case "$IDE" in
    vscode)
        cat > "${OUTPUT_DIR}/settings.json" <<EOF
{
  "mcpServers": {
    "${MCP_SERVER_KEY}": {
      "type": "http",
      "url": "${SERVER_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ VS Code設定を生成しました: ${OUTPUT_DIR}/settings.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker compose up -d"
        echo "   2. VS Code設定を開く (Cmd/Ctrl + ,)"
        echo "   3. 'mcp' で検索"
        echo "   4. 上記の設定を settings.json に追加 (または .vscode/settings.json にコピー)"
        echo "   5. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;

    claude-desktop)
        # Claude Desktop は HTTP transport 非対応 (stdio のみ)
        # docker run -i でバイナリを直接 stdio モードで起動する
        # ※ Claude Desktop はシェル環境変数を引き継がないため、
        #   env ブロックにトークンを平文で記載する必要がある（テンプレートではプレースホルダー）
        CLAUDE_IMAGE="${GITHUB_MCP_IMAGE:-}"
        if [[ -z "${CLAUDE_IMAGE}" ]]; then
            cat >&2 <<'ERRMSG'
エラー: Claude Desktop 用の GitHub MCP サーバーイメージが設定されていません。

- カスタムイメージを利用する場合（推奨・PRRT対応）:
    make build-custom
    GITHUB_MCP_IMAGE=mcp-github-patched:latest ./scripts/generate-ide-config.sh --ide claude-desktop

- 公式イメージを利用する場合:
    GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server:main ./scripts/generate-ide-config.sh --ide claude-desktop

このスクリプトは、利用可能なイメージが明示的に指定されるまで Claude Desktop 用設定を生成しません。
ERRMSG
            exit 1
        fi
        cat > "${OUTPUT_DIR}/claude_desktop_config.json" <<EOF
{
  "mcpServers": {
    "${MCP_SERVER_KEY}": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "${CLAUDE_IMAGE}",
        "stdio"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat_your_token_here"
      }
    }
  }
}
EOF
        echo "✅ Claude Desktop設定を生成しました: ${OUTPUT_DIR}/claude_desktop_config.json"
        echo ""
        echo "⚠️  Claude Desktop は HTTP transport 非対応のため stdio (docker run -i) を使用します"
        echo "   docker compose up は不要です。Claude Desktop が docker run を直接実行します。"
        echo ""
        echo "⚠️  トークンについて:"
        echo "   Claude Desktop はシェル環境変数を引き継がないため、"
        echo "   env.GITHUB_PERSONAL_ACCESS_TOKEN に実際のトークンを平文で記載する必要があります。"
        echo "   生成されたファイルの 'github_pat_your_token_here' を実際のトークンに書き換えてください。"
        echo "   ※ このファイルをリポジトリにコミットしないよう注意してください。"
        echo ""
        echo "📋 設定方法:"
        echo "   1. カスタムイメージをビルド（未実施の場合）: make build-custom"
        echo "   2. 生成されたファイルのトークンを書き換える"
        echo "      ${OUTPUT_DIR}/claude_desktop_config.json"
        echo "   3. Claude Desktop設定ファイルに内容をマージする"
        echo "      macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
        echo "      Linux: ~/.config/Claude/claude_desktop_config.json"
        echo "      Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
        echo "   4. Claude Desktop を再起動"
        ;;

    kiro)
        cat > "${OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcp": {
    "servers": {
      "${MCP_SERVER_KEY}": {
        "type": "http",
        "url": "${SERVER_URL}",
        "headers": {
          "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
EOF
        echo "✅ Kiro設定を生成しました: ${OUTPUT_DIR}/mcp.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker compose up -d"
        echo "   2. Kiro設定ディレクトリに配置"
        echo "      ~/.kiro/settings/mcp.json"
        echo "   3. Kiroを再起動"
        echo "   4. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;

    amazonq)
        cat > "${OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcpServers": {
    "${MCP_SERVER_KEY}": {
      "type": "http",
      "url": "${SERVER_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ Amazon Q設定を生成しました: ${OUTPUT_DIR}/mcp.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker compose up -d"
        echo "   2. Amazon Q設定ファイルを開く"
        echo "      VS Code: 設定 > Amazon Q > MCP Servers"
        echo "   3. 上記の設定を追加"
        echo "   4. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;

    codex)
        cat > "${OUTPUT_DIR}/config.toml" <<EOF
[mcp_servers.${MCP_SERVER_KEY}]
url = "${SERVER_URL}"
bearer_token_env_var = "GITHUB_PERSONAL_ACCESS_TOKEN"
EOF
        echo "✅ Codex設定(TOML)を生成しました: ${OUTPUT_DIR}/config.toml"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker compose up -d"
        echo "   2. Codex設定ファイルを開く"
        echo "      既定: ~/.codex/config.toml"
        echo "   3. 上記設定を追記"
        echo "   4. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;

    copilot-cli)
        cat > "${OUTPUT_DIR}/mcp-config.json" <<EOF
{
  "mcpServers": {
    "${MCP_SERVER_KEY}": {
      "type": "http",
      "url": "${SERVER_URL}",
      "headers": {
        "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ Copilot CLI設定(JSON)を生成しました: ${OUTPUT_DIR}/mcp-config.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker compose up -d"
        echo "   2. Copilot CLI MCP設定ファイルにJSONを配置"
        echo "      既定: ~/.copilot/mcp-config.json"
        echo "   3. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;

    *)
        echo "❌ 未対応のIDE: $IDE"
        usage
        ;;
esac
