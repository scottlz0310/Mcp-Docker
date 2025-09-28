#!/usr/bin/env bash
# GitHub Actions Simulator - 統合インストールスクリプト
#
# このスクリプトは自動的にプラットフォームを検出し、
# 適切なインストーラーを実行します。

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

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# プラットフォーム検出
detect_platform() {
  case "$(uname -s)" in
    Linux*)
      echo "linux"
      ;;
    Darwin*)
      echo "macos"
      ;;
    CYGWIN*|MINGW*|MSYS*)
      echo "windows"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

# 詳細なプラットフォーム情報を取得
get_platform_details() {
  local platform=$(detect_platform)

  case "$platform" in
    linux)
      if command -v lsb_release >/dev/null 2>&1; then
        local distro_name=$(lsb_release -sd 2>/dev/null | tr -d '"')
        echo "$distro_name"
      elif [[ -f /etc/os-release ]]; then
        local name=$(grep '^PRETTY_NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        echo "$name"
      else
        echo "Linux $(uname -r)"
      fi
      ;;
    macos)
      local version=$(sw_vers -productVersion 2>/dev/null || echo "不明")
      echo "macOS $version"
      ;;
    windows)
      echo "Windows ($(uname -s))"
      ;;
    *)
      echo "$(uname -s) $(uname -r)"
      ;;
  esac
}

# Linux インストーラーの実行
run_linux_installer() {
  local linux_installer="$SCRIPT_DIR/install-linux.sh"

  if [[ ! -f "$linux_installer" ]]; then
    error "Linux インストーラーが見つかりません: $linux_installer"
    exit 1
  fi

  info "Linux インストーラーを実行中..."
  bash "$linux_installer" "$@"
}

# macOS インストーラーの実行
run_macos_installer() {
  local macos_installer="$SCRIPT_DIR/install-macos.sh"

  if [[ ! -f "$macos_installer" ]]; then
    error "macOS インストーラーが見つかりません: $macos_installer"
    exit 1
  fi

  info "macOS インストーラーを実行中..."
  bash "$macos_installer" "$@"
}

# Windows インストーラーの実行
run_windows_installer() {
  local windows_installer="$SCRIPT_DIR/install-windows.ps1"

  if [[ ! -f "$windows_installer" ]]; then
    error "Windows インストーラーが見つかりません: $windows_installer"
    exit 1
  fi

  warning "Windows 環境が検出されました"
  echo
  echo "Windows での GitHub Actions Simulator のセットアップには以下の手順が必要です:"
  echo
  echo "1. PowerShell を管理者として実行"
  echo "2. 実行ポリシーを設定:"
  echo "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
  echo "3. Windows インストーラーを実行:"
  echo "   .\\scripts\\install-windows.ps1"
  echo
  echo "または、WSL2 内でこのスクリプトを実行してください:"
  echo "   wsl"
  echo "   cd /mnt/c/path/to/your/project"
  echo "   ./scripts/install.sh"
  echo
  echo "詳細なガイド: docs/PLATFORM_SUPPORT.md#windows-wsl2"
}

# 前提条件のチェック
check_prerequisites() {
  local platform=$(detect_platform)

  case "$platform" in
    linux)
      # sudo 権限の確認
      if ! sudo -n true 2>/dev/null; then
        warning "sudo 権限が必要です。パスワードの入力を求められる場合があります"
      fi
      ;;
    macos)
      # macOS バージョンの確認
      local version=$(sw_vers -productVersion 2>/dev/null || echo "0.0.0")
      local major_version=$(echo "$version" | cut -d'.' -f1)

      if [[ $major_version -lt 12 ]]; then
        error "macOS 12.0 (Monterey) 以降が必要です。現在のバージョン: $version"
        exit 1
      fi
      ;;
    windows)
      # Windows の場合は特別な処理が必要
      return 0
      ;;
    *)
      warning "サポートされていないプラットフォーム: $platform"
      ;;
  esac
}

