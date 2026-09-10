#!/usr/bin/env bats
# 検証対象: シェルスクリプト全般
# 目的: 基本的な構文と動作の確認

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
}

create_docker_mock() {
    local mock_path="$1"
    cat >"$mock_path" <<'EOF'
#!/bin/bash
set -euo pipefail

case "$1" in
    compose)
        printf 'name: test-project\n'
        ;;
    volume)
        printf 'test-volume\n'
        ;;
    run)
        printf 'MSYS_NO_PATHCONV=%s\n' "${MSYS_NO_PATHCONV:-}" >"${DOCKER_MOCK_LOG:?}"
        printf 'arg=%s\n' "$@" >>"${DOCKER_MOCK_LOG}"
        exit "${DOCKER_MOCK_RUN_STATUS:-0}"
        ;;
    *)
        printf 'unexpected docker command: %s\n' "$1" >&2
        exit 2
        ;;
esac
EOF
    chmod +x "$mock_path"
}

create_playwright_pull_mock() {
    local mock_path="$1"
    cat >"$mock_path" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ "${1:-}" != "compose" || "${2:-}" != "pull" || "${3:-}" != "playwright-mcp" ]]; then
    echo "unexpected docker command: $*" >&2
    exit 2
fi

printf 'image=%s\n' "${PLAYWRIGHT_MCP_IMAGE:-}" >>"${DOCKER_MOCK_LOG:?}"

if [[ "${DOCKER_MOCK_PULL_MODE:-main}" == "missing-main" && "${PLAYWRIGHT_MCP_IMAGE:-}" == *":main" ]]; then
    echo "failed to resolve reference \"${PLAYWRIGHT_MCP_IMAGE:-}\": not found" >&2
    exit 1
fi

if [[ "${DOCKER_MOCK_PULL_MODE:-main}" == "error" ]]; then
    echo "Error response from daemon: connection refused" >&2
    exit 42
fi

echo "pulled ${PLAYWRIGHT_MCP_IMAGE:-}"
EOF
    chmod +x "$mock_path"
}

create_playwright_inspect_mock() {
    local mock_path="$1"
    cat >"$mock_path" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ "${1:-}" != "image" || "${2:-}" != "inspect" ]]; then
    echo "unexpected docker command: $*" >&2
    exit 2
fi

printf 'image=%s\n' "${3:-}" >>"${DOCKER_MOCK_LOG:?}"

if [[ "${DOCKER_MOCK_INSPECT_MODE:-missing}" == "error" ]]; then
    echo "Cannot connect to the Docker daemon" >&2
    exit 125
fi

if [[ "${DOCKER_MOCK_INSPECT_IMAGE:-}" == "${3:-}" ]]; then
    echo "inspected ${3:-}"
    exit 0
fi

echo "Error: No such image: ${3:-}" >&2
exit 1
EOF
    chmod +x "$mock_path"
}

@test "health-check.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/health-check.sh" ]
    [ -x "${SCRIPTS_DIR}/health-check.sh" ]
}

@test "health-check.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/health-check.sh"
}

@test "health-check.sh: --helpオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: -hオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: 不明なオプションでエラー終了する" {
    run "${SCRIPTS_DIR}/health-check.sh" --unknown-option
    [ "$status" -eq 1 ]
    [[ "$output" =~ "不明なオプション" ]]
}

@test "health-check.sh: --helpオプションにサービス説明が含まれる" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp-gateway" ]]
}

@test "pull-playwright-main.sh: :main を取得できる場合は main を選択する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    local stderr_log="${BATS_TEST_TMPDIR}/stderr.log"
    create_playwright_pull_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        bash -c 'bash "$1" "$2" "$3" 2>"$4"' _ \
        "${SCRIPTS_DIR}/pull-playwright-main.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest" \
        "$stderr_log"

    [ "$status" -eq 0 ]
    [ "$output" = "mcr.microsoft.com/playwright/mcp:main" ]
    grep -Fx 'image=mcr.microsoft.com/playwright/mcp:main' "$mock_log"
}

@test "pull-playwright-main.sh: :main の manifest 未公開時は latest にフォールバックする" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    local stderr_log="${BATS_TEST_TMPDIR}/stderr.log"
    create_playwright_pull_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_PULL_MODE=missing-main \
        bash -c 'bash "$1" "$2" "$3" 2>"$4"' _ \
        "${SCRIPTS_DIR}/pull-playwright-main.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest" \
        "$stderr_log"

    [ "$status" -eq 0 ]
    [ "$output" = "mcr.microsoft.com/playwright/mcp:latest" ]
    grep -Fx 'image=mcr.microsoft.com/playwright/mcp:main' "$mock_log"
    grep -Fx 'image=mcr.microsoft.com/playwright/mcp:latest' "$mock_log"
    grep -F 'manifest が公開されていない' "$stderr_log"
}

