# セキュリティ方針

## 現在の運用

| サービス | 実行時イメージ | Security Scan |
|---|---|---|
| `review-raven` | `ghcr.io/scottlz0310/review-raven:latest`（外部イメージ） | 外部リポジトリ側で管理 |

GitHub MCP（`github-mcp`）は、reviewed rev44・reviewer rev30が依存しなくなったため、構成から撤去した。

## 脆弱性管理

`.github/workflows/security.yml` で以下を継続実行します。

1. Trivy filesystem scan（リポジトリ全体）

`review-raven` はソースコードを外部リポジトリ（`ghcr.io/scottlz0310/review-raven`）に移行したため、イメージスキャンは外部リポジトリ側で実施します。

## 参考リンク

- [Trivy](https://github.com/aquasecurity/trivy)
