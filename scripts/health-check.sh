#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SERVICE="mcp-gateway"

usage() {
    cat <<EOF
使用方法: $0 [オプション]

オプション:
  --service <サービス名>  ヘルスチェック対象サービス (デフォルト: mcp-gateway)
                          mcp-gateway        : mcp-gateway 経由のエンドポイントを確認 (port MCP_GATEWAY_PORT、デフォルト: 8080)
                          review-raven       : review-raven / mcp-gateway の各コンテナ状態 + mcp-gateway 経由で確認
  -h, --help              ヘルプを表示
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --service)
            SERVICE="$2"
            shift 2
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

case "$SERVICE" in
    mcp-gateway|review-raven) ;;
    *)
        echo "❌ 未対応のサービス: $SERVICE"
        echo "対応サービス: mcp-gateway, review-raven"
        exit 1
        ;;
esac

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

resolve_gateway_url() {
    local url="${MCP_GATEWAY_URL:-}"
    if [[ -z "${url}" ]]; then
        url="$(extract_env_value "MCP_GATEWAY_URL")"
    fi
    if [[ -z "${url}" ]]; then
        url="${MCP_GATEWAY_PUBLIC_URL:-}"
    fi
    if [[ -z "${url}" ]]; then
        url="$(extract_env_value "MCP_GATEWAY_PUBLIC_URL")"
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

# ローカル HTTPS (make setup-tls) は mkcert ローカル CA 署名のため、curl が CA を
# 信頼していない環境でも疎通確認できるよう localhost / 127.0.0.1 宛てに限り
# 証明書検証のスキップ (-k) を許可する。それ以外のホストでは検証を維持し誤設定を検知する。
# https://localhost:pass@evil.com のような userinfo 付き URL で実ホストを誤認しないよう、
# authority を解析して host を完全一致で判定し、userinfo を含む URL は拒否する。
curl_insecure_ok() {
    local url="$1"
    local authority host
    case "${url}" in
        https://*) ;;
        *) return 1 ;;
    esac
    authority="${url#https://}"
    authority="${authority%%/*}"
    if [[ "${authority}" == *@* ]]; then
        return 1
    fi
    host="${authority%%:*}"
    [[ "${host}" == "localhost" || "${host}" == "127.0.0.1" ]]
}

check_gateway_endpoint() {
    local gateway_url="$1"
    local curl_args=(-s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10)
    if curl_insecure_ok "${gateway_url}"; then
        curl_args+=(-k)
    fi

    local http_status
    # curl failures should not abort the script, so we use || true and check the result
    http_status="$(curl "${curl_args[@]}" "${gateway_url}/health" || true)"
    # 正常な3桁のHTTPステータスコードでない場合は "000" をデフォルトとする
    if [[ ! "${http_status}" =~ ^[0-9]{3}$ ]]; then
        http_status="000"
    fi
    if [[ "${http_status}" == "200" ]]; then
        echo "✅ mcp-gateway ヘルスエンドポイント疎通成功 (${gateway_url}/health, status=${http_status})"
        return 0
    fi
    echo "❌ mcp-gateway ヘルスエンドポイント疎通失敗 (${gateway_url}/health, status=${http_status})"
    return 1
}


check_container_state() {
    local service_name="$1"
    local container_id
    container_id="$(docker compose ps -q "${service_name}")"
    if [[ -z "${container_id}" ]]; then
        echo "❌ コンテナが見つかりません (${service_name})"
        echo "   起動: docker compose up -d ${service_name}"
        return 1
    fi

    local running_state
    running_state="$(docker inspect -f '{{.State.Running}}' "${container_id}")"
    if [[ "${running_state}" != "true" ]]; then
        echo "❌ コンテナは停止状態です (${service_name})"
        echo "   ログ確認: docker compose logs ${service_name}"
        return 1
    fi
    echo "✅ コンテナは起動しています (${service_name})"

    local restart_count
    restart_count="$(docker inspect -f '{{.RestartCount}}' "${container_id}")"
    if [[ "${restart_count}" != "0" ]]; then
        echo "⚠️  コンテナの再起動回数: ${restart_count} (${service_name})"
        echo "   不安定な可能性があるためログ確認を推奨: docker compose logs --tail=200 ${service_name}"
    else
        echo "✅ 再起動は発生していません (${service_name})"
    fi
}

echo "🏥 MCP ヘルスチェック (--service ${SERVICE})"
echo ""

ensure_docker_ready

if [[ "${SERVICE}" == "review-raven" ]]; then
    check_container_state "review-raven"
    check_container_state "mcp-gateway"
    gateway_url="$(resolve_gateway_url)"
    if command -v curl > /dev/null 2>&1; then
        check_gateway_endpoint "${gateway_url}" || exit 1
    else
        echo "⚠️  curl が未インストールのため、HTTP エンドポイント確認をスキップします"
    fi
    echo ""
    echo "🎉 すべてのチェックに合格しました"
    exit 0
fi

# mcp-gateway のヘルスチェック
check_container_state "mcp-gateway"

# HTTP エンドポイント確認 (mcp-gateway 経由)
gateway_url="$(resolve_gateway_url)"
if command -v curl > /dev/null 2>&1; then
    check_gateway_endpoint "${gateway_url}" || exit 1
else
    echo "⚠️  curl が未インストールのため、HTTP エンドポイント確認をスキップします"
fi

echo ""
echo "🎉 すべてのチェックに合格しました"
