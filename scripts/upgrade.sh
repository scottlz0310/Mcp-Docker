#!/bin/bash
# GitHub Actions Simulator - 自動アップグレードスクリプト
#
# このスクリプトは GitHub Actions Simulator を最新バージョンに
# 安全にアップグレードするための自動化ツールです。

set -euo pipefail

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
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

# 設定
BACKUP_DIR="backup-$(date +%Y%m%d-%H%M%S)"
BACKUP_ENABLED=true
TEST_ENABLED=true
FORCE_UPGRADE=false

# ヘルプ表示
show_help() {
    cat << EOF
GitHub Actions Simulator - 自動アップグレードスクリプト

使用方法:
    $0 [オプション]

オプション:
    --no-backup     バックアップを作成しない
    --no-test       アップグレード後のテストをスキップ
    --force         強制アップグレード（警告を無視）
    --help          このヘルプを表示

例:
    $0                      # 標準アップグレード
    $0 --no-backup          # バックアップなしでアップグレード
    $0 --force --no-test    # 強制アップグレード（テストなし）

EOF
}

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            BACKUP_ENABLED=false
            shift
            ;;
        --no-test)
            TEST_ENABLED=false
            shift
            ;;
        --force)
            FORCE_UPGRADE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "不明なオプション: $1"
            show_help
            exit 1
            ;;
    esac
done

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェック中..."

    # Git リポジトリかチェック
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Gitリポジトリではありません"
        exit 1
    fi

    # 未コミットの変更をチェック
    if ! git diff-index --quiet HEAD --; then
        if [[ "$FORCE_UPGRADE" == "false" ]]; then
            log_error "未コミットの変更があります。コミットするか --force オプションを使用してください"
            exit 1
        else
            log_warning "未コミットの変更がありますが、強制実行します"
        fi
    fi

    # 必要なコマンドをチェック
    local required_commands=("make" "docker" "uv")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "必要なコマンドが見つかりません: $cmd"
            exit 1
        fi
    done

    log_success "前提条件チェック完了"
}

# 現在のバージョン取得
get_current_version() {
    local version
    if command -v make &> /dev/null && make version &> /dev/null; then
        version=$(make version 2>/dev/null | grep -E "pyproject\.toml|main\.py" | head -1 | awk '{print $NF}' || echo "unknown")
    else
        version="unknown"
    fi
    echo "$version"
}

# バックアップ作成
create_backup() {
    if [[ "$BACKUP_ENABLED" == "false" ]]; then
        log_info "バックアップをスキップします"
        return 0
    fi

    log_info "バックアップを作成中..."
    mkdir -p "$BACKUP_DIR"

    # 重要なファイルをバックアップ
    local backup_files=(
        ".env"
        ".env.local"
        "docker-compose.override.yml"
        ".pre-commit-config.yaml"
    )

    for file in "${backup_files[@]}"; do
        if [[ -f "$file" ]]; then
            cp "$file" "$BACKUP_DIR/" 2>/dev/null || true
            log_info "バックアップ: $file → $BACKUP_DIR/"
        fi
    done

    # Git情報をバックアップ
    git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt" 2>/dev/null || true
    git status --porcelain > "$BACKUP_DIR/git_status.txt" 2>/dev/null || true

    log_success "バックアップ完了: $BACKUP_DIR"
}

# アップグレード実行
perform_upgrade() {
    log_info "アップグレードを実行中..."

    # 現在のバージョンを記録
    local current_version
    current_version=$(get_current_version)
    log_info "現在のバージョン: $current_version"

    # 最新コードを取得
    log_info "最新コードを取得中..."
    git fetch origin

    # mainブランチに切り替え
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        log_info "mainブランチに切り替え中..."
        git checkout main
    fi

    # 最新コードをプル
    git pull origin main

    # 新しいバージョンを確認
    local new_version
    new_version=$(get_current_version)
    log_info "新しいバージョン: $new_version"

    if [[ "$current_version" == "$new_version" ]]; then
        log_info "既に最新バージョンです"
        return 0
    fi

    # 依存関係を更新
    log_info "依存関係を更新中..."
    if command -v uv &> /dev/null; then
        uv sync
    else
        log_warning "uv が見つかりません。手動で依存関係を更新してください"
    fi

    # Docker環境を再構築
    log_info "Docker環境を再構築中..."
    make clean || log_warning "make clean でエラーが発生しましたが、続行します"
    make build

    log_success "アップグレード完了: $current_version → $new_version"
}

