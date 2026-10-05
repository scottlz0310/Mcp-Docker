#!/bin/bash
# 注入済みの環境変数 GITHUB_APP_PRIVATE_KEY_B64 を復号し、PEM と SHA-256 を比べる。
#
# 出力は、一致・不一致と長さだけで、鍵の値は出さない。
# 未設定・復号失敗・不一致は、非ゼロで終了する。
# bw sync → dsx-env を実行した、同じシェルで実行する。
#
# 使い方: scripts/verify-github-app-key.sh <PEM のパス>
set -euo pipefail

usage() {
  echo "使い方: $0 <PEM のパス>" >&2
}

# 標準入力の SHA-256 を、16 進数で出す。
sha256_of_stdin() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    echo "エラー: sha256sum か shasum が必要です" >&2
    return 1
  fi
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi
pem=$1

if [ ! -f "$pem" ] || [ ! -r "$pem" ]; then
  echo "エラー: PEM を読み取れません: $pem" >&2
  exit 1
fi

b64=${GITHUB_APP_PRIVATE_KEY_B64:-}
if [ -z "$b64" ]; then
  echo "エラー: GITHUB_APP_PRIVATE_KEY_B64 が未設定です（bw sync → dsx-env を実行した、同じシェルで実行してください）" >&2
  exit 1
fi

if ! decoded_hash=$(printf '%s' "$b64" | base64 -d 2>/dev/null | sha256_of_stdin); then
  echo "エラー: GITHUB_APP_PRIVATE_KEY_B64 を base64 として復号できません" >&2
  exit 1
fi
decoded_bytes=$(printf '%s' "$b64" | base64 -d 2>/dev/null | wc -c | tr -d '[:space:]')
pem_hash=$(sha256_of_stdin <"$pem")

if [ "$decoded_hash" != "$pem_hash" ]; then
  echo "エラー: GITHUB_APP_PRIVATE_KEY_B64 が PEM と一致しません（base64 の長さ ${#b64} 文字、復号後 ${decoded_bytes} バイト）" >&2
  exit 1
fi

echo "一致しました（base64 の長さ ${#b64} 文字、復号後 ${decoded_bytes} バイト）"
