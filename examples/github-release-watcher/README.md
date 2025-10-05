# GitHub Release Watcher - 使用ガイド

GitHub Release Watcher は、任意の GitHub リポジトリの新しいリリースを監視し、複数の通知チャネルで通知を送信するサービスです。

## 目次

- [特徴](#特徴)
- [クイックスタート](#クイックスタート)
- [設定](#設定)
- [通知チャネル](#通知チャネル)
- [使用例](#使用例)
- [トラブルシューティング](#トラブルシューティング)

## 特徴

- 🔔 **マルチチャネル通知**: ネイティブ通知、Discord、Slack、Email、Webhook、ファイル出力に対応
- 🚀 **非同期処理**: 高速な並列リポジトリチェック
- 💾 **キャッシュ対応**: GitHub API レート制限を考慮した効率的なキャッシング
- 🔄 **バージョン比較**: セマンティックバージョニング対応の賢いバージョン比較
- 🎯 **フィルタリング**: 安定版のみ、プレリリースのみなど柔軟なフィルタリング
- 🐳 **Docker対応**: 簡単なデプロイとスケーリング
- 🔒 **セキュア**: 環境変数による秘密情報管理

## クイックスタート

### 1. 環境変数の設定

```bash
# プロジェクトルートで .env ファイルを作成
cp .env.example .env

# .env ファイルを編集して GitHub Token を設定
# GITHUB_TOKEN=your_github_token_here
```

### 2. 設定ファイルの編集

`examples/github-release-watcher/config/config.toml` を編集して監視するリポジトリと通知設定を行います。

```toml
[[repositories]]
owner = "microsoft"
repo = "WSL"
url = "https://github.com/microsoft/WSL"
filter_mode = "stable"
```

### 3. サービスの起動

```bash
# 起動スクリプトを使用
./examples/github-release-watcher/scripts/start.sh

# または Docker Compose で直接起動
docker compose up -d github-release-watcher
```

### 4. ログの確認

```bash
# ログをフォロー
docker compose logs -f github-release-watcher

# または起動時にフォロー
./examples/github-release-watcher/scripts/start.sh --follow
```

## 設定

### GitHub API 設定

```toml
[github]
token = "${GITHUB_TOKEN}"
check_interval = 300  # チェック間隔（秒）
```

### リポジトリ設定

```toml
[[repositories]]
owner = "owner-name"          # リポジトリオーナー
repo = "repo-name"            # リポジトリ名
url = "https://github.com/owner-name/repo-name"
filter_mode = "stable"        # フィルタモード: all, stable, prerelease
version_pattern = "^v?\\d+\\.\\d+\\.\\d+$"  # オプション: バージョンパターン（正規表現）
```

### 通知設定

```toml
[notifications]
enabled = true
channels = ["native", "discord", "slack"]
```

## 通知チャネル

### 1. ネイティブ通知 (Windows Toast/macOS/Linux)

```toml
[notifications.native]
enabled = true
duration = 10    # 表示時間（秒）
sound = true     # サウンド再生
```

**対応プラットフォーム:**
- Windows: Windows Toast Notification
- macOS: macOS Notification Center
- Linux: libnotify (plyer経由)

### 2. Discord Webhook

```toml
[notifications.discord]
enabled = true
webhook_url = "${DISCORD_WEBHOOK_URL}"
username = "GitHub Release Watcher"
color = 0x0366D6
mention_users = ["user_id_1", "user_id_2"]  # オプション
```

**Webhook URLの取得方法:**
1. Discord サーバー設定 → 連携サービス → ウェブフック
2. "新しいウェブフック" をクリック
3. Webhook URL をコピー

### 3. Slack Webhook

```toml
[notifications.slack]
enabled = true
webhook_url = "${SLACK_WEBHOOK_URL}"
username = "GitHub Release Watcher"
icon_emoji = ":rocket:"
channel = "#releases"  # オプション
```

**Webhook URLの取得方法:**
1. Slack App を作成
2. Incoming Webhooks を有効化
3. Webhook URL をコピー

### 4. Email (SMTP)

```toml
[notifications.email]
enabled = true
smtp_server = "${SMTP_SERVER}"
smtp_port = 587
username = "${SMTP_USERNAME}"
password = "${SMTP_PASSWORD}"
from = "noreply@example.com"
to = ["user@example.com"]
use_tls = true
```

### 5. 汎用 Webhook

```toml
[notifications.webhook]
enabled = true
url = "https://your-webhook-endpoint.com/notify"
method = "POST"

[notifications.webhook.headers]
Authorization = "Bearer your-token"
```

### 6. ファイル出力

```toml
[notifications.file]
enabled = true
output_path = "/app/data/notifications.json"
format = "json"  # json または markdown
append = true    # 追記モード
```

## 使用例

### 例1: WSL カーネルの新しいリリースを監視

```toml
[[repositories]]
owner = "microsoft"
repo = "WSL"
url = "https://github.com/microsoft/WSL"
filter_mode = "stable"

[notifications]
enabled = true
channels = ["native", "discord"]
```

### 例2: 複数のツールを監視

```toml
[[repositories]]
owner = "docker"
repo = "compose"
url = "https://github.com/docker/compose"
filter_mode = "stable"

[[repositories]]
owner = "nektos"
repo = "act"
url = "https://github.com/nektos/act"
filter_mode = "all"

[[repositories]]
owner = "astral-sh"
repo = "uv"
url = "https://github.com/astral-sh/uv"
filter_mode = "stable"
```

### 例3: プレリリースのみ監視

```toml
[[repositories]]
owner = "rust-lang"
repo = "rust"
url = "https://github.com/rust-lang/rust"
filter_mode = "prerelease"
```

### 例4: バージョンパターンでフィルタリング

```toml
[[repositories]]
owner = "nodejs"
repo = "node"
url = "https://github.com/nodejs/node"
filter_mode = "stable"
version_pattern = "^v20\\."  # v20.x.x のみ
```

## コマンド

### 起動

```bash
# スクリプトで起動
./examples/github-release-watcher/scripts/start.sh

# ログをフォロー
./examples/github-release-watcher/scripts/start.sh --follow

# Docker Compose で起動
docker compose up -d github-release-watcher
```

### 停止

```bash
# スクリプトで停止
./examples/github-release-watcher/scripts/stop.sh

# Docker Compose で停止
docker compose stop github-release-watcher
```

### 再起動

```bash
docker compose restart github-release-watcher
```

### ログ確認

```bash
# リアルタイムログ
docker compose logs -f github-release-watcher

# 最新100行
docker compose logs --tail 100 github-release-watcher
```

### 設定検証

```bash
# 設定ファイルの検証のみ実行
docker compose run --rm github-release-watcher \
  python -m services.github-release-watcher \
  --config /app/data/config.toml \
  --validate
```

### 1回だけ実行

```bash
# 1回だけチェックして終了
docker compose run --rm github-release-watcher \
  python -m services.github-release-watcher \
  --config /app/data/config.toml \
  --once
```

## トラブルシューティング

### GitHub API レート制限

**問題**: "Rate limit exceeded" エラー

**解決策**:
- GitHub Token を設定（認証済み: 5000リクエスト/時）
- `check_interval` を増やす（例: 600秒）
- キャッシュが有効か確認

### 通知が送信されない

**問題**: 通知が届かない

**チェックリスト**:
1. `notifications.enabled = true` か確認
2. 使用する通知チャネルが `channels` リストに含まれているか
3. 各チャネルの `enabled = true` か確認
4. 環境変数（Webhook URL、SMTP設定など）が正しく設定されているか
5. ログで詳細なエラーを確認

### Docker 権限エラー

**問題**: ファイル書き込み権限エラー

**解決策**:
```bash
# .env で USER_ID と GROUP_ID を設定
echo "USER_ID=$(id -u)" >> .env
echo "GROUP_ID=$(id -g)" >> .env

# 権限を修正
sudo chown -R $(id -u):$(id -g) examples/github-release-watcher/config
```

### ネイティブ通知が表示されない

**問題**: Windows/macOS/Linux でネイティブ通知が表示されない

**原因**: Docker コンテナ内からホストの通知システムにアクセスできない

**解決策**:
- ネイティブ通知は、ホスト上で直接実行する場合のみ動作します
- Docker 環境では Discord、Slack、Email などの通知チャネルを使用してください

### 設定変更が反映されない

**問題**: config.toml を変更しても反映されない

**解決策**:
```bash
# サービスを再起動
docker compose restart github-release-watcher
```

## 高度な設定

### 複数インスタンスの実行

異なる設定で複数のインスタンスを実行する場合:

```yaml
# docker-compose.override.yml
services:
  github-release-watcher-dev:
    extends:
      service: github-release-watcher
    container_name: mcp-github-release-watcher-dev
    volumes:
      - ./examples/github-release-watcher/config-dev:/app/data:rw
```

### カスタムログ設定

```bash
# ログレベルを変更
docker compose run --rm \
  -e LOG_LEVEL=DEBUG \
  github-release-watcher
```

### Secret Manager との統合

環境変数を Secret Manager から取得する場合:

```bash
# AWS Secrets Manager
export GITHUB_TOKEN=$(aws secretsmanager get-secret-value --secret-id github-token --query SecretString --output text)
export DISCORD_WEBHOOK_URL=$(aws secretsmanager get-secret-value --secret-id discord-webhook --query SecretString --output text)
```

## 参考リンク

- [GitHub Release Watcher 設計ドキュメント](../../docs/services/github-release-watcher.md)
- [実装計画](../../docs/analysis/github-release-watcher-implementation-plan.md)
- [GitHub API ドキュメント](https://docs.github.com/en/rest/releases/releases)
- [Discord Webhook](https://discord.com/developers/docs/resources/webhook)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
