# GitHub Actions Simulator - コンテナ設定ガイド

## 概要

GitHub Actions Simulatorのコンテナ設定と環境セットアップに関する包括的なガイドです。このドキュメントでは、Docker統合の最適化、セキュリティ設定、ヘルスチェック機能について説明します。

## 目次

1. [クイックスタート](#クイックスタート)
2. [コンテナ設定詳細](#コンテナ設定詳細)
3. [環境変数設定](#環境変数設定)
4. [ヘルスチェック機能](#ヘルスチェック機能)
5. [トラブルシューティング](#トラブルシューティング)
6. [セキュリティ設定](#セキュリティ設定)
7. [パフォーマンス最適化](#パフォーマンス最適化)

## クイックスタート

### 1. 環境セットアップ

```bash
# Docker統合環境の自動セットアップ
make setup-docker

# または手動セットアップ
./scripts/setup-docker-integration.sh
```

### 2. ヘルスチェック実行

```bash
# 包括的ヘルスチェック
make health-check

# 個別チェック
make health-daemon    # Docker daemon接続確認
make health-socket    # Dockerソケットアクセス確認
make health-container # コンテナ実行テスト
make health-network   # ネットワーク設定確認
make health-act       # actバイナリ確認
```

### 3. Actions Simulator起動

```bash
# Actions Simulator環境の完全セットアップ
make actions-setup

# または段階的セットアップ
docker-compose --profile tools up -d actions-simulator
make actions-verify
```

## コンテナ設定詳細

### Actions Simulatorコンテナ

#### 基本設定

```yaml
services:
  actions-simulator:
    build: .
    container_name: mcp-actions-simulator
    profiles:
      - tools
    restart: unless-stopped
```

#### ボリュームマウント

| マウントポイント | 用途 | アクセス権限 |
|------------------|------|--------------|
| `./.github:/app/.github` | ワークフローファイル | 読み取り専用 |
| `./output:/app/output` | 実行結果出力 | 読み書き可能 |
| `./logs:/app/logs` | ログファイル出力 | 読み書き可能 |
| `act-cache:/opt/act/cache` | actキャッシュ | 読み書き可能 |
| `/var/run/docker.sock:/var/run/docker.sock` | Docker統合 | 読み書き可能 |
| `act-workspace:/github/workspace` | actワークスペース | 読み書き可能 |

#### リソース制限

```yaml
deploy:
  resources:
    limits:
      memory: 4G      # 最大メモリ使用量
      cpus: '4.0'     # 最大CPU使用量
    reservations:
      memory: 1G      # 最小メモリ予約
      cpus: '1.0'     # 最小CPU予約
```

#### セキュリティ設定

```yaml
privileged: false
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # ネットワークバインド
  - DAC_OVERRIDE      # ファイル権限オーバーライド
  - SETUID            # UID変更
  - SETGID            # GID変更
  - SYS_PTRACE        # プロセストレース
  - CHOWN             # ファイル所有者変更
  - FOWNER            # ファイル所有者操作
```

### Docker Health Checkサービス

Docker daemon接続の事前確認を行う専用サービス：

```yaml
docker-health-check:
  image: docker:24-cli
  container_name: mcp-docker-health-check
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  command: ["sh", "-c", "docker version && docker info && echo 'Docker daemon is healthy'"]
  restart: "no"
  profiles:
    - tools
```

## 環境変数設定

### 必須環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `DOCKER_HOST` | Dockerソケットパス | `unix:///var/run/docker.sock` |
| `ACT_CACHE_DIR` | actキャッシュディレクトリ | `/opt/act/cache` |
| `ACTIONS_SIMULATOR_ENGINE` | シミュレーションエンジン | `act` |
| `ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS` | タイムアウト時間 | `600` |

### 最適化設定

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `DOCKER_BUILDKIT` | BuildKit有効化 | `1` |
| `COMPOSE_DOCKER_CLI_BUILD` | Docker Compose CLI Build | `1` |
| `PYTHONUNBUFFERED` | Python出力バッファリング無効化 | `1` |
| `DOCKER_API_VERSION` | Docker APIバージョン | `1.41` |

### デバッグ設定

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `ACT_LOG_LEVEL` | actログレベル | `info` |
| `ACTIONS_RUNNER_DEBUG` | GitHub Actionsデバッグ | `false` |
| `RUNNER_DEBUG` | ランナーデバッグ | `false` |

### プラットフォーム設定

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `ACT_PLATFORM` | actプラットフォーム | `ubuntu-latest=catthehacker/ubuntu:act-latest` |
| `ACT_CONTAINER_DAEMON_SOCKET` | コンテナ内Dockerソケット | `/var/run/docker.sock` |

## ヘルスチェック機能

### コンテナヘルスチェック

Actions Simulatorコンテナには包括的なヘルスチェックが設定されています：

```yaml
healthcheck:
  test: ["CMD", "bash", "-c",
         "python -c 'import services.actions.docker_integration_checker; checker = services.actions.docker_integration_checker.DockerIntegrationChecker(); exit(0 if checker.verify_socket_access() else 1)' &&
          docker version --format '{{.Server.Version}}' > /dev/null 2>&1 &&
          act --version > /dev/null 2>&1"]
  interval: 30s
  timeout: 15s
  retries: 5
  start_period: 30s
```

### ヘルスチェック項目

1. **Dockerソケットアクセス**: Python統合チェッカーによる検証
2. **Docker daemon接続**: `docker version`コマンドによる確認
3. **actバイナリ**: `act --version`コマンドによる確認

### 手動ヘルスチェック

```bash
# 包括的ヘルスチェック
./scripts/docker-health-check.sh --comprehensive

# 個別チェック
./scripts/docker-health-check.sh --daemon-only
./scripts/docker-health-check.sh --socket-only
./scripts/docker-health-check.sh --container-test-only
./scripts/docker-health-check.sh --network-only
./scripts/docker-health-check.sh --act-only
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. Dockerソケットアクセス権限エラー

**症状**: `permission denied while trying to connect to the Docker daemon socket`

**解決方法**:
```bash
# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# ログアウト・ログインまたは新しいグループを適用
newgrp docker

# 権限確認
./scripts/docker-health-check.sh --socket-only
```

#### 2. actバイナリが見つからない

**症状**: `act: command not found`

**解決方法**:
```bash
# Homebrewでインストール
brew install act

# または手動インストール
curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# インストール確認
act --version
```

#### 3. Docker daemon接続エラー

**症状**: `Cannot connect to the Docker daemon`

**解決方法**:
```bash
# Docker Desktopの起動確認
docker version

# Docker daemonの再起動
sudo systemctl restart docker  # Linux
# または Docker Desktopを再起動

# 接続確認
./scripts/docker-health-check.sh --daemon-only
```

#### 4. コンテナ起動失敗

**症状**: コンテナが`Exited`状態になる

**解決方法**:
```bash
# ログ確認
docker logs mcp-actions-simulator

# 詳細検証
./scripts/verify-container-startup.sh --actions-simulator

# 環境変数確認
docker exec mcp-actions-simulator printenv | grep -E "(DOCKER|ACT|ACTIONS)"
```

#### 5. ヘルスチェック失敗

**症状**: コンテナのヘルスチェックが`unhealthy`

**解決方法**:
```bash
# ヘルスチェックログ確認
docker inspect mcp-actions-simulator --format='{{json .State.Health}}'

# 手動ヘルスチェック実行
docker exec mcp-actions-simulator python -c "
import services.actions.docker_integration_checker
checker = services.actions.docker_integration_checker.DockerIntegrationChecker()
results = checker.run_comprehensive_docker_check()
print(results)
"
```

### デバッグコマンド

```bash
# コンテナ内でのデバッグセッション
docker exec -it mcp-actions-simulator bash

# Docker統合の詳細確認
docker exec mcp-actions-simulator python -c "
from services.actions.docker_integration_checker import DockerIntegrationChecker
checker = DockerIntegrationChecker()
results = checker.run_comprehensive_docker_check()
for key, value in results.items():
    print(f'{key}: {value}')
"

# actの動作確認
docker exec mcp-actions-simulator act --list

# 環境変数の確認
docker exec mcp-actions-simulator env | sort
```

## セキュリティ設定

### 最小権限の原則

Actions Simulatorコンテナは最小限の権限で実行されます：

- `privileged: false`: 特権モード無効
- `cap_drop: ALL`: 全ての権限を削除
- 必要最小限の権限のみ追加

### Dockerグループアクセス

```yaml
group_add:
  - "${DOCKER_GID:-999}"  # Dockerグループへの追加
```

環境変数`DOCKER_GID`でDockerグループIDを指定します。

### ボリュームマウントセキュリティ

- ワークフローファイル: 読み取り専用
- Dockerソケット: 必要最小限のアクセス
- 出力ディレクトリ: 制限された書き込み権限

## パフォーマンス最適化

### リソース設定

```yaml
deploy:
  resources:
    limits:
      memory: 4G      # actの実行に十分なメモリ
      cpus: '4.0'     # 並列実行のためのCPU
    reservations:
      memory: 1G      # 基本動作保証
      cpus: '1.0'     # 最小CPU予約
```

### キャッシュ最適化

- `act-cache`ボリューム: actのキャッシュデータ永続化
- `act-workspace`ボリューム: ワークスペースデータ永続化
- Docker BuildKit: ビルド高速化

### ログ設定

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "100m"    # ログファイル最大サイズ
    max-file: "5"       # ログファイル保持数
    labels: "service=actions-simulator"
```

## 監視とメトリクス

### ヘルスチェック監視

```bash
# ヘルスチェック状態の継続監視
watch -n 30 'docker inspect mcp-actions-simulator --format="{{.State.Health.Status}}"'

# リソース使用量監視
docker stats mcp-actions-simulator
```

### ログ監視

```bash
# リアルタイムログ監視
docker logs -f mcp-actions-simulator

# 構造化ログの解析
docker logs mcp-actions-simulator 2>&1 | jq '.'
```

## 設定ファイル参照

### 主要設定ファイル

- `docker-compose.yml`: コンテナ設定
- `.env.template`: 環境変数テンプレート
- `scripts/setup-docker-integration.sh`: セットアップスクリプト
- `scripts/verify-container-startup.sh`: 検証スクリプト
- `scripts/docker-health-check.sh`: ヘルスチェックスクリプト

### 設定例

完全な設定例は`docker-compose.yml`の`actions-simulator`サービス定義を参照してください。

## 関連ドキュメント

- [GitHub Actions Simulator API](./API.md)
- [トラブルシューティングガイド](./TROUBLESHOOTING.md)
- [セキュリティガイド](./Security_tool_selection.md)
- [Docker統合実装サマリー](./docker-integration-implementation-summary.md)

## サポート

問題が発生した場合は、以下の手順で情報を収集してください：

1. ヘルスチェック実行: `make health-check`
2. コンテナ検証実行: `make actions-verify`
3. ログ収集: `docker logs mcp-actions-simulator > debug.log`
4. 環境情報収集: `docker exec mcp-actions-simulator env > env.log`

収集した情報と共にIssueを作成してください。