@test "pull-playwright-main.sh: manifest 未公開以外のエラーは伝播する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    local stderr_log="${BATS_TEST_TMPDIR}/stderr.log"
    create_playwright_pull_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_PULL_MODE=error \
        bash -c 'bash "$1" "$2" "$3" 2>"$4"' _ \
        "${SCRIPTS_DIR}/pull-playwright-main.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest" \
        "$stderr_log"

    [ "$status" -eq 42 ]
    [ "$(wc -l <"$mock_log")" -eq 1 ]
    grep -F 'fallback は行いません' "$stderr_log"
}

@test "select-playwright-main-image.sh: ローカルに main があれば main を選択する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_playwright_inspect_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_INSPECT_IMAGE="mcr.microsoft.com/playwright/mcp:main" \
        bash "${SCRIPTS_DIR}/select-playwright-main-image.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest"

    [ "$status" -eq 0 ]
    [ "$output" = "mcr.microsoft.com/playwright/mcp:main" ]
    [ "$(wc -l <"$mock_log")" -eq 1 ]
}

@test "select-playwright-main-image.sh: main がなければローカル fallback を選択する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_playwright_inspect_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_INSPECT_IMAGE="mcr.microsoft.com/playwright/mcp:latest" \
        bash "${SCRIPTS_DIR}/select-playwright-main-image.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest"

    [ "$status" -eq 0 ]
    [ "$output" = "mcr.microsoft.com/playwright/mcp:latest" ]
    [ "$(wc -l <"$mock_log")" -eq 2 ]
}

@test "select-playwright-main-image.sh: Docker daemon エラーは fallback せず伝播する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_playwright_inspect_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_INSPECT_MODE=error \
        bash "${SCRIPTS_DIR}/select-playwright-main-image.sh" \
        "mcr.microsoft.com/playwright/mcp:main" \
        "mcr.microsoft.com/playwright/mcp:latest"

    [ "$status" -eq 125 ]
    [ "$(wc -l <"$mock_log")" -eq 1 ]
}

@test "Makefile: pull-main は Playwright の main/fallback resolver を呼び出す" {
    run make -C "${PROJECT_ROOT}" --dry-run pull-main

    [ "$status" -eq 0 ]
    [[ "$output" == *"pull-playwright-main.sh"* ]]
    [[ "$output" == *"mcr.microsoft.com/playwright/mcp:main"* ]]
}

@test "Makefile: start-main は pull せずローカルイメージ選択を呼び出す" {
    run sed -n '/^start-main:/,/^\.PHONY: restart-main/p' "${PROJECT_ROOT}/Makefile"

    [ "$status" -eq 0 ]
    [[ "$output" == *"select-playwright-main-image.sh"* ]]
    [[ "$output" == *"--pull never"* ]]
    [[ "$output" != *"pull-playwright-main.sh"* ]]
}

@test "health-check.sh: curl_insecure_ok が -k 付与を localhost / 127.0.0.1 に限定する" {
    # スクリプトはトップレベルで即実行されるため、判定関数のみを抽出して読み込む
    source /dev/stdin <<<"$(sed -n '/^curl_insecure_ok()/,/^}/p' "${SCRIPTS_DIR}/health-check.sh")"

    local allow=(
        "https://localhost:8080"
        "https://localhost"
        "https://127.0.0.1:8080"
        "https://127.0.0.1:8080/health"
    )
    local deny=(
        "https://mcp.example.com"
        "https://localhost.evil.com"
        "https://localhost:password@example.com"
        "https://user@localhost:8080"
        "http://localhost:8080"
        "http://127.0.0.1:8080"
    )
    for url in "${allow[@]}"; do
        if ! curl_insecure_ok "$url"; then
            echo "expected -k allowed for: $url"
            return 1
        fi
    done
    for url in "${deny[@]}"; do
        if curl_insecure_ok "$url"; then
            echo "expected -k denied for: $url"
            return 1
        fi
    done
}

@test "Makefile: health-check は Git Bash 経由で credential 診断を実行する" {
    run make -C "${PROJECT_ROOT}" --dry-run health-check SERVICE=review-raven

    [ "$status" -eq 0 ]
    [[ "$output" == *'./scripts/health-check.sh --service "review-raven" --with-api'* ]]
}

@test "Makefile: health-check-quick は credential 診断をスキップする" {
    run make -C "${PROJECT_ROOT}" --dry-run health-check-quick SERVICE=github-mcp

    [ "$status" -eq 0 ]
    [[ "$output" == *'./scripts/health-check.sh --service "github-mcp" --no-api'* ]]
}

@test "lint-shell.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/lint-shell.sh" ]
    [ -x "${SCRIPTS_DIR}/lint-shell.sh" ]
}

@test "lint-shell.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/lint-shell.sh"
}

@test "require-pwsh.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/require-pwsh.sh" ]
    [ -x "${SCRIPTS_DIR}/require-pwsh.sh" ]
}

@test "require-pwsh.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/require-pwsh.sh"
}

@test "require-pwsh.sh: pwsh が PATH にあれば成功する" {
    local bash_bin
    bash_bin="$(command -v bash)"
    local mock_bin="${BATS_TEST_TMPDIR}/bin"
    mkdir -p "$mock_bin"
    printf '#!/usr/bin/env bash\nexit 0\n' > "${mock_bin}/pwsh"
    chmod +x "${mock_bin}/pwsh"

    run env -i PATH="${mock_bin}" "$bash_bin" "${SCRIPTS_DIR}/require-pwsh.sh"

    [ "$status" -eq 0 ]
}

