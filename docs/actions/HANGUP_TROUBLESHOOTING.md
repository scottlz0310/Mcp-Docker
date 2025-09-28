# GitHub Actions Simulator ハングアップ問題 トラブルシューティングガイド

## 概要

GitHub Actions Simulatorでワークフローがハングアップする問題の診断と解決方法を説明します。このガイドでは、包括的な診断機能、強化されたプロセス監視、自動復旧メカニズム、デバッグバンドル作成機能を活用した問題解決方法を提供します。

## 🆕 新機能概要

### 診断・デバッグ機能
- **包括的システム診断**: Docker接続、act バイナリ、権限、リソース使用量の自動チェック
- **実行トレース機能**: ワークフロー実行の詳細な追跡とボトルネック分析
- **パフォーマンス監視**: リアルタイムリソース監視とメトリクス収集
- **デバッグバンドル**: ハングアップ時の詳細情報を自動収集・パッケージ化

### 強化されたプロセス管理
- **EnhancedActWrapper**: デッドロック検出とプロセス監視機能を統合
- **自動復旧機能**: Docker再接続、プロセス再起動、バッファクリアの自動実行
- **タイムアウト管理**: より精密なタイムアウト制御と段階的エスカレーション

### CLI統合機能
- `--diagnose`: 実行前システム診断
- `--enhanced`: 強化されたプロセス監視とエラー検出
- `--auto-recovery`: 自動復旧機能の有効化
- `--create-debug-bundle`: ハングアップ時のデバッグ情報自動収集
- `--show-performance-metrics`: リアルタイムパフォーマンス監視

## 🚨 緊急対応手順

### 1. 即座に実行すべき診断コマンド

```bash
# 包括的システム診断（推奨）
uv run python main.py actions diagnose

# 詳細診断（パフォーマンス・トレース分析含む）
uv run python main.py actions diagnose --include-performance --include-trace

# JSON形式で診断結果を保存
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json

# デバッグバンドルの手動作成
uv run python main.py actions diagnose --create-debug-bundle

# Docker環境の基本確認
docker system info
docker ps -a
docker system df
```

### 2. ハングアップ発生時の緊急停止

```bash
# 実行中のコンテナを強制停止
docker compose down --timeout 10

# 全てのactions-simulatorコンテナを停止
docker stop $(docker ps -q --filter "name=actions-simulator") 2>/dev/null || true

# プロセスの強制終了
pkill -f "act" 2>/dev/null || true
pkill -f "actions" 2>/dev/null || true

# Docker環境の完全リセット
make clean
docker system prune -f

# 自動復旧機能付きで再実行を試行
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery
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
- デッドロック状態の発生

#### 診断方法
```bash
# 実行中のプロセス確認
ps aux | grep act
ps aux | grep docker

# 詳細診断とパフォーマンス分析
uv run python main.py actions diagnose --include-performance --include-trace

# プロセス状態の詳細確認
pgrep -f "act|docker" | xargs -I {} ps -p {} -o pid,ppid,state,wchan,comm
```

#### 解決策
```bash
# 強化されたプロセス監視とデッドロック検出を有効化
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced

# 自動復旧機能付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery

# タイムアウト値の調整
export ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS=300
export ACTIONS_SIMULATOR_PERFORMANCE_INTERVAL=1.0

# デバッグバンドル自動作成付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --create-debug-bundle
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
# 包括的システム健康状態チェック
uv run python main.py actions diagnose

# JSON形式での診断結果出力
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json

# 診断結果の詳細表示
uv run python main.py actions diagnose --verbose
```

### 詳細診断コマンド

```bash
# パフォーマンス分析を含む診断
uv run python main.py actions diagnose --include-performance

# 実行トレース分析を含む診断
uv run python main.py actions diagnose --include-trace

# 全ての詳細分析を含む診断
uv run python main.py actions diagnose --include-performance --include-trace

