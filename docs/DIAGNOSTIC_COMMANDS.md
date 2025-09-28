# 診断コマンド完全ガイド

## 概要

GitHub Actions Simulatorの診断機能とデバッグコマンドの完全なリファレンスガイドです。システムの健康状態チェック、ハングアップ問題の診断、パフォーマンス分析などの機能について詳しく説明します。

## 🔧 基本診断コマンド

### システム全体の診断

```bash
# 包括的なシステムヘルスチェック
uv run python main.py actions diagnose

# 診断結果をJSON形式で出力
uv run python main.py actions diagnose --output-format json

# 診断結果をファイルに保存
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json
```

### 詳細診断オプション

```bash
# パフォーマンス分析を含む診断
uv run python main.py actions diagnose --include-performance

# 実行トレース分析を含む診断
uv run python main.py actions diagnose --include-trace

# 全ての詳細分析を含む診断
uv run python main.py actions diagnose --include-performance --include-trace
```

## 📊 診断項目の詳細

### 1. Docker接続性チェック

**チェック内容:**
- Dockerコマンドの存在確認
- Docker daemonとの通信テスト
- Dockerバージョンの確認

**正常な結果例:**
```json
{
  "component": "Docker接続性",
  "status": "OK",
  "message": "Docker接続は正常です",
  "details": {
    "version": "Docker version 24.0.0, build 98fdcd7",
    "docker_path": "/usr/bin/docker"
  }
}
```

**よくある問題と解決策:**
```bash
# Docker daemonが起動していない場合
sudo systemctl start docker

# 権限問題の場合
sudo usermod -aG docker $USER
newgrp docker
```

### 2. actバイナリチェック

**チェック内容:**
- actバイナリの存在確認
- actのバージョン確認
- 基本機能テスト

**正常な結果例:**
```json
{
  "component": "actバイナリ",
  "status": "OK",
  "message": "actバイナリは正常に動作しています",
  "details": {
    "version": "act version 0.2.50",
    "path": "/usr/local/bin/act"
  }
}
```

**インストール方法:**
```bash
# Homebrewでのインストール
brew install act

# curlでのインストール
curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### 3. コンテナ権限チェック

**チェック内容:**
- ユーザーのDocker権限確認
- Dockerソケットアクセス権限
- dockerグループメンバーシップ

**権限問題の解決:**
```bash
# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# グループ変更を即座に反映
newgrp docker

# 権限確認
groups | grep docker
```

### 4. Dockerソケットアクセス

**チェック内容:**
- Docker APIへの接続テスト
- システム情報の取得
- ネットワーク設定の確認

**トラブルシューティング:**
```bash
# Docker socketの権限確認
ls -la /var/run/docker.sock

# Docker daemonの状態確認
sudo systemctl status docker

# Docker情報の詳細確認
docker system info
```

### 5. コンテナ通信テスト

**チェック内容:**
- テストコンテナの実行
- ボリュームマウントテスト
- ネットワーク通信確認

**通信問題の解決:**
```bash
# ネットワークの確認
docker network ls

# mcp-networkの再作成
docker network rm mcp-network
docker network create mcp-network
```

### 6. 環境変数チェック

**チェック内容:**
- 重要な環境変数の確認
- PATH設定の検証
- 設定値の妥当性チェック

**推奨環境変数設定:**
```bash
export ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=600
export ACTIONS_SIMULATOR_ENGINE=enhanced
export ACT_CACHE_DIR=~/.cache/act
export DOCKER_BUILDKIT=1
```

### 7. リソース使用量チェック

**チェック内容:**
- ディスク使用量の確認
- メモリ使用量の確認
- Docker関連リソースの確認

**リソース最適化:**
```bash
# Dockerリソースのクリーンアップ
docker system prune -a

# 不要なボリュームの削除
docker volume prune

# 不要なネットワークの削除
docker network prune
```

## 🚀 ワークフロー実行時の診断

### 事前診断付き実行

```bash
# ワークフロー実行前にシステム診断を実行
uv run python main.py actions simulate .github/workflows/ci.yml --diagnose

# 診断でエラーが検出された場合は実行を中止
uv run python main.py actions simulate .github/workflows/ci.yml --diagnose --strict
```

### 強化機能付き実行

```bash
# 強化されたエラー検出・プロセス監視を使用
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced

# 診断機能も同時に有効化
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --diagnose

# 自動復旧機能も有効化
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery
```

### パフォーマンス監視付き実行

```bash
# リアルタイムパフォーマンス監視
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics

# 監視間隔の調整
export ACTIONS_SIMULATOR_PERFORMANCE_INTERVAL=1.0
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics
```

## 🛠️ デバッグバンドル機能

### デバッグバンドルの作成

```bash
# ハングアップ発生時に自動でデバッグバンドルを作成
uv run python main.py actions simulate .github/workflows/ci.yml --create-debug-bundle

# 出力ディレクトリを指定
uv run python main.py actions simulate .github/workflows/ci.yml --create-debug-bundle --debug-bundle-dir ./debug_output

# 手動でデバッグバンドルを作成
uv run python main.py actions diagnose --create-debug-bundle
```

### デバッグバンドルの内容

デバッグバンドルには以下の情報が含まれます：

1. **システム診断結果** (`diagnosis.json`)
2. **実行トレース情報** (`execution_trace.json`)
3. **プロセス状態スナップショット** (`process_state.json`)
4. **Docker環境詳細** (`docker_info.json`)
5. **ログファイル** (`logs/`)
6. **環境変数情報** (`environment.json`)
7. **エラーレポート** (`error_report.json`)

### デバッグバンドルの分析

```bash
# デバッグバンドルの展開
tar -xzf debug_bundle_20250928_120000.tar.gz

