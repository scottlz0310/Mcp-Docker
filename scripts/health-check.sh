#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
WITH_API_CHECK="auto"

usage() {
    cat <<EOF
使用方法: $0 [オプション]

オプション:
  --with-api    GitHub API接続確認を必ず実行
  --no-api      GitHub API接続確認をスキップ
  -h, --help    ヘルプを表示
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-api)
            WITH_API_CHECK="always"
            shift
            ;;
        --no-api)
            WITH_API_CHECK="never"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "❌ 不明なオプション: $1"
            echo ""
            usage
            exit 1
            ;;
    esac
done

require_command() {
    local cmd="$1"
    local install_hint="$2"

    if command -v "${cmd}" > /dev/null 2>&1; then
        return
    fi

    echo "❌ 必須コマンドが見つかりません: ${cmd}"
    echo "   ${install_hint}"
    exit 1
}

ensure_docker_ready() {
    require_command "docker" "Docker Desktop または Docker Engine をインストールしてください。"

    if ! docker compose version > /dev/null 2>&1; then
        echo "❌ Docker Compose v2 が利用できません"
        echo "   Docker Composeプラグインを有効化してください。"
        exit 1
    fi

    if ! docker info > /dev/null 2>&1; then
        echo "❌ Dockerデーモンに接続できません"
        echo "   Docker Desktop / Docker Engine を起動してください。"
        exit 1
    fi
}

extract_env_value() {
    local key="$1"
    if [[ ! -f "${ENV_FILE}" ]]; then
        return 0
    fi

    local line
    line="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 || true)"
    echo "${line#*=}"
}

extract_token_from_env_file() {
    extract_env_value "GITHUB_PERSONAL_ACCESS_TOKEN"
}

extract_api_url_from_env_file() {
    extract_env_value "GITHUB_API_URL"
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

    server_url="${server_url%/}"
    echo "${server_url}"
}

is_placeholder_token() {
    local token="$1"

    if [[ -z "${token}" ]]; then
        return 0
    fi

    # Match common placeholder patterns from .env.template
    # Explicit patterns improve readability despite redundancy with *your_token_here*
    case "${token}" in
        github_pat_your_token_here|ghp_your_token_here|*your_token_here*)
            return 0
            ;;
    esac

    if [[ "${token}" =~ ^github_pat_[xX]+$ ]] || [[ "${token}" =~ ^ghp_[xX]+$ ]]; then
        return 0
    fi

    return 1
}

is_token_prefix_valid() {
    local token="$1"
    [[ "${token}" =~ ^(github_pat_|ghp_) ]]
}

echo "🏥 GitHub MCP Server ヘルスチェック"
echo ""

ensure_docker_ready

# コンテナ状態確認
container_id="$(docker compose ps -q github-mcp)"
if [[ -z "${container_id}" ]]; then
    echo "❌ コンテナが見つかりません"
    echo "   起動: docker compose up -d github-mcp"
    exit 1
fi

running_state="$(docker inspect -f '{{.State.Running}}' "${container_id}")"
if [[ "${running_state}" != "true" ]]; then
    echo "❌ コンテナは停止状態です"
    echo "   ログ確認: docker compose logs github-mcp"
    exit 1
fi
echo "✅ コンテナは起動しています"

restart_count="$(docker inspect -f '{{.RestartCount}}' "${container_id}")"
if [[ "${restart_count}" != "0" ]]; then
    echo "⚠️  コンテナの再起動回数: ${restart_count}"
    echo "   不安定な可能性があるためログ確認を推奨: docker compose logs --tail=200 github-mcp"
else
    echo "✅ 再起動は発生していません"
fi

# HTTPエンドポイント確認
server_url="$(resolve_server_url)"
if command -v curl > /dev/null 2>&1; then
    # curl failures should not abort the script, so we use || true and check the result
    http_status="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${server_url}/" || true)"
    # 正常な3桁のHTTPステータスコードでない場合は "000" をデフォルトとする
    if [[ ! "${http_status}" =~ ^[0-9]{3}$ ]]; then
        http_status="000"
    fi
    if [[ "${http_status}" == "200" ]] || [[ "${http_status}" == "401" ]]; then
        echo "✅ MCP HTTPエンドポイント疎通成功 (${server_url}, status=${http_status})"
    else
        echo "❌ MCP HTTPエンドポイント疎通失敗 (${server_url}, status=${http_status})"
        exit 1
    fi
else
    echo "⚠️  curl が未インストールのため、MCP HTTPエンドポイント確認をスキップします"
fi

# GitHub API接続確認
token="${GITHUB_PERSONAL_ACCESS_TOKEN:-}"
if [[ -z "${token}" ]]; then
    token="$(extract_token_from_env_file)"
fi

api_url="${GITHUB_API_URL:-}"
if [[ -z "${api_url}" ]]; then
    api_url="$(extract_api_url_from_env_file)"
fi
if [[ -z "${api_url}" ]]; then
    api_url="https://api.github.com"
fi

should_run_api_check=false
if [[ "${WITH_API_CHECK}" == "always" ]]; then
    should_run_api_check=true
elif [[ "${WITH_API_CHECK}" == "auto" ]] && [[ -n "${token}" ]]; then
    should_run_api_check=true
fi

if [[ "${should_run_api_check}" == "true" ]]; then
    if is_placeholder_token "${token}" || ! is_token_prefix_valid "${token}"; then
        echo "⚠️  GITHUB_PERSONAL_ACCESS_TOKEN が未設定またはプレースホルダのため、API接続確認をスキップします"
    elif ! command -v curl > /dev/null 2>&1; then
        echo "⚠️  curl が未インストールのため、API接続確認をスキップします"
    elif curl -fsS -H "Authorization: Bearer ${token}" "${api_url}/user" > /dev/null; then
        echo "✅ GitHub API接続成功"
    else
        echo "❌ GitHub API接続失敗"
        echo "   GITHUB_PERSONAL_ACCESS_TOKEN を確認してください"
        exit 1
    fi
else
    if [[ "${WITH_API_CHECK}" == "never" ]]; then
        echo "ℹ️  API接続確認はスキップしました (--no-api)"
    else
        echo "ℹ️  GITHUB_PERSONAL_ACCESS_TOKEN が未設定のため、API接続確認をスキップしました"
    fi
fi

echo ""
echo "🎉 すべてのチェックに合格しました"