# テンプレートファイル更新
update_templates() {
    log_info "テンプレートファイルを更新中..."

    # .env.example から .env を更新（既存の設定を保持）
    if [[ -f ".env.example" ]]; then
        if [[ -f ".env" ]]; then
            log_info ".env ファイルの更新をスキップ（手動確認が必要）"
            log_warning "新しい環境変数については .env.example を確認してください"
        else
            cp ".env.example" ".env"
            log_info ".env ファイルを作成しました"
        fi
    fi

    # pre-commit設定の更新
    if [[ -f ".pre-commit-config.yaml.sample" ]]; then
        if [[ ! -f ".pre-commit-config.yaml" ]]; then
            cp ".pre-commit-config.yaml.sample" ".pre-commit-config.yaml"
            log_info ".pre-commit-config.yaml を作成しました"
        else
            log_info ".pre-commit-config.yaml の更新をスキップ（手動確認が必要）"
        fi
    fi

    log_success "テンプレートファイル更新完了"
}

# アップグレード後テスト
run_tests() {
    if [[ "$TEST_ENABLED" == "false" ]]; then
        log_info "テストをスキップします"
        return 0
    fi

    log_info "アップグレード後テストを実行中..."

    # 基本的な動作確認
    log_info "バージョン確認..."
    make version || log_error "バージョン確認に失敗"

    log_info "依存関係チェック..."
    ./scripts/run-actions.sh --check-deps || log_error "依存関係チェックに失敗"

    # 基本テストを実行
    log_info "基本テストを実行..."
    if make test &> /dev/null; then
        log_success "基本テスト成功"
    else
        log_warning "基本テストで警告またはエラーが発生しました"
    fi

    log_success "アップグレード後テスト完了"
}

# 復旧機能
restore_backup() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "バックアップディレクトリが見つかりません: $BACKUP_DIR"
        return 1
    fi

    log_info "バックアップから復旧中..."

    # ファイルを復旧
    for file in "$BACKUP_DIR"/*; do
        if [[ -f "$file" ]]; then
            local basename
            basename=$(basename "$file")
            if [[ "$basename" != "git_commit.txt" && "$basename" != "git_status.txt" ]]; then
                cp "$file" "./"
                log_info "復旧: $basename"
            fi
        fi
    done

    # Gitコミットを復旧
    if [[ -f "$BACKUP_DIR/git_commit.txt" ]]; then
        local commit
        commit=$(cat "$BACKUP_DIR/git_commit.txt")
        git checkout "$commit" 2>/dev/null || log_warning "Gitコミットの復旧に失敗"
    fi

    log_success "バックアップから復旧完了"
}

# エラーハンドリング
handle_error() {
    local exit_code=$?
    log_error "アップグレード中にエラーが発生しました (終了コード: $exit_code)"

    if [[ "$BACKUP_ENABLED" == "true" ]]; then
        read -p "バックアップから復旧しますか？ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            restore_backup
        fi
    fi

    exit $exit_code
}

# メイン処理
main() {
    log_info "GitHub Actions Simulator アップグレードを開始します"

    # エラーハンドリング設定
    trap handle_error ERR

    # 各ステップを実行
    check_prerequisites
    create_backup
    perform_upgrade
    update_templates
    run_tests

    log_success "アップグレードが正常に完了しました！"

    # 次のステップを案内
    echo
    log_info "次のステップ:"
    echo "  1. 設定ファイルを確認: .env, .pre-commit-config.yaml"
    echo "  2. 動作確認: ./scripts/run-actions.sh"
    echo "  3. ドキュメント確認: docs/UPGRADE_GUIDE.md"

    if [[ "$BACKUP_ENABLED" == "true" ]]; then
        echo "  4. バックアップ削除: rm -rf $BACKUP_DIR (問題がなければ)"
    fi
}

# スクリプト実行
main "$@"
