#!/usr/bin/env bash
# GitHub Actions Simulator one-shot launcher.
#
# Usage:
#   ./scripts/run-actions.sh [WORKFLOW_FILE] [-- <additional CLI args>]
#
# The script ensures the simulator image is up-to-date, then executes the
# Click CLI inside the dedicated Docker container.

echo "DEBUG: Script started" >&2
echo "DEBUG: Args: $*" >&2

set -euo pipefail

# エラーハンドリング設定
readonly SCRIPT_NAME="$(basename "$0")"

# エラートラップの設定
trap 'handle_error $? $LINENO' ERR
trap 'cleanup_on_exit' EXIT

# 依存関係の最小バージョン要件
readonly MIN_DOCKER_VERSION="20.10.0"
readonly MIN_COMPOSE_VERSION="2.0.0"
readonly MIN_GIT_VERSION="2.20.0"

# ユーティリティ関数（早期定義）
info() {
  printf '👉 %s\n' "$*"
}

error() {
  printf '❌ %s\n' "$*" >&2
}

warning() {
  printf '⚠️  %s\n' "$*" >&2
}

success() {
  printf '✅ %s\n' "$*"
}

# エラーハンドリング関数
handle_error() {
  local exit_code=$1
  local line_number=$2
  local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

  # ログディレクトリの作成
  mkdir -p "$LOG_DIR" 2>/dev/null || true

  # エラー情報をログに記録
  {
    echo "=== エラー発生 ==="
    echo "時刻: $timestamp"
    echo "スクリプト: $SCRIPT_NAME"
    echo "行番号: $line_number"
    echo "終了コード: $exit_code"
    echo "コマンド: ${BASH_COMMAND:-不明}"
    echo "==================="
    echo
  } >> "$ERROR_LOG" 2>/dev/null || true

  # 診断情報の収集
  collect_diagnostic_info

  # エラーメッセージの表示
  show_error_guidance "$exit_code" "$line_number"
}

cleanup_on_exit() {
  local exit_code=$?
  if [[ $exit_code -eq 0 ]]; then
    # 成功時のクリーンアップ
    return 0
  fi
}

# 診断情報収集
collect_diagnostic_info() {
  local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

  # ログディレクトリの作成
  mkdir -p "$LOG_DIR" 2>/dev/null || true

  {
    echo "=== 診断情報 ($timestamp) ==="
    echo "OS: $(uname -a 2>/dev/null || echo '不明')"
    echo "シェル: $BASH_VERSION"
    echo "作業ディレクトリ: $(pwd)"
    echo "ユーザー: $(whoami 2>/dev/null || echo '不明')"
    echo

    echo "--- 環境変数 ---"
    env | grep -E '^(DOCKER|COMPOSE|ACTIONS_SIMULATOR|PATH)' | sort || true
    echo

    echo "--- Docker 情報 ---"
    if command -v docker >/dev/null 2>&1; then
      echo "Docker バージョン: $(docker --version 2>/dev/null || echo 'エラー')"
      echo "Docker 状態: $(docker info --format '{{.ServerVersion}}' 2>/dev/null || echo 'サービス停止中')"
      echo "Docker Compose: $(docker compose version 2>/dev/null || echo 'エラー')"
    else
      echo "Docker: インストールされていません"
    fi
    echo

    echo "--- Git 情報 ---"
    if command -v git >/dev/null 2>&1; then
      echo "Git バージョン: $(git --version 2>/dev/null || echo 'エラー')"
      echo "リポジトリ状態: $(git status --porcelain 2>/dev/null | wc -l || echo '不明') 個の変更"
    else
      echo "Git: インストールされていません"
    fi
    echo

    echo "--- ディスク容量 ---"
    df -h . 2>/dev/null || echo "ディスク情報取得エラー"
    echo

    echo "--- プロセス情報 ---"
    ps aux | grep -E '(docker|compose)' | grep -v grep || echo "Docker関連プロセスなし"
    echo

    echo "=== 診断情報終了 ==="
    echo
  } >> "$DIAGNOSTIC_LOG" 2>/dev/null || true
}

# エラー別ガイダンス表示
show_error_guidance() {
  local exit_code=$1
  local line_number=$2

  echo
  error "🚨 実行中にエラーが発生しました"
  echo

  case $exit_code in
    1)
      show_general_error_guidance
      ;;
    2)
      show_dependency_error_guidance
      ;;
    126)
      show_permission_error_guidance
      ;;
    127)
      show_command_not_found_guidance
      ;;
    130)
      show_interrupt_guidance
      ;;
    *)
      show_unknown_error_guidance "$exit_code"
      ;;
  esac

  show_recovery_suggestions
  show_support_information
}

# 一般的なエラーガイダンス
show_general_error_guidance() {
  echo "📋 一般的なエラーが発生しました"
  echo
  echo "🔍 考えられる原因:"
  echo "  • 設定ファイルの問題"
  echo "  • ネットワーク接続の問題"
  echo "  • ディスク容量不足"
  echo "  • 権限の問題"
  echo
}

# 依存関係エラーガイダンス
show_dependency_error_guidance() {
  echo "📋 依存関係エラーが発生しました"
  echo
  echo "🔍 考えられる原因:"
  echo "  • Docker がインストールされていない"
  echo "  • Docker サービスが起動していない"
  echo "  • Docker Compose が古いバージョン"
  echo "  • Git がインストールされていない"
  echo
}

# 権限エラーガイダンス
show_permission_error_guidance() {
  echo "📋 権限エラーが発生しました"
  echo
  echo "🔍 考えられる原因:"
  echo "  • Docker グループに所属していない"
  echo "  • ファイル/ディレクトリの権限不足"
  echo "  • sudo 権限が必要"
  echo
  echo "🛠️  解決方法:"
  echo "  # Docker グループに追加"
  echo "  sudo usermod -aG docker \$USER"
  echo "  newgrp docker"
  echo
  echo "  # ファイル権限の修正"
  echo "  sudo chown -R \$(id -u):\$(id -g) ."
  echo
}

# コマンド未発見エラーガイダンス
show_command_not_found_guidance() {
  echo "📋 コマンドが見つかりません"
  echo
  echo "🔍 考えられる原因:"
  echo "  • 必要なツールがインストールされていない"
  echo "  • PATH 環境変数の設定問題"
  echo "  • スクリプトの実行権限がない"
  echo
}

# 中断エラーガイダンス
show_interrupt_guidance() {
  echo "📋 実行が中断されました (Ctrl+C)"
  echo
  echo "ℹ️  これは正常な中断です"
  echo "   再実行する場合は、同じコマンドを実行してください"
  echo
}

# 不明なエラーガイダンス
show_unknown_error_guidance() {
  local exit_code=$1
  echo "📋 不明なエラーが発生しました (終了コード: $exit_code)"
  echo
  echo "🔍 詳細な診断情報を確認してください:"
  echo "  cat $DIAGNOSTIC_LOG"
  echo
}

# 復旧提案機能
show_recovery_suggestions() {
  echo "🔧 自動復旧提案:"
  echo

  # Docker サービス確認と提案
  if ! docker info >/dev/null 2>&1; then
    echo "  1. Docker サービスを開始:"
    case "$(detect_platform)" in
      ubuntu|fedora|linux)
        echo "     sudo systemctl start docker"
        echo "     sudo systemctl enable docker"
        ;;
      macos)
        echo "     Docker Desktop を起動してください"
        ;;
      windows)
        echo "     Docker Desktop を起動してください"
        ;;
    esac
    echo
  fi

  # ディスク容量確認と提案
  local available_space
  available_space=$(df . | awk 'NR==2 {print $4}' 2>/dev/null || echo "0")
  if [[ "$available_space" -lt 1048576 ]]; then  # 1GB未満
    echo "  2. ディスク容量を確保:"
    echo "     docker system prune -f"
    echo "     docker volume prune -f"
    echo
  fi

  # 権限確認と提案
  if [[ ! -w "." ]]; then
    echo "  3. 権限を修正:"
    echo "     sudo chown -R \$(id -u):\$(id -g) ."
    echo
  fi

  # ネットワーク確認と提案
  if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "  4. ネットワーク接続を確認:"
    echo "     ping google.com"
    echo "     # プロキシ設定が必要な場合があります"
    echo
  fi
}

