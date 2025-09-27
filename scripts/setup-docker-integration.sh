#!/bin/bash
# Docker統合セットアップスクリプト
# GitHub Actions Simulatorのための適切なDocker環境を設定します

set -euo pipefail

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker環境の確認
check_docker_installation() {
    log_info "Docker環境を確認中..."

    if ! command -v docker &> /dev/null; then
        log_error "Dockerがインストールされていません"
        log_info "Docker Desktopをインストールしてください: https://www.docker.com/products/docker-desktop/"
        return 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemonが実行されていません"
        log_info "Docker Desktopを起動してください"
        return 1
    fi

    log_success "Docker環境は正常です"
    docker --version
    return 0
}

# actバイナリの確認とインストール
check_act_installation() {
    log_info "actバイナリを確認中..."

    if ! command -v act &> /dev/null; then
        log_warning "actがインストールされていません"
        log_info "actをインストール中..."

        if command -v brew &> /dev/null; then
            brew install act
        elif command -v curl &> /dev/null; then
            curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
        else
            log_error "actのインストールに失敗しました"
            log_info "手動でactをインストールしてください: https://github.com/nektos/act#installation"
            return 1
        fi
    fi

    if command -v act &> /dev/null; then
        log_success "actバイナリは正常です"
        act --version
        return 0
    else
        log_error "actのインストールに失敗しました"
        return 1
    fi
}

# Dockerグループの確認と設定
setup_docker_permissions() {
    log_info "Docker権限を確認中..."

    # Dockerグループの存在確認
    if ! getent group docker &> /dev/null; then
        log_warning "dockerグループが存在しません"
        log_info "dockerグループを作成中..."
        sudo groupadd docker
    fi

    # 現在のユーザーがdockerグループに属しているか確認
    if ! groups "$USER" | grep -q docker; then
        log_warning "ユーザー $USER がdockerグループに属していません"
        log_info "ユーザーをdockerグループに追加中..."
        sudo usermod -aG docker "$USER"
        log_warning "グループ変更を反映するため、ログアウト・ログインしてください"
        log_warning "または 'newgrp docker' を実行してください"
    else
        log_success "Docker権限は正常です"
    fi

    return 0
}

# Docker Composeネットワークの設定
setup_docker_network() {
    log_info "Docker Composeネットワークを設定中..."

    # 既存のネットワークを確認
    if docker network ls | grep -q mcp-network; then
        log_info "mcp-networkは既に存在します"
    else
        log_info "mcp-networkを作成中..."
        docker network create mcp-network
        log_success "mcp-networkを作成しました"
    fi

    return 0
}

# 必要なディレクトリの作成
setup_directories() {
    log_info "必要なディレクトリを作成中..."

    local directories=(
        "output"
        "logs"
        ".github/workflows"
    )

    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "ディレクトリを作成しました: $dir"
        else
            log_info "ディレクトリは既に存在します: $dir"
        fi
    done

    # ディレクトリの権限設定
    chmod 755 output logs
    log_info "ディレクトリの権限を設定しました"

    return 0
}

# 環境変数の設定
setup_environment_variables() {
    log_info "環境変数を設定中..."

    # .envファイルの作成
    if [[ ! -f .env ]]; then
        if [[ -f .env.template ]]; then
            cp .env.template .env
            log_success ".envファイルを作成しました"
        else
            log_warning ".env.templateが見つかりません"
        fi
    else
        log_info ".envファイルは既に存在します"
    fi

    # DockerグループIDの取得と設定
    DOCKER_GID=$(getent group docker | cut -d: -f3)
    if [[ -n "$DOCKER_GID" ]]; then
        log_info "DockerグループID: $DOCKER_GID"

        # .envファイルにDOCKER_GIDを追加または更新
        if [[ -f .env ]]; then
            if grep -q "DOCKER_GID" .env; then
                sed -i "s/^DOCKER_GID=.*/DOCKER_GID=$DOCKER_GID/" .env
                log_success "DOCKER_GIDを更新しました: $DOCKER_GID"
            else
                echo "DOCKER_GID=$DOCKER_GID" >> .env
                log_success "DOCKER_GIDを.envファイルに追加しました: $DOCKER_GID"
            fi
        fi
    fi

    # ユーザーIDとグループIDの設定
    USER_ID=$(id -u)
    GROUP_ID=$(id -g)

    if [[ -f .env ]]; then
        # USER_IDの設定
        if grep -q "USER_ID" .env; then
            sed -i "s/^USER_ID=.*/USER_ID=$USER_ID/" .env
        else
            echo "USER_ID=$USER_ID" >> .env
        fi

        # GROUP_IDの設定
        if grep -q "GROUP_ID" .env; then
            sed -i "s/^GROUP_ID=.*/GROUP_ID=$GROUP_ID/" .env
        else
            echo "GROUP_ID=$GROUP_ID" >> .env
        fi

        log_success "ユーザー権限を設定しました: USER_ID=$USER_ID, GROUP_ID=$GROUP_ID"
    fi

    return 0
}

# Docker統合テストの実行
run_integration_test() {
    log_info "Docker統合テストを実行中..."

    if [[ -f examples/docker_integration_test.py ]]; then
        if python examples/docker_integration_test.py; then
            log_success "Docker統合テストが成功しました"
            return 0
        else
            log_warning "Docker統合テストで問題が検出されました"
            log_info "上記の出力を確認して問題を修正してください"
            return 1
        fi
    else
        log_warning "Docker統合テストスクリプトが見つかりません"
        return 1
    fi
}

# コンテナ起動検証の実行
run_container_verification() {
    log_info "コンテナ起動検証を実行中..."

    if [[ -f scripts/verify-container-startup.sh ]]; then
        if bash scripts/verify-container-startup.sh --docker-health-check; then
            log_success "Docker Health Checkが正常に完了しました"
            return 0
        else
            log_warning "Docker Health Checkで問題が検出されました"
            log_info "詳細は上記の出力を確認してください"
            return 1
        fi
    else
        log_warning "コンテナ起動検証スクリプトが見つかりません"
        return 1
    fi
}

# メイン処理
main() {
    log_info "GitHub Actions Simulator Docker統合セットアップを開始します"
    echo "=================================================================="

    local exit_code=0

    # 各セットアップステップを実行
    check_docker_installation || exit_code=1
    check_act_installation || exit_code=1
    setup_docker_permissions || exit_code=1
    setup_docker_network || exit_code=1
    setup_directories || exit_code=1
    setup_environment_variables || exit_code=1

    if [[ $exit_code -eq 0 ]]; then
        log_info "統合テストを実行します..."
        run_integration_test || exit_code=1

        # Docker Health Checkサービスを起動して検証
        log_info "Docker Health Checkサービスを起動して検証します..."
        if docker-compose --profile tools up --no-deps docker-health-check; then
            run_container_verification || exit_code=1
        else
            log_error "Docker Health Checkサービスの起動に失敗しました"
            exit_code=1
        fi
    fi

    echo "=================================================================="

    if [[ $exit_code -eq 0 ]]; then
        log_success "Docker統合セットアップが完了しました！"
        log_info "GitHub Actions Simulatorを使用する準備ができています"
        log_info "次のコマンドでサービスを起動できます:"
        echo "  docker-compose --profile tools up -d actions-simulator"
        echo ""
        log_info "コンテナの起動状態を確認するには:"
        echo "  bash scripts/verify-container-startup.sh"
    else
        log_error "Docker統合セットアップで問題が発生しました"
        log_info "上記のエラーメッセージを確認して問題を修正してください"
    fi

    return $exit_code
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
