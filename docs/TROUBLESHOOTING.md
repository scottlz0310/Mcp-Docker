# トラブルシューティングガイド

GitHub Actions Simulator の軽量actベースアーキテクチャに対応したトラブルシューティングガイドです。

## 📖 このガイドの使い方

**問題別クイック検索:**

- 🚀 [実行できない](#クイック診断) → 依存関係・権限の問題
- 🐳 [Docker関連](#軽量actベースアーキテクチャ関連) → Docker・コンテナの問題
- 🎯 [ワークフロー関連](#ワークフロー実行の問題) → 実行・ハングアップの問題
- 🔄 [CI/CD関連](#cicd統合の問題) → 自動化・非対話モードの問題
- ⚡ [パフォーマンス](#パフォーマンス最適化) → 速度・リソースの問題

**症状別クイック検索:**

- `permission denied` → [Docker権限の問題](#docker環境の問題)
- `command not found` → [依存関係の問題](#依存関係チェック失敗)
- `timeout` → [ハングアップ問題](#ワークフローハングアップ)
- `disk space` → [リソース不足](#パフォーマンス最適化)

## 🎯 軽量アーキテクチャの特徴

GitHub Actions Simulator は以下の軽量アーキテクチャを採用しています：

- **ワンショット実行**: `scripts/run-actions.sh` による単一コマンド実行
- **軽量actベース**: Dockerコンテナ内でactを使用した高速シミュレーション
- **自動依存関係管理**: Docker、uv、gitの自動チェックとガイダンス
- **包括的診断**: 実行前チェック、エラー検出、自動復旧機能

## 📚 専門ガイド

- **[ハングアップ問題の詳細ガイド](./HANGUP_TROUBLESHOOTING.md)** - GitHub Actions Simulatorのハングアップ問題に特化した包括的なトラブルシューティング
- **[診断コマンド完全ガイド](./DIAGNOSTIC_COMMANDS.md)** - 全ての診断機能とデバッグコマンドの詳細リファレンス
- **[診断コマンド使用例](#診断コマンド使用例)** - システム診断とデバッグ機能の基本的な使用方法

## 🚀 クイック診断

問題が発生した場合、まず以下のコマンドで包括的な診断を実行してください：

```bash
# 依存関係と環境の包括的チェック
./scripts/run-actions.sh --check-deps

# 詳細な診断情報の取得
uv run python main.py actions diagnose --include-performance --include-trace
```

## よくある問題と解決方法

### 🐳 軽量actベースアーキテクチャ関連

#### 1. ワンショット実行スクリプトの問題

**症状**: `./scripts/run-actions.sh` が実行できない

```bash
# 実行権限の確認と付与
ls -la scripts/run-actions.sh
chmod +x scripts/run-actions.sh

# 依存関係の自動チェック
./scripts/run-actions.sh --check-deps

# 詳細なエラー情報の確認
cat logs/diagnostic.log
cat logs/error.log
```

#### 2. Docker環境の問題

**症状**: Docker関連のエラーが発生する

```bash
# Docker サービス状態の確認
docker info
systemctl status docker  # Linux
# Docker Desktop の状態確認 (macOS/Windows)

# Docker権限の修正
sudo usermod -aG docker $USER
newgrp docker

# Docker環境のクリーンアップ
docker system prune -f
docker volume prune -f
```

#### 3. actコンテナの問題

**症状**: actベースのシミュレーションが失敗する

```bash
# actコンテナイメージの確認
docker images | grep actions-simulator

# イメージの強制更新
docker-compose --profile tools pull actions-simulator

# コンテナの再ビルド
docker-compose build actions-simulator

# ログの確認
docker-compose logs actions-simulator
```

### 🔧 依存関係管理の問題

#### 1. 依存関係チェック失敗

**症状**: 必要なツールが見つからない

```bash
# プラットフォーム別の自動インストールガイダンス
./scripts/run-actions.sh --check-deps

# 手動でのDocker確認
docker --version
docker compose version

# 手動でのGit確認
git --version

# uvの確認（オプション）
uv --version || echo "uv is optional"
```

**プラットフォーム別解決方法:**

**Ubuntu/Debian:**

```bash
# Docker のインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Git のインストール
sudo apt-get update && sudo apt-get install git

# uv のインストール（推奨）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS:**

```bash
# Homebrew を使用
brew install --cask docker
brew install git
brew install uv
```

**Windows (WSL):**

```bash
# Docker Desktop をインストール
# Git for Windows をインストール
# uv をインストール
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. バージョン互換性の問題

**症状**: ツールのバージョンが古い

```bash
# 最小要件の確認
# Docker: 20.10.0+
# Docker Compose: 2.0.0+
# Git: 2.20.0+

# バージョンアップグレード
sudo apt-get update && sudo apt-get upgrade docker-ce docker-compose-plugin git  # Ubuntu
brew upgrade docker git uv  # macOS
```

### 🎯 ワークフロー実行の問題

#### 1. ワークフロー選択の問題

**症状**: ワークフローが見つからない、または選択できない

```bash
# 利用可能なワークフローの確認
find .github/workflows -name "*.yml" -o -name "*.yaml"

# 対話的なワークフロー選択
./scripts/run-actions.sh

# 特定のワークフローを直接指定
./scripts/run-actions.sh .github/workflows/ci.yml

# 非対話モードでの実行
NON_INTERACTIVE=1 INDEX=1 ./scripts/run-actions.sh
```

#### 2. ワークフローハングアップ

**症状**: ワークフロー実行が停止する

```bash
# 緊急診断の実行
uv run python main.py actions diagnose

# 詳細なハングアップ分析
uv run python main.py actions diagnose --include-performance --include-trace

# 自動復旧機能付きで再実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced --auto-recovery

# タイムアウト値の調整
./scripts/run-actions.sh --timeout=600 .github/workflows/ci.yml
```

#### 3. パフォーマンスの問題

**症状**: 実行が遅い、リソース使用量が多い

```bash
# パフォーマンス監視付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics

# リソース使用量の確認
docker stats

# システムリソースの最適化
docker system prune -f
docker volume prune -f

# メモリ制限の設定
export DOCKER_MEMORY_LIMIT=2g
```

#### 4. 実行環境の問題

**症状**: 環境変数や設定の問題

```bash
# 環境変数の確認
env | grep -E '^(DOCKER|COMPOSE|ACTIONS_SIMULATOR|PATH)'

# 設定ファイルの確認
cat .env 2>/dev/null || echo ".env file not found"

# 設定テンプレートからの作成
cp .env.template .env
# .env ファイルを編集してください

# 出力ディレクトリの権限確認
ls -la output/
sudo chown -R $(id -u):$(id -g) output/
```

### 🔄 CI/CD統合の問題

#### 1. 非対話モードでの実行問題

**症状**: CI/CD環境で対話的プロンプトが表示される

```bash
# 非対話モードの明示的な有効化
export NON_INTERACTIVE=1
./scripts/run-actions.sh

# 環境変数での自動選択
export INDEX=1  # 最初のワークフローを自動選択
./scripts/run-actions.sh

# GitHub Actions での使用例
- name: Run GitHub Actions Simulator
  run: |
    export NON_INTERACTIVE=1
    export INDEX=1
    ./scripts/run-actions.sh
```

#### 2. GitHub Actions環境での問題

**症状**: GitHub Actions内でシミュレーターが動作しない

```yaml
# GitHub Actions ワークフロー例
jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Docker
        uses: docker/setup-buildx-action@v3
      - name: Run Actions Simulator
        run: |
          chmod +x scripts/run-actions.sh
          NON_INTERACTIVE=1 INDEX=1 ./scripts/run-actions.sh
```

#### 3. セキュリティスキャンの問題

**症状**: セキュリティスキャンが失敗する

```bash
# ローカルでのセキュリティスキャン
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image actions-simulator:latest

# 脆弱性レポートの生成
docker run --rm -v $(pwd):/workspace \
  aquasec/trivy fs --format json --output /workspace/security-report.json .

# セキュリティ設定の確認
./scripts/run-actions.sh .github/workflows/security.yml
```

## 🔍 診断コマンド使用例

### 軽量アーキテクチャ対応診断機能

#### 基本システム診断

```bash
# ワンショットスクリプトによる依存関係チェック
./scripts/run-actions.sh --check-deps

# 包括的なシステムヘルスチェック
uv run python main.py actions diagnose

# JSON形式での診断結果出力
uv run python main.py actions diagnose --output-format json --output-file diagnosis.json

# 詳細分析を含む診断
uv run python main.py actions diagnose --include-performance --include-trace
```

#### ワンショット実行での診断

```bash
# 診断機能付きでワークフローを実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose

# 強化されたラッパーと診断機能を使用
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced --diagnose

# パフォーマンス監視付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics

# デバッグバンドル自動作成
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced --create-debug-bundle
```

#### 軽量actベース環境の診断

```bash
# actコンテナの状態確認
docker-compose ps actions-simulator
docker-compose logs actions-simulator

# Docker統合の詳細チェック
docker system info
docker images | grep actions-simulator
docker network ls

# 実行中プロセスの確認
ps aux | grep act
ps aux | grep docker
ps aux | grep run-actions

# ログファイルの確認
cat logs/diagnostic.log
cat logs/error.log
```

#### プラットフォーム固有の診断

```bash
# プラットフォーム検出と対応状況
./scripts/run-actions.sh --check-deps | grep "プラットフォーム"

# Linux固有の診断
systemctl status docker  # Docker サービス状態
df -h .                   # ディスク容量
free -h                   # メモリ使用量

# macOS固有の診断
brew list | grep docker   # Docker Desktop 状態
docker-machine ls         # Docker Machine 状態（該当する場合）

# Windows (WSL) 固有の診断
wsl --list --verbose      # WSL 状態
docker context ls         # Docker コンテキスト
```

### 診断結果の解釈

#### ステータス表示の意味

| ステータス | 意味 | 対応 | 軽量アーキテクチャでの対応 |
|-----------|------|------|---------------------------|
| ✅ OK | 正常動作 | 対応不要 | そのまま実行可能 |
| ⚠️ WARNING | 警告あり | 推奨事項を確認 | 実行可能だが最適化推奨 |
| ❌ ERROR | エラー検出 | 即座に修正が必要 | 自動復旧機能を試行 |
| 🔧 FIXING | 自動修正中 | 待機 | スクリプトが自動対応中 |
| 📋 GUIDANCE | ガイダンス表示 | 手順に従う | プラットフォーム別手順を実行 |

#### 診断項目の詳細

**依存関係チェック:**

- Docker: バージョン 20.10.0+ が必要
- Docker Compose: バージョン 2.0.0+ が必要
- Git: バージョン 2.20.0+ が必要
- uv: オプション（推奨）

**環境チェック:**

- ディスク容量: 2GB以上の空き容量推奨
- メモリ: 4GB以上推奨
- ネットワーク: Docker Hub へのアクセス必要

**権限チェック:**

- Docker グループ所属確認
- ファイル書き込み権限確認
- 実行権限確認

## 🛠️ デバッグコマンド

### 軽量アーキテクチャ対応デバッグ

#### 基本システム確認

```bash
# 軽量アーキテクチャのシステム情報
docker version
docker compose version  # 注意: docker-compose ではなく docker compose
uv --version || echo "uv not installed (optional)"
git --version

# ワンショットスクリプトの状態確認
ls -la scripts/run-actions.sh
file scripts/run-actions.sh

# プロジェクト構造の確認
ls -la
find . -name "*.yml" -path "./.github/workflows/*"
```

#### actベースコンテナの確認

```bash
# actions-simulator コンテナの状態
docker images | grep actions-simulator
docker-compose ps actions-simulator
docker-compose top actions-simulator

# コンテナリソース使用量
docker stats actions-simulator

# コンテナ内部の確認
docker-compose exec actions-simulator /bin/sh
# コンテナ内で: act --version
```

#### ログ収集（軽量アーキテクチャ対応）

```bash
# ワンショットスクリプトのログ
cat logs/diagnostic.log
cat logs/error.log

# Docker Compose ログ
docker-compose logs actions-simulator > debug-actions.log

# 全サービスログ（該当する場合）
docker-compose logs > debug-all.log

# リアルタイムログ監視
docker-compose logs -f actions-simulator

# システムログ（Linux）
journalctl -u docker --since "1 hour ago"
```

#### ネットワーク・接続診断

```bash
# Docker ネットワーク確認
docker network ls
docker network inspect $(docker-compose config --services | head -1)_default 2>/dev/null || echo "Network not found"

# 外部接続確認
ping -c 3 docker.io
curl -I https://github.com

# プロキシ設定確認
env | grep -i proxy
```

#### パフォーマンス診断

```bash
# システムリソース確認
free -h                    # メモリ使用量
df -h .                    # ディスク使用量
docker system df           # Docker リソース使用量

# プロセス確認
ps aux | grep -E "(docker|act|run-actions)" | grep -v grep

# I/O 統計（Linux）
iostat -x 1 3 2>/dev/null || echo "iostat not available"
```

## ⚡ パフォーマンス最適化

### 軽量actベースアーキテクチャの最適化

#### メモリ使用量の最適化

```bash
# Docker メモリ制限の設定
export DOCKER_MEMORY_LIMIT=2g

# actions-simulator コンテナのメモリ制限
# docker-compose.yml で設定:
services:
  actions-simulator:
    mem_limit: 1g
    memswap_limit: 1g
```

#### 起動時間の短縮

```bash
# Docker イメージキャッシュの活用
docker-compose build --parallel actions-simulator

# 不要リソースの削除
docker container prune -f
docker image prune -f
docker volume prune -f

# ワンショットスクリプトの高速化
# 依存関係チェックをスキップ（既に確認済みの場合）
SKIP_DEPS_CHECK=1 ./scripts/run-actions.sh .github/workflows/ci.yml
```

#### ディスク使用量の最適化

```bash
# Docker システムクリーンアップ
docker system prune -a -f

# ログファイルのローテーション
find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true

# 出力ディレクトリのクリーンアップ
find output/ -type f -mtime +1 -delete 2>/dev/null || true
```

#### ネットワーク最適化

```bash
# Docker イメージの事前プル
docker-compose --profile tools pull

# ローカルレジストリの使用（高度）
docker run -d -p 5000:5000 --name registry registry:2
docker tag actions-simulator:latest localhost:5000/actions-simulator:latest
docker push localhost:5000/actions-simulator:latest
```

#### act実行の最適化

```bash
# act タイムアウトの調整
./scripts/run-actions.sh --timeout=300 .github/workflows/ci.yml

# 並列実行の制限
export ACT_MAX_PARALLEL=2

# キャッシュディレクトリの設定
export ACT_CACHE_DIR=~/.cache/act
mkdir -p "$ACT_CACHE_DIR"
```

## 📞 サポート

### 軽量アーキテクチャ対応サポート情報

#### 問題報告時に必要な情報

**基本システム情報:**

```bash
# 以下のコマンド結果を含めてください
./scripts/run-actions.sh --check-deps
docker version
docker compose version
git --version
uv --version 2>/dev/null || echo "uv not installed"
```

**診断ログ:**

```bash
# 診断ログの収集
cat logs/diagnostic.log
cat logs/error.log

# 詳細診断の実行
uv run python main.py actions diagnose --include-performance --include-trace --output-format json
```

**環境情報:**

```bash
# プラットフォーム情報
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release 2>/dev/null || echo "OS info not available"

# Docker 環境
docker info
docker-compose config --services 2>/dev/null || echo "No services configured"
```

#### Issue作成テンプレート（軽量アーキテクチャ対応）

```markdown
## 問題の概要
[簡潔な説明]

## 軽量アーキテクチャ環境
- 実行方法: [ ] ワンショットスクリプト [ ] 直接CLI [ ] make コマンド
- 実行モード: [ ] 対話モード [ ] 非対話モード [ ] CI/CD環境

## 再現手順
1. [手順1]
2. [手順2]
3. [手順3]

## 期待する動作
[期待する結果]

## 実際の動作
[実際の結果]

## 環境情報
- OS: [Ubuntu 22.04 / macOS 14.0 / Windows 11 WSL2]
- Docker: [24.0.0]
- Docker Compose: [2.20.0]
- Git: [2.40.0]
- uv: [0.1.0 / not installed]

## 診断情報
```bash
# 以下のコマンド結果を貼り付けてください
./scripts/run-actions.sh --check-deps
```

## ログファイル

```bash
# logs/diagnostic.log の内容
[ログ内容を貼り付け]

# logs/error.log の内容（エラーがある場合）
[エラーログを貼り付け]
```

## 追加情報

- ワークフローファイル: [.github/workflows/ci.yml]
- 使用した引数: [--enhanced --diagnose]
- 実行時間: [約X分で停止]

```

#### サポートチャネル

**ドキュメント:**
- 📖 [README.md](../README.md) - 基本的な使用方法
- 🚀 [クイックスタートガイド](./QUICK_START.md) - 5分で始める方法
- 📚 [actions/ユーザーガイド](./actions/USER_GUIDE.md) - 詳細な利用方法
- ❓ [FAQ](./actions/FAQ.md) - よくある質問

**診断ツール:**
```bash
# 自動診断の実行
./scripts/run-actions.sh --check-deps

# 包括的診断
uv run python main.py actions diagnose --include-performance --include-trace

# 環境リセット
make clean  # または docker system prune -f
```

**コミュニティサポート:**

- 🐛 GitHub Issues - バグ報告・機能要望
- 💬 GitHub Discussions - 質問・議論
- 📧 メンテナー連絡 - 緊急時のみ

#### 自己解決のためのチェックリスト

問題報告前に以下を確認してください：

- [ ] `./scripts/run-actions.sh --check-deps` を実行して依存関係を確認
- [ ] 最新版のDockerとDocker Composeを使用している
- [ ] ディスク容量が2GB以上ある
- [ ] ネットワーク接続が正常（`ping docker.io`）
- [ ] 実行権限が正しく設定されている（`chmod +x scripts/run-actions.sh`）
- [ ] ログファイル（`logs/diagnostic.log`, `logs/error.log`）を確認
- [ ] 既存のIssueで同様の問題が報告されていないか確認

## 🔍 よくあるエラーメッセージと解決方法

### 実行権限関連

```bash
# エラー: permission denied: ./scripts/run-actions.sh
chmod +x scripts/run-actions.sh

# エラー: Got permission denied while trying to connect to the Docker daemon
sudo usermod -aG docker $USER
newgrp docker
```

### 依存関係関連

```bash
# エラー: docker: command not found
# → Docker をインストールしてください
./scripts/run-actions.sh --check-deps  # インストール手順を表示

# エラー: docker compose: command not found
# → Docker Compose プラグインをインストール
sudo apt-get install docker-compose-plugin  # Ubuntu
brew install docker  # macOS (Docker Desktop に含まれる)
```

### ワークフロー関連

```bash
# エラー: workflow file not found
# → ワークフローファイルのパスを確認
find .github/workflows -name "*.yml"

# エラー: act timeout
# → タイムアウト値を増加
./scripts/run-actions.sh --timeout=600 .github/workflows/ci.yml
```

### リソース関連

```bash
# エラー: no space left on device
docker system prune -f
docker volume prune -f

# エラー: cannot allocate memory
# → メモリ制限を設定
export DOCKER_MEMORY_LIMIT=1g
```

### ネットワーク関連

```bash
# エラー: failed to pull image
# → ネットワーク接続を確認
ping docker.io
# プロキシ設定が必要な場合
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

---

**📝 最終更新**: 2025年09月28日
**🔄 対応バージョン**: GitHub Actions Simulator v1.0.1+
**🏗️ アーキテクチャ**: 軽量actベース配布形式