# サポート情報表示
show_support_information() {
  echo "📞 サポート情報:"
  echo
  echo "  🔍 診断ログ: $DIAGNOSTIC_LOG"
  echo "  📝 エラーログ: $ERROR_LOG"
  echo
  echo "  📚 ドキュメント:"
  echo "     • README.md - 基本的な使用方法"
  echo "     • docs/TROUBLESHOOTING.md - トラブルシューティング"
  echo "     • docs/actions/FAQ.md - よくある質問"
  echo
  echo "  🐛 問題報告:"
  echo "     • GitHub Issues で報告してください"
  echo "     • 上記のログファイルを添付してください"
  echo
  echo "  💡 クイック診断コマンド:"
  echo "     make diagnostic  # 診断情報の表示"
  echo "     make clean       # 環境のリセット"
  echo
}

prepare_output_dir() {
  local dir="${PROJECT_ROOT}/output"
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir" 2>/dev/null || {
      error "output ディレクトリを作成できません: $dir"
      echo
      echo "🔧 解決方法:"
      echo "  sudo mkdir -p $dir"
      echo "  sudo chown -R \$(id -u):\$(id -g) $dir"
      exit 2
    }
  fi
  if [[ ! -w "$dir" ]]; then
    error "output ディレクトリに書き込みできません: $dir"
    echo
    echo "🔧 解決方法:"
    echo "  sudo chown -R \$(id -u):\$(id -g) $dir"
    echo "  # または"
    echo "  sudo chmod -R 755 $dir"
    exit 126
  fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# PROJECT_ROOTの決定ロジック
if [[ -n "${PROJECT_ROOT_FROM_ENV:-}" ]]; then
  # uv tool install時: ユーザーのカレントディレクトリ
  PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
  PACKAGE_ROOT="${SCRIPT_DIR}/.."
else
  # 開発時: スクリプトの親ディレクトリ
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  PACKAGE_ROOT="${PROJECT_ROOT}"
fi

# ログディレクトリの設定（常にユーザーのプロジェクトルート）
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly ERROR_LOG="${LOG_DIR}/error.log"
readonly DIAGNOSTIC_LOG="${LOG_DIR}/diagnostic.log"

# 作業ディレクトリの設定
if [[ -z "${PROJECT_ROOT_FROM_ENV:-}" ]]; then
  # 開発時のみプロジェクトルートに移動
  cd "${PROJECT_ROOT}" || {
    echo "❌ プロジェクトディレクトリに移動できません: ${PROJECT_ROOT}" >&2
    exit 1
  }
fi

# ログディレクトリの初期化
initialize_logging() {
  mkdir -p "$LOG_DIR" 2>/dev/null || true

  # ログファイルの初期化
  if [[ -w "$LOG_DIR" ]]; then
    {
      echo "=== GitHub Actions Simulator ログ ==="
      echo "開始時刻: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
      echo "スクリプト: $SCRIPT_NAME"
      echo "プロジェクト: $PROJECT_ROOT"
      echo "======================================"
      echo
    } > "$DIAGNOSTIC_LOG" 2>/dev/null || true
  fi
}

# ログ初期化の実行
initialize_logging

DEFAULT_WORKFLOW=".github/workflows/ci.yml"
declare -a WORKFLOW_CHOICES=()

# 早期ヘルプチェック（依存関係チェック前）
for arg in "$@"; do
  if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
    cat <<'EOF'
GitHub Actions Simulator - ワンショット実行スクリプト

使用方法:
  ./scripts/run-actions.sh [オプション] [ワークフローファイル] [-- <追加のCLI引数>]

オプション:
  --help, -h                    このヘルプを表示
  --check-deps                  依存関係のみをチェック（実行はしない）
  --check-deps-extended         拡張依存関係チェック（プラットフォーム最適化情報を含む）
  --non-interactive             非対話モード（CI/CD環境用）
  --timeout=<秒数>              act のタイムアウト時間を設定
  --act-timeout=<秒数>          同上

環境変数:
  NON_INTERACTIVE=1             非対話モードを有効化
  INDEX=<番号>                  ワークフロー選択を自動化
  ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=<秒数>  タイムアウト設定

例:
  ./scripts/run-actions.sh                              # 対話的にワークフローを選択
  ./scripts/run-actions.sh .github/workflows/ci.yml    # 特定のワークフローを実行
  ./scripts/run-actions.sh --check-deps                # 依存関係のみをチェック
  ./scripts/run-actions.sh --check-deps-extended      # 拡張依存関係チェック
  NON_INTERACTIVE=1 ./scripts/run-actions.sh            # 非対話モードで実行
  INDEX=1 ./scripts/run-actions.sh                     # 最初のワークフローを自動選択

詳細情報:
  README.md および docs/actions/ を参照してください
EOF
    exit 0
  fi
done

# プラットフォーム検出
detect_platform() {
  local os_name
  case "$(uname -s)" in
    Linux*)
      if command -v lsb_release >/dev/null 2>&1; then
        local distro
        distro=$(lsb_release -si 2>/dev/null | tr '[:upper:]' '[:lower:]')
        case "$distro" in
          ubuntu|debian) echo "ubuntu" ;;
          fedora|centos|rhel|rocky|almalinux) echo "fedora" ;;
          arch|manjaro) echo "arch" ;;
          opensuse*|suse*) echo "opensuse" ;;
          *) echo "linux" ;;
        esac
      elif [[ -f /etc/os-release ]]; then
        local distro
        distro=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"' | tr '[:upper:]' '[:lower:]')
        case "$distro" in
          ubuntu|debian) echo "ubuntu" ;;
          fedora|centos|rhel|rocky|almalinux) echo "fedora" ;;
          arch|manjaro) echo "arch" ;;
          opensuse*|suse*) echo "opensuse" ;;
          *) echo "linux" ;;
        esac
      else
        echo "linux"
      fi
      ;;
    Darwin*) echo "macos" ;;
    CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

# 詳細なプラットフォーム情報を取得
get_platform_details() {
  local platform=$(detect_platform)
  local details=""

  case "$(uname -s)" in
    Linux*)
      if command -v lsb_release >/dev/null 2>&1; then
        local distro_name=$(lsb_release -sd 2>/dev/null | tr -d '"')
        local version=$(lsb_release -sr 2>/dev/null)
        details="$distro_name $version"
      elif [[ -f /etc/os-release ]]; then
        local name=$(grep '^PRETTY_NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        details="$name"
      else
        details="Linux $(uname -r)"
      fi
      ;;
    Darwin*)
      local version=$(sw_vers -productVersion 2>/dev/null || echo "不明")
      local build=$(sw_vers -buildVersion 2>/dev/null || echo "不明")
      details="macOS $version (Build: $build)"
      ;;
    CYGWIN*|MINGW*|MSYS*)
      details="Windows ($(uname -s))"
      ;;
    *)
      details="$(uname -s) $(uname -r)"
      ;;
  esac

  echo "$details"
}

# アーキテクチャ情報を取得
get_architecture_info() {
  local arch=$(uname -m)
  local details=""

  case "$arch" in
    x86_64|amd64)
      details="x86_64 (Intel/AMD 64-bit)"
      ;;
    aarch64|arm64)
      details="ARM64 (Apple Silicon/ARM 64-bit)"
      ;;
    armv7l)
      details="ARM v7 (32-bit)"
      ;;
    i386|i686)
      details="x86 (32-bit)"
      ;;
    *)
      details="$arch"
      ;;
  esac

  echo "$details"
}

