#!/bin/bash
# GitHub Actions Simulator - CHANGELOG管理スクリプト
#
# このスクリプトはCHANGELOG.mdの管理を自動化します。

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
CHANGELOG_FILE="CHANGELOG.md"
TEMP_FILE=$(mktemp)
BACKUP_FILE="${CHANGELOG_FILE}.backup.$(date +%Y%m%d-%H%M%S)"

# ヘルプ表示
show_help() {
    cat << EOF
GitHub Actions Simulator - CHANGELOG管理スクリプト

使用方法:
    $0 <コマンド> [オプション]

コマンド:
    add-entry TYPE "DESCRIPTION"    新しいエントリを追加
    prepare-release VERSION         リリース準備（Unreleased → バージョン）
    validate                        CHANGELOG形式を検証
    generate-from-commits FROM TO   コミット履歴からエントリを生成
    show-unreleased                 未リリースの変更を表示

TYPE:
    added       新機能
    changed     既存機能の変更
    deprecated  非推奨機能
    removed     削除された機能
    fixed       バグ修正
    security    セキュリティ修正

例:
    $0 add-entry added "新しい診断機能を追加"
    $0 add-entry fixed "Docker権限エラーを修正"
    $0 prepare-release "1.2.0"
    $0 generate-from-commits v1.1.0 HEAD

EOF
}

# CHANGELOG.mdの存在確認
check_changelog_exists() {
    if [[ ! -f "$CHANGELOG_FILE" ]]; then
        log_error "CHANGELOG.md が見つかりません"
        exit 1
    fi
}

# バックアップ作成
create_backup() {
    cp "$CHANGELOG_FILE" "$BACKUP_FILE"
    log_info "バックアップを作成しました: $BACKUP_FILE"
}

# 新しいエントリを追加
add_entry() {
    local type="$1"
    local description="$2"

    # タイプの検証
    case "$type" in
        added|changed|deprecated|removed|fixed|security)
            ;;
        *)
            log_error "無効なタイプ: $type"
            log_info "有効なタイプ: added, changed, deprecated, removed, fixed, security"
            exit 1
            ;;
    esac

    # 日本語のタイプマッピング
    local japanese_type
    case "$type" in
        added) japanese_type="✨ 新機能" ;;
        changed) japanese_type="🔄 変更" ;;
        deprecated) japanese_type="⚠️ 非推奨" ;;
        removed) japanese_type="🗑️ 削除" ;;
        fixed) japanese_type="🐛 修正" ;;
        security) japanese_type="🔒 セキュリティ" ;;
    esac

    log_info "エントリを追加中: [$type] $description"

    # Unreleased セクションを探して追加
    if grep -q "## \[Unreleased\]" "$CHANGELOG_FILE"; then
        # 既存のUnreleasedセクションに追加
        awk -v type="$japanese_type" -v desc="$description" '
        /^## \[Unreleased\]/ {
            print $0
            if (!found_section) {
                print ""
                found_section = 1
            }
            next
        }
        /^### / && found_section && !added {
            if ($0 ~ type) {
                print $0
                print "- " desc
                added = 1
                next
            } else if (!type_section_exists) {
                print "### " type
                print "- " desc
                print ""
                print $0
                added = 1
                type_section_exists = 1
                next
            }
        }
        /^## / && !/^## \[Unreleased\]/ && found_section && !added {
            print "### " type
            print "- " desc
            print ""
            print $0
            added = 1
            next
        }
        { print }
        END {
            if (!added && found_section) {
                print "### " type
                print "- " desc
            }
        }
        ' "$CHANGELOG_FILE" > "$TEMP_FILE"
    else
        # Unreleasedセクションを新規作成
        awk -v type="$japanese_type" -v desc="$description" '
        /^# Changelog/ {
            print $0
            print ""
            print "All notable changes to this project will be documented in this file."
            print ""
            print "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),"
            print "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
            print ""
            print "## [Unreleased]"
            print ""
            print "### " type
            print "- " desc
            print ""
            next
        }
        /^All notable changes/ { next }
        /^The format is based/ { next }
        /^and this project adheres/ { next }
        /^$/ && prev_empty { next }
        {
            prev_empty = ($0 == "")
            print
        }
        ' "$CHANGELOG_FILE" > "$TEMP_FILE"
    fi

    mv "$TEMP_FILE" "$CHANGELOG_FILE"
    log_success "エントリを追加しました"
}

# リリース準備
prepare_release() {
    local version="$1"
    local release_date=$(date +%Y-%m-%d)

    log_info "リリース準備中: v$version ($release_date)"

    # Unreleasedセクションをバージョンに変更
    sed -i.bak "s/## \[Unreleased\]/## [$version] - $release_date/" "$CHANGELOG_FILE"

    # 新しいUnreleasedセクションを追加
    awk -v version="$version" -v date="$release_date" '
    /^# Changelog/ {
        print $0
        print ""
        print "All notable changes to this project will be documented in this file."
        print ""
        print "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),"
        print "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
        print ""
        print "## [Unreleased]"
        print ""
        next
    }
    /^All notable changes/ { next }
    /^The format is based/ { next }
    /^and this project adheres/ { next }
    /^## \['"$version"'\]/ {
        print $0
        next
    }
    { print }
    ' "$CHANGELOG_FILE" > "$TEMP_FILE"

    mv "$TEMP_FILE" "$CHANGELOG_FILE"
    rm -f "${CHANGELOG_FILE}.bak"

    log_success "リリース準備完了: v$version"
}

