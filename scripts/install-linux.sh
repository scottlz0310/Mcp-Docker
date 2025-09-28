#!/usr/bin/env bash
# GitHub Actions Simulator - Linux インストールスクリプト
#
# このスクリプトは Linux 環境での GitHub Actions Simulator の
# 自動インストールを支援します。

set -euo pipefail

# カラー出力の設定
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# ログ関数
info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }

# プラットフォーム検出
detect_linux_distro() {
  if command -v lsb_release >/dev/null 2>&1; then
    lsb_release -si 2>/dev/null | tr '[:upper:]' '[:lower:]'
  elif [[ -f /etc/os-release ]]; then
    grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"' | tr '[:upper:]' '[:lower:]'
  else
    echo "unknown"
  fi
}

# Docker インストール (Ubuntu/Debian)
install_docker_ubuntu() {
  info "Ubuntu/Debian 用 Docker をインストール中..."

  # 古いバージョンの削除
  sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

  # 必要なパッケージのインストール
  sudo apt-get update
  sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

  # Docker の公式 GPG キーを追加
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

  # Docker リポジトリを追加
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  # Docker Engine のインストール
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

  success "Docker のインストールが完了しました"
}

# Docker インストール (Fedora/RHEL/CentOS)
install_docker_fedora() {
  info "Fedora/RHEL/CentOS 用 Docker をインストール中..."

  # 古いバージョンの削除
  sudo dnf remove -y docker \
    docker-client \
    docker-client-latest \
    docker-common \
    docker-latest \
    docker-latest-logrotate \
    docker-logrotate \
    docker-selinux \
    docker-engine-selinux \
    docker-engine 2>/dev/null || true

  # Docker CE リポジトリの追加
  sudo dnf -y install dnf-plugins-core
  sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo

  # Docker Engine のインストール
  sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

  success "Docker のインストールが完了しました"
}

# Docker インストール (Arch Linux)
install_docker_arch() {
  info "Arch Linux 用 Docker をインストール中..."

  # Docker のインストール
  sudo pacman -S --noconfirm docker docker-compose

  success "Docker のインストールが完了しました"
}

# Docker サービスの設定
configure_docker_service() {
  info "Docker サービスを設定中..."

  # Docker サービスの開始と自動起動設定
  sudo systemctl start docker
  sudo systemctl enable docker

  # 現在のユーザーを docker グループに追加
  sudo usermod -aG docker "$USER"

  success "Docker サービスの設定が完了しました"
  warning "新しいグループ設定を適用するため、ログアウト/ログインまたは 'newgrp docker' を実行してください"
}

# uv のインストール
install_uv() {
  info "uv をインストール中..."

  if command -v uv >/dev/null 2>&1; then
    success "uv は既にインストールされています"
    return 0
  fi

  # 公式インストーラーを使用
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # PATH の更新
  export PATH="$HOME/.cargo/bin:$PATH"

  if command -v uv >/dev/null 2>&1; then
    success "uv のインストールが完了しました"
  else
    warning "uv のインストールに失敗しました。手動でインストールしてください"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi
}

# Git のインストール
install_git() {
  info "Git をインストール中..."

  if command -v git >/dev/null 2>&1; then
    success "Git は既にインストールされています"
    return 0
  fi

  local distro
  distro=$(detect_linux_distro)

  case "$distro" in
    ubuntu|debian)
      sudo apt-get update
      sudo apt-get install -y git
      ;;
    fedora|centos|rhel|rocky|almalinux)
      sudo dnf install -y git
      ;;
    arch|manjaro)
      sudo pacman -S --noconfirm git
      ;;
    opensuse*|suse*)
      sudo zypper install -y git
      ;;
    *)
      error "サポートされていないディストリビューション: $distro"
      echo "手動で Git をインストールしてください"
      return 1
      ;;
  esac

  success "Git のインストールが完了しました"
}

# Docker の最適化設定
optimize_docker_config() {
  info "Docker の最適化設定を適用中..."

  # daemon.json の作成
  local daemon_config="/etc/docker/daemon.json"
  if [[ ! -f "$daemon_config" ]]; then
    sudo tee "$daemon_config" > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  }
}
EOF

    # Docker サービスの再起動
    sudo systemctl restart docker
    success "Docker の最適化設定を適用しました"
  else
    info "Docker 設定ファイルは既に存在します: $daemon_config"
  fi
}

# ファイアウォール設定 (Fedora/RHEL系)
configure_firewall_fedora() {
  if command -v firewall-cmd >/dev/null 2>&1; then
    info "ファイアウォール設定を適用中..."

    sudo firewall-cmd --permanent --zone=trusted --add-interface=docker0 2>/dev/null || true
    sudo firewall-cmd --permanent --zone=trusted --add-masquerade 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true

    success "ファイアウォール設定を適用しました"
  fi
}

