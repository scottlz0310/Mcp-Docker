# MCP Docker Environment

MCPサーバーとツールを統合管理するDocker環境

## 構成

```
mcp-docker/
├── services/           # サービス別設定
│   ├── github/         # GitHub MCP設定
│   ├── datetime/       # 日付検証スクリプト
│   └── codeql/         # CodeQL設定
├── scripts/            # 管理スクリプト
├── Dockerfile          # 統合イメージ
├── docker-compose.yml  # サービス定義
├── Makefile           # 簡単コマンド
└── .env.template      # 環境変数テンプレート
```

## 特徴

- **統合イメージ**: 1つのDockerイメージで全機能提供
- **サービス分離**: 同じイメージから異なるコマンドで起動
- **軽量運用**: 必要なサービスのみ選択起動

## クイックスタート

### 1. 初期設定
```bash
# 環境変数設定
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc

# セットアップ実行
./scripts/setup.sh
```

### 2. 使用方法
```bash
# 全サービス起動
make start

# 個別サービス
make github    # GitHub MCPのみ
make datetime  # 日付検証のみ
make codeql    # CodeQL分析

# その他
make logs      # ログ確認
make stop      # 停止
make clean     # クリーンアップ
```

## サービス詳細

### GitHub MCP Server
- ポート: 8080
- GitHub API連携
- 環境変数: `GITHUB_PERSONAL_ACCESS_TOKEN`

### DateTime Validator
- ファイル監視による日付自動修正
- 2025-01, 2024-12などの疑わしい日付を検出

### CodeQL
- 静的コード分析
- オンデマンド実行