# バージョン比較関数
version_compare() {
  local version1="$1"
  local version2="$2"

  # バージョン文字列から数字とドットのみを抽出
  version1=$(echo "$version1" | grep -oE '[0-9]+(\.[0-9]+)*' | head -1)
  version2=$(echo "$version2" | grep -oE '[0-9]+(\.[0-9]+)*' | head -1)

  if [[ "$version1" == "$version2" ]]; then
    return 0
  fi

  local IFS=.
  local i ver1=($version1) ver2=($version2)

  # 配列の長さを揃える
  for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
    ver1[i]=0
  done
  for ((i=${#ver2[@]}; i<${#ver1[@]}; i++)); do
    ver2[i]=0
  done

  # バージョン比較
  for ((i=0; i<${#ver1[@]}; i++)); do
    if ((10#${ver1[i]} > 10#${ver2[i]})); then
      return 1  # version1 > version2
    fi
    if ((10#${ver1[i]} < 10#${ver2[i]})); then
      return 2  # version1 < version2
    fi
  done

  return 0  # version1 == version2
}

# Docker インストールガイダンス
show_docker_installation_guide() {
  local platform="$1"

  error "Docker が見つからないか、バージョンが古すぎます（最小要件: ${MIN_DOCKER_VERSION}）"
  echo
  echo "📦 Docker インストール手順:"
  echo

  case "$platform" in
    ubuntu)
      cat <<'EOF'
Ubuntu/Debian の場合:
  # 公式リポジトリからインストール
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh

  # ユーザーを docker グループに追加
  sudo usermod -aG docker $USER

  # Docker Compose プラグインをインストール
  sudo apt-get update
  sudo apt-get install docker-compose-plugin

  # 再ログインまたは以下を実行
  newgrp docker

EOF
      ;;
    fedora)
      cat <<'EOF'
Fedora/RHEL/CentOS の場合:
  # Docker CE をインストール
  sudo dnf remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-selinux docker-engine-selinux docker-engine
  sudo dnf -y install dnf-plugins-core
  sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
  sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin

  # Docker サービスを開始
  sudo systemctl start docker
  sudo systemctl enable docker

  # ユーザーを docker グループに追加
  sudo usermod -aG docker $USER

EOF
      ;;
    macos)
      cat <<'EOF'
macOS の場合:
  # Homebrew を使用（推奨）
  brew install --cask docker

  # または Docker Desktop を直接ダウンロード
  # https://docs.docker.com/desktop/install/mac-install/

  # Docker Desktop を起動してください

EOF
      ;;
    windows)
      cat <<'EOF'
Windows の場合:
  # WSL2 を有効にしてから Docker Desktop をインストール
  # 1. WSL2 を有効化
  wsl --install

  # 2. Docker Desktop for Windows をダウンロード・インストール
  # https://docs.docker.com/desktop/install/windows-install/

  # 3. Docker Desktop を起動し、WSL2 統合を有効化

EOF
      ;;
    *)
      cat <<'EOF'
その他のプラットフォーム:
  公式ドキュメントを参照してください:
  https://docs.docker.com/engine/install/

EOF
      ;;
  esac

  echo "インストール後、以下のコマンドで確認してください:"
  echo "  docker --version"
  echo "  docker compose version"
  echo
}

# uv インストールガイダンス
show_uv_installation_guide() {
  local platform="$1"

  warning "uv が見つかりません（オプション）"
  echo
  echo "📦 uv インストール手順（推奨）:"
  echo

  case "$platform" in
    ubuntu|fedora|linux)
      cat <<'EOF'
Linux の場合:
  # 公式インストーラー（推奨）
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # または pip を使用
  pip install uv

  # パスを更新
  source ~/.bashrc

EOF
      ;;
    macos)
      cat <<'EOF'
macOS の場合:
  # Homebrew を使用（推奨）
  brew install uv

  # または公式インストーラー
  curl -LsSf https://astral.sh/uv/install.sh | sh

EOF
      ;;
    windows)
      cat <<'EOF'
Windows の場合:
  # PowerShell で実行
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

  # または pip を使用
  pip install uv

EOF
      ;;
    *)
      cat <<'EOF'
その他のプラットフォーム:
  公式ドキュメントを参照してください:
  https://docs.astral.sh/uv/getting-started/installation/

EOF
      ;;
  esac

  echo "注意: uv がない場合は、コンテナ内の uv を使用します"
  echo
}

# Git インストールガイダンス
show_git_installation_guide() {
  local platform="$1"

  error "Git が見つからないか、バージョンが古すぎます（最小要件: ${MIN_GIT_VERSION}）"
  echo
  echo "📦 Git インストール手順:"
  echo

  case "$platform" in
    ubuntu)
      cat <<'EOF'
Ubuntu/Debian の場合:
  sudo apt-get update
  sudo apt-get install git

EOF
      ;;
    fedora)
      cat <<'EOF'
Fedora/RHEL/CentOS の場合:
  sudo dnf install git

EOF
      ;;
    macos)
      cat <<'EOF'
macOS の場合:
  # Homebrew を使用（推奨）
  brew install git

  # または Xcode Command Line Tools
  xcode-select --install

EOF
      ;;
    windows)
      cat <<'EOF'
Windows の場合:
  # Git for Windows をダウンロード・インストール
  # https://git-scm.com/download/win

  # または Chocolatey を使用
  choco install git

EOF
      ;;
    *)
      cat <<'EOF'
その他のプラットフォーム:
  公式ドキュメントを参照してください:
  https://git-scm.com/downloads

EOF
      ;;
  esac

  echo "インストール後、以下のコマンドで確認してください:"
  echo "  git --version"
  echo
}

