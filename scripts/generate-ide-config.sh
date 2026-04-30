#!/bin/bash
# Legacy/Fallback: IDE/CLI 向けの MCP 設定ファイル生成スクリプト。
# CLI 登録に対応しているエージェント（Claude CLI / GitHub Copilot CLI / Codex CLI）では
# `mcp-docker register`（make register-*）の利用を推奨しますが、
# 設定ファイル方式が必要な場合のフォールバックとしてこのスクリプトも利用できます。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# MCP サーバー識別子（全IDE設定で統一）
MCP_SERVER_KEY="github-mcp-server-docker"

usage() {
    cat <<EOF
使用方法: $0 --ide <IDE名> [--service <サービス名>]

IDE名:
  vscode          VS Code / Cursor
  claude-desktop  Claude Desktop
  kiro            Kiro
  amazonq         Amazon Q
  codex           Codex CLI
  copilot-cli     GitHub Copilot CLI

サービス名 (--service):
  github-mcp          GitHub MCP Server（Docker ネットワーク内部のみ port 8082、ホストからは直接アクセス不可）
                      ※ ホストから接続するには mcp-gateway 経由を推奨
  copilot-review-mcp  Copilot Review MCP Server（mcp-gateway 経由、port 8080）
  mcp-gateway         MCP Gateway（OAuth 2.0 認証ゲートウェイ、port 8080）
                      ※ Claude Desktop から github-mcp-server に接続する場合はこちらを使用

例:
  $0 --ide vscode
  $0 --ide vscode --service copilot-review-mcp
  $0 --ide claude-desktop
  $0 --ide claude-desktop --service mcp-gateway
  $0 --ide amazonq --service copilot-review-mcp
  $0 --ide codex
  $0 --ide copilot-cli

環境変数 (github-mcp):
  GITHUB_MCP_SERVER_URL         HTTP 接続先 URL（未設定時は GITHUB_MCP_HTTP_PORT から生成）
  GITHUB_MCP_HTTP_PORT          HTTP ポート番号（デフォルト: 8082）
  GITHUB_PERSONAL_ACCESS_TOKEN  GitHub API 用の個人アクセストークン（fine-grained PAT 推奨）
  GITHUB_MCP_IMAGE              コンテナイメージのオーバーライド（デフォルト: ghcr.io/github/github-mcp-server:main）

環境変数 (copilot-review-mcp):
  MCP_GATEWAY_URL               mcp-gateway の接続先 URL（優先）
  MCP_GATEWAY_BASE_URL          mcp-gateway の接続先 URL（MCP_GATEWAY_URL 未設定時のフォールバック）
  MCP_GATEWAY_PORT              mcp-gateway のポート番号（デフォルト: 8080、URL 未指定時に使用）
  GITHUB_PERSONAL_ACCESS_TOKEN  Bearer トークン（GitHub PAT, fine-grained 推奨）

環境変数 (mcp-gateway):
  MCP_GATEWAY_URL               HTTP 接続先 URL（優先）
  MCP_GATEWAY_BASE_URL          HTTP 接続先 URL（MCP_GATEWAY_URL 未設定時のフォールバック）
  MCP_GATEWAY_PORT              HTTP ポート番号（デフォルト: 8080、URL 未指定時に使用）
  GITHUB_PERSONAL_ACCESS_TOKEN  Bearer トークン（GitHub PAT または OAuth トークン）
EOF
    exit 1
}

IDE=""
SERVICE="github-mcp"
while [[ $# -gt 0 ]]; do
    case $1 in
        --ide)
            IDE="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
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

case "$SERVICE" in
    github-mcp|copilot-review-mcp|mcp-gateway) ;;
    *) echo "❌ 未対応のサービス: $SERVICE"; usage ;;
esac

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

# ── URL 解決 ──────────────────────────────────────────────────────────────────

resolve_copilot_review_url() {
    # copilot-review-mcp は mcp-gateway 経由でアクセスする
    # URL: <gateway_url>/mcp/copilot-review
    local gateway_url
    gateway_url="$(resolve_gateway_url)"
    echo "${gateway_url}/mcp/copilot-review"
}