# インストール後の確認
post_install_check() {
  local platform=$(detect_platform)

  echo
  info "インストール後の確認を実行中..."

  # 基本的な依存関係チェック
  if [[ -f "$SCRIPT_DIR/run-actions.sh" ]]; then
    bash "$SCRIPT_DIR/run-actions.sh" --check-deps
  else
    warning "run-actions.sh が見つかりません。手動で依存関係を確認してください"
  fi
}

# 使用方法の表示
show_usage() {
  cat <<EOF
GitHub Actions Simulator - 統合インストールスクリプト

このスクリプトは自動的にプラットフォームを検出し、適切なインストーラーを実行します。

使用方法:
  $0 [オプション]

オプション:
  --help, -h          このヘルプを表示
  --docker-only       Docker のみをインストール
  --skip-optimization 最適化設定をスキップ
  --verify-only       インストール検証のみを実行
  --platform=PLATFORM 特定のプラットフォーム用インストーラーを強制実行
                      (linux, macos, windows)

例:
  $0                        # 自動検出してインストール
  $0 --docker-only          # Docker のみインストール
  $0 --verify-only          # 検証のみ実行
  $0 --platform=linux       # Linux インストーラーを強制実行

サポートプラットフォーム:
  • Linux (Ubuntu, Debian, Fedora, RHEL, CentOS, Arch)
  • macOS (12.0 Monterey 以降)
  • Windows (WSL2 経由)

詳細なドキュメント:
  docs/PLATFORM_SUPPORT.md
EOF
}

# メイン処理
main() {
  local force_platform=""
  local installer_args=()

  # 引数の解析
  while [[ $# -gt 0 ]]; do
    case $1 in
      --help|-h)
        show_usage
        exit 0
        ;;
      --platform=*)
        force_platform="${1#*=}"
        shift
        ;;
      --docker-only|--skip-optimization|--verify-only|--performance-test|--wsl-only)
        installer_args+=("$1")
        shift
        ;;
      *)
        error "不明なオプション: $1"
        show_usage
        exit 1
        ;;
    esac
  done

  echo "🚀 GitHub Actions Simulator - 統合インストーラー"
  echo "================================================"
  echo

  # プラットフォーム検出
  local platform
  if [[ -n "$force_platform" ]]; then
    platform="$force_platform"
    info "強制指定されたプラットフォーム: $platform"
  else
    platform=$(detect_platform)
    info "検出されたプラットフォーム: $platform"
  fi

  info "詳細: $(get_platform_details)"
  echo

  # 前提条件のチェック
  check_prerequisites

  # プラットフォーム別のインストーラー実行
  case "$platform" in
    linux)
      run_linux_installer "${installer_args[@]}"
      ;;
    macos)
      run_macos_installer "${installer_args[@]}"
      ;;
    windows)
      run_windows_installer "${installer_args[@]}"
      exit 0  # Windows の場合はここで終了
      ;;
    *)
      error "サポートされていないプラットフォーム: $platform"
      echo
      echo "サポートされているプラットフォーム:"
      echo "  • Linux (Ubuntu, Debian, Fedora, RHEL, CentOS, Arch)"
      echo "  • macOS (12.0 Monterey 以降)"
      echo "  • Windows (WSL2 経由)"
      echo
      echo "詳細なドキュメント: docs/PLATFORM_SUPPORT.md"
      exit 1
      ;;
  esac

  # インストール後の確認
  if [[ ! " ${installer_args[*]} " =~ " --verify-only " ]]; then
    post_install_check
  fi

  echo
  success "🎉 GitHub Actions Simulator のセットアップが完了しました！"
  echo
  echo "📋 次のステップ:"
  echo "  1. 依存関係の確認: ./scripts/run-actions.sh --check-deps"
  echo "  2. 基本実行: ./scripts/run-actions.sh"
  echo "  3. 拡張チェック: ./scripts/run-actions.sh --check-deps-extended"
  echo
  echo "📖 詳細なドキュメント:"
  echo "  • プラットフォームガイド: docs/PLATFORM_SUPPORT.md"
  echo "  • トラブルシューティング: docs/TROUBLESHOOTING.md"
  echo "  • 開発ワークフロー統合: docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md"
}

# スクリプトが直接実行された場合のみ main を呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
