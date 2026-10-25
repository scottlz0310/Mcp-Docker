#!/usr/bin/env bats
# 検証対象: 内部連携のサービス主体のトークン取得に関するもの
#   scripts/issue-internal-token.sh
# 目的: device flow の各応答に正しく従い、トークンを画面・標準出力・コマンドラインに出さず、クリップボードへだけ渡すこと

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPT="${PROJECT_ROOT}/scripts/issue-internal-token.sh"
    export MOCK_DIR="${BATS_TEST_TMPDIR}/mock"
    mkdir -p "$MOCK_DIR"

    export CLIP_MOCK_OUT="${MOCK_DIR}/clip.out"
    export CURL_MOCK_DIR="$MOCK_DIR"
    export SLEEP_MOCK_OUT="${MOCK_DIR}/sleep.out"
    export STDOUT_FILE="${MOCK_DIR}/stdout"
    export STDERR_FILE="${MOCK_DIR}/stderr"

    create_clip_mock "${MOCK_DIR}/clip"
    create_curl_mock "${MOCK_DIR}/curl"
    create_sleep_mock "${MOCK_DIR}/sleep"

    export CLIP_CMD="${MOCK_DIR}/clip"
    export CURL_BIN="${MOCK_DIR}/curl"
    export SLEEP_BIN="${MOCK_DIR}/sleep"
    export GATEWAY_URL="https://gateway.test:8080"
    unset MCP_GATEWAY_PUBLIC_URL GATEWAY_CACERT

    DEVICE_CODE="dc-secret-0123456789"
    TOKEN=$(make_jwt svc-owl review-raven-internal)
    write_device_response 5 900
}

create_clip_mock() {
    cat >"$1" <<'EOF'
#!/bin/bash
cat >"${CLIP_MOCK_OUT:?}"
EOF
    chmod +x "$1"
}

# curl のモック。最後の引数を URL とし、標準入力（本文）と引数を記録する。
# /device_authorization は device.resp を、/token は token.<n>（無ければ token.last）を、curl -w の形式（本文 + 改行 + ステータス）で返す。
create_curl_mock() {
    cat >"$1" <<'EOF'
#!/bin/bash
url="${*: -1}"
body=$(cat)
printf '%s\n' "$*" >>"${CURL_MOCK_DIR}/args"
printf '%s\n' "$body" >>"${CURL_MOCK_DIR}/bodies"
case "$url" in
    */device_authorization)
        cat "${CURL_MOCK_DIR}/device.resp"
        ;;
    */token)
        n=$(($(cat "${CURL_MOCK_DIR}/count" 2>/dev/null || echo 0) + 1))
        echo "$n" >"${CURL_MOCK_DIR}/count"
        f="${CURL_MOCK_DIR}/token.${n}"
        [ -f "$f" ] || f="${CURL_MOCK_DIR}/token.last"
        cat "$f"
        ;;
esac
EOF
    chmod +x "$1"
}

create_sleep_mock() {
    cat >"$1" <<'EOF'
#!/bin/bash
printf '%s\n' "$1" >>"${SLEEP_MOCK_OUT:?}"
EOF
    chmod +x "$1"
}

# 署名なしのダミー JWT を作る（スクリプトはクレームの表示にしか使わず、検証しない）。
make_jwt() {
    local sub="$1" aud="$2" payload
    payload=$(printf '{"sub":"%s","aud":"%s","exp":1900000000}' "$sub" "$aud" | base64 | tr -d '=\n' | tr '+/' '-_')
    printf 'eyJhbGciOiJSUzI1NiJ9.%s.c2ln' "$payload"
}

write_device_response() {
    local interval="$1" expires_in="$2"
    printf '{"device_code":"%s","user_code":"ABCD-1234","verification_uri":"https://gateway.test:8080/activate","expires_in":%s,"interval":%s}\n200' \
        "$DEVICE_CODE" "$expires_in" "$interval" >"${MOCK_DIR}/device.resp"
}

# token エンドポイントの n 回目（last なら以降すべて）の応答を書く。
write_token_response() {
    local name="$1" status="$2" body="$3"
    printf '%s\n%s' "$body" "$status" >"${MOCK_DIR}/token.${name}"
}

write_token_success() {
    write_token_response "$1" 200 "{\"access_token\":\"${TOKEN}\",\"token_type\":\"Bearer\",\"expires_in\":7776000,\"refresh_token\":\"rt-secret-should-not-leak\"}"
}

write_token_error() {
    write_token_response "$1" 400 "{\"error\":\"$2\"}"
}

# ファイルに、どのパターンも含まれないことを確認する（bats は途中行の `! cmd` を失敗にしないため）。
refute_in() {
    local file="$1" pattern
    shift
    for pattern in "$@"; do
        if grep -q -F -e "$pattern" "$file"; then
            echo "${file} に含まれてはならない値がある" >&2
            return 1
        fi
    done
}

# 標準出力と標準エラーを別ファイルへ取る。
run_script() {
    run bash -c '"$0" "$@" >"$STDOUT_FILE" 2>"$STDERR_FILE"' "$SCRIPT" "$@"
}