# デバッグバンドル作成付き診断
uv run python main.py actions diagnose --create-debug-bundle --debug-bundle-dir ./debug_output
```

### ワークフロー実行時の診断

```bash
# 事前診断付きでワークフローを実行
uv run python main.py actions simulate .github/workflows/ci.yml --diagnose

# 強化されたプロセス監視と診断を使用
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --diagnose

# パフォーマンス監視付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics

# 実行トレース表示付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --show-execution-trace

# 全機能を有効化した実行
uv run python main.py actions simulate .github/workflows/ci.yml \
  --enhanced --diagnose --auto-recovery --create-debug-bundle \
  --show-performance-metrics --show-execution-trace
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

ハングアップが発生した場合、詳細な診断情報を含むデバッグバンドルを自動作成できます：

```bash
# ハングアップ発生時にデバッグバンドルを自動作成
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --create-debug-bundle

# 出力ディレクトリを指定してデバッグバンドルを作成
uv run python main.py actions simulate .github/workflows/ci.yml \
  --create-debug-bundle --debug-bundle-dir ./debug_output

# 手動でデバッグバンドルを作成
uv run python main.py actions diagnose --create-debug-bundle

# 詳細分析付きデバッグバンドル作成
uv run python main.py actions diagnose --create-debug-bundle \
  --include-performance --include-trace --debug-bundle-dir ./debug_output
```

### デバッグバンドルの内容

デバッグバンドルには以下の情報が含まれます：

#### 基本診断情報
- **システム診断結果** (`diagnosis.json`) - 全診断項目の詳細結果
- **環境変数情報** (`environment.json`) - システム・Docker・アプリケーション環境変数
- **システム情報** (`system_info.json`) - OS、ハードウェア、Docker情報

#### 実行・パフォーマンス情報
- **実行トレース情報** (`execution_trace.json`) - ワークフロー実行の詳細ログ
- **プロセス状態スナップショット** (`process_state.json`) - 実行時のプロセス状態
- **パフォーマンスメトリクス** (`performance_metrics.json`) - CPU、メモリ、I/O使用量

#### Docker・コンテナ情報
- **Docker環境詳細** (`docker_info.json`) - Docker daemon、ネットワーク、ボリューム情報
- **コンテナ状態** (`container_state.json`) - 実行中・停止中コンテナの詳細
- **Docker ログ** (`logs/docker/`) - コンテナログとDocker daemon ログ

#### エラー・ログ情報
- **エラーレポート** (`error_report.json`) - 検出されたエラーと推奨解決策
- **アプリケーションログ** (`logs/application/`) - アプリケーション実行ログ
- **システムログ** (`logs/system/`) - システムレベルのログ（可能な場合）

### デバッグバンドルの分析

```bash
# デバッグバンドルの展開
tar -xzf debug_bundle_$(date +%Y%m%d_%H%M%S).tar.gz

# 診断結果の確認（エラー・警告のみ）
cat debug_bundle/diagnosis.json | jq '.results[] | select(.status != "OK")'

# エラーレポートの確認
cat debug_bundle/error_report.json | jq '.issues[] | select(.severity == "ERROR")'

# パフォーマンス問題の確認
cat debug_bundle/performance_metrics.json | jq '.bottlenecks'

# 実行トレースの確認（ハング箇所の特定）
cat debug_bundle/execution_trace.json | jq '.stages[] | select(.status == "HANGING")'

# Docker関連問題の確認
cat debug_bundle/docker_info.json | jq '.connectivity_issues'
```

## 🔄 自動復旧機能

### 復旧メカニズム

自動復旧機能は以下の段階的なアプローチでハングアップ問題を解決します：

#### 1. 軽度復旧（Level 1）
- **出力バッファクリア** - stdout/stderr バッファの詰まり解消
- **プロセス状態リフレッシュ** - プロセス監視状態のリセット
- **一時ファイルクリーンアップ** - 不要な一時ファイルの削除

#### 2. 中度復旧（Level 2）
- **Docker再接続** - Docker daemon接続の自動復旧
- **ネットワーク再初期化** - Docker ネットワークの再構築
- **プロセス再起動** - ハングしたプロセスの安全な再起動

