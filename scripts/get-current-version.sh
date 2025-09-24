#!/bin/bash
# 現在のバージョンを取得するスクリプト

set -euo pipefail

# pyproject.tomlから現在のバージョンを取得
get_version_from_pyproject() {
    if [[ -f "pyproject.toml" ]]; then
        grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' | head -n1
    else
        echo "0.0.0"
    fi
}

# main.pyから現在のバージョンを取得
get_version_from_main_py() {
    if [[ -f "main.py" ]]; then
        grep '^__version__ = ' main.py | sed 's/__version__ = "\(.*\)"/\1/' | head -n1
    else
        echo ""
    fi
}

# 最新のGitタグを取得（存在する場合）
get_latest_tag() {
    git tag --sort=-version:refname 2>/dev/null | head -n1 | sed 's/^v//' || echo ""
}

# メイン処理
main() {
    local pyproject_version
    local main_py_version
    local latest_tag
    pyproject_version=$(get_version_from_pyproject)
    main_py_version=$(get_version_from_main_py)
    latest_tag=$(get_latest_tag)

    echo "📦 Current Version Information:"
    echo "  - pyproject.toml: v$pyproject_version"

    if [[ -n "$main_py_version" ]]; then
        echo "  - main.py: v$main_py_version"

        if [[ "$pyproject_version" != "$main_py_version" ]]; then
            echo "  ⚠️  Version mismatch between pyproject.toml and main.py!"
        else
            echo "  ✅ pyproject.toml and main.py are synchronized"
        fi
    else
        echo "  - main.py: Not found or no version defined"
    fi

    if [[ -n "$latest_tag" ]]; then
        echo "  - Latest Git tag: v$latest_tag"

        if [[ "$pyproject_version" != "$latest_tag" ]]; then
            echo "  ⚠️  Version mismatch detected!"
        else
            echo "  ✅ Versions are synchronized"
        fi
    else
        echo "  - Git tags: None found"
        echo "  💡 This will be the first release"
    fi

    # 推奨される次のバージョンを表示
    echo ""
    echo "🚀 Suggested next versions:"
    IFS='.' read -r major minor patch <<< "$pyproject_version"
    echo "  - Patch: v${major}.${minor}.$((patch + 1))"
    echo "  - Minor: v${major}.$((minor + 1)).0"
    echo "  - Major: v$((major + 1)).0.0"
}

# スクリプトが直接実行された場合のみメイン関数を実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
