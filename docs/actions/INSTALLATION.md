# GitHub Actions Simulator - インストールガイド

## 🎯 概要

GitHub Actions Simulatorのインストール方法を詳しく説明します。

## 📋 前提条件

### 必須要件
- **Docker**: 20.10+
- **Python**: 3.13+
- **Git**: 2.30+

### 推奨要件
- **uv**: 最新版（Python パッケージマネージャー）
- **make**: GNU Make 4.0+

## 🚀 インストール手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker
```

### 2. 環境設定

```bash
# 環境変数ファイルの作成
cp .env.example .env

# .envファイルを編集してGitHubトークンを設定
# GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
```

### 3. 依存関係のインストール

#### uvを使用（推奨）
```bash
# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール
uv sync --group test --group dev
```

#### pipを使用
```bash
# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 依存関係のインストール
pip install -e .
```

### 4. Docker環境のセットアップ

```bash
# Docker統合環境のセットアップ
make setup-docker

# ヘルスチェック
make health-check
```

## 🔧 プラットフォーム別インストール

### Linux (Ubuntu/Debian)

```bash
# システム依存関係のインストール
sudo apt update
sudo apt install -y docker.io docker-compose git python3 python3-pip make

# Dockerグループに追加（再ログイン必要）
sudo usermod -aG docker $USER

# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### macOS

```bash
# Homebrewを使用
brew install docker docker-compose git python@3.13 make

# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (WSL2)

```bash
# WSL2内でLinux手順を実行
# Docker Desktopのインストールが必要
```

## ✅ インストール確認

### 基本動作確認

```bash
# バージョン確認
python main.py --version

# 依存関係チェック
./scripts/run-actions.sh --check-deps

# 簡単なテスト実行
make actions-auto
```

### 詳細テスト

```bash
# 統合テスト
make test

# Docker環境テスト
make test-docker

# Actions Simulatorテスト
make test-hangup
```

## 🛠️ トラブルシューティング

### よくある問題

#### Docker権限エラー
```bash
# Dockerグループに追加
sudo usermod -aG docker $USER
# 再ログインまたは
newgrp docker
```

#### Python依存関係エラー
```bash
# 仮想環境の再作成
rm -rf .venv
uv sync --group test --group dev
```

#### ポート競合
```bash
# 使用中のポートを確認
netstat -tulpn | grep :8000
# または
lsof -i :8000
```

## 📚 次のステップ

インストール完了後は以下のドキュメントを参照してください：

- [クイックスタート](QUICK_START.md)
- [ユーザーガイド](USER_GUIDE.md)
- [CLIリファレンス](CLI_REFERENCE.md)
- [トラブルシューティング](TROUBLESHOOTING.md)