# 診断結果の確認
cat debug_bundle/diagnosis.json | jq '.results[] | select(.status != "OK")'

# エラーレポートの確認
cat debug_bundle/error_report.json | jq '.issues'

# 実行トレースの確認
cat debug_bundle/execution_trace.json | jq '.stages'
```

## 📈 パフォーマンス分析

### 監視項目

1. **CPU使用率** - プロセスのCPU消費量
2. **メモリ使用量** - プロセスのメモリ消費量
3. **ディスクI/O** - ファイル読み書き量
4. **ネットワーク通信** - Docker API通信量
5. **Docker操作応答時間** - Docker操作の実行時間

### パフォーマンス分析の実行

```bash
# 詳細なパフォーマンス分析
uv run python main.py actions diagnose --include-performance

# 実行トレースと組み合わせた分析
uv run python main.py actions diagnose --include-performance --include-trace
```

### パフォーマンス結果の解釈

```json
{
  "performance_metrics": {
    "cpu_usage_percent": 15.2,
    "memory_usage_mb": 256.5,
    "disk_io_mb": 12.3,
    "network_operations": 45,
    "docker_response_time_ms": 150.2,
    "total_execution_time_seconds": 45.8
  }
}
```

## 🔄 自動復旧機能

### 復旧メカニズム

1. **Docker再接続** - Docker daemon接続の自動復旧
2. **プロセス再起動** - ハングしたプロセスの安全な再起動
3. **バッファクリア** - 出力バッファの詰まり解消
4. **コンテナリセット** - コンテナ状態の初期化

### 自動復旧の有効化

```bash
# 自動復旧機能付きでワークフローを実行
uv run python main.py actions simulate .github/workflows/ci.yml --auto-recovery

# 強化機能と組み合わせて使用
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery
```

### 復旧統計の確認

```json
{
  "recovery_statistics": {
    "docker_reconnections": 2,
    "process_restarts": 1,
    "buffer_clears": 3,
    "container_resets": 1,
    "total_recovery_attempts": 7,
    "successful_recoveries": 6
  }
}
```

## 🚨 緊急時の対応

### 即座に実行すべきコマンド

```bash
# 1. システム診断の実行
uv run python main.py actions diagnose

# 2. Docker環境の確認
docker system info
docker ps -a

# 3. 実行中プロセスの確認
ps aux | grep act
ps aux | grep docker

# 4. リソース使用量の確認
free -h
df -h
docker system df
```

### 緊急停止手順

```bash
# 1. 実行中のコンテナを強制停止
docker compose down --timeout 10

# 2. actions-simulatorコンテナを停止
docker stop $(docker ps -q --filter "name=actions-simulator")

# 3. Docker環境のリセット
make clean
docker system prune -a
```

## 📋 診断結果の解釈

### ステータスレベル

| ステータス | アイコン | 意味 | 対応レベル |
|-----------|---------|------|-----------|
| OK | ✅ | 正常動作 | 対応不要 |
| WARNING | ⚠️ | 警告あり | 推奨事項を確認 |
| ERROR | ❌ | エラー検出 | 即座に修正が必要 |

### 推奨事項の優先度

1. **高優先度** - システムの基本動作に影響する問題
2. **中優先度** - パフォーマンスや安定性に影響する問題
3. **低優先度** - 最適化や改善に関する推奨事項

## 🔗 関連コマンド

### Docker関連

```bash
# Docker環境の詳細確認
docker version
docker system info
docker system df

# ネットワーク関連
docker network ls
docker network inspect mcp-network

# コンテナ関連
docker ps -a
docker logs <container_name>
```

### システム関連

```bash
# プロセス確認
ps aux | grep -E "(act|docker)"
pgrep -f "act|docker"

# リソース確認
top -p $(pgrep -d, -f "act|docker")
htop -p $(pgrep -d, -f "act|docker")

# ネットワーク確認
netstat -tulpn | grep -E "(8000|8080)"
ss -tulpn | grep -E "(8000|8080)"
```

## 📞 サポート情報の収集

### 基本情報収集スクリプト

```bash
#!/bin/bash
# support_info_collector.sh

echo "=== GitHub Actions Simulator サポート情報 ===" > support_info.txt
echo "収集日時: $(date)" >> support_info.txt
echo "" >> support_info.txt

echo "=== システム情報 ===" >> support_info.txt
uname -a >> support_info.txt
echo "" >> support_info.txt

echo "=== Docker情報 ===" >> support_info.txt
docker version >> support_info.txt
docker-compose version >> support_info.txt
echo "" >> support_info.txt

echo "=== 診断結果 ===" >> support_info.txt
uv run python main.py actions diagnose --output-format json >> support_info.txt
echo "" >> support_info.txt

echo "=== Docker環境 ===" >> support_info.txt
docker system info >> support_info.txt
docker ps -a >> support_info.txt
echo "" >> support_info.txt

echo "サポート情報が support_info.txt に保存されました"
```

### 実行方法

```bash
chmod +x support_info_collector.sh
./support_info_collector.sh
```

## 🔗 関連ドキュメント

- [ハングアップ問題トラブルシューティング](./HANGUP_TROUBLESHOOTING.md)
- [基本トラブルシューティング](./TROUBLESHOOTING.md)
- [API仕様書](./API.md)
- [Docker統合実装サマリー](./docker-integration-implementation-summary.md)
- [自動復旧実装サマリー](./auto_recovery_implementation_summary.md)
- [パフォーマンス監視実装](./performance_monitoring_implementation.md)
