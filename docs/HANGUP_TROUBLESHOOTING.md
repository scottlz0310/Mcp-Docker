# GitHub Actions Simulator ハングアップ問題 トラブルシューティングガイド

## 概要

GitHub Actions Simulatorでワークフローがハングアップする問題の診断と解決方法を説明します。このガイドでは、一般的なハングアップシナリオ、診断コマンド、および解決策を提供します。

## 🚨 緊急対応手順

### 1. 即座に実行すべき診断コマンド

```bash
# システム全体の診断を実行
uv run python main.py actions diagnose

# 詳細な診断（パフォーマンス分析含む）
uv run python main.py actions diagnose --include-performance --include-trace

# Docker統合の確認
docker system info
docker ps -a
```

### 2. ハングアップ発生時の緊急停止

```bash
# 実行中のコンテナを強制停止
docker compose down --timeout 10

# 全てのactions-simulatorコンテナを停止
docker stop $(docker ps -q --filter "name=actions-simulator")

# 必要に応じてDocker環境をリセット
make clean
```

## 📋 一般的なハングアップシナリオと解決策

### シナリオ 1: Docker Socket通信の問題

#### 症状
- ワークフロー選択後に無応答
- `act` コマンドが Docker daemon に接続できない
- タイムアウトエラー（600秒後）

#### 診断方法
```bash
# Docker接続の確認
docker info

# Docker socket権限の確認
ls -la /var/run/docker.sock

# 診断サービスでの確認
uv run python main.py actions diagnose
```

#### 解決策
```bash
# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
newgrp docker

# Docker Desktopの再起動
# GUI: Docker Desktop → Restart

# Docker daemonの再起動（Linux）
sudo systemctl restart docker
```

### シナリオ 2: act バイナリの問題

#### 症状
- `act` コマンドが見つからない
- `act` の実行権限がない
- 古いバージョンの `act` による互換性問題

#### 診断方法
```bash
# actバイナリの確認
which act
act --version

# 診断サービスでの詳細確認
uv run python main.py actions diagnose
```

#### 解決策
```bash
# actのインストール（Homebrew）
brew install act

# actのインストール（curl）
curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 権限の修正
chmod +x $(which act)
```

### シナリオ 3: プロセス監視とタイムアウトの問題

#### 症状
- プロセスが応答しないが終了もしない
- stdout/stderr の出力が停止
- CPU使用率が0%のまま

#### 診断方法
```bash
# 実行中のプロセス確認
ps aux | grep act
ps aux | grep docker

# 詳細診断の実行
uv run python main.py actions diagnose --include-performance
```

#### 解決策
```bash
# タイムアウト値の調整
export ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=300

# 強化されたプロセス監視を有効化
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --diagnose
```

### シナリオ 4: メモリ・リソース不足

#### 症状
- システムが重くなる
- Docker操作が遅い
- OOM (Out of Memory) エラー

#### 診断方法
```bash
# システムリソースの確認
free -h
df -h
docker system df

# 診断サービスでのリソースチェック
uv run python main.py actions diagnose
```

#### 解決策
```bash
# Dockerリソースのクリーンアップ
docker system prune -a
docker volume prune

# 不要なコンテナの削除
docker container prune

# メモリ制限の設定（docker-compose.yml）
# services:
#   actions-simulator:
#     mem_limit: 2g
```

### シナリオ 5: ネットワーク・ファイアウォールの問題

#### 症状
- Docker Hub からのイメージ取得に失敗
- コンテナ間通信ができない
- DNS解決に失敗

#### 診断方法
```bash
# ネットワーク接続の確認
ping docker.io
nslookup docker.io

# Dockerネットワークの確認
docker network ls
docker network inspect mcp-network
```

#### 解決策
```bash
# Dockerネットワークの再作成
docker network rm mcp-network
docker network create mcp-network

# DNS設定の確認・修正
# /etc/docker/daemon.json に DNS設定を追加
```

## 🔧 診断コマンド詳細ガイド

### 基本診断コマンド

```bash
# システム全体の健康状態チェック
uv run python main.py actions diagnose

# JSON形式での診断結果出力
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json
```

### 詳細診断コマンド

```bash
# パフォーマンス分析を含む診断
uv run python main.py actions diagnose --include-performance

# 実行トレース分析を含む診断
uv run python main.py actions diagnose --include-trace

# 全ての詳細分析を含む診断
uv run python main.py actions diagnose --include-performance --include-trace
```

### ワークフロー実行時の診断

```bash
# 事前診断付きでワークフローを実行
uv run python main.py actions simulate .github/workflows/ci.yml --diagnose

# 強化されたラッパーと診断を使用
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --diagnose

# パフォーマンス監視付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics
```

## 📊 診断結果の解釈ガイド

### ステータスの意味