@test "require-pwsh.sh: pwsh が PATH になければ日本語エラーで失敗する" {
    local bash_bin
    bash_bin="$(command -v bash)"
    local empty_path="${BATS_TEST_TMPDIR}/empty-bin"
    mkdir -p "$empty_path"

    run env -i PATH="${empty_path}" "$bash_bin" "${SCRIPTS_DIR}/require-pwsh.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"pwsh (PowerShell 7+) が見つかりません"* ]]
    [[ "$output" == *"winget install --id Microsoft.PowerShell --exact"* ]]
}

@test "rotate-secret.sh: Git Bashのパス変換を無効化して削除を検証する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_docker_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        "${SCRIPTS_DIR}/rotate-secret.sh"

    [ "$status" -eq 0 ]
    grep -Fx 'MSYS_NO_PATHCONV=1' "$mock_log"
    grep -Fx 'arg=test-volume:/data' "$mock_log"
    grep -Fx "arg=rm -f /data/config.yaml && test ! -e /data/config.yaml" "$mock_log"
    [ "$output" = "config.yaml を削除しました (test-volume)" ]
}

@test "rotate-secret.sh: config削除の検証失敗を伝播する" {
    local mock_docker="${BATS_TEST_TMPDIR}/docker"
    local mock_log="${BATS_TEST_TMPDIR}/docker.log"
    create_docker_mock "$mock_docker"

    run env \
        DOCKER_BIN="$mock_docker" \
        DOCKER_MOCK_LOG="$mock_log" \
        DOCKER_MOCK_RUN_STATUS=1 \
        "${SCRIPTS_DIR}/rotate-secret.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"エラー: /data/config.yaml の削除を確認できませんでした (test-volume)"* ]]
    [[ ! "$output" =~ "config.yaml を削除しました" ]]
}

# --- check-skill-revision.sh ---

setup_skill_repo() {
    local repo="$1"
    mkdir -p "${repo}/scripts" "${repo}/skills/alpha"
    cp "${SCRIPTS_DIR}/check-skill-revision.sh" "${repo}/scripts/"
    chmod +x "${repo}/scripts/check-skill-revision.sh"
    cd "${repo}" || return 1
    git init -q -b main
    git config user.email "test@example.com"
    git config user.name "test"
    printf 'v1\n' >skills/alpha/SKILL.md
    printf '{"skills":{"alpha":{"revision":1}}}\n' >skills/catalog.json
    git add -A
    git commit -qm "init"
    git branch base
}

commit_all() {
    git add -A
    git commit -qm "change"
}

@test "check-skill-revision.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/check-skill-revision.sh" ]
    [ -x "${SCRIPTS_DIR}/check-skill-revision.sh" ]
}

@test "check-skill-revision.sh: skill 未変更なら成功する" {
    setup_skill_repo "${BATS_TEST_TMPDIR}/repo"
    printf 'note\n' >README.md
    commit_all

    run bash scripts/check-skill-revision.sh base
    [ "$status" -eq 0 ]
    [[ "$output" == *"変更なし"* ]]
}

@test "check-skill-revision.sh: 内容変更で revision 据え置きなら失敗する" {
    setup_skill_repo "${BATS_TEST_TMPDIR}/repo"
    printf 'v2\n' >skills/alpha/SKILL.md
    commit_all

    run bash scripts/check-skill-revision.sh base
    [ "$status" -eq 1 ]
    [[ "$output" == *"revision が上がっていません"* ]]
}

@test "check-skill-revision.sh: 内容変更で revision を上げれば成功する" {
    setup_skill_repo "${BATS_TEST_TMPDIR}/repo"
    printf 'v2\n' >skills/alpha/SKILL.md
    printf '{"skills":{"alpha":{"revision":2}}}\n' >skills/catalog.json
    commit_all

    run bash scripts/check-skill-revision.sh base
    [ "$status" -eq 0 ]
    [[ "$output" == *"rev 1 → 2"* ]]
}

@test "check-skill-revision.sh: 新規 skill は revision があれば成功する" {
    setup_skill_repo "${BATS_TEST_TMPDIR}/repo"
    mkdir -p skills/beta
    printf 'beta\n' >skills/beta/SKILL.md
    printf '{"skills":{"alpha":{"revision":1},"beta":{"revision":1}}}\n' >skills/catalog.json
    commit_all

    run bash scripts/check-skill-revision.sh base
    [ "$status" -eq 0 ]
    [[ "$output" == *"新規追加"* ]]
}

@test "check-skill-revision.sh: catalog.json に revision が無ければ失敗する" {
    setup_skill_repo "${BATS_TEST_TMPDIR}/repo"
    printf '{"skills":{}}\n' >skills/catalog.json
    commit_all

    run bash scripts/check-skill-revision.sh base
    [ "$status" -eq 1 ]
    [[ "$output" == *"revision がありません"* ]]
}
