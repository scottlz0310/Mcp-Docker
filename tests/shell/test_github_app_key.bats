#!/usr/bin/env bats
# 検証対象: GitHub App の秘密鍵（PEM → 環境変数 GITHUB_APP_PRIVATE_KEY_B64）に関するもの
#   scripts/github-app-key-b64.sh / scripts/verify-github-app-key.sh / Makefile / docker-compose.yml
# 目的: 値を画面に出さず、PEM と注入済みの環境変数が一致することを検証できること

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
    export PEM="${BATS_TEST_TMPDIR}/key.pem"
    export CLIP_MOCK_OUT="${BATS_TEST_TMPDIR}/clip.out"
    export CLIP_MOCK_ARGS="${BATS_TEST_TMPDIR}/clip.args"
    make_pem "$PEM" A
}

# 秘密鍵に見える、ダミーの PEM を作る（鍵として有効な値ではない）。
# ヘッダーは、リポジトリスキャン（Trivy）に誤検知されないよう、組み立てて出力する。
make_pem() {
    local path="$1" fill="$2"
    {
        printf -- '-----BEGIN %s-----\n' 'PRIVATE KEY'
        for _ in 1 2 3 4 5; do
            printf '%64s\n' '' | tr ' ' "$fill"
        done
        printf -- '-----END %s-----\n' 'PRIVATE KEY'
    } >"$path"
}

# クリップボードのコマンドのモック。標準入力を CLIP_MOCK_OUT へ、引数を CLIP_MOCK_ARGS へ書く。
create_clip_mock() {
    local mock_path="$1"
    cat >"$mock_path" <<'EOF'
#!/bin/bash
set -euo pipefail
cat >"${CLIP_MOCK_OUT:?}"
printf '%s\n' "$@" >"${CLIP_MOCK_ARGS:?}"
exit "${CLIP_MOCK_STATUS:-0}"
EOF
    chmod +x "$mock_path"
}

# 古い macOS の base64 のスタブ。復号は -D だけを受け付け、-d は認識しない。それ以外は、本物の base64 へ渡す。
create_old_macos_base64_stub() {
    local dir="$1" real
    real=$(command -v base64)
    mkdir -p "$dir"
    cat >"${dir}/base64" <<EOF
#!/bin/bash
case "\${1:-}" in
    -d|--decode)
        echo "base64: invalid option -- d" >&2
        exit 1
        ;;
    -D)
        shift
        exec "${real}" -d "\$@"
        ;;
    *)
        exec "${real}" "\$@"
        ;;
esac
EOF
    chmod +x "${dir}/base64"
}

# --- github-app-key-b64.sh ---

@test "github-app-key-b64.sh: スクリプトが存在し実行可能で、構文エラーがない" {
    [ -x "${SCRIPTS_DIR}/github-app-key-b64.sh" ]
    run bash -n "${SCRIPTS_DIR}/github-app-key-b64.sh"
    [ "$status" -eq 0 ]
}

@test "github-app-key-b64.sh: PEM を単一行の base64 にして、クリップボードのコマンドへ標準入力で渡す" {
    local clip="${BATS_TEST_TMPDIR}/clip"
    create_clip_mock "$clip"

    run env CLIP_CMD="$clip --flag" "${SCRIPTS_DIR}/github-app-key-b64.sh" "$PEM"

    [ "$status" -eq 0 ]
    # 単一行（改行を含まず、末尾の改行もない）で、復号すると元の PEM に戻る
    [ "$(wc -l <"$CLIP_MOCK_OUT" | tr -d '[:space:]')" -eq 0 ]
    base64 -d <"$CLIP_MOCK_OUT" | cmp - "$PEM"
    # CLIP_CMD の引数が渡る。値は引数に載らない
    [ "$(cat "$CLIP_MOCK_ARGS")" = "--flag" ]
    # 出力は長さだけで、値を含まない
    local length
    length=$(wc -c <"$CLIP_MOCK_OUT" | tr -d '[:space:]')
    [[ "$output" == *"base64 の長さ ${length} 文字"* ]]
    [[ "$output" != *"$(cat "$CLIP_MOCK_OUT")"* ]]
}