# Docker バージョンチェック
check_docker_version() {
  local docker_version
  if ! docker_version=$(docker --version 2>/dev/null); then
    return 1
  fi

  local version_num
  version_num=$(echo "$docker_version" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

  if [[ -z "$version_num" ]]; then
    return 1
  fi

  version_compare "$version_num" "$MIN_DOCKER_VERSION"
  local result=$?

  if [[ $result -eq 2 ]]; then
    return 1  # バージョンが古い
  fi

  return 0  # バージョンOK
}

# Docker Compose バージョンチェック
check_compose_version() {
  local compose_version
  if ! compose_version=$(docker compose version 2>/dev/null); then
    return 1
  fi

  local version_num
  version_num=$(echo "$compose_version" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

  if [[ -z "$version_num" ]]; then
    return 1
  fi

  version_compare "$version_num" "$MIN_COMPOSE_VERSION"
  local result=$?

  if [[ $result -eq 2 ]]; then
    return 1  # バージョンが古い
  fi

  return 0  # バージョンOK
}

# Git バージョンチェック
check_git_version() {
  local git_version
  if ! git_version=$(git --version 2>/dev/null); then
    return 1
  fi

  local version_num
  version_num=$(echo "$git_version" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

  if [[ -z "$version_num" ]]; then
    return 1
  fi

  version_compare "$version_num" "$MIN_GIT_VERSION"
  local result=$?

  if [[ $result -eq 2 ]]; then
    return 1  # バージョンが古い
  fi

  return 0  # バージョンOK
}

# 包括的な依存関係チェック
check_dependencies() {
  local platform
  platform=$(detect_platform)
  local has_errors=false
  local missing_deps=()

  info "🔍 依存関係をチェック中..."
  info "プラットフォーム: $platform"
  info "詳細: $(get_platform_details)"
  info "アーキテクチャ: $(get_architecture_info)"
  echo

  # Docker チェック
  if check_docker_version; then
    local docker_version
    docker_version=$(docker --version 2>/dev/null)
    success "Docker: $docker_version"

    # Docker サービス状態チェック
    if ! docker info >/dev/null 2>&1; then
      warning "Docker サービスが起動していません"
      echo "🔧 Docker サービスを開始してください:"
      case "$platform" in
        ubuntu|fedora|linux)
          echo "  sudo systemctl start docker"
          echo "  sudo systemctl enable docker"
          ;;
        macos|windows)
          echo "  Docker Desktop を起動してください"
          ;;
      esac
      echo
      has_errors=true
    fi
  else
    has_errors=true
    missing_deps+=("Docker")
    show_docker_installation_guide "$platform"
  fi

  # Docker Compose チェック
  if check_compose_version; then
    local compose_version
    compose_version=$(docker compose version 2>/dev/null)
    success "Docker Compose: $compose_version"
  else
    has_errors=true
    missing_deps+=("Docker Compose")
    if command -v docker >/dev/null 2>&1; then
      error "Docker Compose プラグインが見つからないか、バージョンが古すぎます"
      echo
      echo "🔧 Docker Compose プラグインをインストールしてください:"
      case "$platform" in
        ubuntu)
          echo "  sudo apt-get update"
          echo "  sudo apt-get install docker-compose-plugin"
          ;;
        fedora)
          echo "  sudo dnf install docker-compose-plugin"
          ;;
        macos)
          echo "  Docker Desktop に含まれています（Docker Desktop を再インストールしてください）"
          ;;
        windows)
          echo "  Docker Desktop に含まれています（Docker Desktop を再インストールしてください）"
          ;;
      esac
      echo
    fi
  fi

  # Git チェック
  if check_git_version; then
    local git_version
    git_version=$(git --version 2>/dev/null)
    success "Git: $git_version"

    # Git リポジトリ状態チェック
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
      warning "現在のディレクトリは Git リポジトリではありません"
      echo "ℹ️  GitHub Actions Simulator は Git リポジトリ内で実行することを推奨します"
      echo
    fi
  else
    has_errors=true
    missing_deps+=("Git")
    show_git_installation_guide "$platform"
  fi

  # uv チェック（オプション）
  if command -v uv >/dev/null 2>&1; then
    local uv_version
    uv_version=$(uv --version 2>/dev/null)
    success "uv: $uv_version"
  else
    warning "uv が見つかりません（オプション）"
    show_uv_installation_guide "$platform"
  fi

  # ディスク容量チェック
  check_disk_space

  # ネットワーク接続チェック
  check_network_connectivity

  if [[ "$has_errors" == "true" ]]; then
    echo
    error "必要な依存関係が不足しています: ${missing_deps[*]}"
    echo
    echo "🔧 自動復旧を試行しますか？ (y/N)"
    if [[ -t 0 ]]; then
      read -r -n 1 response
      echo
      if [[ "$response" =~ ^[Yy]$ ]]; then
        attempt_auto_recovery "$platform" "${missing_deps[@]}"
      fi
    fi

    echo "📚 詳細なトラブルシューティング情報:"
    echo "  docs/TROUBLESHOOTING.md を参照してください"
    echo
    exit 2
  fi

  echo
  success "すべての依存関係が満たされています！"
  echo
}

# ディスク容量チェック
check_disk_space() {
  local available_space
  available_space=$(df . | awk 'NR==2 {print $4}' 2>/dev/null || echo "0")
  local required_space=2097152  # 2GB in KB

  if [[ "$available_space" -lt "$required_space" ]]; then
    warning "ディスク容量が不足している可能性があります"
    echo "利用可能: $(( available_space / 1024 / 1024 ))GB, 推奨: 2GB以上"
    echo
    echo "🔧 容量を確保するには:"
    echo "  docker system prune -f    # 未使用のDockerリソースを削除"
    echo "  docker volume prune -f    # 未使用のボリュームを削除"
    echo
  fi
}

# ネットワーク接続チェック
check_network_connectivity() {
  if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    warning "ネットワーク接続に問題がある可能性があります"
    echo
    echo "🔧 ネットワーク接続を確認してください:"
    echo "  ping google.com"
    echo "  # プロキシ設定が必要な場合は環境変数を設定してください"
    echo "  # export HTTP_PROXY=http://proxy.example.com:8080"
    echo "  # export HTTPS_PROXY=http://proxy.example.com:8080"
    echo
  fi
}

# 自動復旧試行
attempt_auto_recovery() {
  local platform="$1"
  shift
  local missing_deps=("$@")

  info "🔧 自動復旧を試行中..."
  echo

  for dep in "${missing_deps[@]}"; do
    case "$dep" in
      "Docker")
        attempt_docker_recovery "$platform"
        ;;
      "Docker Compose")
        attempt_compose_recovery "$platform"
        ;;
      "Git")
        attempt_git_recovery "$platform"
        ;;
    esac
  done

  echo
  info "自動復旧が完了しました。依存関係を再チェックします..."
  echo
}

# Docker 自動復旧
attempt_docker_recovery() {
  local platform="$1"

  case "$platform" in
    ubuntu)
      if command -v curl >/dev/null 2>&1; then
        info "Docker の自動インストールを試行中..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        sudo usermod -aG docker "$USER"
        rm -f /tmp/get-docker.sh
      fi
      ;;
    macos)
      if command -v brew >/dev/null 2>&1; then
        info "Docker Desktop の自動インストールを試行中..."
        brew install --cask docker
      fi
      ;;
  esac
}

# Docker Compose 自動復旧
attempt_compose_recovery() {
  local platform="$1"

  case "$platform" in
    ubuntu)
      sudo apt-get update
      sudo apt-get install -y docker-compose-plugin
      ;;
    fedora)
      sudo dnf install -y docker-compose-plugin
      ;;
  esac
}

# Git 自動復旧
attempt_git_recovery() {
  local platform="$1"

  case "$platform" in
    ubuntu)
      sudo apt-get update
      sudo apt-get install -y git
      ;;
    fedora)
      sudo dnf install -y git
      ;;
    macos)
      if command -v brew >/dev/null 2>&1; then
        brew install git
      fi
      ;;
  esac
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    error "必要なコマンドが見つかりません: $cmd"
    echo
    echo "🔧 インストール方法:"
    case "$cmd" in
      docker)
        show_docker_installation_guide "$(detect_platform)"
        ;;
      git)
        show_git_installation_guide "$(detect_platform)"
        ;;
      uv)
        show_uv_installation_guide "$(detect_platform)"
        ;;
      *)
        echo "  パッケージマネージャーを使用してインストールしてください"
        echo "  例: sudo apt-get install $cmd (Ubuntu)"
        echo "      brew install $cmd (macOS)"
        ;;
    esac
    exit 127
  fi
}

normalize_workflow_path() {
  local path="$1"
  path="${path#./}"
  printf '%s' "$path"
}

discover_workflows() {
  WORKFLOW_CHOICES=()
  if [[ -d ".github/workflows" ]]; then
    while IFS= read -r wf; do
      wf="${wf#./}"
      WORKFLOW_CHOICES+=("$wf")
    done < <(find .github/workflows -type f \( -name '*.yml' -o -name '*.yaml' \) -print 2>/dev/null | sort)
  fi
}

