#!/usr/bin/env bash
# pwsh (PowerShell 7+) の存在を確認する。
#
# Makefile の recipe に日本語リテラルを直接埋め込むと、一部の Windows 版 GNU Make
# バイナリが Makefile の UTF-8 テキストをレガシーコードページとして誤って
# 再エンコードし、echo 出力が文字化けする（make 自体の bug）。
# Makefile 側は本スクリプトの呼び出しのみ（ASCII）に留め、日本語メッセージは
# bash が直接読み込むこのファイル側に置くことで回避する。
set -euo pipefail

if ! command -v pwsh >/dev/null 2>&1; then
	echo "エラー: pwsh (PowerShell 7+) が見つかりません。" >&2
	echo "  Windows PowerShell 5.1 (powershell.exe) は BOM なし UTF-8 スクリプト内の日本語文字列を" >&2
	echo "  システムのレガシーコードページで誤読し、パースエラーになるため使用できません。" >&2
	echo "  winget install --id Microsoft.PowerShell --exact でインストールしてください。" >&2
	exit 1
fi
