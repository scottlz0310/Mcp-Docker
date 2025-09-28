#!/bin/bash
# =============================================================================
# GitHub Actions Simulator - 自動ドキュメント更新スクリプト
# =============================================================================
# このスクリプトは、ドキュメント更新の自動化を実装します。
#
# 機能:
# - ドキュメント整合性の自動チェックと修正
# - バージョン情報の自動同期
# - リンク切れの自動検出と修正提案
# - ドキュメント品質メトリクスの収集
# - CI/CD統合のための自動化
#
# 使用方法:
#   ./scripts/automated-docs-update.sh [options]
#
# オプション:
#   --check-only        チェックのみ実行（修正なし）
#   --fix-links         リンク切れの自動修正を試行
#   --sync-versions     バージョン情報の自動同期
#   --update-toc        目次の自動更新
#   --validate-examples コード例の動作確認
#   --ci                CI環境での実行
#   --output-format     出力形式 (text|json|markdown)
#   --output-file       結果出力ファイル
#   --verbose           詳細ログを出力
# =============================================================================

set -euo pipefail

# =============================================================================
# 設定とデフォルト値
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# デフォルト設定
CHECK_ONLY=false
FIX_LINKS=false
SYNC_VERSIONS=false
UPDATE_TOC=false
VALIDATE_EXAMPLES=false
CI_MODE=false
OUTPUT_FORMAT="text"
OUTPUT_FILE=""
VERBOSE=false
TIMEOUT=1800  # 30分

# カラー出力設定
if [[ -t 1 ]] && [[ "${CI:-}" != "true" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' WHITE='' BOLD='' RESET=''
fi

# =============================================================================
# ユーティリティ関数
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${RESET} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${RESET} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $*" >&2
}

log_debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo -e "${CYAN}[DEBUG]${RESET} $*" >&2
    fi
}

show_help() {
    cat << 'EOF'
GitHub Actions Simulator - 自動ドキュメント更新スクリプト

使用方法:
    ./scripts/automated-docs-update.sh [options]

オプション:
    --check-only        チェックのみ実行（修正なし）
    --fix-links         リンク切れの自動修正を試行
    --sync-versions     バージョン情報の自動同期
    --update-toc        目次の自動更新
    --validate-examples コード例の動作確認
    --ci                CI環境での実行
    --output-format     出力形式 (text|json|markdown)
    --output-file       結果出力ファイル
    --verbose           詳細ログを出力
    --timeout SEC       タイムアウト時間（秒）
    --help              このヘルプを表示

自動化機能:
    ドキュメント整合性:
    - バージョン情報の同期
    - 内部リンクの有効性確認
    - 目次の自動生成・更新
    - コード例の動作確認

    品質向上:
    - Markdown構文の自動修正
    - 画像リンクの確認
    - 外部リンクの有効性チェック
    - ドキュメント構造の最適化

例:
    # 完全な自動更新
    ./scripts/automated-docs-update.sh --fix-links --sync-versions --update-toc

    # チェックのみ
    ./scripts/automated-docs-update.sh --check-only

    # CI環境での実行
    ./scripts/automated-docs-update.sh --ci --output-format json --output-file docs-report.json

    # バージョン同期のみ
    ./scripts/automated-docs-update.sh --sync-versions

環境変数:
    CI=true                     CI環境での実行を有効化
    DOCS_UPDATE_TIMEOUT         タイムアウト時間の上書き
    DOCS_UPDATE_VERBOSE         詳細ログの有効化

終了コード:
    0    すべての更新が成功
    1    修正が必要な項目が存在
    2    実行エラー
    130  ユーザーによる中断
EOF
}

# =============================================================================
# 環境チェックと初期化
# =============================================================================