@test "主体ごとに正しい resource で開始し、トークンをクリップボードへだけ渡す" {
    write_token_success last
    local row principal resource var_name
    for row in "raven thread_owl_internal REVIEW_RAVEN_OWL_INTERNAL_TOKEN" \
        "owl review_raven_internal THREAD_OWL_RAVEN_INTERNAL_TOKEN" \
        "squirrel review_raven_internal SQUIRREL_OBSERVATION_TOKEN"; do
        read -r principal resource var_name <<<"$row"
        rm -f "${MOCK_DIR}/args" "${MOCK_DIR}/bodies" "${MOCK_DIR}/count" "$CLIP_MOCK_OUT"

        run_script "$principal"

        [ "$status" -eq 0 ]
        grep -q "resource=${resource}" "${MOCK_DIR}/bodies"
        grep -q "client_id=mcp-client" "${MOCK_DIR}/bodies"
        [ "$(cat "$CLIP_MOCK_OUT")" = "$TOKEN" ]
        [ ! -s "$STDOUT_FILE" ]
        grep -q "env:${var_name}" "$STDERR_FILE"
        grep -q "sub=svc-owl aud=review-raven-internal exp=2030-03-17T17:46:40Z" "$STDERR_FILE"
        refute_in "$STDERR_FILE" "$TOKEN" "rt-secret-should-not-leak"
    done
}

@test "承認用の URL とコードを標準エラーに出す" {
    write_token_success last

    run_script owl

    [ "$status" -eq 0 ]
    grep -q "https://gateway.test:8080/activate" "$STDERR_FILE"
    grep -q "ABCD-1234" "$STDERR_FILE"
}

@test "device_code をコマンドラインに載せず、標準入力で渡す" {
    write_token_success last

    run_script owl

    [ "$status" -eq 0 ]
    refute_in "${MOCK_DIR}/args" "$DEVICE_CODE"
    grep -q "device_code=${DEVICE_CODE}" "${MOCK_DIR}/bodies"
}

@test "authorization_pending の間は待ち、interval に従って再試行する" {
    write_token_error 1 authorization_pending
    write_token_error 2 authorization_pending
    write_token_success last

    run_script owl

    [ "$status" -eq 0 ]
    [ "$(cat "$CLIP_MOCK_OUT")" = "$TOKEN" ]
    [ "$(cat "${MOCK_DIR}/count")" -eq 3 ]
    [ "$(cat "$SLEEP_MOCK_OUT")" = "$(printf '5\n5\n5')" ]
}

@test "slow_down を受けたら interval を5秒延ばす" {
    write_token_error 1 slow_down
    write_token_success last

    run_script owl

    [ "$status" -eq 0 ]
    [ "$(cat "$SLEEP_MOCK_OUT")" = "$(printf '5\n10')" ]
}

@test "承認が拒否されたら、クリップボードへ渡さず失敗する" {
    write_token_error last access_denied

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "拒否" "$STDERR_FILE"
    [ ! -e "$CLIP_MOCK_OUT" ]
}

@test "device code の期限切れなら、クリップボードへ渡さず失敗する" {
    write_token_error last expired_token

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "期限" "$STDERR_FILE"
    [ ! -e "$CLIP_MOCK_OUT" ]
}

@test "想定外のエラーは原因を示して失敗する" {
    write_token_error last invalid_grant

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "invalid_grant" "$STDERR_FILE"
    [ ! -e "$CLIP_MOCK_OUT" ]
}

@test "expires_in を過ぎても承認されなければ失敗する" {
    write_device_response 5 0
    write_token_error last authorization_pending

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "期限" "$STDERR_FILE"
    [ ! -e "$CLIP_MOCK_OUT" ]
}

@test "JWT でないトークンは、クリップボードへ渡さず失敗する" {
    TOKEN="gho_opaque_provider_token"
    write_token_success last

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "JWT" "$STDERR_FILE"
    [ ! -e "$CLIP_MOCK_OUT" ]
    refute_in "$STDERR_FILE" "$TOKEN"
}

@test "device flow を開始できなければ、HTTP ステータスと理由を示して失敗する" {
    printf '{"error":"invalid_target","error_description":"resource \\"x\\" is not registered with this gateway"}\n400' >"${MOCK_DIR}/device.resp"

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "HTTP 400" "$STDERR_FILE"
    grep -q "not registered" "$STDERR_FILE"
    [ ! -e "${MOCK_DIR}/count" ]
}

@test "GATEWAY_URL が無ければ MCP_GATEWAY_PUBLIC_URL を使う" {
    write_token_success last
    unset GATEWAY_URL
    export MCP_GATEWAY_PUBLIC_URL="https://public.test"

    run_script owl

    [ "$status" -eq 0 ]
    grep -q "https://public.test/device_authorization" "${MOCK_DIR}/args"
}

@test "GATEWAY_CACERT を curl の --cacert へ渡す" {
    write_token_success last
    export GATEWAY_CACERT="${MOCK_DIR}/ca.pem"

    run_script owl

    [ "$status" -eq 0 ]
    grep -q -e "--cacert ${MOCK_DIR}/ca.pem" "${MOCK_DIR}/args"
}

@test "gateway の URL がどちらも無ければ失敗する" {
    unset GATEWAY_URL MCP_GATEWAY_PUBLIC_URL

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "GATEWAY_URL" "$STDERR_FILE"
}

@test "引数が無い、または未知の主体なら使い方を示して終了コード2" {
    local args
    for args in "" "unknown" "owl extra"; do
        # shellcheck disable=SC2086
        run_script $args

        [ "$status" -eq 2 ]
        grep -q "使い方" "$STDERR_FILE"
    done
}

@test "クリップボードへの書き込みに失敗したら失敗する" {
    write_token_success last
    printf '#!/bin/bash\nexit 1\n' >"${MOCK_DIR}/clip"

    run_script owl

    [ "$status" -eq 1 ]
    grep -q "クリップボード" "$STDERR_FILE"
}
