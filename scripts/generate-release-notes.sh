#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 5 ]]; then
    printf '使用方法: %s TAG SOURCE_SHA REPOSITORY [CHANGELOG_FILE] [OUTPUT_FILE]\n' "$0" >&2
    exit 1
fi

TAG="$1"
SOURCE_SHA="$2"
REPOSITORY="$3"
CHANGELOG_FILE="${4:-CHANGELOG.md}"
OUTPUT_FILE="${5:-release-notes.md}"

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
    printf '不正なリリースタグです: %s\n' "$TAG" >&2
    exit 1
fi

if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    printf '不正な source SHA です: %s\n' "$SOURCE_SHA" >&2
    exit 1
fi

if [[ ! "$REPOSITORY" =~ ^[^/]+/[^/]+$ ]]; then
    printf '不正なリポジトリ名です: %s\n' "$REPOSITORY" >&2
    exit 1
fi

if [[ ! -f "$CHANGELOG_FILE" ]]; then
    printf 'CHANGELOG が見つかりません: %s\n' "$CHANGELOG_FILE" >&2
    exit 1
fi

VERSION="${TAG#v}"
RELEASE_URL="https://github.com/${REPOSITORY}/releases/tag/${TAG}"
DOWNLOAD_URL="https://github.com/${REPOSITORY}/releases/download/${TAG}"
CHANGELOG_URL="https://github.com/${REPOSITORY}/blob/${TAG}/CHANGELOG.md"
COMMIT_URL="https://github.com/${REPOSITORY}/commit/${SOURCE_SHA}"
OUTPUT_DIRECTORY="$(dirname "$OUTPUT_FILE")"
mkdir -p "$OUTPUT_DIRECTORY"

CHANGELOG_SECTION="$(mktemp)"
NOTES_FILE="$(mktemp)"
trap 'rm -f "$CHANGELOG_SECTION" "$NOTES_FILE"' EXIT

if ! awk -v version="$VERSION" '
    BEGIN {
        heading = "## [" version "]"
        found = 0
        content = 0
        pending_blank = 0
    }
    !found && index($0, heading) == 1 && \
        (length($0) == length(heading) || substr($0, length(heading) + 1, 3) == " - ") {
        found = 1
        next
    }
    found && /^## \[/ {
        exit
    }
    found {
        if ($0 ~ /^[[:space:]]*$/) {
            if (content) {
                pending_blank = 1
            }
            next
        }
        if (pending_blank) {
            print ""
            pending_blank = 0
        }
        content = 1
        print
    }
    END {
        if (!found || !content) {
            exit 1
        }
    }
' "$CHANGELOG_FILE" > "$CHANGELOG_SECTION"; then
    printf 'CHANGELOG に対象バージョンのセクションがありません: %s\n' "$TAG" >&2
    exit 1
fi

{
    printf '## 変更内容\n\n'
    cat "$CHANGELOG_SECTION"

    printf '\n## インストール\n\n'
    printf '### Go でインストール\n\n'
    printf '指定したリリースタグからインストールする場合:\n\n'
    printf '```sh\n'
    printf 'go install github.com/scottlz0310/mcp-docker/v2/cmd/mcp-docker@%s\n' "$TAG"
    printf '```\n\n'
    printf 'バージョン確認:\n\n'
    printf '```sh\n'
    printf 'mcp-docker --version\n'
    printf '```\n\n'
    printf '### ビルド済み成果物\n\n'
    printf 'GitHub Release のアーカイブを利用する場合は、対象 OS のファイルをダウンロードして配置してください。\n\n'

    printf '| 対象 | 成果物 |\n'
    printf '| --- | --- |\n'
    printf '| Windows amd64 | [mcp-docker-windows-amd64.zip](%s/mcp-docker-windows-amd64.zip) |\n' "$DOWNLOAD_URL"
    printf '| Linux amd64 | [mcp-docker-linux-amd64.tar.gz](%s/mcp-docker-linux-amd64.tar.gz) |\n' "$DOWNLOAD_URL"
    printf '| Linux arm64 | [mcp-docker-linux-arm64.tar.gz](%s/mcp-docker-linux-arm64.tar.gz) |\n' "$DOWNLOAD_URL"
    printf '| macOS amd64 | [mcp-docker-darwin-amd64.tar.gz](%s/mcp-docker-darwin-amd64.tar.gz) |\n' "$DOWNLOAD_URL"
    printf '| macOS arm64 | [mcp-docker-darwin-arm64.tar.gz](%s/mcp-docker-darwin-arm64.tar.gz) |\n' "$DOWNLOAD_URL"

    printf '\n## チェックサム\n\n'
    printf '[checksums.txt](%s/checksums.txt) に、すべてのアーカイブの SHA-256 を収録しています。\n' "$DOWNLOAD_URL"

    printf '\n## 検証\n\n'
    printf -- '- リリースタグ: [%s](%s)\n' "$TAG" "$RELEASE_URL"
    printf -- '- 対象コミット: [%s](%s)\n' "$SOURCE_SHA" "$COMMIT_URL"
    printf -- '- Linux amd64 の成果物で `mcp-docker --version` が `mcp-docker %s` になることを確認しています。\n' "$VERSION"

    printf '\n[CHANGELOG.md](%s)\n' "$CHANGELOG_URL"
} > "$NOTES_FILE"

mv "$NOTES_FILE" "$OUTPUT_FILE"