| ステータス | アイコン | 意味 | 対応 |
|-----------|---------|------|------|
| OK | ✅ | 正常 | 対応不要 |
| WARNING | ⚠️ | 警告 | 推奨事項を確認 |
| ERROR | ❌ | エラー | 即座に修正が必要 |

### 診断項目の詳細

#### Docker接続性
- **正常**: Docker daemonとの通信が正常
- **警告**: 接続は可能だが応答が遅い
- **エラー**: Docker daemonに接続できない

#### actバイナリ
- **正常**: actが正しくインストールされ動作する
- **警告**: 古いバージョンまたは設定に問題
- **エラー**: actが見つからないまたは実行できない

#### コンテナ権限
- **正常**: 適切な権限でDockerを使用可能
- **警告**: 一部の権限に制限がある
- **エラー**: Docker操作に必要な権限がない

#### リソース使用量
- **正常**: 十分なリソースが利用可能
- **警告**: リソース使用量が高い
- **エラー**: リソース不足でハングアップの可能性

## 🛠️ デバッグバンドル機能

### デバッグバンドルの作成

ハングアップが発生した場合、詳細な診断情報を含むデバッグバンドルを作成できます：

```bash
# ハングアップ発生時にデバッグバンドルを自動作成
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --create-debug-bundle

# 手動でデバッグバンドルを作成
uv run python main.py actions diagnose --create-debug-bundle --debug-bundle-dir ./debug_output
```

### デバッグバンドルの内容

デバッグバンドルには以下の情報が含まれます：

- システム診断結果
- 実行トレース情報
- プロセス状態のスナップショット
- Docker環境の詳細
- ログファイル
- 環境変数情報
- エラーレポート

## 🔄 自動復旧機能

### 自動復旧の有効化

```bash
# 自動復旧機能付きでワークフローを実行
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery
```

### 復旧メカニズム

1. **Docker再接続**: Docker daemon接続の自動復旧
2. **プロセス再起動**: ハングしたプロセスの安全な再起動
3. **バッファクリア**: 出力バッファの詰まり解消
4. **コンテナリセット**: コンテナ状態の初期化

## 📈 パフォーマンス監視

### リアルタイム監視

```bash
# パフォーマンス監視付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics

# 監視間隔の調整
export ACTIONS_SIMULATOR_PERFORMANCE_INTERVAL=1.0
```

### 監視項目

- CPU使用率
- メモリ使用量
- ディスクI/O
- ネットワーク通信
- Docker操作の応答時間

## 🚀 予防策とベストプラクティス

### 定期的なメンテナンス

```bash
# 週次メンテナンススクリプト
#!/bin/bash
# システム診断の実行
uv run python main.py actions diagnose

# Dockerリソースのクリーンアップ
docker system prune -f

# 不要なイメージの削除
docker image prune -a -f
```

### 環境設定の最適化

```bash
# 推奨環境変数設定
export ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=600
export ACTIONS_SIMULATOR_ENGINE=enhanced
export ACT_CACHE_DIR=~/.cache/act
export DOCKER_BUILDKIT=1
```

### 監視とアラート

```bash
# ヘルスチェックスクリプト
#!/bin/bash
HEALTH_STATUS=$(uv run python main.py actions diagnose --output-format json | jq -r '.overall_status')

if [ "$HEALTH_STATUS" = "ERROR" ]; then
    echo "システムエラーが検出されました"
    # アラート送信処理
fi
```

## 📞 サポートとエスカレーション

### ログ収集

問題報告時には以下の情報を収集してください：

```bash
# 基本情報の収集
echo "=== システム情報 ===" > support_info.txt
uname -a >> support_info.txt
docker version >> support_info.txt
docker-compose version >> support_info.txt

echo "=== 診断結果 ===" >> support_info.txt
uv run python main.py actions diagnose --output-format json >> support_info.txt

echo "=== Docker情報 ===" >> support_info.txt
docker system info >> support_info.txt
docker ps -a >> support_info.txt
```

### Issue作成テンプレート

```markdown
## ハングアップ問題の詳細

### 環境情報
- OS: [例: Ubuntu 22.04]
- Docker: [例: 24.0.0]
- Docker Compose: [例: 2.20.0]
- act: [例: 0.2.50]

### 再現手順
1. [具体的な手順]
2. [実行したコマンド]
3. [発生した現象]

### 診断結果
```json
[uv run python main.py actions diagnose --output-format json の結果]
```

### ログ
```
[関連するログの内容]
```

### 期待する動作
[期待していた結果]

### 実際の動作
[実際に発生した結果]
```

## 🔗 関連ドキュメント

- [基本トラブルシューティング](./TROUBLESHOOTING.md)
- [API仕様書](./API.md)
- [Docker統合実装サマリー](./docker-integration-implementation-summary.md)
- [自動復旧実装サマリー](./auto_recovery_implementation_summary.md)
- [パフォーマンス監視実装](./performance_monitoring_implementation.md)