workflow_exists() {
  local target="$1"
  for wf in "${WORKFLOW_CHOICES[@]}"; do
    if [[ "$wf" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}

print_workflow_menu() {
  local default="$1"
  info "📋 使用可能なワークフロー:"
  local idx=1
  for wf in "${WORKFLOW_CHOICES[@]}"; do
    local marker=""
    if [[ "$wf" == "$default" ]]; then
      marker=" (default)"
    fi
    printf '  %2d) %s%s
' "$idx" "$wf" "$marker"
    ((idx++))
  done
}

choose_workflow() {
  if [[ ${#WORKFLOW_CHOICES[@]} -eq 0 ]]; then
    discover_workflows
  fi
  if [[ ${#WORKFLOW_CHOICES[@]} -eq 0 ]]; then
    error "ワークフローファイルが見つかりません (.github/workflows)"
    exit 1
  fi

  local default_path
  default_path=$(normalize_workflow_path "$DEFAULT_WORKFLOW")
  local default_index=1
  local found_default="false"
  if [[ -n "$default_path" ]]; then
    for i in "${!WORKFLOW_CHOICES[@]}"; do
      if [[ "${WORKFLOW_CHOICES[$i]}" == "$default_path" ]]; then
        default_index=$((i + 1))
        found_default="true"
        break
      fi
    done
  fi

  if [[ "$found_default" != "true" ]]; then
    default_index=1
    default_path="${WORKFLOW_CHOICES[0]}"
  fi

  # 非対話モードの場合はデフォルトを自動選択
  if is_non_interactive; then
    info "🤖 非対話モード: デフォルトワークフローを自動選択" >&2
    info "🚀 実行ワークフロー: ${default_path}" >&2
    printf '%s' "$default_path"
    return
  fi

  print_workflow_menu "$default_path" >&2

  local choice="${INDEX:-}"
  if [[ -z "$choice" ]]; then
    if [[ -t 0 ]]; then
      printf '🎯 実行するワークフローを選択してください (Enter=%d): ' "$default_index" >&2
      read -r choice || choice=""
    else
      choice=""
    fi
  else
    info "INDEX=${choice} を使用します" >&2
  fi

  if [[ -z "$choice" ]]; then
    choice=$default_index
  fi

  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    error "無効な選択です: $choice"
    exit 1
  fi

  local choice_index=$((choice))
  if (( choice_index < 1 || choice_index > ${#WORKFLOW_CHOICES[@]} )); then
    error "無効な番号です: $choice"
    exit 1
  fi

  local selected="${WORKFLOW_CHOICES[$((choice_index - 1))]}"
  info "🚀 実行ワークフロー: ${selected}" >&2
  printf '%s' "$selected"
}

# 依存関係チェックは引数解析後に実行

# Docker Compose コマンドの設定
COMPOSE_CMD=(docker compose)

# 進捗表示機能
show_progress() {
  local step="$1"
  local total="$2"
  local message="$3"
  local percentage=$((step * 100 / total))

  # パイプ経由での実行時に\rが問題を起こすため、通常のechoを使用
  echo "🔄 [$step/$total] ($percentage%) $message"
}

# 非対話モードの検出
is_non_interactive() {
  [[ ! -t 0 ]] || [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]] || [[ -n "${NON_INTERACTIVE:-}" ]]
}

# Docker イメージの準備（進捗表示付き）
prepare_docker_image() {
  local total_steps=3
  local current_step=0

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "Docker イメージの確認中..."

  # docker-compose.ymlの絶対パスを取得
  local compose_file="${PACKAGE_ROOT}/docker-compose.yml"
  if [[ ! -f "$compose_file" ]]; then
    compose_file="${PROJECT_ROOT}/docker-compose.yml"
  fi

  # 既存イメージの確認
  local has_existing_image=false
  if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "actions-simulator"; then
    has_existing_image=true
  fi

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "Docker イメージの更新を試行中..."

  # イメージのプル試行（compose fileを明示的に指定）
  local pull_success=false
  if "${COMPOSE_CMD[@]}" -f "$compose_file" --profile tools pull actions-simulator >/dev/null 2>&1; then
    pull_success=true
  fi

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "Docker イメージの準備完了"
  echo

  if [[ "$pull_success" == "true" ]]; then
    success "✅ Docker イメージを最新版に更新しました"
  elif [[ "$has_existing_image" == "true" ]]; then
    warning "⚠️  Docker イメージの更新に失敗しましたが、既存のイメージを使用します"
  else
    warning "⚠️  actions-simulator イメージが見つかりません"
    echo
    info "🔨 Docker イメージを自動ビルド中..."
    echo "   これには数分かかる場合があります。初回のみ実行されます。"
    echo

    # docker-compose.ymlが存在する場合はビルドを試行
    if [[ -f "$compose_file" ]]; then
      info "📦 docker-compose.yml を使用してビルド中..."
      echo "   進捗を表示します:"
      echo
      if "${COMPOSE_CMD[@]}" -f "$compose_file" build actions-simulator; then
        echo
        success "✅ Docker イメージのビルドが完了しました"
      else
        echo
        error "❌ Docker イメージのビルドに失敗しました"
        echo
        echo "🔧 手動セットアップ手順:"
        echo "  1. プロジェクトをクローン:"
        echo "     git clone https://github.com/scottlz0310/mcp-docker.git"
        echo "     cd mcp-docker"
        echo
        echo "  2. Docker イメージをビルド:"
        echo "     docker compose build actions-simulator"
        echo
        echo "  3. 再実行:"
        echo "     mcp-docker actions .github/workflows/basic-test.yml"
        echo
        exit 1
      fi
    else
      error "❌ docker-compose.yml が見つかりません"
      echo
      echo "💡 uv tool install での使用方法:"
      echo
      echo "  uv tool install は依存関係チェックなどの軽量操作に適しています:"
      echo "    mcp-docker actions --check-deps"
      echo "    mcp-docker --version"
      echo
      echo "  実際のワークフロー実行には、プロジェクトのクローンが必要です:"
      echo "    git clone https://github.com/scottlz0310/mcp-docker.git"
      echo "    cd mcp-docker"
      echo "    docker compose build actions-simulator"
      echo "    ./scripts/run-actions.sh .github/workflows/basic-test.yml"
      echo
      exit 1
    fi
  fi
  echo
}

# Docker イメージ準備は引数解析後に実行

WORKFLOW="${WORKFLOW:-}"
workflow_from_argument="false"
workflow_selected_interactively="false"
REST_ARGS=()
ACT_TIMEOUT="${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS:-}"

pass_remaining="false"
check_deps_only="false"
check_deps_extended="false"

while [[ $# -gt 0 ]]; do
  arg="$1"
  shift

  if [[ "$pass_remaining" == "true" ]]; then
    REST_ARGS+=("$arg")
    continue
  fi

  case "$arg" in
    --)
      pass_remaining="true"
      ;;
    --check-deps|--check-dependencies)
      check_deps_only="true"
      ;;
    --check-deps-extended)
      check_deps_extended="true"
      ;;
    --non-interactive)
      export NON_INTERACTIVE=1
      ;;
    --help|-h)
      # Already handled above
      ;;
    --timeout|--act-timeout)
      if [[ $# -eq 0 ]]; then
        error "--timeout には秒数を指定してください"
        exit 1
      fi
      ACT_TIMEOUT="$1"
      shift
      ;;
    --timeout=*|--act-timeout=*)
      ACT_TIMEOUT="${arg#*=}"
      ;;
    -* )
      REST_ARGS+=("$arg")
      ;;
    *)
      if [[ -z "$WORKFLOW" ]]; then
        WORKFLOW="$arg"
      else
        REST_ARGS+=("$arg")
      fi
      ;;
  esac
done

# プラットフォーム固有の最適化提案
show_platform_optimization_tips() {
  local platform=$(detect_platform)
  local arch=$(uname -m)

  echo
  info "💡 プラットフォーム固有の最適化提案:"
  echo

  case "$platform" in
    ubuntu|fedora|linux)
      echo "  📋 Linux 最適化:"
      echo "    • Docker のメモリ制限設定: /etc/docker/daemon.json"
      echo "    • ユーザーを docker グループに追加: sudo usermod -aG docker \$USER"
      echo "    • システムリソース監視: htop, docker stats"
      echo "    • 詳細ガイド: docs/PLATFORM_SUPPORT.md#linux"
      ;;
    macos)
      echo "  🍎 macOS 最適化:"
      echo "    • Docker Desktop リソース設定を調整"
      echo "    • VirtioFS を有効化（Apple Silicon）"
      if [[ "$arch" == "arm64" ]]; then
        echo "    • Apple Silicon 検出: マルチアーキテクチャ対応を確認"
        echo "    • Rosetta 2 設定（Intel イメージ使用時）"
      fi
      echo "    • ファイル共有の最適化: .dockerignore を適切に設定"
      echo "    • 詳細ガイド: docs/PLATFORM_SUPPORT.md#macos"
      ;;
    windows)
      echo "  🪟 Windows (WSL2) 最適化:"
      echo "    • WSL2 メモリ制限設定: %USERPROFILE%\\.wslconfig"
      echo "    • Docker Desktop WSL2 統合を有効化"
      echo "    • WSL2 ファイルシステム内でプロジェクト作業を推奨"
      echo "    • 詳細ガイド: docs/PLATFORM_SUPPORT.md#windows-wsl2"
      ;;
    *)
      echo "  ❓ 不明なプラットフォーム:"
      echo "    • 基本的な Docker 設定を確認してください"
      echo "    • 詳細ガイド: docs/PLATFORM_SUPPORT.md"
      ;;
  esac

  echo
  echo "  🔗 完全なプラットフォームガイド:"
  echo "    docs/PLATFORM_SUPPORT.md を参照してください"
  echo
}

# プラットフォーム固有の既知の問題をチェック
check_platform_known_issues() {
  local platform=$(detect_platform)
  local arch=$(uname -m)
  local issues_found=false

  case "$platform" in
    macos)
      # Docker Desktop の状態確認
      if ! pgrep -f "Docker Desktop" >/dev/null 2>&1; then
        warning "Docker Desktop が起動していない可能性があります"
        echo "  解決方法: /Applications/Docker.app を起動してください"
        issues_found=true
      fi

      # Apple Silicon での Intel イメージ使用チェック
      if [[ "$arch" == "arm64" ]]; then
        info "Apple Silicon 検出: Intel イメージ使用時は --platform linux/amd64 を指定してください"
      fi
      ;;
    windows)
      # WSL2 の状態確認
      if command -v wsl.exe >/dev/null 2>&1; then
        local wsl_version
        wsl_version=$(wsl.exe --version 2>/dev/null | head -1 || echo "")
        if [[ -z "$wsl_version" ]]; then
          warning "WSL2 が正しく設定されていない可能性があります"
          echo "  解決方法: wsl --set-default-version 2 を実行してください"
          issues_found=true
        fi
      fi
      ;;
    ubuntu|fedora|linux)
      # Docker サービスの状態確認
      if command -v systemctl >/dev/null 2>&1; then
        if ! systemctl is-active --quiet docker 2>/dev/null; then
          warning "Docker サービスが起動していません"
          echo "  解決方法: sudo systemctl start docker"
          issues_found=true
        fi
      fi

      # ユーザーの docker グループ確認
      if ! groups | grep -q docker; then
        warning "現在のユーザーが docker グループに属していません"
        echo "  解決方法: sudo usermod -aG docker \$USER && newgrp docker"
        issues_found=true
      fi
      ;;
  esac

  if [[ "$issues_found" == "true" ]]; then
    echo
    echo "  📖 詳細なトラブルシューティング: docs/PLATFORM_SUPPORT.md"
    echo
  fi
}

