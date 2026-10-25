#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 || ! "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
    echo '使用方法: verify-release-assets.sh DIRECTORY VERSION' >&2
    exit 1
fi
cd "$1"
expected=(mcp-docker-darwin-amd64.tar.gz mcp-docker-darwin-arm64.tar.gz
    mcp-docker-linux-amd64.tar.gz mcp-docker-linux-arm64.tar.gz mcp-docker-windows-amd64.zip)
mapfile -t recorded < <(awk '{print $2}' checksums.txt | sort)
if [[ "${recorded[*]}" != "${expected[*]}" ]]; then
    echo 'チェックサムの成果物一覧が配布契約と一致しません' >&2
    exit 1
fi
sha256sum --strict -c checksums.txt
for archive in "${expected[@]}"; do
    if [[ "$archive" == *.zip ]]; then
        contents=$(unzip -Z1 "$archive")
        expected_binary=mcp-docker.exe
    else
        contents=$(tar -tzf "$archive")
        expected_binary=mcp-docker
    fi
    if [[ "$contents" != "$expected_binary" ]]; then
        printf '成果物 %s の内容が %s と一致しません\n' "$archive" "$expected_binary" >&2
        exit 1
    fi
done
verify_dir=$(mktemp -d)
trap 'rm -rf "$verify_dir"' EXIT
tar xzf mcp-docker-linux-amd64.tar.gz -C "$verify_dir"
actual=$(timeout 10 "$verify_dir/mcp-docker" --version)
if [[ "$actual" != "mcp-docker $2" ]]; then
    printf 'Linux amd64 の版が不一致です: expected=%s actual=%s\n' "$2" "$actual" >&2
    exit 1
fi
echo '全5アーカイブのチェックサム・内容と Linux amd64 の版が一致しました'
