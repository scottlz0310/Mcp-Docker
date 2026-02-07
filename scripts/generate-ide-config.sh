#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

usage() {
    cat <<EOF
使用方法: $0 --ide <IDE名>

IDE名:
  vscode          VS Code / Cursor
  claude-desktop  Claude Desktop
  kiro            Kiro
  amazonq         Amazon Q

例:
  $0 --ide vscode
  $0 --ide claude-desktop
  $0 --ide amazonq
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
    "github": {
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
        echo "   1. Dockerコンテナを起動: docker-compose up -d"
        echo "   2. VS Code設定を開く (Cmd/Ctrl + ,)"
        echo "   3. 'mcp' で検索"
        echo "   4. 上記の設定をmcp.jsonに追加"
        echo "   5. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;
    
    claude-desktop)
        cat > "${OUTPUT_DIR}/claude_desktop_config.json" <<EOF
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "${SERVER_URL}",
      "headers": {
        "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
        echo "✅ Claude Desktop設定を生成しました: ${OUTPUT_DIR}/claude_desktop_config.json"
        echo ""
        echo "📋 設定方法:"
        echo "   1. Dockerコンテナを起動: docker-compose up -d"
        echo "   2. Claude Desktop設定ファイルを開く"
        echo "      macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
        echo "      Linux: ~/.config/Claude/claude_desktop_config.json"
        echo "      Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
        echo "   3. 上記の設定を追加"
        echo "   4. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;
    
    kiro)
        cat > "${OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcp": {
    "servers": {
      "github": {
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
        echo "   1. Dockerコンテナを起動: docker-compose up -d"
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
    "github": {
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
        echo "   1. Dockerコンテナを起動: docker-compose up -d"
        echo "   2. Amazon Q設定ファイルを開く"
        echo "      VS Code: 設定 > Amazon Q > MCP Servers"
        echo "   3. 上記の設定を追加"
        echo "   4. 接続先URL: ${SERVER_URL}"
        echo ""
        echo "💡 環境変数の設定も忘れずに:"
        echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here"
        ;;
    
    *)
        echo "❌ 未対応のIDE: $IDE"
        usage
        ;;
esac
