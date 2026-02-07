# セキュリティ方針

## 現在の運用

2026-02-07時点で、本プロジェクトは公式イメージを直接利用します。

- 既定: `ghcr.io/github/github-mcp-server:main`
- 理由: HTTP transport（`github-mcp-server http`）を利用するため
- 補足: 公式最新リリース `v0.30.3` には `http` サブコマンドが未搭載

## 脆弱性管理

`.github/workflows/security.yml` で以下を継続実行します。

1. Trivy filesystem scan（リポジトリ全体）
2. Trivy container scan（`GITHUB_MCP_IMAGE`）

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