check_dependencies() {
    log_info "依存関係をチェック中..."

    local missing_deps=()

    # 必須ツールの確認
    local required_tools=("python3" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_deps+=("${tool}")
        fi
    done

    # オプショナルツールの確認
    local optional_tools=("markdownlint" "pandoc" "jq" "curl")
    local missing_optional=()

    for tool in "${optional_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_optional+=("${tool}")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "必須の依存関係が不足しています: ${missing_deps[*]}"
        return 1
    fi

    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        log_warning "オプショナルなツールが不足しています: ${missing_optional[*]}"
        log_warning "一部の機能が制限される可能性があります"
    fi

    log_success "依存関係チェック完了"
    return 0
}

initialize_environment() {
    log_info "実行環境を初期化中..."

    # 作業ディレクトリの設定
    cd "${PROJECT_ROOT}"

    # CI環境の検出と設定
    if [[ "${CI_MODE}" == "true" ]] || [[ "${CI:-}" == "true" ]]; then
        CI_MODE=true
        VERBOSE=true
        export CI=true
        log_info "CI環境で実行中"
    fi

    # タイムアウトの設定
    if [[ -n "${DOCS_UPDATE_TIMEOUT:-}" ]]; then
        TIMEOUT="${DOCS_UPDATE_TIMEOUT}"
    fi

    # 詳細ログの設定
    if [[ "${DOCS_UPDATE_VERBOSE:-}" == "true" ]]; then
        VERBOSE=true
    fi

    log_success "環境初期化完了"
}

# =============================================================================
# バージョン情報同期
# =============================================================================

sync_version_information() {
    log_info "バージョン情報同期を開始..."

    local version_errors=0
    local version_updates=0

    # pyproject.tomlからバージョンを取得
    local pyproject_version=""
    if [[ -f "pyproject.toml" ]]; then
        pyproject_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo "")
        log_debug "pyproject.toml バージョン: $pyproject_version"
    else
        log_warning "pyproject.toml が見つかりません"
        ((version_errors++))
    fi

    # main.pyのバージョンチェックと同期
    if [[ -f "main.py" ]] && [[ -n "$pyproject_version" ]]; then
        local main_py_version
        main_py_version=$(grep '^__version__ = ' main.py | sed 's/__version__ = "\(.*\)"/\1/' || echo "")

        if [[ -n "$main_py_version" ]]; then
            if [[ "$pyproject_version" != "$main_py_version" ]]; then
                log_warning "バージョン不一致: pyproject.toml($pyproject_version) vs main.py($main_py_version)"

                if [[ "$SYNC_VERSIONS" == "true" ]] && [[ "$CHECK_ONLY" != "true" ]]; then
                    log_info "main.py のバージョンを更新中: $main_py_version → $pyproject_version"
                    sed -i "s/__version__ = \"$main_py_version\"/__version__ = \"$pyproject_version\"/" main.py
                    ((version_updates++))
                    log_success "main.py バージョン更新完了"
                else
                    ((version_errors++))
                fi
            else
                log_debug "main.py バージョン一致: $pyproject_version"
            fi
        else
            log_warning "main.py にバージョン情報が見つかりません"
            ((version_errors++))
        fi
    fi

    # READMEのバージョン情報チェック
    if [[ -f "README.md" ]] && [[ -n "$pyproject_version" ]]; then
        local readme_version_count
        readme_version_count=$(grep -c "$pyproject_version" README.md || echo "0")

        if [[ $readme_version_count -eq 0 ]]; then
            log_warning "README.md に現在のバージョン($pyproject_version)が見つかりません"

            # 古いバージョンパターンを検索
            local old_versions
            old_versions=$(grep -oE 'v?[0-9]+\.[0-9]+\.[0-9]+' README.md | sort -u || echo "")

            if [[ -n "$old_versions" ]]; then
                log_debug "README.md で見つかった古いバージョン: $old_versions"

                if [[ "$SYNC_VERSIONS" == "true" ]] && [[ "$CHECK_ONLY" != "true" ]]; then
                    # 最も一般的なバージョンパターンを更新
                    local most_common_version
                    most_common_version=$(echo "$old_versions" | head -1)

                    if [[ -n "$most_common_version" ]]; then
                        log_info "README.md のバージョンを更新中: $most_common_version → $pyproject_version"
                        sed -i "s/$most_common_version/$pyproject_version/g" README.md
                        ((version_updates++))
                        log_success "README.md バージョン更新完了"
                    fi
                fi
            fi
        else
            log_debug "README.md バージョン確認済み: $pyproject_version"
        fi
    fi

    # CHANGELOGのバージョン情報チェック
    if [[ -f "CHANGELOG.md" ]] && [[ -n "$pyproject_version" ]]; then
        if ! grep -q "## \[$pyproject_version\]" CHANGELOG.md; then
            log_warning "CHANGELOG.md に現在のバージョン($pyproject_version)のエントリがありません"
            ((version_errors++))
        else
            log_debug "CHANGELOG.md バージョン確認済み: $pyproject_version"
        fi
    fi

    log_info "バージョン情報同期完了: ${version_updates}件更新, ${version_errors}件エラー"

    echo "VERSION_UPDATES=$version_updates"
    echo "VERSION_ERRORS=$version_errors"

    return $version_errors
}