resolve_gateway_url() {
    local url="${MCP_GATEWAY_URL:-}"
    if [[ -z "${url}" ]]; then
        url="$(extract_env_value "MCP_GATEWAY_URL")"
    fi
    if [[ -z "${url}" ]]; then
        url="${MCP_GATEWAY_BASE_URL:-}"
    fi
    if [[ -z "${url}" ]]; then
        url="$(extract_env_value "MCP_GATEWAY_BASE_URL")"
    fi
    if [[ -z "${url}" ]]; then
        local port="${MCP_GATEWAY_PORT:-}"
        if [[ -z "${port}" ]]; then
            port="$(extract_env_value "MCP_GATEWAY_PORT")"
        fi
        port="${port:-8080}"
        url="http://127.0.0.1:${port}"
    fi
    url="${url%/}"
    url="${url%/mcp}"
    echo "${url}"
}

SERVER_URL="$(resolve_server_url)"
COPILOT_REVIEW_URL="$(resolve_copilot_review_url)"
GATEWAY_URL="$(resolve_gateway_url)"

# ── 出力先・サービス別ディスパッチ ───────────────────────────────────────────

if [[ "$SERVICE" == "copilot-review-mcp" ]]; then
    CRM_SERVER_KEY="copilot-review-mcp"
    # copilot-review-mcp は mcp-gateway 経由でアクセス
    # resolve_copilot_review_url は最終 MCP エンドポイント(/mcp/copilot-review)を返すため
    # 追加の /mcp は付与しない
    CRM_MCP_URL="${COPILOT_REVIEW_URL}"

    # IDE の妥当性を先に検証（mkdir より前）
    case "$IDE" in
        vscode|claude-desktop|kiro|amazonq|codex|copilot-cli)
            ;;
        *)
            echo "❌ 未対応のIDEです: $IDE"
            echo "対応IDE: vscode, claude-desktop, kiro, amazonq, codex, copilot-cli"
            exit 1
            ;;
    esac

    CRM_OUTPUT_DIR="${PROJECT_ROOT}/config/ide-configs/copilot-review-mcp/${IDE}"
    mkdir -p "${CRM_OUTPUT_DIR}"

    case "$IDE" in
        vscode)
            cat > "${CRM_OUTPUT_DIR}/settings.json" <<EOF
{
  "mcpServers": {
    "${CRM_SERVER_KEY}": {
      "type": "http",
      "url": "${CRM_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ VS Code設定を生成しました: ${CRM_OUTPUT_DIR}/settings.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. copilot-review-mcp サービスを起動 (docker build + docker run)"
            echo "   2. VS Code設定 (.vscode/settings.json または User settings.json) に追加:"
            echo "      ${CRM_OUTPUT_DIR}/settings.json"
            echo "   3. 接続先URL: ${CRM_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            echo "   ※ fine-grained PAT (repo スコープ) 推奨"
            echo ""
            echo "🔑 OAuth フロー（ブラウザ認証）を使う場合:"
            echo "   ブラウザで ${COPILOT_REVIEW_URL}/authorize を開く"
            ;;

        kiro)
            cat > "${CRM_OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcp": {
    "servers": {
      "${CRM_SERVER_KEY}": {
        "type": "http",
        "url": "${CRM_MCP_URL}",
        "headers": {
          "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
EOF
            echo "✅ Kiro設定を生成しました: ${CRM_OUTPUT_DIR}/mcp.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. copilot-review-mcp サービスを起動"
            echo "   2. 設定ファイルを ~/.kiro/settings/mcp.json に配置"
            echo "   3. 接続先URL: ${CRM_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            ;;

        amazonq)
            cat > "${CRM_OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcpServers": {
    "${CRM_SERVER_KEY}": {
      "type": "http",
      "url": "${CRM_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ Amazon Q設定を生成しました: ${CRM_OUTPUT_DIR}/mcp.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. copilot-review-mcp サービスを起動"
            echo "   2. Amazon Q 設定に上記JSONを追加"
            echo "   3. 接続先URL: ${CRM_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            ;;

        codex)
            cat > "${CRM_OUTPUT_DIR}/config.toml" <<EOF
[mcp_servers.${CRM_SERVER_KEY}]
url = "${CRM_MCP_URL}"
bearer_token_env_var = "GITHUB_PERSONAL_ACCESS_TOKEN"
EOF
            echo "✅ Codex設定を生成しました: ${CRM_OUTPUT_DIR}/config.toml"
            echo ""
            echo "📋 設定方法:"
            echo "   1. copilot-review-mcp サービスを起動"
            echo "   2. ~/.codex/config.toml に上記設定を追記"
            echo "   3. 接続先URL: ${CRM_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            ;;

        copilot-cli)
            cat > "${CRM_OUTPUT_DIR}/mcp-config.json" <<EOF
{
  "mcpServers": {
    "${CRM_SERVER_KEY}": {
      "type": "http",
      "url": "${CRM_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ Copilot CLI設定を生成しました: ${CRM_OUTPUT_DIR}/mcp-config.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. copilot-review-mcp サービスを起動"
            echo "   2. ~/.copilot/mcp-config.json に配置"
            echo "   3. 接続先URL: ${CRM_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            ;;

        claude-desktop)
            echo "⚠️  Claude Desktop は stdio トランスポートのみ対応しており、"
            echo "   copilot-review-mcp (HTTP only) には直接接続できません。"
            echo ""
            echo "   代替手段: VS Code / Cursor / Kiro / Amazon Q / Codex / Copilot CLI"
            echo "   を使用してください。"
            echo "   例: $0 --ide vscode --service copilot-review-mcp"
            exit 0
            ;;

        *)
            echo "❌ 未対応のIDE: $IDE"
            usage
            ;;
    esac
    exit 0
fi

# ── mcp-gateway サービス ─────────────────────────────────────────────────────

if [[ "$SERVICE" == "mcp-gateway" ]]; then
    GW_SERVER_KEY="github-mcp-server-docker"
    GW_MCP_URL="${GATEWAY_URL}/mcp/github"

    case "$IDE" in
        vscode|claude-desktop|kiro|amazonq|codex|copilot-cli)
            ;;
        *)
            echo "❌ 未対応のIDEです: $IDE"
            echo "対応IDE: vscode, claude-desktop, kiro, amazonq, codex, copilot-cli"
            exit 1
            ;;
    esac

    GW_OUTPUT_DIR="${PROJECT_ROOT}/config/ide-configs/mcp-gateway/${IDE}"
    mkdir -p "${GW_OUTPUT_DIR}"

    case "$IDE" in
        claude-desktop)
            cat > "${GW_OUTPUT_DIR}/claude_desktop_config.json" <<EOF
{
  "mcpServers": {
    "${GW_SERVER_KEY}": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "${GW_MCP_URL}"
      ]
    }
  }
}
EOF
            echo "✅ Claude Desktop設定を生成しました: ${GW_OUTPUT_DIR}/claude_desktop_config.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. mcp-gateway / github-mcp サービスを起動:"
            echo "      make start-gateway"
            echo "   2. 生成された設定を Claude Desktop設定ファイルにマージ:"
            echo "      Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
            echo "      macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json"
            echo "   3. Claude Desktop を再起動"
            echo "   4. ブラウザで GitHub OAuth 認証フロー（初回のみ）"
            echo ""
            echo "ℹ️  mcp-remote が OAuth フローを自動的に処理します（ブラウザが開きます）"
            echo "   接続先: ${GW_MCP_URL}"
            ;;

        vscode)
            cat > "${GW_OUTPUT_DIR}/settings.json" <<EOF
{
  "mcpServers": {
    "${GW_SERVER_KEY}": {
      "type": "http",
      "url": "${GW_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ VS Code設定を生成しました: ${GW_OUTPUT_DIR}/settings.json"
            echo ""
            echo "📋 設定方法:"
            echo "   1. mcp-gateway / github-mcp サービスを起動:"
            echo "      make start-gateway"
            echo "   2. VS Code設定 (.vscode/settings.json) に追加"
            echo "   3. 接続先URL: ${GW_MCP_URL}"
            echo ""
            echo "💡 Bearer トークンの設定:"
            echo "   export GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here"
            ;;

        kiro)
            cat > "${GW_OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcp": {
    "servers": {
      "${GW_SERVER_KEY}": {
        "type": "http",
        "url": "${GW_MCP_URL}",
        "headers": {
          "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
EOF
            echo "✅ Kiro設定を生成しました: ${GW_OUTPUT_DIR}/mcp.json"
            echo "   接続先URL: ${GW_MCP_URL}"
            ;;

        amazonq)
            cat > "${GW_OUTPUT_DIR}/mcp.json" <<EOF
{
  "mcpServers": {
    "${GW_SERVER_KEY}": {
      "type": "http",
      "url": "${GW_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ Amazon Q設定を生成しました: ${GW_OUTPUT_DIR}/mcp.json"
            echo "   接続先URL: ${GW_MCP_URL}"
            ;;

        codex)
            cat > "${GW_OUTPUT_DIR}/config.toml" <<EOF
[mcp_servers.${GW_SERVER_KEY}]
url = "${GW_MCP_URL}"
bearer_token_env_var = "GITHUB_PERSONAL_ACCESS_TOKEN"
EOF
            echo "✅ Codex設定を生成しました: ${GW_OUTPUT_DIR}/config.toml"
            echo "   接続先URL: ${GW_MCP_URL}"
            ;;

        copilot-cli)
            cat > "${GW_OUTPUT_DIR}/mcp-config.json" <<EOF
{
  "mcpServers": {
    "${GW_SERVER_KEY}": {
      "type": "http",
      "url": "${GW_MCP_URL}",
      "headers": {
        "Authorization": "Bearer \${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
EOF
            echo "✅ Copilot CLI設定を生成しました: ${GW_OUTPUT_DIR}/mcp-config.json"
            echo "   接続先URL: ${GW_MCP_URL}"
            ;;
    esac
    exit 0
fi

# ── github-mcp サービス（既存ロジック）─────────────────────────────────────────
#
# ⚠️  注意: docker-compose.yml の変更により github-mcp はホスト非公開（Docker ネットワーク内部のみ）
# になっています。GITHUB_MCP_SERVER_URL を明示的に設定していない場合、生成される設定の接続先
# (http://127.0.0.1:8082) には接続できません。
#
# ホストから github-mcp-server に接続するには mcp-gateway 経由を推奨:
#   $0 --ide ${IDE} --service mcp-gateway
#
if [[ -z "${GITHUB_MCP_SERVER_URL:-}" ]] && [[ -z "$(extract_env_value "GITHUB_MCP_SERVER_URL")" ]]; then
    echo "⚠️  警告: github-mcp はホスト非公開（Docker ネットワーク内部のみ）です。"
    echo "   生成された設定の接続先 (${SERVER_URL}) には接続できない可能性があります。"
    echo "   代わりに mcp-gateway 経由を使用することを推奨します:"
    echo "   $0 --ide ${IDE} --service mcp-gateway"
    echo ""
fi

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
        DEFAULT_GITHUB_MCP_IMAGE="ghcr.io/github/github-mcp-server:main"

        # 環境変数が未設定の場合のみ .env から GITHUB_MCP_IMAGE を補完
        if [ -z "${GITHUB_MCP_IMAGE:-}" ] && [ -f "${ENV_FILE}" ]; then
            ENV_GITHUB_MCP_IMAGE="$(extract_env_value "GITHUB_MCP_IMAGE")"
            if [ -n "${ENV_GITHUB_MCP_IMAGE}" ]; then
                GITHUB_MCP_IMAGE="${ENV_GITHUB_MCP_IMAGE}"
            fi
        fi

        CLAUDE_DOCKER_IMAGE="${GITHUB_MCP_IMAGE:-${DEFAULT_GITHUB_MCP_IMAGE}}"
        CONFIG_BIND_PATH="${PROJECT_ROOT}/config/github-mcp"

        if command -v wslpath &>/dev/null; then
            CONFIG_BIND_PATH="$(wslpath -w "${CONFIG_BIND_PATH}")"
        fi
        CONFIG_BIND_PATH_JSON="${CONFIG_BIND_PATH//\\/\\\\}"

        cat > "${OUTPUT_DIR}/claude_desktop_config.json" <<EOF
{
  "mcpServers": {
    "${MCP_SERVER_KEY}": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-v", "${CONFIG_BIND_PATH_JSON}:/app/config:rw",
        "-v", "github-mcp-cache:/app/cache:rw",
        "${CLAUDE_DOCKER_IMAGE}",
        "stdio"
      ]
    }
  }
}
EOF
        echo "✅ Claude Desktop設定を生成しました: ${OUTPUT_DIR}/claude_desktop_config.json"
        echo ""
        echo "ℹ️  Claude Desktop -> docker run -i --rm ${CLAUDE_DOCKER_IMAGE} stdio"
        echo "   PATは環境変数 GITHUB_PERSONAL_ACCESS_TOKEN を -e で受け渡します"
        echo ""
        echo "📋 設定方法:"
        echo "   1. 生成された設定を Claude Desktop設定ファイルにマージする"
        echo "      ${OUTPUT_DIR}/claude_desktop_config.json"
        echo "      Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
        echo "      macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
        echo "      Linux: ~/.config/Claude/claude_desktop_config.json"
        echo "   2. 環境変数 GITHUB_PERSONAL_ACCESS_TOKEN を設定"
        echo "   3. Claude Desktop を再起動"
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
