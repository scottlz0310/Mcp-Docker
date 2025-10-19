# GitHub MCP Server 統合設計

**作成日**: 2025-10-19
**バージョン**: 1.0.0
**ステータス**: Draft

## 概要

VS Code、Cursor、Kiro等の統合IDEに対してGitHub MCP Server機能を提供するDocker常駐サービス。
フル機能のGitHub公式MCPサーバーイメージを使用し、各IDE用の設定支援まで提供する。

## アーキテクチャ

### システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                        統合IDE                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ VS Code  │  │  Cursor  │  │   Kiro   │  │  Claude  │   │
│  │ Desktop  │  │          │  │          │  │  Desktop │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                         │                                    │
│                    MCP Protocol                              │
│                    (stdio/SSE)                               │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Docker Host (localhost)                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  GitHub MCP Server Container                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ghcr.io/github/github-mcp-server:latest        │  │  │
│  │  │                                                   │  │  │
│  │  │  - Repository管理                                │  │  │
│  │  │  - Issue/PR操作                                  │  │  │
│  │  │  - GitHub Actions連携                            │  │  │
│  │  │  - Code Search                                   │  │  │
│  │  │  - Discussions                                   │  │  │
│  │  │  - Projects                                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  Environment:                                           │  │
│  │  - GITHUB_PERSONAL_ACCESS_TOKEN (Personal Access Token)                │  │
│  │  - GITHUB_API_URL (optional)                           │  │
│  │                                                         │  │
│  │  Ports:                                                 │  │
│  │  - 3000:3000 (SSE endpoint)                            │  │
│  │                                                         │  │
│  │  Volumes:                                               │  │
│  │  - ./config:/app/config (設定永続化)                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub API                                │
│  - REST API v3                                               │
│  - GraphQL API v4                                            │
│  - GitHub Actions API                                        │
└─────────────────────────────────────────────────────────────┘
```

## コア機能

### 1. GitHub MCP Server (公式イメージ)

**イメージ**: `ghcr.io/github/github-mcp-server:latest`

**提供機能**:
- リポジトリ管理 (作成、削除、設定)
- Issue/PR操作 (作成、更新、コメント、レビュー)
- GitHub Actions連携 (ワークフロー実行、ログ取得)
- Code Search (コード検索、ファイル検索)
- Discussions (ディスカッション管理)
- Projects (プロジェクト管理)

**必須環境変数**:
- `GITHUB_PERSONAL_ACCESS_TOKEN`: Personal Access Token (PAT)
  - 推奨スコープ: `repo`, `workflow`, `read:org`, `read:user`

**オプション環境変数**:
- `GITHUB_API_URL`: GitHub Enterprise Server用 (デフォルト: `https://api.github.com`)

### 2. Docker常駐サービス

**特徴**:
- 常時起動 (`restart: unless-stopped`)
- ヘルスチェック機能
- ログローテーション
- 自動再起動

**リソース制限(暫定)**:
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### 3. IDE統合設定支援

各IDEに対応した設定ファイル自動生成機能を提供。

#### VS Code / Cursor
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-github",
        "node",
        "/app/dist/index.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

#### Claude Desktop
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-github",
        "node",
        "/app/dist/index.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

#### Kiro
```json
{
  "mcp": {
    "servers": {
      "github": {
        "type": "docker",
        "container": "mcp-github",
        "command": "node /app/dist/index.js",
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
```

## ディレクトリ構成

```
Mcp-Docker/
├── docker-compose.yml              # メインサービス定義
├── .env.template                   # 環境変数テンプレート
├── .env                           # 環境変数 (gitignore)
├── config/
│   └── github-mcp/
│       ├── settings.json          # サーバー設定
│       └── cache/                 # キャッシュディレクトリ
├── scripts/
│   ├── setup.sh                   # 初期セットアップ
│   ├── generate-ide-config.sh     # IDE設定生成
│   └── health-check.sh            # ヘルスチェック
├── docs/
│   ├── setup/
│   │   ├── vscode.md             # VS Code設定ガイド
│   │   ├── cursor.md             # Cursor設定ガイド
│   │   ├── kiro.md               # Kiro設定ガイド
│   │   └── claude-desktop.md     # Claude Desktop設定ガイド
│   └── api/
│       └── github-mcp-api.md     # API仕様
└── examples/
    └── ide-configs/
        ├── vscode/
        │   └── settings.json
        ├── cursor/
        │   └── settings.json
        ├── kiro/
        │   └── mcp.json
        └── claude-desktop/
            └── claude_desktop_config.json
```

## セキュリティ設計

### 1. トークン管理