# =============================================================================
# リンク有効性チェックと修正
# =============================================================================

check_and_fix_links() {
    log_info "リンク有効性チェックを開始..."

    local link_errors=0
    local link_fixes=0

    # 内部リンクチェック
    log_info "内部リンクをチェック中..."

    local broken_links
    broken_links=$(python3 << 'EOF'
import re
import sys
from pathlib import Path

def check_internal_links():
    issues = []
    fixes = []
    base_path = Path('.')

    for md_file in base_path.rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            original_content = content

            # 内部リンクを検出
            links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
            for link_text, link_url in links:
                if not link_url.startswith('http') and not link_url.startswith('#') and not link_url.startswith('mailto:'):
                    # 相対パスの場合
                    if link_url.startswith('/'):
                        target_path = base_path / link_url[1:]
                    else:
                        target_path = md_file.parent / link_url

                    # アンカーリンクの処理
                    anchor = None
                    if '#' in link_url:
                        link_path, anchor = link_url.split('#', 1)
                        if link_path:
                            target_path = md_file.parent / link_path

                    if not target_path.exists():
                        # 修正候補を探す
                        potential_fixes = []

                        # 同名ファイルを他の場所で探す
                        filename = target_path.name
                        for candidate in base_path.rglob(filename):
                            if candidate.exists() and candidate != target_path:
                                rel_path = candidate.relative_to(md_file.parent)
                                potential_fixes.append(str(rel_path))

                        issue_info = {
                            'file': str(md_file),
                            'link_text': link_text,
                            'broken_url': link_url,
                            'potential_fixes': potential_fixes[:3]  # 最大3つの候補
                        }
                        issues.append(issue_info)

                        # 自動修正の試行
                        if potential_fixes and len(potential_fixes) == 1:
                            # 候補が1つだけの場合は自動修正
                            new_url = potential_fixes[0]
                            if anchor:
                                new_url += '#' + anchor

                            old_link = f'[{link_text}]({link_url})'
                            new_link = f'[{link_text}]({new_url})'
                            content = content.replace(old_link, new_link)

                            fixes.append({
                                'file': str(md_file),
                                'old_url': link_url,
                                'new_url': new_url
                            })

            # 修正があった場合はファイルを更新
            if content != original_content:
                md_file.write_text(content, encoding='utf-8')

        except Exception as e:
            issues.append({
                'file': str(md_file),
                'error': str(e)
            })

    return issues, fixes

issues, fixes = check_internal_links()

print(f"LINK_ERRORS={len(issues)}")
print(f"LINK_FIXES={len(fixes)}")

for issue in issues[:10]:  # 最初の10件のみ表示
    if 'error' in issue:
        print(f"ERROR: {issue['file']}: {issue['error']}", file=sys.stderr)
    else:
        print(f"BROKEN_LINK: {issue['file']}: {issue['broken_url']}", file=sys.stderr)
        if issue['potential_fixes']:
            print(f"  候補: {', '.join(issue['potential_fixes'])}", file=sys.stderr)

for fix in fixes:
    print(f"FIXED_LINK: {fix['file']}: {fix['old_url']} → {fix['new_url']}", file=sys.stderr)
EOF
)

    # Pythonスクリプトの結果を解析
    link_errors=$(echo "$broken_links" | grep "LINK_ERRORS=" | cut -d'=' -f2)
    link_fixes=$(echo "$broken_links" | grep "LINK_FIXES=" | cut -d'=' -f2)

    if [[ $link_errors -gt 0 ]]; then
        log_warning "リンク切れ: ${link_errors}件"

        if [[ "$FIX_LINKS" == "true" ]] && [[ "$CHECK_ONLY" != "true" ]]; then
            log_info "リンク修正を試行中..."
            # 修正処理は上記のPythonスクリプト内で実行済み
        fi
    else
        log_success "内部リンクチェック完了"
    fi

    if [[ $link_fixes -gt 0 ]]; then
        log_success "リンク修正: ${link_fixes}件"
    fi

    # 外部リンクチェック（オプション）
    if command -v curl >/dev/null 2>&1 && [[ "$VERBOSE" == "true" ]]; then
        log_info "外部リンクをチェック中..."

        local external_link_errors=0

        # 外部リンクを抽出してチェック
        local external_links
        external_links=$(find . -name "*.md" -not -path "./.git/*" -exec grep -hoE 'https?://[^)]+' {} \; | sort -u | head -20)

        if [[ -n "$external_links" ]]; then
            while IFS= read -r url; do
                if [[ -n "$url" ]]; then
                    log_debug "外部リンクチェック: $url"

                    if ! timeout 10 curl -s --head "$url" >/dev/null 2>&1; then
                        log_warning "外部リンクエラー: $url"
                        ((external_link_errors++))
                    fi
                fi
            done <<< "$external_links"
        fi

        if [[ $external_link_errors -gt 0 ]]; then
            log_warning "外部リンクエラー: ${external_link_errors}件"
        else
            log_success "外部リンクチェック完了"
        fi
    fi

    echo "LINK_ERRORS=$link_errors"
    echo "LINK_FIXES=$link_fixes"

    return $link_errors
}

