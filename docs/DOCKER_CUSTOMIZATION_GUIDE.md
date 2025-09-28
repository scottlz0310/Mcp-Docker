# Docker設定カスタマイズガイド

GitHub Actions Simulator の Docker 設定をカスタマイズするための包括的なガイドです。

## 📋 目次

- [概要](#概要)
- [基本的な使用方法](#基本的な使用方法)
- [開発環境設定](#開発環境設定)
- [本番環境設定](#本番環境設定)
- [パフォーマンス最適化](#パフォーマンス最適化)
- [セキュリティ設定](#セキュリティ設定)
- [監視・メトリクス](#監視メトリクス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

Docker Compose Override 機能を使用して、環境に応じた設定をカスタマイズできます。

### ファイル構成

```
├── docker-compose.yml                    # ベース設定
├── docker-compose.override.yml.sample    # カスタマイズテンプレート
├── docker-compose.override.yml           # 実際のカスタマイズ設定
└── monitoring/                           # 監視設定
    ├── prometheus.yml
    └── grafana/
        ├── dashboards/
        └── datasources/
```

## 基本的な使用方法

### 1. テンプレートのコピー

```bash
# カスタマイズテンプレートをコピー
cp docker-compose.override.yml.sample docker-compose.override.yml

# 必要に応じて編集
vi docker-compose.override.yml
```

### 2. 設定の確認

```bash
# 最終的な設定を確認
docker-compose config

# 特定のサービスの設定を確認
docker-compose config actions-simulator
```

### 3. サービスの起動

```bash
# 開発環境での起動
docker-compose up -d actions-simulator actions-shell

# 本番環境での起動
docker-compose up -d actions-server

# プロファイル指定での起動
docker-compose --profile monitoring up -d
```

## 開発環境設定

### リソース設定の最適化

```yaml
services:
  actions-simulator:
    deploy:
      resources:
        limits:
          memory: 8G        # 開発時は大きめに設定
          cpus: "6.0"
        reservations:
          memory: 2G
          cpus: "2.0"
```

### デバッグ設定の有効化

```yaml
environment:
  - ACTIONS_SIMULATOR_VERBOSE=true
  - ACTIONS_SIMULATOR_DEBUG=true
  - ACT_LOG_LEVEL=debug
  - PYTHONUNBUFFERED=1
```

### ホットリロード対応

```yaml
volumes:
  # ソースコードのマウント
  - ./src:/app/src:rw
  - ./services:/app/services:rw
  - ./main.py:/app/main.py:rw

  # 設定ファイルのマウント
  - ./pyproject.toml:/app/pyproject.toml:ro
  - ./.env:/app/.env:ro
```

### 開発ツールの追加

```yaml
volumes:
  # 開発ツール用キャッシュ
  - pip-cache:/app/.cache/pip:rw
  - pytest-cache:/app/.pytest_cache:rw
  - mypy-cache:/app/.mypy_cache:rw
```

## 本番環境設定

### セキュリティ強化

```yaml
services:
  actions-server:
    # 読み取り専用マウント
    volumes:
      - ./.github:/app/.github:ro
      - ./pyproject.toml:/app/pyproject.toml:ro

    # セキュリティ設定
    environment:
      - ACTIONS_SIMULATOR_SECURITY_MODE=strict
      - MASK_SECRETS_IN_LOGS=true
      - ACTIONS_SIMULATOR_AUDIT_LOG=true
```

### リソース制限

```yaml
deploy:
  resources:
    limits:
      memory: 6G        # 本番環境での安定した制限
      cpus: "4.0"
    reservations:
      memory: 2G        # 最小リソース保証
      cpus: "1.0"
```

### 高可用性設定

```yaml
deploy:
  replicas: 3           # 複数インスタンス
  placement:
    constraints:
      - node.role == manager
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
```

## パフォーマンス最適化

### CPU最適化

```yaml
environment:
  # 並列処理の最適化
  - ACT_PARALLEL_JOBS=4
  - COMPOSE_PARALLEL_LIMIT=8
  - ACTIONS_SIMULATOR_MAX_CONCURRENT_WORKFLOWS=5

deploy:
  resources:
    limits:
      cpus: "6.0"       # CPU使用量上限
    reservations:
      cpus: "2.0"       # CPU予約
```

### メモリ最適化

```yaml
environment:
  # メモリ使用量の最適化
  - PYTHONDONTWRITEBYTECODE=1   # .pycファイル生成無効
  - UV_CACHE_DIR=/app/.cache/uv
  - ACT_CACHE_DIR=/opt/act/cache

deploy:
  resources:
    limits:
      memory: 8G        # メモリ上限
    reservations:
      memory: 2G        # メモリ予約
```

### ディスクI/O最適化

```yaml
volumes:
  # キャッシュボリュームの活用
  - act-cache:/opt/act/cache:rw
  - uv-cache:/app/.cache/uv:rw
  - pip-cache:/app/.cache/pip:rw

# ボリューム設定
volumes:
  act-cache:
    driver: local
    driver_opts:
      type: tmpfs       # メモリ上のファイルシステム
      device: tmpfs
      o: size=2g,uid=1000
```

### ネットワーク最適化

```yaml
networks:
  mcp-network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: mcp-br0
      com.docker.network.driver.mtu: 1500
    ipam:
      config:
        - subnet: 172.18.0.0/16
```

## セキュリティ設定

### コンテナセキュリティ

```yaml
services:
  actions-simulator:
    # 権限の最小化
    user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
    privileged: false

    # Capability の制限
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
      - DAC_OVERRIDE

    # セキュリティオプション
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
```

### ネットワークセキュリティ

```yaml
networks:
  mcp-network:
    driver: bridge
    internal: true      # 外部ネットワークアクセス制限

  external-network:
    external: true      # 必要な場合のみ外部接続
```

### シークレット管理

```yaml
secrets:
  github_token:
    file: ./secrets/github_token.txt

services:
  actions-simulator:
    secrets:
      - github_token
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN_FILE=/run/secrets/github_token
```

## 監視・メトリクス

### Prometheus 監視

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus:rw
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=200h'
```

### Grafana ダッシュボード

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana:rw
      - ./monitoring/grafana:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
```

### ログ監視

```yaml
services:
  actions-simulator:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
        labels: "service=actions-simulator,env=production"
```

## トラブルシューティング

### 一般的な問題と解決方法

#### 1. メモリ不足エラー

**症状**: コンテナが OOMKilled で終了する

**解決方法**:
```yaml
deploy:
  resources:
    limits:
      memory: 8G        # メモリ制限を増加
    reservations:
      memory: 2G        # 最小メモリを確保
```

#### 2. CPU使用率が高い

**症状**: システムが重くなる

**解決方法**:
```yaml
deploy:
  resources:
    limits:
      cpus: "4.0"       # CPU使用量を制限
environment:
  - ACT_PARALLEL_JOBS=2 # 並列処理数を削減
```

#### 3. ディスク容量不足

**症状**: ログやキャッシュでディスクが満杯

**解決方法**:
```yaml
logging:
  options:
    max-size: "50m"     # ログサイズを制限
    max-file: "3"       # ログファイル数を制限

# 定期的なクリーンアップ
command: |
  bash -c "
    # 古いログの削除
    find /app/logs -name '*.log' -mtime +7 -delete
    # キャッシュのクリーンアップ
    docker system prune -f
    exec your-main-command
  "
```

#### 4. ネットワーク接続エラー

**症状**: 外部APIへの接続が失敗する

**解決方法**:
```yaml
networks:
  mcp-network:
    driver: bridge
    internal: false     # 外部接続を許可

# プロキシ設定（企業環境）
environment:
  - HTTP_PROXY=http://proxy.company.com:8080
  - HTTPS_PROXY=http://proxy.company.com:8080
  - NO_PROXY=localhost,127.0.0.1,.local
```

### デバッグ用コマンド

```bash
# 設定の確認
docker-compose config

# サービスの状態確認
docker-compose ps

# ログの確認
docker-compose logs -f actions-simulator

# リソース使用量の確認
docker stats

# コンテナ内でのデバッグ
docker-compose exec actions-simulator bash

# ヘルスチェック状態の確認
docker inspect --format='{{.State.Health.Status}}' mcp-actions-simulator
```

### パフォーマンス分析

```bash
# CPU使用率の監視
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# メモリ使用量の詳細
docker exec mcp-actions-simulator cat /proc/meminfo

# ディスクI/O監視
docker exec mcp-actions-simulator iostat -x 1

# ネットワーク監視
docker exec mcp-actions-simulator netstat -i
```

## 環境別設定例

### 開発環境 (development)

```yaml
# docker-compose.override.yml
services:
  actions-simulator:
    environment:
      - NODE_ENV=development
      - LOG_LEVEL=debug
      - ACTIONS_SIMULATOR_DEBUG=true
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: "6.0"
    volumes:
      - ./src:/app/src:rw
      - ./tests:/app/tests:rw
```

### ステージング環境 (staging)

```yaml
services:
  actions-simulator:
    environment:
      - NODE_ENV=staging
      - LOG_LEVEL=info
      - ACTIONS_SIMULATOR_DEBUG=false
    deploy:
      resources:
        limits:
          memory: 6G
          cpus: "4.0"
      replicas: 2
```

### 本番環境 (production)

```yaml
services:
  actions-simulator:
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=warning
      - ACTIONS_SIMULATOR_AUDIT_LOG=true
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
      replicas: 3
      placement:
        constraints:
          - node.role == manager
```

## まとめ

Docker Compose Override を活用することで、環境に応じた柔軟な設定が可能になります。

### 重要なポイント

1. **段階的な設定**: 開発→ステージング→本番の順で設定を厳格化
2. **リソース管理**: 適切なリソース制限と予約の設定
3. **セキュリティ**: 最小権限の原則と適切な権限設定
4. **監視**: メトリクス収集とログ管理の設定
5. **保守性**: 設定の文書化と定期的な見直し

### 次のステップ

- [環境変数設定ガイド](.env.example) を参照
- [トラブルシューティングガイド](TROUBLESHOOTING.md) を確認
- [セキュリティガイド](SECURITY.md) を読む
- [パフォーマンス最適化ガイド](PERFORMANCE.md) を参照