# 拡張された依存関係チェック（--check-deps-extended オプション用）
check_dependencies_extended() {
  echo "🔍 拡張依存関係チェックを実行中..."
  echo

  # 基本的な依存関係チェック
  check_dependencies

  # プラットフォーム固有の問題チェック
  check_platform_known_issues

  # 最適化提案の表示
  show_platform_optimization_tips

  # システムリソース情報
  echo
  info "💻 システムリソース情報:"
  echo

  case "$(uname -s)" in
    Linux*)
      echo "  CPU: $(nproc) コア"
      echo "  メモリ: $(free -h | awk '/^Mem:/ {print $2}') (使用可能: $(free -h | awk '/^Mem:/ {print $7}'))"
      echo "  ディスク: $(df -h . | awk 'NR==2 {print $2}') (使用可能: $(df -h . | awk 'NR==2 {print $4}'))"
      ;;
    Darwin*)
      echo "  CPU: $(sysctl -n hw.ncpu) コア"
      echo "  メモリ: $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 )) GB"
      echo "  ディスク: $(df -h . | awk 'NR==2 {print $2}') (使用可能: $(df -h . | awk 'NR==2 {print $4}'))"
      ;;
    *)
      echo "  システム情報の取得をスキップしました"
      ;;
  esac

  # Docker 環境情報
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo
    info "🐳 Docker 環境情報:"
    echo
    local docker_info
    docker_info=$(docker info 2>/dev/null)
    echo "  Docker バージョン: $(docker --version | cut -d' ' -f3 | tr -d ',')"
    echo "  Docker Compose: $(docker-compose --version 2>/dev/null | cut -d' ' -f4 | tr -d ',' || echo '未インストール')"
    echo "  ストレージドライバー: $(echo "$docker_info" | grep 'Storage Driver:' | cut -d':' -f2 | xargs)"
    echo "  実行中コンテナ: $(docker ps -q | wc -l)"
    echo "  イメージ数: $(docker images -q | wc -l)"
  fi

  echo
  echo "📋 完全なプラットフォームガイドは docs/PLATFORM_SUPPORT.md を参照してください"
}

# 拡張依存関係チェックの場合
if [[ "$check_deps_extended" == "true" ]]; then
  info "🔍 拡張依存関係チェックモード"
  echo
  check_dependencies_extended
  success "✅ 拡張依存関係チェックが完了しました"
  exit 0
fi

# 依存関係チェックのみの場合
echo "DEBUG: check_deps_only=$check_deps_only" >&2
if [[ "$check_deps_only" == "true" ]]; then
  info "🔍 依存関係チェックモード"
  echo
  check_dependencies
  success "✅ 依存関係チェックが完了しました"
  exit 0
fi

# ワークフローファイルの早期検証（依存関係チェック前）
if [[ -n "$ACT_TIMEOUT" ]]; then
  if ! [[ "$ACT_TIMEOUT" =~ ^[0-9]+$ ]] || (( ACT_TIMEOUT <= 0 )); then
    error "タイムアウト値は正の整数（秒）で指定してください: $ACT_TIMEOUT"
    exit 1
  fi
  info "act タイムアウト: ${ACT_TIMEOUT} 秒"
  ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS="$ACT_TIMEOUT"
fi

echo "DEBUG: Current directory: $(pwd)" >&2
echo "DEBUG: WORKFLOW=$WORKFLOW" >&2
discover_workflows
echo "DEBUG: WORKFLOW_CHOICES=(${WORKFLOW_CHOICES[*]})" >&2