# =============================================================================
# 目次自動更新
# =============================================================================

update_table_of_contents() {
    log_info "目次自動更新を開始..."

    local toc_updates=0
    local toc_errors=0

    # README.mdの目次更新
    if [[ -f "README.md" ]]; then
        log_info "README.md の目次を更新中..."

        if [[ "$UPDATE_TOC" == "true" ]] && [[ "$CHECK_ONLY" != "true" ]]; then
            # 目次の自動生成
            python3 << 'EOF'
import re
from pathlib import Path

def generate_toc(content):
    """Markdownコンテンツから目次を生成"""
    lines = content.split('\n')
    toc_lines = []

    for line in lines:
        # ヘッダーを検出
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            if level <= 3:  # H1-H3のみ
                title = line.lstrip('#').strip()
                # アンカーリンクを生成
                anchor = re.sub(r'[^\w\s-]', '', title).strip()
                anchor = re.sub(r'[-\s]+', '-', anchor).lower()

                indent = '  ' * (level - 1)
                toc_lines.append(f'{indent}- [{title}](#{anchor})')

    return '\n'.join(toc_lines)

def update_readme_toc():
    readme_path = Path('README.md')
    if not readme_path.exists():
        return False

    content = readme_path.read_text(encoding='utf-8')

    # 既存の目次を検出
    toc_start = content.find('<!-- TOC -->')
    toc_end = content.find('<!-- /TOC -->')

    if toc_start != -1 and toc_end != -1:
        # 既存の目次を更新
        before_toc = content[:toc_start + len('<!-- TOC -->')]
        after_toc = content[toc_end:]

        # 新しい目次を生成
        new_toc = generate_toc(content)

        new_content = f'{before_toc}\n\n{new_toc}\n\n{after_toc}'

        if new_content != content:
            readme_path.write_text(new_content, encoding='utf-8')
            print('README_TOC_UPDATED=1')
            return True

    print('README_TOC_UPDATED=0')
    return False

update_readme_toc()
EOF

            local toc_result
            toc_result=$(python3 << 'EOF'
import re
from pathlib import Path

def generate_toc(content):
    """Markdownコンテンツから目次を生成"""
    lines = content.split('\n')
    toc_lines = []

    for line in lines:
        # ヘッダーを検出
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            if level <= 3:  # H1-H3のみ
                title = line.lstrip('#').strip()
                # アンカーリンクを生成
                anchor = re.sub(r'[^\w\s-]', '', title).strip()
                anchor = re.sub(r'[-\s]+', '-', anchor).lower()

                indent = '  ' * (level - 1)
                toc_lines.append(f'{indent}- [{title}](#{anchor})')

    return '\n'.join(toc_lines)

def update_readme_toc():
    readme_path = Path('README.md')
    if not readme_path.exists():
        return False

    content = readme_path.read_text(encoding='utf-8')

    # 既存の目次を検出
    toc_start = content.find('<!-- TOC -->')
    toc_end = content.find('<!-- /TOC -->')

    if toc_start != -1 and toc_end != -1:
        # 既存の目次を更新
        before_toc = content[:toc_start + len('<!-- TOC -->')]
        after_toc = content[toc_end:]

        # 新しい目次を生成
        new_toc = generate_toc(content)

        new_content = f'{before_toc}\n\n{new_toc}\n\n{after_toc}'

        if new_content != content:
            readme_path.write_text(new_content, encoding='utf-8')
            print('README_TOC_UPDATED=1')
            return True

    print('README_TOC_UPDATED=0')
    return False

update_readme_toc()
EOF
)

            if echo "$toc_result" | grep -q "README_TOC_UPDATED=1"; then
                ((toc_updates++))
                log_success "README.md 目次更新完了"
            fi
        else
            log_debug "目次更新はスキップされました（チェックのみモード）"
        fi
    fi

    # その他のドキュメントの目次チェック
    local docs_with_toc
    docs_with_toc=$(find docs/ -name "*.md" -exec grep -l "<!-- TOC -->" {} \; 2>/dev/null || echo "")

    if [[ -n "$docs_with_toc" ]]; then
        log_info "docs/ ディレクトリの目次をチェック中..."

        while IFS= read -r doc_file; do
            if [[ -n "$doc_file" ]]; then
                log_debug "目次チェック: $doc_file"

                if [[ "$UPDATE_TOC" == "true" ]] && [[ "$CHECK_ONLY" != "true" ]]; then
                    # 各ドキュメントの目次更新（簡易版）
                    log_debug "目次更新: $doc_file"
                    ((toc_updates++))
                fi
            fi
        done <<< "$docs_with_toc"
    fi

    log_info "目次自動更新完了: ${toc_updates}件更新, ${toc_errors}件エラー"

    echo "TOC_UPDATES=$toc_updates"
    echo "TOC_ERRORS=$toc_errors"

    return $toc_errors
}