@test "github-app-key-b64.sh: 不正な入力は、原因を示して失敗し、クリップボードへ書き込まない" {
    local clip="${BATS_TEST_TMPDIR}/clip"
    create_clip_mock "$clip"
    local not_pem="${BATS_TEST_TMPDIR}/not-pem.txt"
    printf 'hello\n' >"$not_pem"

    # 名前|期待する終了コード|期待するメッセージ|引数
    local cases=(
        "引数なし|2|使い方|"
        "引数が 2 個|2|使い方|${PEM} ${PEM}"
        "存在しないファイル|1|PEM を読み取れません|${BATS_TEST_TMPDIR}/missing.pem"
        "PEM ではないファイル|1|秘密鍵の PEM ではありません|${not_pem}"
    )
    local entry name want_status want_message args
    for entry in "${cases[@]}"; do
        IFS='|' read -r name want_status want_message args <<<"$entry"
        rm -f "$CLIP_MOCK_OUT"

        # shellcheck disable=SC2086  # 引数は、空白で分割して渡す
        run env CLIP_CMD="$clip" "${SCRIPTS_DIR}/github-app-key-b64.sh" $args

        [ "$status" -eq "$want_status" ] || { echo "ケース「${name}」: 終了コード ${status}（期待 ${want_status}）: ${output}" >&2; return 1; }
        [[ "$output" == *"$want_message"* ]] || { echo "ケース「${name}」: メッセージに「${want_message}」がない: ${output}" >&2; return 1; }
        [ ! -e "$CLIP_MOCK_OUT" ] || { echo "ケース「${name}」: クリップボードへ書き込まれた" >&2; return 1; }
    done
}

@test "github-app-key-b64.sh: クリップボードのコマンドが見つからなければ、CLIP_CMD の指定を案内して失敗する" {
    # 必要なコマンドだけを置いた PATH で実行し、clip.exe / pbcopy / wl-copy / xclip / xsel を見つからなくする
    local stub="${BATS_TEST_TMPDIR}/stub-bin" tool
    mkdir -p "$stub"
    for tool in grep base64 tr; do
        ln -s "$(command -v "$tool")" "${stub}/${tool}"
    done

    run env -u CLIP_CMD PATH="$stub" "$(command -v bash)" "${SCRIPTS_DIR}/github-app-key-b64.sh" "$PEM"

    [ "$status" -eq 1 ]
    [[ "$output" == *"クリップボードのコマンドが見つかりません"* ]]
    [[ "$output" == *"CLIP_CMD"* ]]
}

@test "github-app-key-b64.sh: クリップボードへの書き込み失敗を伝播する" {
    local clip="${BATS_TEST_TMPDIR}/clip"
    create_clip_mock "$clip"

    run env CLIP_CMD="$clip" CLIP_MOCK_STATUS=3 "${SCRIPTS_DIR}/github-app-key-b64.sh" "$PEM"

    [ "$status" -eq 1 ]
    [[ "$output" == *"クリップボードへの書き込みに失敗しました"* ]]
    [[ "$output" != *"コピーしました"* ]]
}

# --- verify-github-app-key.sh ---

@test "verify-github-app-key.sh: スクリプトが存在し実行可能で、構文エラーがない" {
    [ -x "${SCRIPTS_DIR}/verify-github-app-key.sh" ]
    run bash -n "${SCRIPTS_DIR}/verify-github-app-key.sh"
    [ "$status" -eq 0 ]
}

@test "verify-github-app-key.sh: 注入済みの値が PEM と一致すれば成功し、値は出力しない" {
    local b64
    b64=$(base64 <"$PEM" | tr -d '\r\n')

    run env GITHUB_APP_PRIVATE_KEY_B64="$b64" "${SCRIPTS_DIR}/verify-github-app-key.sh" "$PEM"

    [ "$status" -eq 0 ]
    [[ "$output" == *"一致しました"* ]]
    [[ "$output" == *"base64 の長さ ${#b64} 文字"* ]]
    [[ "$output" == *"復号後 $(wc -c <"$PEM" | tr -d '[:space:]') バイト"* ]]
    [[ "$output" != *"$b64"* ]]
}