**原則**:
- トークンは環境変数で管理
- `.env`ファイルは`.gitignore`に追加
- コンテナ内でのトークン暗号化

**推奨PAT設定**:
```
スコープ:
  ✓ repo (フルアクセス)
  ✓ workflow (GitHub Actions)
  ✓ read:org (組織情報)
  ✓ read:user (ユーザー情報)
  ✓ project (プロジェクト管理)

有効期限: 90日 (定期更新)
```

### 2. ネットワークセキュリティ

- コンテナは専用ネットワーク (`mcp-network`)
- 外部公開ポートは最小限 (SSE用3000番のみ)
- ローカルホストからのアクセスのみ許可

### 3. ログ管理

- 機密情報のマスキング
- ログローテーション (10MB × 3ファイル)
- 構造化ログ (JSON形式)

## パフォーマンス設計

### 1. キャッシュ戦略

- GitHub API応答のキャッシュ (5分)
- リポジトリメタデータのキャッシュ (1時間)
- 永続化ボリュームでキャッシュ保持

### 2. レート制限対応

- GitHub API レート制限の監視
- 自動リトライ (Exponential Backoff)
- レート制限情報のログ出力

### 3. リソース最適化

- メモリ制限: 512MB
- CPU制限: 1コア
- 自動スケーリング (将来対応)

## 運用設計

### 1. ヘルスチェック

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 2. ログ管理

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. 自動再起動

```yaml
restart: unless-stopped
```

### 4. バックアップ

- 設定ファイルの定期バックアップ
- キャッシュの定期クリーンアップ
- トークンの定期更新リマインダー

## IDE統合フロー

### 1. 初期セットアップ

```bash
# 1. リポジトリクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 2. 環境変数設定
cp .env.template .env
# .envファイルにGITHUB_PERSONAL_ACCESS_TOKENを設定

# 3. サービス起動
docker compose up -d

# 4. IDE設定生成
./scripts/generate-ide-config.sh --ide vscode
```

### 2. IDE設定

各IDEの設定ファイルに生成された設定を追加。

### 3. 動作確認

```bash
# ヘルスチェック
./scripts/health-check.sh

# ログ確認
docker compose logs -f github-mcp
```

## 拡張性設計

### 1. マルチサーバー対応

複数のGitHub組織/アカウントに対応:

```yaml
services:
  github-mcp-personal:
    image: ghcr.io/github/github-mcp-server:latest
    container_name: mcp-github-personal
    env_file: .env.personal

  github-mcp-work:
    image: ghcr.io/github/github-mcp-server:latest
    container_name: mcp-github-work
    env_file: .env.work
```

### 2. プラグイン対応

カスタム機能の追加:

```yaml
volumes:
  - ./plugins:/app/plugins
```

### 3. 監視・メトリクス

Prometheus/Grafana統合 (将来対応):

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

## テスト戦略

### 1. 統合テスト

- Docker起動テスト
- GitHub API接続テスト
- IDE統合テスト

### 2. E2Eテスト

- リポジトリ操作テスト
- Issue/PR操作テスト
- GitHub Actions連携テスト

### 3. パフォーマンステスト

- レスポンスタイム測定
- レート制限対応確認
- メモリ使用量監視

## マイルストーン

### Phase 1: 基盤構築 (1週間)
- [x] 設計ドキュメント作成
- [ ] docker-compose.yml作成
- [ ] 環境変数テンプレート作成
- [ ] 基本セットアップスクリプト作成

### Phase 2: IDE統合 (1週間)
- [ ] VS Code設定生成
- [ ] Cursor設定生成
- [ ] Kiro設定生成
- [ ] Claude Desktop設定生成
- [ ] 設定ガイド作成

### Phase 3: 運用機能 (1週間)
- [ ] ヘルスチェック実装
- [ ] ログ管理設定
- [ ] バックアップスクリプト
- [ ] 監視ダッシュボード

### Phase 4: テスト・ドキュメント (1週間)
- [ ] 統合テスト作成
- [ ] E2Eテスト作成
- [ ] ユーザーガイド作成
- [ ] トラブルシューティングガイド

## 成功基準

- [ ] Docker起動成功率 99%以上
- [ ] GitHub API応答時間 < 500ms
- [ ] メモリ使用量 < 512MB
- [ ] 全IDE統合動作確認完了
- [ ] ドキュメント完全性 100%

## 参考資料

- [GitHub MCP Server公式](https://github.com/github/github-mcp-server)
- [Model Context Protocol仕様](https://modelcontextprotocol.io/)
- [Docker Compose仕様](https://docs.docker.com/compose/)
- [GitHub API v3](https://docs.github.com/en/rest)
- [GitHub GraphQL API v4](https://docs.github.com/en/graphql)