# CHANGELOG形式検証
validate_changelog() {
    log_info "CHANGELOG形式を検証中..."

    local errors=0

    # 基本構造チェック
    if ! grep -q "^# Changelog" "$CHANGELOG_FILE"; then
        log_error "CHANGELOGタイトルが見つかりません"
        ((errors++))
    fi

    if ! grep -q "Keep a Changelog" "$CHANGELOG_FILE"; then
        log_warning "Keep a Changelog リンクが見つかりません"
    fi

    if ! grep -q "Semantic Versioning" "$CHANGELOG_FILE"; then
        log_warning "Semantic Versioning リンクが見つかりません"
    fi

    # バージョン形式チェック
    local invalid_versions
    invalid_versions=$(grep -n "^## \[" "$CHANGELOG_FILE" | grep -v -E "\[(Unreleased|[0-9]+\.[0-9]+\.[0-9]+)\]" || true)
    if [[ -n "$invalid_versions" ]]; then
        log_error "無効なバージョン形式が見つかりました:"
        echo "$invalid_versions"
        ((errors++))
    fi

    # 日付形式チェック
    local invalid_dates
    invalid_dates=$(grep -n "^## \[[0-9]" "$CHANGELOG_FILE" | grep -v -E "[0-9]{4}-[0-9]{2}-[0-9]{2}" || true)
    if [[ -n "$invalid_dates" ]]; then
        log_error "無効な日付形式が見つかりました:"
        echo "$invalid_dates"
        ((errors++))
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "CHANGELOG形式は正常です"
        return 0
    else
        log_error "$errors 個のエラーが見つかりました"
        return 1
    fi
}

# コミット履歴からエントリ生成
generate_from_commits() {
    local from_ref="$1"
    local to_ref="$2"

    log_info "コミット履歴からエントリを生成中: $from_ref..$to_ref"

    # Conventional Commitsパターンでコミットを分類
    local commits
    commits=$(git log --pretty=format:"%s" "$from_ref..$to_ref" 2>/dev/null || true)

    if [[ -z "$commits" ]]; then
        log_warning "指定された範囲にコミットが見つかりません"
        return 1
    fi

    echo "=== 生成されたCHANGELOGエントリ ==="
    echo

    # 各タイプ別にコミットを分類
    local has_entries=false

    # 新機能
    local feat_commits
    feat_commits=$(echo "$commits" | grep -E "^feat(\(.+\))?: " | sed 's/^feat[^:]*: //' || true)
    if [[ -n "$feat_commits" ]]; then
        echo "### ✨ 新機能"
        echo "$feat_commits" | while read -r line; do
            [[ -n "$line" ]] && echo "- $line"
        done
        echo
        has_entries=true
    fi

    # バグ修正
    local fix_commits
    fix_commits=$(echo "$commits" | grep -E "^fix(\(.+\))?: " | sed 's/^fix[^:]*: //' || true)
    if [[ -n "$fix_commits" ]]; then
        echo "### 🐛 修正"
        echo "$fix_commits" | while read -r line; do
            [[ -n "$line" ]] && echo "- $line"
        done
        echo
        has_entries=true
    fi

    # ドキュメント
    local docs_commits
    docs_commits=$(echo "$commits" | grep -E "^docs(\(.+\))?: " | sed 's/^docs[^:]*: //' || true)
    if [[ -n "$docs_commits" ]]; then
        echo "### 📝 ドキュメント"
        echo "$docs_commits" | while read -r line; do
            [[ -n "$line" ]] && echo "- $line"
        done
        echo
        has_entries=true
    fi

    # その他
    local other_commits
    other_commits=$(echo "$commits" | grep -v -E "^(feat|fix|docs)(\(.+\))?: " || true)
    if [[ -n "$other_commits" ]]; then
        echo "### 🔧 その他"
        echo "$other_commits" | while read -r line; do
            [[ -n "$line" ]] && echo "- $line"
        done
        echo
        has_entries=true
    fi

    if [[ "$has_entries" == "false" ]]; then
        log_warning "生成できるエントリがありませんでした"
    else
        log_info "上記のエントリを手動でCHANGELOG.mdに追加してください"
    fi
}

# 未リリース変更の表示
show_unreleased() {
    log_info "未リリースの変更を表示中..."

    if grep -q "## \[Unreleased\]" "$CHANGELOG_FILE"; then
        awk '
        /^## \[Unreleased\]/ { in_unreleased = 1; next }
        /^## \[/ && in_unreleased { exit }
        in_unreleased { print }
        ' "$CHANGELOG_FILE"
    else
        log_info "未リリースの変更はありません"
    fi
}

# メイン処理
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        add-entry)
            if [[ $# -ne 2 ]]; then
                log_error "add-entry には TYPE と DESCRIPTION が必要です"
                show_help
                exit 1
            fi
            check_changelog_exists
            create_backup
            add_entry "$1" "$2"
            ;;
        prepare-release)
            if [[ $# -ne 1 ]]; then
                log_error "prepare-release には VERSION が必要です"
                show_help
                exit 1
            fi
            check_changelog_exists
            create_backup
            prepare_release "$1"
            ;;
        validate)
            check_changelog_exists
            validate_changelog
            ;;
        generate-from-commits)
            if [[ $# -ne 2 ]]; then
                log_error "generate-from-commits には FROM と TO が必要です"
                show_help
                exit 1
            fi
            generate_from_commits "$1" "$2"
            ;;
        show-unreleased)
            check_changelog_exists
            show_unreleased
            ;;
        --help|help)
            show_help
            ;;
        *)
            log_error "不明なコマンド: $command"
            show_help
            exit 1
            ;;
    esac
}

# クリーンアップ
cleanup() {
    [[ -f "$TEMP_FILE" ]] && rm -f "$TEMP_FILE"
}

trap cleanup EXIT

# スクリプト実行
main "$@"