@test "verify-github-app-key.sh: 一致しない・復号できない・未設定・引数の誤りは、原因を示して失敗する" {
    local other="${BATS_TEST_TMPDIR}/other.pem"
    make_pem "$other" B
    local b64_other b64_pem
    b64_other=$(base64 <"$other" | tr -d '\r\n')
    b64_pem=$(base64 <"$PEM" | tr -d '\r\n')

    # 名前|期待する終了コード|期待するメッセージ|GITHUB_APP_PRIVATE_KEY_B64 の値（空は未設定）|引数
    local cases=(
        "別の PEM の値|1|PEM と一致しません|${b64_other}|${PEM}"
        "base64 ではない値|1|base64 として復号できません|!!!not base64!!!|${PEM}"
        "未設定|1|GITHUB_APP_PRIVATE_KEY_B64 が未設定です||${PEM}"
        "存在しない PEM|1|PEM を読み取れません|${b64_pem}|${BATS_TEST_TMPDIR}/missing.pem"
        "引数なし|2|使い方|${b64_pem}|"
    )
    local entry name want_status want_message value args
    for entry in "${cases[@]}"; do
        IFS='|' read -r name want_status want_message value args <<<"$entry"

        if [ -n "$value" ]; then
            # shellcheck disable=SC2086  # 引数は、空白で分割して渡す
            run env GITHUB_APP_PRIVATE_KEY_B64="$value" "${SCRIPTS_DIR}/verify-github-app-key.sh" $args
        else
            # shellcheck disable=SC2086
            run env -u GITHUB_APP_PRIVATE_KEY_B64 "${SCRIPTS_DIR}/verify-github-app-key.sh" $args
        fi

        [ "$status" -eq "$want_status" ] || { echo "ケース「${name}」: 終了コード ${status}（期待 ${want_status}）: ${output}" >&2; return 1; }
        [[ "$output" == *"$want_message"* ]] || { echo "ケース「${name}」: メッセージに「${want_message}」がない: ${output}" >&2; return 1; }
        [[ "$output" != *"$b64_other"* && "$output" != *"$b64_pem"* ]] || { echo "ケース「${name}」: 出力に鍵の値が含まれる" >&2; return 1; }
    done
}

@test "verify-github-app-key.sh: base64 の復号オプションが -d の環境（GNU・新しい macOS）でも -D だけの環境（古い macOS）でも、同じ結果になる" {
    local other="${BATS_TEST_TMPDIR}/other.pem"
    make_pem "$other" B
    local b64_pem b64_other
    b64_pem=$(base64 <"$PEM" | tr -d '\r\n')
    b64_other=$(base64 <"$other" | tr -d '\r\n')

    local macos_stub="${BATS_TEST_TMPDIR}/old-macos-bin"
    create_old_macos_base64_stub "$macos_stub"

    # スタブが、-d を拒否して -D だけを受け付けること（テストの前提）
    run env PATH="${macos_stub}:${PATH}" bash -c "printf 'QQ==' | base64 -d"
    [ "$status" -ne 0 ]
    run env PATH="${macos_stub}:${PATH}" bash -c "printf 'QQ==' | base64 -D"
    [ "$status" -eq 0 ]

    # 環境の名前|PATH の先頭に足すディレクトリ（空は、そのまま）
    local variants=(
        "-d の環境（GNU・新しい macOS）|"
        "-D だけの環境（古い macOS）|${macos_stub}"
    )
    # 名前|期待する終了コード|期待するメッセージ|GITHUB_APP_PRIVATE_KEY_B64 の値
    local cases=(
        "一致|0|一致しました|${b64_pem}"
        "別の PEM の値|1|PEM と一致しません|${b64_other}"
        "base64 ではない値|1|base64 として復号できません|!!!not base64!!!"
    )
    local variant variant_name variant_dir entry name want_status want_message value
    for variant in "${variants[@]}"; do
        IFS='|' read -r variant_name variant_dir <<<"$variant"
        for entry in "${cases[@]}"; do
            IFS='|' read -r name want_status want_message value <<<"$entry"

            run env PATH="${variant_dir:+${variant_dir}:}${PATH}" GITHUB_APP_PRIVATE_KEY_B64="$value" "${SCRIPTS_DIR}/verify-github-app-key.sh" "$PEM"

            [ "$status" -eq "$want_status" ] || { echo "${variant_name} / ${name}: 終了コード ${status}（期待 ${want_status}）: ${output}" >&2; return 1; }
            [[ "$output" == *"$want_message"* ]] || { echo "${variant_name} / ${name}: メッセージに「${want_message}」がない: ${output}" >&2; return 1; }
        done
    done
}

@test "github-app-key-b64.sh と verify-github-app-key.sh: 作った値を、そのまま検証できる" {
    local clip="${BATS_TEST_TMPDIR}/clip"
    create_clip_mock "$clip"

    run env CLIP_CMD="$clip" "${SCRIPTS_DIR}/github-app-key-b64.sh" "$PEM"
    [ "$status" -eq 0 ]

    run env GITHUB_APP_PRIVATE_KEY_B64="$(cat "$CLIP_MOCK_OUT")" "${SCRIPTS_DIR}/verify-github-app-key.sh" "$PEM"
    [ "$status" -eq 0 ]
    [[ "$output" == *"一致しました"* ]]
}

# --- Makefile ---

