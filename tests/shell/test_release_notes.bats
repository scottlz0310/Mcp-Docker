#!/usr/bin/env bats

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPT="${PROJECT_ROOT}/scripts/generate-release-notes.sh"
}

@test "generate-release-notes.sh: CHANGELOG の対象バージョンからリリースノートを生成する" {
    local changelog="${BATS_TEST_TMPDIR}/CHANGELOG.md"
    local output="${BATS_TEST_TMPDIR}/release-notes.md"
    local source_sha="0123456789abcdef0123456789abcdef01234567"

    printf '%s\n' \
        '# Changelog' \
        '' \
        '## [1.2.3] - 2026-09-11' \
        '' \
        '### 改善' \
        '' \
        '- リリースノートを整形' \
        '' \
        '## [1.2.2] - 2026-09-01' \
        '' \
        '- 古い変更' >"$changelog"

    run bash "$SCRIPT" v1.2.3 "$source_sha" scottlz0310/Mcp-Docker "$changelog" "$output"

    [ "$status" -eq 0 ]
    [ -f "$output" ]
    run grep -F -- '- リリースノートを整形' "$output"
    [ "$status" -eq 0 ]
    run grep -F -- 'go install github.com/scottlz0310/mcp-docker/v2/cmd/mcp-docker@v1.2.3' "$output"
    [ "$status" -eq 0 ]
    run grep -F -- '- 古い変更' "$output"
    [ "$status" -eq 1 ]
}

@test "generate-release-notes.sh: CHANGELOG に対象バージョンがなければ失敗する" {
    local changelog="${BATS_TEST_TMPDIR}/CHANGELOG.md"
    local output="${BATS_TEST_TMPDIR}/release-notes.md"
    printf '%s\n' '# Changelog' >"$changelog"

    run bash "$SCRIPT" v1.2.3 0123456789abcdef0123456789abcdef01234567 scottlz0310/Mcp-Docker "$changelog" "$output"

    [ "$status" -eq 1 ]
    [[ "$output" == *"awk"* || "$output" == *"失敗"* ]]
}

@test "generate-release-notes.sh: リリースタグの形式を検証する" {
    local changelog="${BATS_TEST_TMPDIR}/CHANGELOG.md"
    local output="${BATS_TEST_TMPDIR}/release-notes.md"
    printf '%s\n' '## [1.2.3] - 2026-09-11' '- change' >"$changelog"

    run bash "$SCRIPT" release-1.2.3 0123456789abcdef0123456789abcdef01234567 scottlz0310/Mcp-Docker "$changelog" "$output"

    [ "$status" -eq 1 ]
    [[ "$output" == *"不正なリリースタグ"* ]]
}
