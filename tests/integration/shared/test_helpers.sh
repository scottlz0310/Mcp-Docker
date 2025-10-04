#!/usr/bin/env bash
# プロジェクトルート取得の共通関数

get_project_root() {
    # gitリポジトリルートを取得（最も信頼性が高い）
    if command -v git >/dev/null 2>&1; then
        git rev-parse --show-toplevel 2>/dev/null && return
    fi

    # フォールバック: pyproject.tomlを探す
    local current="$PWD"
    for _ in {1..10}; do
        if [[ -f "${current}/pyproject.toml" ]]; then
            echo "${current}"
            return
        fi
        [[ "${current}" == "/" ]] && break
        current="$(dirname "${current}")"
    done

    echo "Error: Project root not found" >&2
    return 1
}

# グローバル変数として公開
PROJECT_ROOT="$(get_project_root)"
export PROJECT_ROOT
