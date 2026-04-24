# セキュリティ方針

## 現在の運用

2026-04-24時点で、本プロジェクトは実行時には公式イメージを利用しつつ、Security Scan では再ビルドした検証用イメージを利用します。

- 既定: `ghcr.io/github/github-mcp-server:main`
- 補足: 公式安定リリースの最新は `v1.0.0`（`v0.31.0` 以降 Streamable HTTP / `http` サブコマンドが正式搭載）
- Security Scan補足: `Dockerfile.github-mcp-server` をベースに、workflow 側で `build-arg` により `go-sdk`（デフォルト: `v1.5.0`、`GITHUB_MCP_GO_SDK_VERSION` で上書き可）を指定してビルドしたイメージを Trivy でスキャン（CVE-2026-27896 対応版。詳細: [CVE-2026-27896](https://nvd.nist.gov/vuln/detail/CVE-2026-27896)）

## 脆弱性管理

`.github/workflows/security.yml` で以下を継続実行します。

1. Trivy filesystem scan（リポジトリ全体）
2. Trivy container scan（`Dockerfile.github-mcp-server` からビルドした `github-mcp-server:security-scan`）

これにより、利用イメージを更新しても継続的に脆弱性を検出できます。

## バージョン固定の推奨

`main` タグは更新されるため、再現性が必要な環境では digest 固定を推奨します。

現在利用中のイメージの digest は以下のコマンドで取得できます:

```bash
docker pull ghcr.io/github/github-mcp-server:main
docker inspect ghcr.io/github/github-mcp-server:main --format='{{index .RepoDigests 0}}'
```

取得した digest の完全な文字列（`ghcr.io/github/github-mcp-server@sha256:...`）をそのまま使用してバージョンを固定:

```bash
export GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server@sha256:1234567890abcdef...
docker compose pull github-mcp
docker compose up -d github-mcp
```

## 参考リンク

- [GitHub MCP Server Releases](https://github.com/github/github-mcp-server/releases)
- [GitHub MCP Server Repository](https://github.com/github/github-mcp-server)
- [Trivy](https://github.com/aquasecurity/trivy)
