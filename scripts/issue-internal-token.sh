#!/bin/bash
# 内部連携のサービス主体の gateway トークンを、device flow で取得してクリップボードへ入れる。
#
# 手順は docs/review-internal-link.md の「サービス主体と資格情報」を参照。
# 承認は、主体の GitHub アカウントでログインしたブラウザで行う（主体のアカウントの形は未決。docs/review-internal-link.md）。利用者本人のアカウントで承認すると、
# ACL の主体と食い違うため、取得後に表示する sub（GitHub login）で必ず確認する。
# トークンは、画面にも標準出力にも出さず、コマンドラインにも載せない（標準入力でクリップボードへ渡す）。
# 貼り付け先は、Bitwarden の項目 env:<変数名> のカスタムフィールド value（非表示）。
#
# 使い方: scripts/issue-internal-token.sh <raven|owl|squirrel>
#
#   主体      resource               貼り付ける変数
#   raven     thread_owl_internal    REVIEW_RAVEN_OWL_INTERNAL_TOKEN
#   owl       review_raven_internal  THREAD_OWL_RAVEN_INTERNAL_TOKEN
#   squirrel  review_raven_internal  SQUIRREL_OBSERVATION_TOKEN
#
# 環境変数:
#   GATEWAY_URL     gateway の base URL。未指定なら MCP_GATEWAY_PUBLIC_URL。
#   GATEWAY_CACERT  gateway の証明書を検証する CA の PEM。mkcert の CA など、curl が信頼しない場合に指定する。
#   CLIP_CMD        クリップボードへ書き込むコマンド（標準入力から受け取る。引数も指定できる）。
#                   未指定なら、clip.exe / pbcopy / wl-copy / xclip / xsel の順に検出する。
#   CURL_BIN / SLEEP_BIN  curl / sleep の差し替え（テスト用）。
set -euo pipefail

CURL_BIN=${CURL_BIN:-curl}
SLEEP_BIN=${SLEEP_BIN:-sleep}
CLIENT_ID=mcp-client

usage() {
  echo "使い方: $0 <raven|owl|squirrel>" >&2
}

detect_clip_cmd() {
  if [ -n "${CLIP_CMD:-}" ]; then
    printf '%s' "$CLIP_CMD"
    return 0
  fi

  local candidate
  for candidate in "clip.exe" "pbcopy" "wl-copy" "xclip -selection clipboard" "xsel --clipboard --input"; do
    if command -v "${candidate%% *}" >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

# フォームを POST し、応答の本文を標準出力へ、HTTP ステータスを最終行へ出す。
# device_code を引数に載せないよう、本文は標準入力で渡す。
post_form() {
  local path=$1 body=$2
  local -a opts=(-sS --max-time 30 -X POST -H 'Content-Type: application/x-www-form-urlencoded' --data @-)
  if [ -n "${GATEWAY_CACERT:-}" ]; then
    opts+=(--cacert "$GATEWAY_CACERT")
  fi
  printf '%s' "$body" | "$CURL_BIN" "${opts[@]}" -w '\n%{http_code}' "${gateway%/}${path}"
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi
principal=$1

case "$principal" in
  raven)
    resource=thread_owl_internal
    var_name=REVIEW_RAVEN_OWL_INTERNAL_TOKEN
    ;;
  owl)
    resource=review_raven_internal
    var_name=THREAD_OWL_RAVEN_INTERNAL_TOKEN
    ;;
  squirrel)
    resource=review_raven_internal
    var_name=SQUIRREL_OBSERVATION_TOKEN
    ;;
  *)
    usage
    exit 2
    ;;
esac

gateway=${GATEWAY_URL:-${MCP_GATEWAY_PUBLIC_URL:-}}
if [ -z "$gateway" ]; then
  echo "エラー: gateway の URL がありません。GATEWAY_URL または MCP_GATEWAY_PUBLIC_URL を指定してください" >&2
  exit 1
fi

for cmd in jq "$CURL_BIN"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "エラー: $cmd が見つかりません" >&2
    exit 1
  fi
done