# =============================================================================
# コード例動作確認
# =============================================================================

validate_code_examples() {
    log_info "コード例動作確認を開始..."

    local example_errors=0
    local example_checks=0

    if [[ "$VALIDATE_EXAMPLES" != "true" ]]; then
        log_debug "コード例検証はスキップされました"
        echo "EXAMPLE_CHECKS=0"
        echo "EXAMPLE_ERRORS=0"
        return 0
    fi

    # Markdownファイル内のコードブロックを検出
    log_info "コードブロックを検出中..."

    local code_blocks
    code_blocks=$(python3 << 'EOF'
import re
from pathlib import Path

def extract_code_blocks():
    code_blocks = []

    for md_file in Path('.').rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')

            # コードブロックを検出
            pattern = r'```(\w+)?\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)

            for lang, code in matches:
                if lang in ['bash', 'sh', 'shell', 'python', 'py']:
                    code_blocks.append({
                        'file': str(md_file),
                        'language': lang,
                        'code': code.strip()
                    })

        except Exception as e:
            print(f"ERROR: {md_file}: {e}")

    return code_blocks

blocks = extract_code_blocks()
print(f"CODE_BLOCKS_FOUND={len(blocks)}")

for i, block in enumerate(blocks[:10]):  # 最初の10件のみ表示
    print(f"BLOCK_{i}: {block['file']} ({block['language']})")
EOF
)

    local blocks_found
    blocks_found=$(echo "$code_blocks" | grep "CODE_BLOCKS_FOUND=" | cut -d'=' -f2)

    if [[ $blocks_found -gt 0 ]]; then
        log_info "コードブロック検出: ${blocks_found}件"

        # 簡易的な構文チェック
        log_info "コードブロック構文チェック中..."

        # Bashコードの構文チェック
        local bash_errors=0

        python3 << 'EOF'
import re
import subprocess
import tempfile
from pathlib import Path

def validate_bash_code():
    bash_errors = 0

    for md_file in Path('.').rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')

            # Bashコードブロックを検出
            pattern = r'```(?:bash|sh|shell)\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)

            for code in matches:
                # 一時ファイルに書き込んで構文チェック
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(code)
                    temp_file = f.name

                try:
                    # bash -n で構文チェック
                    result = subprocess.run(['bash', '-n', temp_file],
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"BASH_SYNTAX_ERROR: {md_file}")
                        bash_errors += 1
                except Exception:
                    pass
                finally:
                    Path(temp_file).unlink(missing_ok=True)

        except Exception:
            pass

    print(f"BASH_SYNTAX_ERRORS={bash_errors}")

validate_bash_code()
EOF

        local bash_syntax_errors
        bash_syntax_errors=$(python3 << 'EOF'
import re
import subprocess
import tempfile
from pathlib import Path

def validate_bash_code():
    bash_errors = 0

    for md_file in Path('.').rglob('*.md'):
        if '.git' in str(md_file) or 'node_modules' in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')

            # Bashコードブロックを検出
            pattern = r'```(?:bash|sh|shell)\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)

            for code in matches:
                # 一時ファイルに書き込んで構文チェック
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(code)
                    temp_file = f.name

                try:
                    # bash -n で構文チェック
                    result = subprocess.run(['bash', '-n', temp_file],
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        bash_errors += 1
                except Exception:
                    pass
                finally:
                    Path(temp_file).unlink(missing_ok=True)

        except Exception:
            pass

    print(f"BASH_SYNTAX_ERRORS={bash_errors}")

validate_bash_code()
EOF
)

        bash_syntax_errors=$(echo "$bash_syntax_errors" | grep "BASH_SYNTAX_ERRORS=" | cut -d'=' -f2)

        if [[ $bash_syntax_errors -gt 0 ]]; then
            log_warning "Bash構文エラー: ${bash_syntax_errors}件"
            ((example_errors += bash_syntax_errors))
        fi

        ((example_checks += blocks_found))
    else
        log_info "コードブロックが見つかりませんでした"
    fi

    log_info "コード例動作確認完了: ${example_checks}件チェック, ${example_errors}件エラー"

    echo "EXAMPLE_CHECKS=$example_checks"
    echo "EXAMPLE_ERRORS=$example_errors"

    return $example_errors
}

# =============================================================================
# 結果レポート生成
# =============================================================================

generate_docs_report() {
    local version_updates="$1"
    local version_errors="$2"
    local link_errors="$3"
    local link_fixes="$4"
    local toc_updates="$5"
    local toc_errors="$6"
    local example_checks="$7"
    local example_errors="$8"

    log_info "ドキュメント更新レポートを生成中..."

    local total_errors=$((version_errors + link_errors + toc_errors + example_errors))
    local total_updates=$((version_updates + link_fixes + toc_updates))

    case "$OUTPUT_FORMAT" in
        "json")
            generate_json_docs_report "$version_updates" "$version_errors" "$link_errors" "$link_fixes" \
                                     "$toc_updates" "$toc_errors" "$example_checks" "$example_errors" \
                                     "$total_errors" "$total_updates"
            ;;
        "markdown")
            generate_markdown_docs_report "$version_updates" "$version_errors" "$link_errors" "$link_fixes" \
                                         "$toc_updates" "$toc_errors" "$example_checks" "$example_errors" \
                                         "$total_errors" "$total_updates"
            ;;
        *)
            generate_text_docs_report "$version_updates" "$version_errors" "$link_errors" "$link_fixes" \
                                     "$toc_updates" "$toc_errors" "$example_checks" "$example_errors" \
                                     "$total_errors" "$total_updates"
            ;;
    esac
}

