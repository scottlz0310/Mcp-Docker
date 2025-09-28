#!/usr/bin/env bash
# GitHub Actions Simulator - macOS インストールスクリプト
#
# このスクリプトは macOS 環境での GitHub Actions Simulator の
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

# macOS バージョン確認
check_macos_version() {
  local version
  version=$(sw_vers -productVersion)
  local major_version
  major_version=$(echo "$version" | cut -d'.' -f1)

  info "macOS バージョン: $version"

  if [[ $major_version -lt 12 ]]; then
    error "macOS 12.0 (Monterey) 以降が必要です。現在のバージョン: $version"
    exit 1
  fi

  success "macOS バージョンは要件を満たしています"
}

# アーキテクチャ検出
detect_architecture() {
  local arch
  arch=$(uname -m)

  case "$arch" in
    arm64)
      echo "apple_silicon"
      ;;
    x86_64)
      echo "intel"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

# Homebrew のインストール
install_homebrew() {
  info "Homebrew をインストール中..."

  if command -v brew >/dev/null 2>&1; then
    success "Homebrew は既にインストールされています"
    return 0
  fi

  # Homebrew のインストール
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # PATH の設定（Apple Silicon の場合）
  local arch
  arch=$(detect_architecture)
  if [[ "$arch" == "apple_silicon" ]]; then
    if [[ -f /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
  fi

  if command -v brew >/dev/null 2>&1; then
    success "Homebrew のインストールが完了しました"
  else
    error "Homebrew のインストールに失敗しました"
    echo "手動でインストールしてください:"
    echo "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
  fi
}

# Docker Desktop のインストール
install_docker_desktop() {
  info "Docker Desktop をインストール中..."

  # Docker Desktop が既にインストールされているかチェック
  if [[ -d "/Applications/Docker.app" ]]; then
    success "Docker Desktop は既にインストールされています"
    return 0
  fi

  # Homebrew 経由でインストール
  brew install --cask docker

  if [[ -d "/Applications/Docker.app" ]]; then
    success "Docker Desktop のインストールが完了しました"
  else
    error "Docker Desktop のインストールに失敗しました"
    echo "手動でインストールしてください:"
    echo "https://docs.docker.com/desktop/install/mac-install/"
    exit 1
  fi
}

# Docker Desktop の起動確認
start_docker_desktop() {
  info "Docker Desktop を起動中..."

  # Docker Desktop が起動しているかチェック
  if pgrep -f "Docker Desktop" >/dev/null 2>&1; then
    success "Docker Desktop は既に起動しています"
    return 0
  fi

  # Docker Desktop を起動
  open /Applications/Docker.app

  # Docker が利用可能になるまで待機
  local max_wait=60
  local wait_time=0

  info "Docker の起動を待機中..."
  while ! docker info >/dev/null 2>&1; do
    if [[ $wait_time -ge $max_wait ]]; then
      error "Docker の起動がタイムアウトしました"
      echo "手動で Docker Desktop を起動してください"
      exit 1
    fi

    sleep 2
    ((wait_time += 2))
    echo -n "."
  done

  echo
  success "Docker Desktop が正常に起動しました"
}

# uv のインストール
install_uv() {
  info "uv をインストール中..."

  if command -v uv >/dev/null 2>&1; then
    success "uv は既にインストールされています"
    return 0
  fi

  # Homebrew 経由でインストール
  brew install uv

  if command -v uv >/dev/null 2>&1; then
    success "uv のインストールが完了しました"
  else
    warning "uv のインストールに失敗しました。公式インストーラーを試行中..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    if command -v uv >/dev/null 2>&1; then
      success "uv のインストールが完了しました"
    else
      warning "uv のインストールに失敗しました。手動でインストールしてください"
    fi
  fi
}

# Git のインストール
install_git() {
  info "Git をインストール中..."

  if command -v git >/dev/null 2>&1; then
    success "Git は既にインストールされています"
    return 0
  fi

  # Xcode Command Line Tools のインストール
  if ! xcode-select -p >/dev/null 2>&1; then
    info "Xcode Command Line Tools をインストール中..."
    xcode-select --install

    # インストール完了まで待機
    info "Xcode Command Line Tools のインストールが完了するまで待機してください..."
    while ! xcode-select -p >/dev/null 2>&1; do
      sleep 5
    done
  fi

  if command -v git >/dev/null 2>&1; then
    success "Git のインストールが完了しました"
  else
    # Homebrew 経由でインストール
    brew install git

    if command -v git >/dev/null 2>&1; then
      success "Git のインストールが完了しました"
    else
      error "Git のインストールに失敗しました"
      exit 1
    fi
  fi
}

# Docker Desktop の最適化設定
optimize_docker_desktop() {
  info "Docker Desktop の最適化設定を提案中..."

  local arch
  arch=$(detect_architecture)

  echo
  echo "📋 Docker Desktop 最適化設定:"
  echo
  echo "  1. リソース設定 (Docker Desktop > Settings > Resources):"
  echo "     • CPU: 使用可能コア数の 50-75%"
  echo "     • Memory: 使用可能メモリの 50-75%"
  echo "     • Disk: 最低 20GB、推奨 50GB"
  echo
  echo "  2. 実験的機能 (Docker Desktop > Settings > Docker Engine):"
  echo "     • BuildKit を有効化"
  echo "     • 実験的機能を有効化"
  echo

  if [[ "$arch" == "apple_silicon" ]]; then
    echo "  3. Apple Silicon 固有設定:"
    echo "     • VirtioFS を有効化 (Settings > General)"
    echo "     • 新しい仮想化フレームワークを使用 (Settings > General)"
    echo "     • Intel イメージ用に Rosetta 2 を有効化 (必要に応じて)"
    echo
  fi

  echo "  4. ファイル共有の最適化:"
  echo "     • 不要なディレクトリを File Sharing から除外"
  echo "     • .dockerignore を適切に設定"
  echo

  warning "これらの設定は Docker Desktop の GUI から手動で行ってください"
}

# パフォーマンステスト
run_performance_test() {
  info "基本的なパフォーマンステストを実行中..."

  # Docker の基本動作確認
  local start_time
  start_time=$(date +%s)

  docker run --rm hello-world >/dev/null 2>&1

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  success "Docker 基本動作確認: ${duration}秒"

  if [[ $duration -gt 30 ]]; then
    warning "Docker の起動が遅い可能性があります。最適化設定を確認してください"
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

  # Docker Desktop の確認
  if [[ -d "/Applications/Docker.app" ]]; then
    success "Docker Desktop: インストール済み"

    if pgrep -f "Docker Desktop" >/dev/null 2>&1; then
      success "Docker Desktop: 起動中"
    else
      warning "Docker Desktop: 停止中"
    fi
  else
    error "Docker Desktop が見つかりません"
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

  # Homebrew の確認
  if command -v brew >/dev/null 2>&1; then
    local brew_version
    brew_version=$(brew --version | head -1 2>/dev/null || echo "取得失敗")
    success "Homebrew: $brew_version"
  else
    warning "Homebrew が見つかりません"
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
GitHub Actions Simulator - macOS インストールスクリプト

使用方法:
  $0 [オプション]

オプション:
  --help, -h          このヘルプを表示
  --docker-only       Docker Desktop のみをインストール
  --skip-optimization 最適化設定の提案をスキップ
  --verify-only       インストール検証のみを実行
  --performance-test  パフォーマンステストを実行

例:
  $0                     # 完全インストール
  $0 --docker-only       # Docker Desktop のみインストール
  $0 --verify-only       # 検証のみ実行
  $0 --performance-test  # パフォーマンステスト実行
EOF
}

# メイン処理
main() {
  local docker_only=false
  local skip_optimization=false
  local verify_only=false
  local performance_test=false

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
      --performance-test)
        performance_test=true
        shift
        ;;
      *)
        error "不明なオプション: $1"
        show_usage
        exit 1
        ;;
    esac
  done

  echo "🍎 GitHub Actions Simulator - macOS インストーラー"
  echo "================================================="
  echo

  # 検証のみの場合
  if [[ "$verify_only" == "true" ]]; then
    verify_installation
    exit $?
  fi

  # パフォーマンステストのみの場合
  if [[ "$performance_test" == "true" ]]; then
    run_performance_test
    exit $?
  fi

  # macOS バージョン確認
  check_macos_version

  # アーキテクチャ検出
  local arch
  arch=$(detect_architecture)
  info "検出されたアーキテクチャ: $arch"
  echo

  # Homebrew のインストール
  install_homebrew

  # Docker Desktop のインストール
  install_docker_desktop
  start_docker_desktop

  # Docker のみの場合はここで終了
  if [[ "$docker_only" == "true" ]]; then
    verify_installation
    exit $?
  fi

  # その他のツールのインストール
  install_git
  install_uv

  # 最適化設定の提案
  if [[ "$skip_optimization" != "true" ]]; then
    optimize_docker_desktop
  fi

  echo
  echo "🎉 インストールが完了しました！"
  echo

  # インストール検証
  verify_installation

  # パフォーマンステスト
  run_performance_test

  echo
  echo "📋 次のステップ:"
  echo "  1. Docker Desktop の設定を最適化（上記の提案を参照）"
  echo "  2. GitHub Actions Simulator を実行:"
  echo "     ./scripts/run-actions.sh --check-deps"
  echo
  echo "📖 詳細なドキュメント: docs/PLATFORM_SUPPORT.md#macos"
}

# スクリプトが直接実行された場合のみ main を呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