#### 3. 重度復旧（Level 3）
- **コンテナリセット** - コンテナ状態の完全初期化
- **Docker環境リセット** - Docker環境の部分的リセット
- **フォールバック実行** - 代替実行モードへの切り替え

### 自動復旧の有効化

```bash
# 基本的な自動復旧機能
uv run python main.py actions simulate .github/workflows/ci.yml --auto-recovery

# 強化機能と組み合わせた自動復旧
uv run python main.py actions simulate .github/workflows/ci.yml --enhanced --auto-recovery

# 診断機能も含めた包括的復旧
uv run python main.py actions simulate .github/workflows/ci.yml \
  --enhanced --auto-recovery --diagnose --create-debug-bundle

# 復旧レベルの指定
export ACTIONS_SIMULATOR_RECOVERY_LEVEL=2  # 1-3の範囲
uv run python main.py actions simulate .github/workflows/ci.yml --auto-recovery
```

### 復旧統計の確認

自動復旧機能の実行結果は詳細な統計として記録されます：

```json
{
  "recovery_statistics": {
    "total_recovery_attempts": 7,
    "successful_recoveries": 6,
    "failed_recoveries": 1,
    "recovery_by_level": {
      "level_1": {"attempts": 3, "successes": 3},
      "level_2": {"attempts": 3, "successes": 2},
      "level_3": {"attempts": 1, "successes": 1}
    },
    "recovery_types": {
      "docker_reconnections": 2,
      "process_restarts": 1,
      "buffer_clears": 3,
      "container_resets": 1,
      "network_resets": 1
    },
    "average_recovery_time_seconds": 15.3,
    "total_recovery_time_seconds": 107.1
  }
}
```

## 📈 パフォーマンス監視

### リアルタイム監視

```bash
# パフォーマンス監視付きで実行
uv run python main.py actions simulate .github/workflows/ci.yml --show-performance-metrics

# 実行トレースも同時に表示
uv run python main.py actions simulate .github/workflows/ci.yml \
  --show-performance-metrics --show-execution-trace

# 監視間隔の調整
export ACTIONS_SIMULATOR_PERFORMANCE_INTERVAL=1.0
export ACTIONS_SIMULATOR_TRACE_LEVEL=DEBUG
```

### 監視項目

#### システムリソース
- **CPU使用率** - プロセス別CPU消費量とシステム全体の負荷
- **メモリ使用量** - 物理メモリ・仮想メモリ・スワップ使用量
- **ディスクI/O** - 読み書き速度・IOPS・待機時間
- **ネットワーク通信** - Docker API通信量・レスポンス時間

#### Docker固有メトリクス
- **Docker操作応答時間** - コンテナ作成・起動・停止時間
- **イメージプル時間** - ベースイメージのダウンロード時間
- **ボリュームマウント時間** - ファイルシステム操作時間
- **ネットワーク設定時間** - Docker ネットワーク構築時間

#### アプリケーションメトリクス
- **ワークフロー解析時間** - YAML パース・検証時間
- **act実行時間** - 実際のワークフロー実行時間
- **出力処理時間** - stdout/stderr 処理時間
- **ログ書き込み時間** - ファイルI/O処理時間

### パフォーマンス分析結果の解釈

```json
{
  "performance_summary": {
    "total_execution_time": 45.8,
    "bottlenecks": [
      {
        "component": "Docker Image Pull",
        "time_seconds": 23.4,
        "percentage": 51.1,
        "recommendation": "ローカルイメージキャッシュの活用を推奨"
      },
      {
        "component": "Workflow Parsing",
        "time_seconds": 8.2,
        "percentage": 17.9,
        "recommendation": "YAML構文の最適化を検討"
      }
    ],
    "resource_usage": {
      "peak_cpu_percent": 85.2,
      "peak_memory_mb": 512.3,
      "total_disk_io_mb": 156.7,
      "docker_api_calls": 47
    }
  }
}
```

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