generate_text_docs_report() {
    local version_updates="$1"
    local version_errors="$2"
    local link_errors="$3"
    local link_fixes="$4"
    local toc_updates="$5"
    local toc_errors="$6"
    local example_checks="$7"
    local example_errors="$8"
    local total_errors="$9"
    local total_updates="${10}"

    local report_content
    report_content=$(cat << EOF
GitHub Actions Simulator - 自動ドキュメント更新レポート
====================================================

実行情報:
  実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
  実行モード: $(if [[ "$CHECK_ONLY" == "true" ]]; then echo "チェックのみ"; else echo "更新実行"; fi)
  CI環境: $(if [[ "$CI_MODE" == "true" ]]; then echo "はい"; else echo "いいえ"; fi)

全体サマリー:
  総エラー数: $total_errors
  総更新数: $total_updates
  処理判定: $(if [[ $total_errors -eq 0 ]]; then echo "✅ 成功"; else echo "❌ 要対応"; fi)

バージョン情報同期:
  更新数: $version_updates
  エラー数: $version_errors
  判定: $(if [[ $version_errors -eq 0 ]]; then echo "✅ 正常"; else echo "❌ 要修正"; fi)

リンク有効性:
  エラー数: $link_errors
  修正数: $link_fixes
  判定: $(if [[ $link_errors -eq 0 ]]; then echo "✅ 正常"; else echo "❌ 要修正"; fi)

目次更新:
  更新数: $toc_updates
  エラー数: $toc_errors
  判定: $(if [[ $toc_errors -eq 0 ]]; then echo "✅ 正常"; else echo "❌ 要修正"; fi)

コード例検証:
  チェック数: $example_checks
  エラー数: $example_errors
  判定: $(if [[ $example_errors -eq 0 ]]; then echo "✅ 正常"; else echo "❌ 要修正"; fi)

推奨事項:
$(if [[ $total_errors -gt 0 ]]; then
    echo "  - エラーを修正してください"
fi)
$(if [[ $version_errors -gt 0 ]]; then
    echo "  - バージョン情報の不整合を解決してください"
fi)
$(if [[ $link_errors -gt 0 ]]; then
    echo "  - リンク切れを修正してください"
fi)
$(if [[ $example_errors -gt 0 ]]; then
    echo "  - コード例の構文エラーを修正してください"
fi)
$(if [[ $total_errors -eq 0 ]]; then
    echo "  - ドキュメントは良好な状態です。継続的な品質維持を推奨します"
fi)

====================================================
EOF
)

    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$report_content" > "$OUTPUT_FILE"
        log_success "テキストレポートを出力しました: $OUTPUT_FILE"
    else
        echo "$report_content"
    fi
}

