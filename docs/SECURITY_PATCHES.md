# セキュリティ方針

## 現在の運用

| サービス | 実行時イメージ | Security Scan |
|---|---|---|
| `github-mcp` | `ghcr.io/github/github-mcp-server:main`（公式イメージ） | 同公式イメージを Trivy でスキャン |
| `copilot-review-mcp` | リポジトリ内 `services/copilot-review-mcp/Dockerfile` からビルド | ビルドしたイメージを Trivy でスキャン |

- 公式安定リリースの最新は `v1.0.0`（`v0.31.0` 以降 Streamable HTTP / `http` サブコマンドが正式搭載）

## 脆弱性管理

`.github/workflows/security.yml` で以下を継続実行します。

1. Trivy filesystem scan（リポジトリ全体）
2. Trivy container scan（`ghcr.io/github/github-mcp-server:main` 公式イメージ）
3. Trivy container scan（`copilot-review-mcp` ローカルビルドイメージ）

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
