#!/bin/bash
# GitHub App の秘密鍵（PEM）を、環境変数で渡せる単一行の base64 にして、クリップボードへ入れる。
#
# 複数行の PEM は、dsx などの環境変数の注入経路で改行が壊れる（dsx は改行入りの値を、警告してスキップする）。
# そのため、gateway へは単一行の base64（GITHUB_APP_PRIVATE_KEY_B64）で渡す。
# 値は、画面にも標準出力にも出さず、コマンドラインにも載せない（標準入力でクリップボードへ渡す）。
# 貼り付け先は、Bitwarden の項目 env:GITHUB_APP_PRIVATE_KEY_B64 のカスタムフィールド value（非表示）。
#
# 使い方: scripts/github-app-key-b64.sh <PEM のパス>
# 環境変数:
#   CLIP_CMD  クリップボードへ書き込むコマンド（標準入力から受け取る。引数も指定できる）。
#             未指定なら、clip.exe / pbcopy / wl-copy / xclip / xsel の順に検出する。
set -euo pipefail

usage() {
  echo "使い方: $0 <PEM のパス>" >&2
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

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi
pem=$1

if [ ! -f "$pem" ] || [ ! -r "$pem" ]; then
  echo "エラー: PEM を読み取れません: $pem" >&2
  exit 1
fi
if ! grep -q -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' "$pem"; then
  echo "エラー: 秘密鍵の PEM ではありません（-----BEGIN ... PRIVATE KEY----- の行がありません）: $pem" >&2
  exit 1
fi

if ! clip_cmd=$(detect_clip_cmd); then
  echo "エラー: クリップボードのコマンドが見つかりません（clip.exe / pbcopy / wl-copy / xclip / xsel）。CLIP_CMD で指定してください" >&2
  exit 1
fi
read -r -a clip_argv <<<"$clip_cmd"

# base64 の折り返し（GNU は 76 文字）を除いて、単一行にする。macOS の base64 には -w0 が無い。
if ! encoded=$(base64 <"$pem" | tr -d '\r\n'); then
  echo "エラー: PEM を base64 にできませんでした: $pem" >&2
  exit 1
fi

if ! printf '%s' "$encoded" | "${clip_argv[@]}"; then
  echo "エラー: クリップボードへの書き込みに失敗しました（$clip_cmd）" >&2
  exit 1
fi

echo "クリップボードにコピーしました（base64 の長さ ${#encoded} 文字）。Bitwarden の env:GITHUB_APP_PRIVATE_KEY_B64 の value に貼り付けてください"
