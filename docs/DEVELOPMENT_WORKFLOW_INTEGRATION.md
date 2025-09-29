# 開発ワークフロー統合ガイド

## 概要

MCP Docker環境を既存の開発ワークフローに統合する方法を説明します。

## CI/CD統合

### GitHub Actions統合

#### 基本設定
```yaml
name: MCP Docker CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup MCP Docker
        run: |
          ./scripts/install-linux.sh
          make setup
      - name: Run Tests
        run: make test
```

#### 品質ゲート統合
```yaml
- name: Quality Gates
  uses: ./.github/workflows/quality-gates.yml
  with:
    quality_level: standard
```

### GitLab CI統合

```yaml
stages:
  - setup
  - test
  - quality

mcp-docker-test:
  stage: test
  script:
    - ./scripts/install-linux.sh
    - make test
  artifacts:
    reports:
      junit: test-results.xml
```

## 開発環境統合

### VS Code統合

#### 推奨拡張機能
- Docker
- Python
- GitHub Actions
- YAML

#### 設定ファイル（.vscode/settings.json）
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "docker.defaultRegistryPath": "ghcr.io",
  "files.associations": {
    "*.yml": "yaml"
  }
}
```

### Pre-commit統合

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mcp-docker-lint
        name: MCP Docker Lint
        entry: make lint
        language: system
        pass_filenames: false
```

## 品質管理統合

### コード品質チェック

```bash
# 統合品質チェック
make quality-check

# 個別チェック
make lint          # コード品質
make security      # セキュリティ
make test          # テスト実行
```

### 自動化されたレポート

- 品質メトリクス収集
- セキュリティスキャン結果
- テストカバレッジレポート
- パフォーマンス測定結果

## デプロイメント統合

### コンテナレジストリ

```bash
# GitHub Container Registry
docker tag mcp-docker:latest ghcr.io/username/mcp-docker:latest
docker push ghcr.io/username/mcp-docker:latest
```

### 環境別デプロイ

| 環境 | 設定 | 品質レベル |
|---|---|---|
| development | 基本チェック | basic |
| staging | 標準チェック | standard |
| production | 厳格チェック | strict |

## 監視・ログ統合

### ログ収集

```yaml
# docker-compose.yml
services:
  mcp-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### メトリクス収集

- Docker統計情報
- アプリケーションメトリクス
- パフォーマンス指標

## チーム開発統合

### ブランチ戦略

```bash
# 機能開発
git checkout -b feature/new-mcp-server
make setup
make test

# プルリクエスト前
make quality-check
git push origin feature/new-mcp-server
```

### レビュープロセス

1. 自動品質チェック実行
2. コードレビュー
3. 統合テスト実行
4. 品質ゲート通過確認

## トラブルシューティング

### 一般的な統合問題

- 環境変数の設定不備
- Docker権限の問題
- 依存関係の競合

詳細は[TROUBLESHOOTING.md](TROUBLESHOOTING.md)を参照してください。
