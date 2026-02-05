# セキュリティパッチ

## 概要

このプロジェクトでは、GitHub公式MCPサーバーイメージ（`ghcr.io/github/github-mcp-server`）にOpenSSLセキュリティパッチを適用したカスタムイメージを使用しています。

## 修正済みの脆弱性

### Critical

#### CVE-2025-15467
- **タイトル**: OpenSSL - Remote code execution or Denial of Service via oversized Initialization Vector in CMS parsing
- **重要度**: Critical
- **説明**: OpenSSLのCMS（Cryptographic Message Syntax）パーサーにおいて、過大なInitialization Vector（IV）を処理する際にスタックバッファオーバーフローが発生し、リモートコード実行またはDoS攻撃が可能になる脆弱性
- **影響**: 攻撃者が細工したCMSメッセージを送信することで、任意のコードを実行したり、サービスをクラッシュさせることが可能
- **修正バージョン**: OpenSSL 3.0.18-1~deb12u2

### High

#### CVE-2025-9230
- **タイトル**: OpenSSL - Denial of Service via malformed PKCS#12 file processing
- **重要度**: High
- **説明**: 不正なPKCS#12ファイルを処理する際にDoS攻撃が可能になる脆弱性
- **影響**: 攻撃者が細工したPKCS#12ファイルを提供することで、サービスをクラッシュさせることが可能
- **修正バージョン**: OpenSSL 3.0.18-1~deb12u2

#### CVE-2025-9231
- **タイトル**: OpenSSL - Arbitrary code execution due to out-of-bounds write in PKCS#12 processing
- **重要度**: High
- **説明**: PKCS#12処理においてバウンダリ外書き込みが発生し、任意のコード実行が可能になる脆弱性
- **影響**: 攻撃者が細工したPKCS#12ファイルを提供することで、任意のコードを実行することが可能
- **修正バージョン**: OpenSSL 3.0.18-1~deb12u2

## 技術的な実装

### カスタムDockerイメージ

`Dockerfile.github-mcp-server`では以下の手順でセキュリティパッチを適用しています：

1. **ベースイメージ**: 最新のDebian 12 (Bookworm) Slimイメージを使用
2. **パッケージ更新**: `apt-get update && apt-get upgrade`で全パッケージを最新化
3. **OpenSSLインストール**: Debianリポジトリで提供される最新のセキュリティパッチ適用済みlibssl3をインストール
4. **ライブラリコピー**: 更新されたOpenSSLライブラリをdistroless基盤イメージにコピー（マルチアーキテクチャ対応）
5. **CA証明書更新**: 最新の信頼できるCA証明書をコピー
6. **バイナリ統合**: GitHub公式MCPサーバーのバイナリを最終イメージに統合
7. **非rootユーザー**: セキュリティ強化のため、UID 65532（nonroot）で実行

### マルチステージビルド

```dockerfile
# Stage 1: 更新されたOpenSSLライブラリを取得
FROM debian:bookworm-slim AS debian-updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y libssl3 openssl ca-certificates && \
    update-ca-certificates

# Stage 2: 公式MCPサーバーイメージからバイナリを取得
FROM ghcr.io/github/github-mcp-server:v0.30.3 AS upstream

# Stage 3: 最終イメージ構築（distroless基盤 + 更新済みOpenSSL + MCPサーバーバイナリ）
FROM gcr.io/distroless/base-debian12:latest
# マルチアーキテクチャ対応: 全てのアーキテクチャのライブラリをコピー
COPY --from=debian-updates /usr/lib/*-linux-gnu*/libssl.so* /usr/lib/
COPY --from=debian-updates /usr/lib/*-linux-gnu*/libcrypto.so* /usr/lib/
COPY --from=debian-updates /etc/ssl/certs /etc/ssl/certs
COPY --from=upstream /server/github-mcp-server .
USER 65532:65532
```

## 検証方法

### ビルド

```bash
docker build -f Dockerfile.github-mcp-server -t mcp-docker/github-mcp-server:v0.30.3-patched .
```

### バージョン確認

```bash
docker run --rm mcp-docker/github-mcp-server:v0.30.3-patched --version
```

### セキュリティスキャン

Trivyを使用して脆弱性スキャンを実行：

```bash
trivy image --severity HIGH,CRITICAL mcp-docker/github-mcp-server:v0.30.3-patched
```

## メンテナンス

### 定期的な更新

1. Debian 12のセキュリティアップデートを定期的に確認
2. OpenSSLの新しいセキュリティパッチがリリースされたら、イメージを再ビルド
3. GitHub公式MCPサーバーの新バージョンがリリースされたら、Dockerfileを更新

### 監視対象

- [Debian Security Tracker - OpenSSL](https://security-tracker.debian.org/tracker/openssl)
- [OpenSSL Security Advisories](https://www.openssl.org/news/vulnerabilities.html)
- [GitHub MCP Server Releases](https://github.com/github/github-mcp-server/releases)

## 参考資料

- [Debian Security Advisory DSA-6015-1](https://www.debian.org/security/)
- [OpenSSL Vulnerabilities](https://openssl-library.org/news/vulnerabilities/)
- [Distroless Images](https://github.com/GoogleContainerTools/distroless)
