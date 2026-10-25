#!/usr/bin/env bats

setup() {
    export SCRIPT="${BATS_TEST_DIRNAME}/../../scripts/verify-release-assets.sh"
    cd "$BATS_TEST_TMPDIR"
    printf '#!/bin/sh\nprintf "mcp-docker 1.2.3\\n"\n' > mcp-docker
    chmod +x mcp-docker
    for suffix in darwin-amd64 darwin-arm64 linux-amd64 linux-arm64; do
        tar czf "mcp-docker-$suffix.tar.gz" mcp-docker
    done
    cp mcp-docker mcp-docker.exe
    zip -q mcp-docker-windows-amd64.zip mcp-docker.exe
    sha256sum mcp-docker-*.tar.gz mcp-docker-*.zip | sort > checksums.txt
}

@test "release assets: 全成果物と版を確認する" {
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.3
    [ "$status" -eq 0 ]
}

@test "release assets: 欠落・改変・版の不一致を拒否する" {
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.4
    [ "$status" -ne 0 ]
    printf changed >> mcp-docker-windows-amd64.zip
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.3
    [ "$status" -ne 0 ]
    rm mcp-docker-windows-amd64.zip
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.3
    [ "$status" -ne 0 ]
}

@test "release assets: チェックサムの余分な項目とアーカイブ内の別ファイルを拒否する" {
    cp checksums.txt original.txt
    sha256sum mcp-docker >> checksums.txt
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.3
    [ "$status" -ne 0 ]
    cp original.txt checksums.txt
    printf extra > extra
    tar czf mcp-docker-linux-arm64.tar.gz mcp-docker extra
    sha256sum mcp-docker-*.tar.gz mcp-docker-*.zip | sort > checksums.txt
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR" 1.2.3
    [ "$status" -ne 0 ]
}
