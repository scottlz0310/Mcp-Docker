# プラットフォーム対応ガイド

GitHub Actions Simulator は複数のプラットフォームで動作するよう設計されています。このドキュメントでは、各プラットフォームでの詳細なセットアップ手順、最適化設定、および既知の問題について説明します。

## 📋 目次

- [サポートプラットフォーム概要](#サポートプラットフォーム概要)
- [Linux](#linux)
- [macOS](#macos)
- [Windows (WSL2)](#windows-wsl2)
- [共通の最適化設定](#共通の最適化設定)
- [トラブルシューティング](#トラブルシューティング)
- [パフォーマンス最適化](#パフォーマンス最適化)

## サポートプラットフォーム概要

| プラットフォーム | 対応状況 | 推奨度 | 備考 |
|----------------|----------|--------|------|
| **Linux** (Ubuntu 20.04+) | ✅ フル対応 | ⭐⭐⭐ | 最も安定 |
| **Linux** (Debian 11+) | ✅ フル対応 | ⭐⭐⭐ | 最も安定 |
| **Linux** (Fedora 35+) | ✅ フル対応 | ⭐⭐⭐ | 最も安定 |
| **Linux** (RHEL/CentOS 8+) | ✅ フル対応 | ⭐⭐⭐ | 最も安定 |
| **macOS** (12.0+) | ✅ フル対応 | ⭐⭐ | Docker Desktop必須 |
| **Windows** (WSL2) | ✅ フル対応 | ⭐⭐ | WSL2 + Docker Desktop |
| **Windows** (ネイティブ) | ⚠️ 制限あり | ⭐ | 非推奨 |

## Linux

### Ubuntu/Debian

#### 前提条件
- Ubuntu 20.04 LTS 以降、または Debian 11 以降
- sudo 権限
- インターネット接続

#### インストール手順

1. **システム更新**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Docker のインストール**
```bash
# 古いバージョンの削除
sudo apt remove docker docker-engine docker.io containerd runc

# 必要なパッケージのインストール
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Docker の公式 GPG キーを追加
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Docker リポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker Engine のインストール
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

3. **Docker の設定**
```bash
# Docker サービスの開始と自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーを docker グループに追加
sudo usermod -aG docker $USER

# 新しいグループ設定を適用（再ログインまたは以下のコマンド実行）
newgrp docker
```

4. **uv のインストール（推奨）**
```bash
# 公式インストーラー
curl -LsSf https://astral.sh/uv/install.sh | sh

# または Homebrew（Linux 版）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install uv
```

5. **Git のインストール（必要に応じて）**
```bash
sudo apt install -y git
```

#### Ubuntu/Debian 固有の最適化

**Docker のメモリ制限設定**
```bash
# /etc/docker/daemon.json を作成
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  }
}
EOF

sudo systemctl restart docker
```

### Fedora/RHEL/CentOS

#### 前提条件
- Fedora 35 以降、RHEL/CentOS 8 以降
- sudo 権限
- インターネット接続

#### インストール手順

1. **システム更新**
```bash
sudo dnf update -y
```

2. **Docker のインストール**
```bash
# 古いバージョンの削除
sudo dnf remove docker \
    docker-client \
    docker-client-latest \
    docker-common \
    docker-latest \
    docker-latest-logrotate \
    docker-logrotate \
    docker-selinux \
    docker-engine-selinux \
    docker-engine

# Docker CE リポジトリの追加
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo

# Docker Engine のインストール
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

3. **Docker の設定**
```bash
# Docker サービスの開始と自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーを docker グループに追加
sudo usermod -aG docker $USER
newgrp docker
```

4. **SELinux の設定（必要に応じて）**
```bash
# SELinux が有効な場合の Docker 設定
sudo setsebool -P container_manage_cgroup on
```

#### Fedora/RHEL 固有の最適化

**Firewall の設定**
```bash
# Docker 用のファイアウォール設定
sudo firewall-cmd --permanent --zone=trusted --add-interface=docker0
sudo firewall-cmd --permanent --zone=trusted --add-masquerade
sudo firewall-cmd --reload
```

### Linux 共通の既知の問題

#### 問題1: Docker デーモンへの接続エラー
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**解決方法:**
```bash
# Docker サービスの状態確認
sudo systemctl status docker

# Docker サービスの開始
sudo systemctl start docker

# ユーザーの docker グループ確認
groups $USER

# docker グループに追加されていない場合
sudo usermod -aG docker $USER
newgrp docker
```

#### 問題2: 権限エラー
```
permission denied while trying to connect to the Docker daemon socket
```

**解決方法:**
```bash
# Docker ソケットの権限確認
ls -la /var/run/docker.sock

# 権限の修正（一時的）
sudo chmod 666 /var/run/docker.sock

# 恒久的な解決（推奨）
sudo usermod -aG docker $USER
```

## macOS

### 前提条件
- macOS 12.0 (Monterey) 以降
- Intel または Apple Silicon Mac
- 管理者権限
- インターネット接続

### インストール手順

1. **Homebrew のインストール（推奨）**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Docker Desktop のインストール**

**方法1: Homebrew（推奨）**
```bash
brew install --cask docker
```

**方法2: 公式サイトからダウンロード**
- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) からダウンロード
- Intel Mac: `Docker Desktop for Mac with Intel chip`
- Apple Silicon Mac: `Docker Desktop for Mac with Apple chip`

3. **Docker Desktop の起動と設定**
```bash
# Docker Desktop を起動
open /Applications/Docker.app

# コマンドラインから Docker が使用可能か確認
docker --version
docker-compose --version
```

4. **uv のインストール**
```bash
# Homebrew 経由（推奨）
brew install uv

# または公式インストーラー
curl -LsSf https://astral.sh/uv/install.sh | sh
```

5. **Git のインストール（通常は既にインストール済み）**
```bash
# Xcode Command Line Tools（Git を含む）
xcode-select --install

# または Homebrew 経由
brew install git
```

### macOS 固有の最適化

#### Docker Desktop の設定

1. **リソース設定**
   - Docker Desktop > Settings > Resources
   - **CPU**: 使用可能コア数の 50-75%
   - **Memory**: 使用可能メモリの 50-75%
   - **Disk**: 最低 20GB、推奨 50GB

2. **ファイル共有の最適化**
   - Docker Desktop > Settings > Resources > File Sharing
   - プロジェクトディレクトリを追加
   - 不要なディレクトリは除外

3. **実験的機能の有効化**
   - Docker Desktop > Settings > Docker Engine
   ```json
   {
     "experimental": true,
     "features": {
       "buildkit": true
     }
   }
   ```

#### パフォーマンス最適化

**VirtioFS の有効化（Apple Silicon）**
```bash
# Docker Desktop > Settings > General
# "Use the new Virtualization framework" を有効化
# "Enable VirtioFS accelerated directory sharing" を有効化
```

**Rosetta 2 の設定（Apple Silicon で Intel イメージを使用する場合）**
```bash
# Docker Desktop > Settings > General
# "Use Rosetta for x86/amd64 emulation on Apple Silicon" を有効化
```

### macOS 固有の既知の問題

#### 問題1: Docker Desktop が起動しない
**症状:** Docker Desktop のアイコンがグレーアウトしている

**解決方法:**
```bash
# Docker Desktop のプロセス確認
ps aux | grep -i docker

# Docker Desktop の完全停止
pkill -f Docker

# Docker Desktop の再起動
open /Applications/Docker.app

# システム再起動（必要に応じて）
sudo reboot
```

#### 問題2: ファイル共有が遅い
**症状:** ボリュームマウントしたファイルの読み書きが遅い

**解決方法:**
```bash
# .dockerignore を適切に設定
echo "node_modules" >> .dockerignore
echo ".git" >> .dockerignore
echo "*.log" >> .dockerignore

# VirtioFS を有効化（上記参照）
# または delegated マウントを使用
docker run -v "$(pwd):/app:delegated" ...
```

#### 問題3: Apple Silicon での互換性問題
**症状:** Intel 用のイメージが動作しない

**解決方法:**
```bash
# プラットフォームを明示的に指定
docker run --platform linux/amd64 <image>

# または Dockerfile で指定
FROM --platform=linux/amd64 ubuntu:20.04

# マルチアーキテクチャ対応
docker buildx build --platform linux/amd64,linux/arm64 .
```

## Windows (WSL2)

### 前提条件
- Windows 10 version 2004 以降、または Windows 11
- WSL2 が有効
- 管理者権限
- インターネット接続

### インストール手順

1. **WSL2 の有効化**
```powershell
# PowerShell を管理者として実行
# WSL 機能の有効化
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 仮想マシン プラットフォーム機能の有効化
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# システム再起動
Restart-Computer

# WSL2 をデフォルトバージョンに設定
wsl --set-default-version 2

# Linux ディストリビューションのインストール（Ubuntu 推奨）
wsl --install -d Ubuntu
```

2. **Docker Desktop for Windows のインストール**
```powershell
# Chocolatey 経由（推奨）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

choco install docker-desktop

# または公式サイトからダウンロード
# https://docs.docker.com/desktop/install/windows-install/
```

3. **Docker Desktop の設定**
   - Docker Desktop を起動
   - Settings > General > "Use the WSL 2 based engine" を有効化
   - Settings > Resources > WSL Integration で使用する WSL ディストリビューションを選択

4. **WSL2 内での設定**
```bash
# WSL2 Ubuntu 内で実行
# システム更新
sudo apt update && sudo apt upgrade -y

# uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# Git のインストール（通常は既にインストール済み）
sudo apt install -y git
```

### Windows 固有の最適化

#### WSL2 の設定

**メモリ制限の設定**
```ini
# %USERPROFILE%\.wslconfig ファイルを作成
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

**ディスク容量の最適化**
```powershell
# PowerShell で実行
# WSL2 の仮想ディスクを圧縮
wsl --shutdown
diskpart
# DISKPART> select vdisk file="C:\Users\<username>\AppData\Local\Packages\CanonicalGroupLimited.UbuntuonWindows_79rhkp1fndgsc\LocalState\ext4.vhdx"
# DISKPART> compact vdisk
# DISKPART> exit
```

#### Docker Desktop の設定

**リソース設定**
- Settings > Resources > Advanced
- **CPU**: 使用可能コア数の 50-75%
- **Memory**: 使用可能メモリの 50-75%
- **Disk**: 最低 20GB、推奨 50GB

**WSL 統合の設定**
- Settings > Resources > WSL Integration
- 使用する WSL ディストリビューションを有効化

### Windows 固有の既知の問題

#### 問題1: WSL2 が起動しない
**症状:** `WslRegisterDistribution failed with error: 0x80370102`

**解決方法:**
```powershell
# BIOS で仮想化機能を有効化
# Hyper-V の有効化
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# WSL カーネル更新プログラムのインストール
# https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
```

#### 問題2: Docker Desktop が WSL2 を認識しない
**症状:** Docker Desktop で WSL2 統合が利用できない

**解決方法:**
```powershell
# WSL2 の状態確認
wsl --list --verbose

# WSL2 バージョンの確認
wsl --version

# Docker Desktop の再起動
# タスクマネージャーで Docker Desktop を終了
# Docker Desktop を再起動
```

#### 問題3: ファイルパフォーマンスの問題
**症状:** Windows ファイルシステム上のファイルアクセスが遅い

**解決方法:**
```bash
# WSL2 ファイルシステム内でプロジェクトを作業
# Windows: C:\Users\username\project
# WSL2: /home/username/project （推奨）

# WSL2 内でプロジェクトをクローン
cd ~
git clone https://github.com/your-repo/project.git
cd project
```

## 共通の最適化設定

### Docker の最適化

#### BuildKit の有効化
```bash
# 環境変数で有効化
export DOCKER_BUILDKIT=1

# または docker-compose.yml で設定
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DOCKER_BUILDKIT=1
```

#### イメージキャッシュの最適化
```dockerfile
# Dockerfile の最適化例
FROM python:3.11-slim

# 依存関係ファイルを先にコピー（キャッシュ効率向上）
COPY requirements.txt .
RUN pip install -r requirements.txt

# アプリケーションコードをコピー
COPY . .
```

#### マルチステージビルドの活用
```dockerfile
# ビルドステージ
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 実行ステージ
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
```

### 環境変数の最適化

#### .env ファイルの設定
```bash
# .env ファイル例
# Docker 設定
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# パフォーマンス設定
COMPOSE_PARALLEL_LIMIT=4

# ログ設定
COMPOSE_LOG_LEVEL=WARNING

# プラットフォーム固有設定
PLATFORM_ARCH=linux/amd64  # Intel Mac や Windows の場合
# PLATFORM_ARCH=linux/arm64  # Apple Silicon Mac の場合
```

### メモリとCPUの最適化

#### Docker Compose でのリソース制限
```yaml
version: '3.8'
services:
  app:
    build: .
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## トラブルシューティング

### 一般的な問題と解決方法

#### Docker 関連

**問題: Docker イメージのビルドが失敗する**
```bash
# キャッシュをクリアしてリビルド
docker system prune -a
docker-compose build --no-cache

# ディスク容量の確認
docker system df
```

**問題: コンテナが起動しない**
```bash
# ログの確認
docker-compose logs -f

# コンテナの状態確認
docker-compose ps

# 詳細な診断情報
docker inspect <container_name>
```

#### ネットワーク関連

**問題: ポートが既に使用されている**
```bash
# ポート使用状況の確認
# Linux/macOS
sudo lsof -i :8080

# Windows
netstat -ano | findstr :8080

# 使用中のプロセスを終了
# Linux/macOS
sudo kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

#### パフォーマンス関連

**問題: Docker が遅い**
```bash
# Docker の統計情報確認
docker stats

# システムリソースの確認
# Linux
htop
free -h
df -h

# macOS
top
vm_stat
df -h

# Windows (PowerShell)
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
```

### 診断コマンド

#### システム情報の収集
```bash
# GitHub Actions Simulator の診断情報
./scripts/run-actions.sh --check-deps

# Docker 環境の診断
docker version
docker info
docker-compose version

# システム情報
uname -a
cat /etc/os-release  # Linux
sw_vers              # macOS
systeminfo           # Windows (PowerShell)
```

#### ログの収集
```bash
# Docker ログ
docker-compose logs --tail=100 > docker-logs.txt

# システムログ
# Linux
journalctl -u docker --since "1 hour ago" > docker-system.log

# macOS
log show --predicate 'process == "Docker"' --last 1h > docker-system.log
```

## パフォーマンス最適化

### ベンチマーク

#### 基本的なパフォーマンステスト
```bash
# Docker ビルド時間の測定
time docker-compose build

# コンテナ起動時間の測定
time docker-compose up -d

# GitHub Actions 実行時間の測定
time ./scripts/run-actions.sh .github/workflows/test.yml
```

#### プラットフォーム別の期待値

| プラットフォーム | ビルド時間 | 起動時間 | 実行時間 |
|----------------|------------|----------|----------|
| Linux (ネイティブ) | 30-60秒 | 5-10秒 | 10-30秒 |
| macOS (Docker Desktop) | 45-90秒 | 10-20秒 | 15-45秒 |
| Windows (WSL2) | 60-120秒 | 15-30秒 | 20-60秒 |

### 最適化のベストプラクティス

1. **Docker イメージの最適化**
   - Alpine Linux ベースイメージの使用
   - マルチステージビルドの活用
   - 不要なパッケージの削除

2. **ファイルシステムの最適化**
   - .dockerignore の適切な設定
   - ボリュームマウントの最適化
   - キャッシュディレクトリの活用

3. **リソース管理**
   - 適切なメモリ制限の設定
   - CPU 使用率の監視
   - ディスク容量の定期的なクリーンアップ

4. **ネットワークの最適化**
   - 不要なポート公開の回避
   - 内部ネットワークの活用
   - DNS 設定の最適化

---

## 📞 サポート

このガイドで解決できない問題がある場合は、以下の方法でサポートを受けることができます：

1. **GitHub Issues**: バグ報告や機能要望
2. **GitHub Discussions**: 質問やアイデアの共有
3. **診断情報の収集**: `./scripts/run-actions.sh --check-deps` の出力を含めて報告

問題報告時は、使用しているプラットフォーム、バージョン情報、エラーメッセージを含めてください。