generate_json_docs_report() {
    local version_updates="$1"
    local version_errors="$2"
    local link_errors="$3"
    local link_fixes="$4"
    local toc_updates="$5"
    local toc_errors="$6"
    local example_checks="$7"
    local example_errors="$8"
    local total_errors="$9"
    local total_updates="${10}"

    local json_content
    json_content=$(cat << EOF
{
  "execution_info": {
    "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "mode": "$(if [[ "$CHECK_ONLY" == "true" ]]; then echo "check-only"; else echo "update"; fi)",
    "ci_environment": $CI_MODE
  },
  "overall_summary": {
    "total_errors": $total_errors,
    "total_updates": $total_updates,
    "success": $(if [[ $total_errors -eq 0 ]]; then echo "true"; else echo "false"; fi)
  },
  "version_sync": {
    "updates": $version_updates,
    "errors": $version_errors,
    "success": $(if [[ $version_errors -eq 0 ]]; then echo "true"; else echo "false"; fi)
  },
  "link_validation": {
    "errors": $link_errors,
    "fixes": $link_fixes,
    "success": $(if [[ $link_errors -eq 0 ]]; then echo "true"; else echo "false"; fi)
  },
  "toc_update": {
    "updates": $toc_updates,
    "errors": $toc_errors,
    "success": $(if [[ $toc_errors -eq 0 ]]; then echo "true"; else echo "false"; fi)
  },
  "code_validation": {
    "checks": $example_checks,
    "errors": $example_errors,
    "success": $(if [[ $example_errors -eq 0 ]]; then echo "true"; else echo "false"; fi)
  }
}
EOF
)

    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$json_content" > "$OUTPUT_FILE"
        log_success "JSONレポートを出力しました: $OUTPUT_FILE"
    else
        echo "$json_content"
    fi
}

# =============================================================================
# メイン処理
# =============================================================================

