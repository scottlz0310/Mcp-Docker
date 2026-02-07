#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_TEMPLATE_FILE="${PROJECT_ROOT}/.env.template"
PREPARE_ONLY=false

usage() {
    cat <<EOF
使用方法: $0 [オプション]

オプション:
  --prepare-only   環境整備のみ実行（.env作成、ディレクトリ作成、事前確認）
  -h, --help       ヘルプを表示
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prepare-only)
            PREPARE_ONLY=true
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

ensure_env_file() {
    if [[ -f "${ENV_FILE}" ]]; then
        return
    fi

    echo "📝 .env ファイルを作成中..."
    cp "${ENV_TEMPLATE_FILE}" "${ENV_FILE}"
    echo "✅ .env ファイルを作成しました"
    echo ""
}

extract_token_from_env_file() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        return 0
    fi

    local token_line
    token_line="$(grep -E "^GITHUB_PERSONAL_ACCESS_TOKEN=" "${ENV_FILE}" | tail -n1 || true)"
    echo "${token_line#GITHUB_PERSONAL_ACCESS_TOKEN=}"
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

ensure_writable_directory() {
    local dir="$1"

    if [[ -w "${dir}" ]]; then
        return
    fi

    echo "⚠️  ディレクトリに書き込みできません: ${dir}"
    echo "   必要に応じて権限を修正してください: sudo chown -R $(id -un):$(id -gn) ${dir}"
    echo "   現在の権限のまま続行します"
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

validate_token_or_exit() {
    local token="$1"

    if [[ -z "${token}" ]]; then
        echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN が設定されていません"
        echo "   .env または環境変数に設定してください。"
        echo "   取得先: https://github.com/settings/tokens?type=beta"
        exit 1
    fi

    if is_placeholder_token "${token}"; then
        echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN がプレースホルダのままです"
        echo "   実際のトークン値に置き換えてください。"
        exit 1
    fi

    if ! is_token_prefix_valid "${token}"; then
        echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN の形式が不正です"
        echo "   github_pat_ または ghp_ で始まるトークンを設定してください。"
        exit 1
    fi
}

show_token_setup_help() {
    echo "⚠️  GITHUB_PERSONAL_ACCESS_TOKEN を設定してください:"
    echo "   1. Fine-grained tokenを作成 (推奨): https://github.com/settings/tokens?type=beta"
    echo "   2. .env の GITHUB_PERSONAL_ACCESS_TOKEN に設定"
    echo "   3. もしくは環境変数を設定: export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxx"
    echo ""
}

echo "🚀 GitHub MCP Server セットアップ"
echo ""

ensure_env_file

token_source=".env"
token="${GITHUB_PERSONAL_ACCESS_TOKEN:-}"
if [[ -n "${token}" ]]; then
    token_source="環境変数"
else
    token="$(extract_token_from_env_file)"
fi

if [[ "${PREPARE_ONLY}" == "true" ]]; then
    echo "🧰 環境整備モードで実行します (--prepare-only)"
    echo ""

    if [[ -z "${token}" ]] || is_placeholder_token "${token}" || ! is_token_prefix_valid "${token}"; then
        show_token_setup_help
    else
        echo "✅ GITHUB_PERSONAL_ACCESS_TOKEN は ${token_source} から検出されました"
        echo ""
    fi
else
    validate_token_or_exit "${token}"
    echo "✅ GITHUB_PERSONAL_ACCESS_TOKEN を ${token_source} から使用します"
    echo ""
fi

# 設定ディレクトリの作成
echo "📁 設定ディレクトリを作成中..."
mkdir -p "${PROJECT_ROOT}/config/github-mcp"
ensure_writable_directory "${PROJECT_ROOT}/config/github-mcp"
echo "✅ 設定ディレクトリを作成しました"
echo ""

if [[ "${PREPARE_ONLY}" == "true" ]]; then
    echo "🎉 環境整備のみ完了しました"
    echo ""
    echo "📋 次のステップ:"
    echo "   1. Dockerをインストール/起動"
    echo "   2. .env の GITHUB_PERSONAL_ACCESS_TOKEN を実値に更新"
    echo "   3. セットアップ本実行: ./scripts/setup.sh"
    exit 0
fi

ensure_docker_ready

# Dockerイメージのビルド
echo "🔨 Docker イメージをビルド中..."
docker compose build github-mcp
echo "✅ Docker イメージをビルドしました"
echo ""

# サービスの起動
echo "🚀 サービスを起動中..."
docker compose up -d github-mcp
echo "✅ サービスを起動しました"
echo ""

# ヘルスチェック
echo "🏥 ヘルスチェック中..."
sleep 3
container_id="$(docker compose ps -q github-mcp)"
if [[ -n "${container_id}" ]] && [[ "$(docker inspect -f '{{.State.Running}}' "${container_id}")" == "true" ]]; then
    echo "✅ サービスコンテナは起動しています"
else
    echo "⚠️  コンテナ起動状態を確認できませんでした"
    echo "   ログを確認してください: docker compose logs github-mcp"
fi
echo ""

echo "🎉 セットアップ完了！"
echo ""
echo "📋 次のステップ:"
echo "   1. IDE設定を生成: ./scripts/generate-ide-config.sh --ide vscode"
echo "   2. ログを確認: docker compose logs -f github-mcp"
echo "   3. ステータス確認: docker compose ps"