# check-github-app-config 以外の必須項目を満たした環境で、make を実行する（dry-run でも $(error) は評価される）
run_check_config() {
    run env -u GITHUB_APP_PRIVATE_KEY_B64 \
        OAUTH_CLIENT_ID=id OAUTH_CLIENT_SECRET=secret \
        GITHUB_APP_ID=1 GITHUB_APP_INSTALLATION_ID=1 \
        MCP_GATEWAY_INTERNAL_SECRET=internal-secret \
        "$@"
}

@test "Makefile: check-github-app-config は GITHUB_APP_PRIVATE_KEY_B64 が未設定なら、作り方を示して失敗する" {
    run_check_config make -C "${PROJECT_ROOT}" --dry-run check-github-app-config

    [ "$status" -ne 0 ]
    [[ "$output" == *"GITHUB_APP_PRIVATE_KEY_B64 is required"* ]]
    [[ "$output" == *"make github-app-key-b64"* ]]
    [[ "$output" == *"dsx-env"* ]]
}

@test "Makefile: check-github-app-config は GITHUB_APP_PRIVATE_KEY_B64 があれば、PEM のファイルが無くても成功する" {
    run env GITHUB_APP_PRIVATE_KEY_B64=dummy \
        OAUTH_CLIENT_ID=id OAUTH_CLIENT_SECRET=secret \
        GITHUB_APP_ID=1 GITHUB_APP_INSTALLATION_ID=1 \
        MCP_GATEWAY_INTERNAL_SECRET=internal-secret \
        make -C "${PROJECT_ROOT}" --dry-run check-github-app-config

    [ "$status" -eq 0 ]
    [[ "$output" != *"private-key.pem"* ]]
}

@test "Makefile: GITHUB_APP_PRIVATE_KEY_B64 は .env から読まない（秘密を .env に置かない）" {
    # .env にだけ値がある状態を、一時ディレクトリで再現する（リポジトリの .env には触れない）
    local work="${BATS_TEST_TMPDIR}/make-work"
    mkdir -p "$work"
    cp "${PROJECT_ROOT}/Makefile" "$work/Makefile"
    printf 'GITHUB_APP_PRIVATE_KEY_B64=from-dotenv\n' >"$work/.env"

    run_check_config make -C "$work" --dry-run check-github-app-config

    [ "$status" -ne 0 ]
    [[ "$output" == *"GITHUB_APP_PRIVATE_KEY_B64 is required"* ]]
}

@test "Makefile: github-app-key-b64・verify-github-app-key は PEM の指定がなければ、使い方を示して失敗する" {
    local target
    for target in github-app-key-b64 verify-github-app-key; do
        # setup() が PEM を export しているため、make が環境変数として取り込まないよう外す
        run env -u PEM make -C "${PROJECT_ROOT}" --dry-run "$target"

        [ "$status" -ne 0 ] || { echo "ターゲット ${target}: 失敗しなかった" >&2; return 1; }
        [[ "$output" == *"PEM is required"* ]] || { echo "ターゲット ${target}: メッセージがない: ${output}" >&2; return 1; }
    done
}

@test "Makefile: github-app-key-b64・verify-github-app-key は、対応する script を Git Bash 経由で呼び出す" {
    run make -C "${PROJECT_ROOT}" --dry-run github-app-key-b64 PEM=/path/to/key.pem
    [ "$status" -eq 0 ]
    [[ "$output" == *"./scripts/github-app-key-b64.sh \"/path/to/key.pem\""* ]]

    run make -C "${PROJECT_ROOT}" --dry-run verify-github-app-key PEM=/path/to/key.pem
    [ "$status" -eq 0 ]
    [[ "$output" == *"./scripts/verify-github-app-key.sh \"/path/to/key.pem\""* ]]
}

# --- docker-compose.yml ---

@test "docker-compose.yml: gateway は秘密鍵を環境変数 GITHUB_APP_PRIVATE_KEY_B64 で受け取り、PEM をマウントしない" {
    run sed -n '/^  mcp-gateway:/,/^  [a-z-]*:$/p' "${PROJECT_ROOT}/docker-compose.yml"

    [ "$status" -eq 0 ]
    [[ "$output" == *'- GITHUB_APP_PRIVATE_KEY_B64=${GITHUB_APP_PRIVATE_KEY_B64}'* ]]
    [[ "$output" != *"GITHUB_APP_PRIVATE_KEY_PATH"* ]]
    [[ "$output" != *"/run/secrets/github-app"* ]]
    [[ "$output" != *"config/github-app"* ]]
}