# SELinux 設定 (Fedora/RHEL系)
configure_selinux() {
  if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce)" == "Enforcing" ]]; then
    info "SELinux 設定を適用中..."

    sudo setsebool -P container_manage_cgroup on 2>/dev/null || true

    success "SELinux 設定を適用しました"
  fi
}

# インストール検証
verify_installation() {
  info "インストールを検証中..."

  local errors=0

  # Docker の確認
  if command -v docker >/dev/null 2>&1; then
    local docker_version
    docker_version=$(docker --version 2>/dev/null || echo "取得失敗")
    success "Docker: $docker_version"
  else
    error "Docker が見つかりません"
    ((errors++))
  fi

  # Docker Compose の確認
  if docker compose version >/dev/null 2>&1; then
    local compose_version
    compose_version=$(docker compose version --short 2>/dev/null || echo "取得失敗")
    success "Docker Compose: $compose_version"
  else
    error "Docker Compose が見つかりません"
    ((errors++))
  fi

  # Git の確認
  if command -v git >/dev/null 2>&1; then
    local git_version
    git_version=$(git --version 2>/dev/null || echo "取得失敗")
    success "Git: $git_version"
  else
    error "Git が見つかりません"
    ((errors++))
  fi

  # uv の確認
  if command -v uv >/dev/null 2>&1; then
    local uv_version
    uv_version=$(uv --version 2>/dev/null || echo "取得失敗")
    success "uv: $uv_version"
  else
    warning "uv が見つかりません（オプション）"
  fi

  if [[ $errors -eq 0 ]]; then
    success "✅ すべての依存関係が正常にインストールされました！"
    return 0
  else
    error "❌ $errors 個のエラーが見つかりました"
    return 1
  fi
}

# 使用方法の表示
show_usage() {
  cat <<EOF
GitHub Actions Simulator - Linux インストールスクリプト

使用方法:
  $0 [オプション]

オプション:
  --help, -h          このヘルプを表示
  --docker-only       Docker のみをインストール
  --skip-optimization 最適化設定をスキップ
  --verify-only       インストール検証のみを実行

例:
  $0                  # 完全インストール
  $0 --docker-only    # Docker のみインストール
  $0 --verify-only    # 検証のみ実行
EOF
}

# メイン処理
main() {
  local docker_only=false
  local skip_optimization=false
  local verify_only=false

  # 引数の解析
  while [[ $# -gt 0 ]]; do
    case $1 in
      --help|-h)
        show_usage
        exit 0
        ;;
      --docker-only)
        docker_only=true
        shift
        ;;
      --skip-optimization)
        skip_optimization=true
        shift
        ;;
      --verify-only)
        verify_only=true
        shift
        ;;
      *)
        error "不明なオプション: $1"
        show_usage
        exit 1
        ;;
    esac
  done

  echo "🐧 GitHub Actions Simulator - Linux インストーラー"
  echo "=================================================="
  echo

  # 検証のみの場合
  if [[ "$verify_only" == "true" ]]; then
    verify_installation
    exit $?
  fi

  # プラットフォーム検出
  local distro
  distro=$(detect_linux_distro)
  info "検出されたディストリビューション: $distro"
  echo

  # Docker のインストール
  if ! command -v docker >/dev/null 2>&1; then
    case "$distro" in
      ubuntu|debian)
        install_docker_ubuntu
        ;;
      fedora|centos|rhel|rocky|almalinux)
        install_docker_fedora
        ;;
      arch|manjaro)
        install_docker_arch
        ;;
      *)
        error "サポートされていないディストリビューション: $distro"
        echo "手動で Docker をインストールしてください:"
        echo "https://docs.docker.com/engine/install/"
        exit 1
        ;;
    esac

    configure_docker_service
  else
    success "Docker は既にインストールされています"
  fi

  # Docker のみの場合はここで終了
  if [[ "$docker_only" == "true" ]]; then
    verify_installation
    exit $?
  fi

  # その他のツールのインストール
  install_git
  install_uv

  # 最適化設定
  if [[ "$skip_optimization" != "true" ]]; then
    optimize_docker_config

    case "$distro" in
      fedora|centos|rhel|rocky|almalinux)
        configure_firewall_fedora
        configure_selinux
        ;;
    esac
  fi

  echo
  echo "🎉 インストールが完了しました！"
  echo

  # インストール検証
  verify_installation

  echo
  echo "📋 次のステップ:"
  echo "  1. 新しいシェルセッションを開始するか、'newgrp docker' を実行"
  echo "  2. GitHub Actions Simulator を実行:"
  echo "     ./scripts/run-actions.sh --check-deps"
  echo
  echo "📖 詳細なドキュメント: docs/PLATFORM_SUPPORT.md#linux"
}

# スクリプトが直接実行された場合のみ main を呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