if [[ -n "$WORKFLOW" ]]; then
  if [[ "$WORKFLOW" == /* ]]; then
    error "ワークフローファイルはリポジトリ相対パスで指定してください: $WORKFLOW"
    exit 1
  fi
  normalized=$(normalize_workflow_path "$WORKFLOW")
  if [[ -f "$normalized" ]]; then
    WORKFLOW="$normalized"
    workflow_from_argument="true"
  elif workflow_exists "$normalized"; then
    WORKFLOW="$normalized"
    workflow_from_argument="true"
  else
    error "指定されたワークフローが見つかりません: $WORKFLOW"
    echo
    echo "🔍 利用可能なワークフローを確認してください:"
    if [[ -d ".github/workflows" ]]; then
      find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | head -5 || echo "  ワークフローファイルが見つかりません"
    else
      echo "  .github/workflows ディレクトリが存在しません"
    fi
    echo
    echo "ヘルプを表示するには: $0 --help"
    exit 1
  fi
fi

# 通常実行時の依存関係チェック
check_dependencies

# Docker イメージの準備
echo "=== prepare_docker_image を呼び出します ==="
prepare_docker_image
echo "=== prepare_docker_image が完了しました ==="

if [[ -z "$WORKFLOW" ]]; then
  should_prompt="true"
  if [[ ${#REST_ARGS[@]} -gt 0 ]]; then
    first_arg="${REST_ARGS[0]}"
    if [[ -n "$first_arg" && "$first_arg" != -* ]]; then
      should_prompt="false"
    fi
  fi

  if [[ "$should_prompt" == "true" ]]; then
    WORKFLOW="$(choose_workflow)"
    workflow_selected_interactively="true"
  fi
fi

if [[ "$workflow_from_argument" == "true" && "$workflow_selected_interactively" == "false" && -n "$WORKFLOW" ]]; then
  info "🚀 実行ワークフロー: ${WORKFLOW}"
fi

CMD=("uv" "run" "python" "main.py" "actions")
if [[ -n "${WORKFLOW}" ]]; then
  CMD+=("simulate" "${WORKFLOW}")
elif [[ ${#REST_ARGS[@]} -eq 0 ]]; then
  CMD+=("--help")
fi

if [[ ${#REST_ARGS[@]} -gt 0 ]]; then
  CMD+=("${REST_ARGS[@]}")
fi

# 実行前の最終チェック（進捗表示付き）
pre_execution_check() {
  local total_checks=4
  local current_check=0

  info "🔍 実行前チェックを実行中..."
  echo

  current_check=$((current_check + 1))
  show_progress "$current_check" "$total_checks" "Docker サービス状態を確認中..."

  # Docker サービス確認
  if ! docker info >/dev/null 2>&1; then
    echo
    error "Docker サービスが利用できません"
    echo
    echo "🔧 Docker サービスを開始してください:"
    case "$(detect_platform)" in
      ubuntu|fedora|linux)
        echo "  sudo systemctl start docker"
        ;;
      macos|windows)
        echo "  Docker Desktop を起動してください"
        ;;
    esac
    exit 2
  fi

  current_check=$((current_check + 1))
  show_progress "$current_check" "$total_checks" "ワークフローファイルを確認中..."

  # ワークフローファイル確認
  if [[ -n "$WORKFLOW" && ! -f "$WORKFLOW" ]]; then
    echo
    error "ワークフローファイルが見つかりません: $WORKFLOW"
    echo
    echo "🔍 利用可能なワークフロー:"
    find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | head -5 || echo "  ワークフローファイルが見つかりません"
    exit 1
  fi

  current_check=$((current_check + 1))
  show_progress "$current_check" "$total_checks" "出力ディレクトリを確認中..."

  # 出力ディレクトリの確認（実行時のみ必要）
  if [[ ! -d "${PROJECT_ROOT}/output" ]]; then
    mkdir -p "${PROJECT_ROOT}/output" 2>/dev/null || {
      warning "output ディレクトリを作成できませんでした（権限不足の可能性）"
      echo "  実行時に必要に応じて作成されます"
    }
  fi

  current_check=$((current_check + 1))
  show_progress "$current_check" "$total_checks" "実行前チェック完了"
  echo

  success "✅ すべての実行前チェックが完了しました"
  echo
}

# メイン実行部分（進捗表示付き）
execute_simulation() {
  local start_time=$(date +%s)
  local total_steps=4
  local current_step=0

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "実行環境を準備中..."

  # 実行ログの開始
  {
    echo "=== 実行開始 $(date -u +"%Y-%m-%d %H:%M:%S UTC") ==="
    echo "ワークフロー: ${WORKFLOW:-未指定}"
    echo "コマンド: ${CMD[*]}"
    echo "非対話モード: $(is_non_interactive && echo "有効" || echo "無効")"
    echo "=========================================="
  } >> "$DIAGNOSTIC_LOG" 2>/dev/null || true

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "Docker Compose 環境を設定中..."

  # Docker Compose 実行設定
  # docker-compose.ymlの絶対パスを使用（uv tool install対応）
  local compose_file="${PACKAGE_ROOT}/docker-compose.yml"
  if [[ ! -f "$compose_file" ]]; then
    compose_file="${PROJECT_ROOT}/docker-compose.yml"
  fi

  COMPOSE_RUN_ARGS=("-f" "$compose_file" "--profile" "tools" "run" "--rm")

  # ワークフローパスはPROJECT_ROOT相対で解決
  local workflow_abs="${PROJECT_ROOT}/${WORKFLOW}"

  COMPOSE_ENV_VARS=(
    '-e' "WORKFLOW_FILE=${WORKFLOW}"
    '-e' "ACTIONS_USE_ACT_BRIDGE=1"
    '-v' "${PROJECT_ROOT}/.github:/app/.github:ro"
    '-v' "${PROJECT_ROOT}/output:/app/output:rw"
    '-v' "${PROJECT_ROOT}/logs:/app/logs:rw"
  )
  if [[ -n "${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS:-}" ]]; then
    COMPOSE_ENV_VARS+=(
      "-e" "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=${ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS}"
    )
  fi
  if [[ -n "${ACTIONS_SIMULATOR_ENGINE:-}" ]]; then
    COMPOSE_ENV_VARS+=(
      "-e" "ACTIONS_SIMULATOR_ENGINE=${ACTIONS_SIMULATOR_ENGINE}"
    )
  fi

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "GitHub Actions シミュレーションを実行中..."
  echo

  info "🚀 GitHub Actions Simulator を実行中..."
  if [[ -n "$WORKFLOW" ]]; then
    info "📄 ワークフロー: $WORKFLOW"
  fi
  info "⚠️ act bridge (Phase1 skeleton) モードを有効化しています。問題があれば従来実装に自動フォールバックします。"
  if is_non_interactive; then
    info "🤖 非対話モード: 自動実行中"
  fi
  echo

  # 実行とエラーハンドリング
  local exit_code=0
  "${COMPOSE_CMD[@]}" \
    "${COMPOSE_RUN_ARGS[@]}" \
    "${COMPOSE_ENV_VARS[@]}" \
    actions-simulator \
    "${CMD[@]}" || exit_code=$?

  current_step=$((current_step + 1))
  show_progress "$current_step" "$total_steps" "実行結果を処理中..."

  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  # 実行結果のログ記録
  {
    echo "=== 実行終了 $(date -u +"%Y-%m-%d %H:%M:%S UTC") ==="
    echo "終了コード: $exit_code"
    echo "実行時間: ${duration}秒"
    echo "=========================================="
    echo
  } >> "$DIAGNOSTIC_LOG" 2>/dev/null || true

  echo

  # 結果の表示
  if [[ $exit_code -eq 0 ]]; then
    success "🎉 シミュレーションが正常に完了しました！"
    echo
    show_success_summary "$duration"
  else
    error "❌ シミュレーションがエラーで終了しました (終了コード: $exit_code)"
    echo
    show_failure_summary "$exit_code" "$duration"
  fi

  return $exit_code
}

# 成功時のサマリー表示
show_success_summary() {
  local duration=$1
  local formatted_duration

  # 実行時間のフォーマット
  if [[ $duration -lt 60 ]]; then
    formatted_duration="${duration}秒"
  elif [[ $duration -lt 3600 ]]; then
    formatted_duration="$((duration / 60))分$((duration % 60))秒"
  else
    formatted_duration="$((duration / 3600))時間$(((duration % 3600) / 60))分$((duration % 60))秒"
  fi

  echo "📊 実行サマリー:"
  echo "  ✅ ステータス: 成功"
  echo "  ⏱️  実行時間: $formatted_duration"
  echo "  📄 ワークフロー: ${WORKFLOW:-未指定}"
  echo "  📁 出力ディレクトリ: ./output"
  echo "  📝 ログファイル: $DIAGNOSTIC_LOG"
  echo

  # 出力ファイルの確認
  if [[ -d "./output" ]]; then
    local output_files
    output_files=$(find ./output -type f 2>/dev/null | wc -l)
    if [[ $output_files -gt 0 ]]; then
      echo "📋 生成されたファイル: ${output_files}個"
      echo "  最新のファイル:"
      find ./output -type f -printf "    %TY-%Tm-%Td %TH:%TM %p\n" 2>/dev/null | sort -r | head -3 || true
      echo
    fi
  fi

  echo "🎯 推奨される次のステップ:"
  echo
  echo "  1️⃣  結果を確認:"
  echo "     ls -la output/                    # 出力ファイル一覧"
  echo "     cat output/simulation-report.json # 詳細レポート（存在する場合）"
  echo
  echo "  2️⃣  他のワークフローを試行:"
  echo "     $0                               # 対話的選択"
  echo "     $0 .github/workflows/test.yml    # 特定のワークフロー"
  echo
  echo "  3️⃣  設定をカスタマイズ:"
  echo "     cp .env.template .env            # 環境変数設定"
  echo "     make actions                     # Makefile経由での実行"
  echo
  echo "  4️⃣  継続的インテグレーション:"
  echo "     # pre-commit フックとして設定"
  echo "     echo '$0 \$WORKFLOW' > .git/hooks/pre-commit"
  echo "     chmod +x .git/hooks/pre-commit"
  echo

  if is_non_interactive; then
    echo "  🤖 非対話モード用のコマンド例:"
    echo "     NON_INTERACTIVE=1 $0 .github/workflows/ci.yml"
    echo "     INDEX=1 $0                      # 最初のワークフローを自動選択"
    echo
  fi

  echo "📚 詳細情報:"
  echo "  • README.md - 基本的な使用方法"
  echo "  • docs/actions/ - 詳細なドキュメント"
  echo "  • make help - 利用可能なコマンド一覧"
  echo
}

# 失敗時のサマリー表示
show_failure_summary() {
  local exit_code=$1
  local duration=$2
  local formatted_duration

  # 実行時間のフォーマット
  if [[ $duration -lt 60 ]]; then
    formatted_duration="${duration}秒"
  elif [[ $duration -lt 3600 ]]; then
    formatted_duration="$((duration / 60))分$((duration % 60))秒"
  else
    formatted_duration="$((duration / 3600))時間$(((duration % 3600) / 60))分$((duration % 60))秒"
  fi

  echo "📊 実行サマリー:"
  echo "  ❌ ステータス: 失敗"
  echo "  🔢 終了コード: $exit_code"
  echo "  ⏱️  実行時間: $formatted_duration"
  echo "  📄 ワークフロー: ${WORKFLOW:-未指定}"
  echo "  📝 エラーログ: $ERROR_LOG"
  echo "  🔍 診断ログ: $DIAGNOSTIC_LOG"
  echo

  # エラー分類と対処法
  echo "🔧 推奨される対処法:"
  echo

  case $exit_code in
    1)
      echo "  🎯 ワークフローまたは設定の問題:"
      echo "     1. ワークフローファイルの構文を確認"
      echo "        yamllint $WORKFLOW"
      echo "     2. 必要な secrets や環境変数を確認"
      echo "        cat .env.template"
      echo "     3. GitHub Actions の公式ドキュメントを参照"
      echo
      ;;
    125)
      echo "  🐳 Docker コンテナの問題:"
      echo "     1. Docker リソースをクリーンアップ"
      echo "        docker system prune -f"
      echo "     2. イメージを再取得"
      echo "        docker-compose pull"
      echo "     3. コンテナを再ビルド"
      echo "        docker-compose build --no-cache"
      echo
      ;;
    126)
      echo "  🔒 権限の問題:"
      echo "     1. ファイル権限を確認"
      echo "        ls -la $WORKFLOW"
      echo "     2. Docker グループに所属しているか確認"
      echo "        groups | grep docker"
      echo "     3. 権限を修正"
      echo "        sudo chown -R \$(id -u):\$(id -g) ."
      echo
      ;;
    127)
      echo "  🔍 コマンドが見つからない:"
      echo "     1. 依存関係を再確認"
      echo "        $0 --check-deps"
      echo "     2. PATH 環境変数を確認"
      echo "        echo \$PATH"
      echo
      ;;
    130)
      echo "  ⏹️  実行が中断されました (Ctrl+C)"
      echo "     これは正常な中断です。再実行してください。"
      echo
      ;;
    *)
      echo "  ❓ 不明なエラー (終了コード: $exit_code)"
      echo "     1. 詳細な診断情報を確認"
      echo "        cat $DIAGNOSTIC_LOG"
      echo "     2. エラーログを確認"
      echo "        cat $ERROR_LOG"
      echo
      ;;
  esac

  echo "🛠️  一般的なトラブルシューティング手順:"
  echo "  1️⃣  ログファイルを確認:"
  echo "     cat $ERROR_LOG                   # エラーの詳細"
  echo "     cat $DIAGNOSTIC_LOG              # システム診断情報"
  echo
  echo "  2️⃣  環境をリセット:"
  echo "     make clean                       # 環境のクリーンアップ"
  echo "     docker system prune -f          # Docker リソースの削除"
  echo
  echo "  3️⃣  依存関係を再確認:"
  echo "     docker --version                 # Docker バージョン確認"
  echo "     docker info                      # Docker サービス状態"
  echo
  echo "  4️⃣  設定を確認:"
  echo "     cat .env                         # 環境変数設定"
  echo "     yamllint $WORKFLOW               # ワークフロー構文チェック"
  echo

  if is_non_interactive; then
    echo "  🤖 非対話モードでのデバッグ:"
    echo "     DEBUG=1 NON_INTERACTIVE=1 $0 $WORKFLOW"
    echo "     # より詳細なログ出力が有効になります"
    echo
  fi

  echo "📚 サポートリソース:"
  echo "  • docs/TROUBLESHOOTING.md - 詳細なトラブルシューティング"
  echo "  • docs/actions/FAQ.md - よくある質問"
  echo "  • GitHub Issues - 問題報告とサポート"
  echo
  echo "🆘 問題が解決しない場合:"
  echo "  上記のログファイルを添付して GitHub Issues で報告してください"
  echo
}

# 全体実行の開始
main_execution() {
  local overall_start_time=$(date +%s)

  info "🎬 GitHub Actions Simulator セッションを開始します"
  if is_non_interactive; then
    info "🤖 非対話モード: 自動実行"
  fi
  echo

  # 実行前チェック
  pre_execution_check

  # メイン実行
  execute_simulation
  run_exit=$?

  # 全体サマリー
  overall_end_time=$(date +%s)
  overall_duration=$((overall_end_time - overall_start_time))

  echo
  echo "═══════════════════════════════════════════════════════════════"
  if [[ $run_exit -eq 0 ]]; then
    success "🏆 GitHub Actions Simulator セッションが正常に完了しました"
  else
    error "💥 GitHub Actions Simulator セッションがエラーで終了しました"
  fi

  echo
  echo "📈 セッション統計:"
  echo "  🕐 総実行時間: $((overall_duration / 60))分$((overall_duration % 60))秒"
  echo "  📄 実行ワークフロー: ${WORKFLOW:-未指定}"
  echo "  🤖 実行モード: $(is_non_interactive && echo "非対話" || echo "対話")"
  echo "  📊 最終結果: $([ $run_exit -eq 0 ] && echo "成功 ✅" || echo "失敗 ❌")"
  echo

  if [[ $run_exit -eq 0 ]]; then
    echo "🚀 GitHub Actions の事前チェックが完了しました！"
    echo "   本番環境へのプッシュ前に問題を発見できました。"
  else
    echo "🔧 問題が発見されました。修正後に再実行してください。"
  fi

  echo "═══════════════════════════════════════════════════════════════"
  echo

  return $run_exit
}

# メイン実行
main_execution
RUN_EXIT=$?

exit "${RUN_EXIT}"