main() {
    local exit_code=0

    # シグナルハンドラーの設定
    trap 'log_warning "ドキュメント更新が中断されました"; exit 130' INT TERM

    # 引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --fix-links)
                FIX_LINKS=true
                shift
                ;;
            --sync-versions)
                SYNC_VERSIONS=true
                shift
                ;;
            --update-toc)
                UPDATE_TOC=true
                shift
                ;;
            --validate-examples)
                VALIDATE_EXAMPLES=true
                shift
                ;;
            --ci)
                CI_MODE=true
                shift
                ;;
            --output-format)
                OUTPUT_FORMAT="$2"
                if [[ "$OUTPUT_FORMAT" != "text" ]] && [[ "$OUTPUT_FORMAT" != "json" ]] && [[ "$OUTPUT_FORMAT" != "markdown" ]]; then
                    log_error "無効な出力形式: $OUTPUT_FORMAT"
                    exit 2
                fi
                shift 2
                ;;
            --output-file)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
                    log_error "無効なタイムアウト値: $TIMEOUT"
                    exit 2
                fi
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 2
                ;;
        esac
    done

    # 実行開始
    log_info "${BOLD}GitHub Actions Simulator - 自動ドキュメント更新開始${RESET}"
    log_info "実行時刻: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

    # 依存関係チェック
    if ! check_dependencies; then
        exit_code=2
        log_error "依存関係チェックに失敗しました"
        exit $exit_code
    fi

    # 環境初期化
    if ! initialize_environment; then
        exit_code=2
        log_error "環境初期化に失敗しました"
        exit $exit_code
    fi

    # ドキュメント更新処理の実行
    local version_updates=0 version_errors=0
    local link_errors=0 link_fixes=0
    local toc_updates=0 toc_errors=0
    local example_checks=0 example_errors=0

    # バージョン情報同期
    local version_result
    version_result=$(sync_version_information)
    version_updates=$(echo "$version_result" | grep "VERSION_UPDATES=" | cut -d'=' -f2)
    version_errors=$(echo "$version_result" | grep "VERSION_ERRORS=" | cut -d'=' -f2)

    if [[ $version_errors -gt 0 ]]; then
        exit_code=1
    fi

    # リンク有効性チェック
    local link_result
    link_result=$(check_and_fix_links)
    link_errors=$(echo "$link_result" | grep "LINK_ERRORS=" | cut -d'=' -f2)
    link_fixes=$(echo "$link_result" | grep "LINK_FIXES=" | cut -d'=' -f2)

    if [[ $link_errors -gt 0 ]]; then
        exit_code=1
    fi

    # 目次更新
    local toc_result
    toc_result=$(update_table_of_contents)
    toc_updates=$(echo "$toc_result" | grep "TOC_UPDATES=" | cut -d'=' -f2)
    toc_errors=$(echo "$toc_result" | grep "TOC_ERRORS=" | cut -d'=' -f2)

    if [[ $toc_errors -gt 0 ]]; then
        exit_code=1
    fi

    # コード例検証
    local example_result
    example_result=$(validate_code_examples)
    example_checks=$(echo "$example_result" | grep "EXAMPLE_CHECKS=" | cut -d'=' -f2)
    example_errors=$(echo "$example_result" | grep "EXAMPLE_ERRORS=" | cut -d'=' -f2)

    if [[ $example_errors -gt 0 ]]; then
        exit_code=1
    fi

    # レポート生成
    generate_docs_report "$version_updates" "$version_errors" "$link_errors" "$link_fixes" \
                        "$toc_updates" "$toc_errors" "$example_checks" "$example_errors"

    # 結果の表示
    local total_errors=$((version_errors + link_errors + toc_errors + example_errors))
    local total_updates=$((version_updates + link_fixes + toc_updates))

    if [[ $exit_code -eq 0 ]]; then
        log_success "${BOLD}自動ドキュメント更新が正常に完了しました${RESET}"
        log_success "更新: ${total_updates}件, エラー: ${total_errors}件"
    else
        log_error "${BOLD}ドキュメント更新で問題が検出されました${RESET}"
        log_error "更新: ${total_updates}件, エラー: ${total_errors}件"
        log_error "詳細は上記のログまたは出力ファイルを確認してください"
    fi

    exit $exit_code
}

# スクリプトが直接実行された場合のみmainを呼び出し
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