if ! clip_cmd=$(detect_clip_cmd); then
  echo "エラー: クリップボードのコマンドが見つかりません（clip.exe / pbcopy / wl-copy / xclip / xsel）。CLIP_CMD で指定してください" >&2
  exit 1
fi
read -r -a clip_argv <<<"$clip_cmd"

# 1. device flow を始める。
if ! response=$(post_form /device_authorization "client_id=${CLIENT_ID}&scope=repo%20user&resource=${resource}"); then
  echo "エラー: ${gateway%/}/device_authorization に接続できませんでした" >&2
  exit 1
fi
status=${response##*$'\n'}
body=${response%$'\n'*}
if [ "$status" != 200 ]; then
  echo "エラー: device flow を開始できませんでした（HTTP $status: $(printf '%s' "$body" | jq -r '.error_description // .error // empty' 2>/dev/null)）。resource=${resource} が gateway に登録されているか（REVIEW_INTERNAL_LINK_ENABLED が有効か）を確認してください" >&2
  exit 1
fi

if ! IFS=$'\t' read -r device_code user_code verification_uri expires_in interval < <(
  printf '%s' "$body" | jq -er '[.device_code, .user_code, .verification_uri, .expires_in, .interval] | @tsv' | tr -d '\r'
); then
  echo "エラー: device_authorization の応答を解釈できませんでした" >&2
  exit 1
fi

{
  echo "${principal} 主体のアカウントでログインしたブラウザで、次を開いて承認してください。"
  echo "  URL : ${verification_uri}"
  echo "  コード: ${user_code}"
  echo "（${expires_in} 秒以内。待機中...）"
} >&2

# 2. 承認されるまで token エンドポイントをポーリングする（RFC 8628 §3.5）。
deadline=$((SECONDS + expires_in))
access_token=
while [ -z "$access_token" ]; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "エラー: 承認の期限が切れました。もう一度実行してください" >&2
    exit 1
  fi
  "$SLEEP_BIN" "$interval"

  if ! response=$(post_form /token "grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=${device_code}&client_id=${CLIENT_ID}&resource=${resource}"); then
    echo "エラー: ${gateway%/}/token に接続できませんでした" >&2
    exit 1
  fi
  status=${response##*$'\n'}
  body=${response%$'\n'*}

  if [ "$status" = 200 ]; then
    if ! access_token=$(printf '%s' "$body" | jq -er '.access_token' | tr -d '\r'); then
      echo "エラー: token の応答に access_token がありません" >&2
      exit 1
    fi
    continue
  fi

  error=$(printf '%s' "$body" | jq -r '.error // empty' 2>/dev/null || true)
  case "$error" in
    authorization_pending) ;;
    slow_down) interval=$((interval + 5)) ;;
    access_denied)
      echo "エラー: 承認が拒否されました" >&2
      exit 1
      ;;
    expired_token)
      echo "エラー: 承認の期限が切れました。もう一度実行してください" >&2
      exit 1
      ;;
    *)
      echo "エラー: トークンを取得できませんでした（HTTP $status: ${error:-不明}）" >&2
      exit 1
      ;;
  esac
done

# 3. 誰の・どの宛先のトークンかを、署名を検証せずクレームだけ表示して確認させる（値そのものは出さない）。
if ! claims=$(printf '%s' "$access_token" | jq -Rer 'split(".")[1] | gsub("-"; "+") | gsub("_"; "/") | @base64d | fromjson | "sub=\(.sub) aud=\(.aud) exp=\(.exp | todate)"'); then
  echo "エラー: トークンが JWT ではありません（gateway が builtin mode でない可能性があります）。クリップボードへはコピーしません" >&2
  exit 1
fi

if ! printf '%s' "$access_token" | "${clip_argv[@]}"; then
  echo "エラー: クリップボードへの書き込みに失敗しました（$clip_cmd）" >&2
  exit 1
fi

echo "クリップボードにコピーしました（${claims}）。sub が ${principal} 主体のアカウントの login であることを確認し、Bitwarden の env:${var_name} の value に貼り付けてください" >&2
