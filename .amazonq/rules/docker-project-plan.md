# MCP Docker Environment - リポジトリ化計画

## Phase 1: リポジトリ設計・初期設定

### 1.1 リポジトリ構成設計
- **目的**: MCP統合Docker環境の管理・配布
- **対象**: GitHub/DateTime/CodeQL MCPサービス
- **技術スタック**: Docker, Docker Compose, Shell, YAML

### 1.2 ディレクトリ構造
```
mcp-docker/
├── .github/workflows/     # CI/CD設定
├── .amazonq/rules/        # 開発ルール
├── services/              # サービス別設定
├── scripts/               # 管理スクリプト
├── docs/                  # ドキュメント
├── tests/                 # 統合テスト
├── Dockerfile             # 統合イメージ
├── docker-compose.yml     # サービス定義
├── Makefile              # 開発コマンド
├── .gitignore            # Git除外設定
├── .env.template         # 環境変数テンプレート
└── README.md             # プロジェクト説明
```

### 1.3 初期タスク
- [x] GitHubリポジトリ作成
- [x] 基本ファイル整備（.gitignore, LICENSE, CONTRIBUTING.md）
- [x] Docker特化ルール策定
- [ ] CI/CD設計

### 1.4 Exit Criteria
- リポジトリ作成完了
- 基本構造確立
- 開発ルール合意

## Phase 2: Docker環境実装・CI/CD構築

### 2.1 Docker設定最適化
- 統合Dockerfileの改善
- マルチステージビルド導入
- セキュリティ強化（rootless実行）

### 2.2 CI/CD実装
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t mcp-docker .
      - name: Test services
        run: make test
```

### 2.3 品質チェック
- Dockerfile linting (hadolint)
- YAML validation
- Shell script checking (shellcheck)
- セキュリティスキャン (Trivy)

### 2.4 Exit Criteria
- Docker build成功
- 全サービス起動確認
- CI/CD動作確認

## Phase 3: テスト・ドキュメント整備

### 3.1 統合テスト実装
```bash
# tests/integration_test.sh
#!/bin/bash
set -e

# サービス起動テスト
docker-compose up -d
sleep 10

# GitHub MCP接続テスト
curl -f http://localhost:8080/health || exit 1

# DateTime validator動作テスト
echo "2025-01-01" > test_date.txt
# 修正確認ロジック

# クリーンアップ
docker-compose down
```

### 3.2 ドキュメント整備
- [ ] README.md詳細化
- [ ] CONTRIBUTING.md作成
- [ ] API仕様書
- [ ] トラブルシューティングガイド

### 3.3 Exit Criteria
- 統合テスト完成
- ドキュメント完備
- 使用方法明確化

## Docker特化開発ルール

### コンテナ設計原則
- **単一責任**: 1コンテナ1サービス
- **軽量化**: Alpine Linux使用、不要パッケージ削除
- **セキュリティ**: 非rootユーザー実行、最小権限

### 設定管理
- 環境変数による設定注入
- シークレット管理（Docker secrets/環境変数）
- 設定ファイルのボリュームマウント

### テスト戦略
- **ビルドテスト**: Dockerfile構文・依存関係
- **起動テスト**: サービス正常起動確認
- **統合テスト**: サービス間連携確認
- **セキュリティテスト**: 脆弱性スキャン

### CI/CD要件
- **マトリクス**: Docker version × OS (Ubuntu/Windows/macOS)
- **キャッシュ**: Docker layer caching
- **セキュリティ**: イメージスキャン必須
- **リリース**: タグ付きイメージ自動push

## 進捗管理

### マイルストーン
1. **Week 1**: リポジトリ作成・基本構造
2. **Week 2**: CI/CD構築・Docker最適化
3. **Week 3**: テスト実装・ドキュメント整備
4. **Week 4**: リリース準備・品質確認

### 優先度
- **High**: リポジトリ作成、CI/CD、セキュリティ
- **Medium**: テスト自動化、ドキュメント
- **Low**: 高度な機能、パフォーマンス最適化

## リスク・対策

### 技術リスク
- **Docker互換性**: 複数バージョンでのテスト
- **セキュリティ**: 定期的な脆弱性スキャン
- **依存関係**: ベースイメージ更新戦略

### 運用リスク
- **設定管理**: 環境変数の標準化
- **トラブルシューティング**: ログ集約・監視
- **バックアップ**: 設定・データの保護

---

**次のアクション**: Phase 1の実行開始
- GitHubリポジトリ作成
- .gitignore, LICENSE等の基本ファイル作成
- Docker特化ルールの詳細化