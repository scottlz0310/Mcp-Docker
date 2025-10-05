# GitHub Release Watcher サービス設計書

**作成日**: 2025-10-05
**ステータス**: 設計段階
**元プロジェト**: [WSL-kernel-watcher](https://github.com/scottlz0310/WSL-kernel-watcher)

---

## 📋 目次

- [概要](#概要)
- [設計方針](#設計方針)
- [アーキテクチャ](#アーキテクチャ)
- [機能仕様](#機能仕様)
- [実装計画](#実装計画)
- [使用例](#使用例)
- [移行ガイド](#移行ガイド)

---

## 概要

### プロジェクト目的

WSL-kernel-watcherをDocker版として再構成し、**GitHub Release Watcher**として汎用化。任意のGitHubリポジトリの新しいリリースを監視し、複数の通知チャネルで通知する常駐型サービスを提供します。

### 主要な変更点

| 項目 | WSL-kernel-watcher（元） | GitHub Release Watcher（新） |
|------|------------------------|---------------------------|
| **対象** | WSL2カーネル専用 | 任意のGitHubリポジトリ |
| **プラットフォーム** | Windows専用 | Docker（Linux/Mac/Windows） |
| **通知方法** | Windowsトースト | **ネイティブ通知**/Webhook/Discord/Slack/メール/ログ |
| **UI** | タスクトレイ | CLI + Docker管理 |
| **実行モード** | 常駐/ワンショット | 常駐/ワンショット/スケジュール |
| **配布** | Python Package | Dockerイメージ |

**ネイティブ通知**: Windows Toast、macOS通知センター、Linux libnotify

---

## 設計方針

### 1. **汎用化**

- **任意のGitHubリポジトリ監視**: WSL2カーネルに限定せず、あらゆるGitHubリポジトリのリリースを監視
- **複数リポジトリ対応**: 1つのサービスで複数リポジトリを監視可能
- **フィルタリング機能**: 安定版のみ、プレリリースを含む、タグパターンマッチングなど

### 2. **プラットフォーム非依存**

- **Docker化**: Windows/Linux/macOSで同一の実行環境
- **クラウド対応**: AWS/Azure/GCP等のコンテナサービスで実行可能
- **CI/CD統合**: GitHub Actions、GitLab CI等での利用を想定

### 3. **通知チャネルの多様化**

| 通知方法 | 用途 | 設定例 | プラットフォーム |
|---------|------|-------|----------------|
| **ネイティブ通知** | デスクトップ通知 | OSネイティブAPI | Windows/macOS/Linux |
| ↳ Windows Toast | Windows環境 | win10toast | Windows |
| ↳ macOS通知センター | macOS環境 | pync | macOS |
| ↳ Linux libnotify | Linux環境 | plyer/notify-send | Linux |
| **Webhook** | 汎用的な通知 | カスタムエンドポイントにPOST | All |
| **Discord** | チーム通知 | Discord Webhook URL | All |
| **Slack** | チーム通知 | Slack Incoming Webhook | All |
| **メール** | 個人通知 | SMTP設定 | All |
| **ファイル出力** | ログ・監査 | JSON/Markdownファイル | All |
| **標準出力** | デバッグ | コンソールログ | All |

### 4. **Mcp-Docker統合**

- **既存サービスとの統合**: GitHub MCP、Actions Simulator、DateTime Validatorと同一構造
- **統一管理**: docker-compose.ymlで一括管理
- **examples/構造**: 他リポジトリへの導入を容易化

---

## アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────┐
│          GitHub Release Watcher Container           │
│                                                      │
│  ┌──────────────┐    ┌─────────────────────────┐   │
│  │   Scheduler  │───→│  GitHub API Client      │   │
│  │  (定期実行)   │    │  - リリース取得          │   │
│  └──────────────┘    │  - レート制限管理        │   │
│         │            └─────────────────────────┘   │
│         ↓                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │         Release Comparator                    │  │
│  │  - バージョン比較                              │  │
│  │  - プレリリースフィルタリング                   │  │
│  │  - 重複チェック                                │  │
│  └──────────────────────────────────────────────┘  │
│         │                                           │
│         ↓                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │      Notification Manager                     │  │
│  │  ┌────────────┐  ┌────────────┐              │  │
│  │  │  Webhook   │  │  Discord   │              │  │
│  │  └────────────┘  └────────────┘              │  │
│  │  ┌────────────┐  ┌────────────┐              │  │
│  │  │   Slack    │  │   Email    │              │  │
│  │  └────────────┘  └────────────┘              │  │
│  └──────────────────────────────────────────────┘  │
│         │                                           │
│         ↓                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │         State Manager                         │  │
│  │  - 最終チェック時刻                            │  │
│  │  - 最新バージョン記録                          │  │
│  │  - 通知履歴                                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
         │                                    │
         ↓                                    ↓
    Volume (状態保存)              Notification Channels
```

### ディレクトリ構造

```
Mcp-Docker/
├── services/
│   └── github-release-watcher/
│       ├── __init__.py
│       ├── main.py                    # エントリーポイント
│       ├── config.py                  # 設定管理
│       ├── github_client.py           # GitHub API (既存コードを汎用化)
│       ├── scheduler.py               # スケジューリング (既存コードを汎用化)
│       ├── notification/              # 通知システム
│       │   ├── __init__.py
│       │   ├── base.py               # 通知基底クラス
│       │   ├── webhook.py            # Webhook通知
│       │   ├── discord.py            # Discord通知
│       │   ├── slack.py              # Slack通知
│       │   ├── email.py              # メール通知
│       │   └── file.py               # ファイル出力
│       ├── comparator.py             # バージョン比較ロジック
│       ├── state.py                  # 状態管理
│       └── logger.py                 # ログ設定
│
├── examples/
│   └── github-release-watcher/
│       ├── README.md                 # 使用方法
│       ├── docker-compose.yml        # 単体実行用
│       ├── .env.example              # 環境変数テンプレート
│       └── config/
│           ├── single-repo.toml      # 単一リポジトリ監視例
│           ├── multi-repo.toml       # 複数リポジトリ監視例
│           └── wsl-kernel.toml       # WSL2カーネル監視例（互換性）
│
├── docs/
│   └── services/
│       └── github-release-watcher.md # 本ドキュメント
│
├── tests/
│   └── services/
│       └── github-release-watcher/
│           ├── test_github_client.py
│           ├── test_notification.py
│           └── test_comparator.py
│
└── docker-compose.yml                # ルートCompose（統合）
```

---

## 機能仕様

### 1. リポジトリ監視

#### 設定形式（TOML）

```toml
# config.toml

[general]
execution_mode = "continuous"  # continuous | oneshot | scheduled
check_interval_minutes = 30
timezone = "Asia/Tokyo"

[[repositories]]
url = "microsoft/WSL2-Linux-Kernel"
name = "WSL2 Kernel"
enabled = true
filter = "stable_only"  # all | stable_only | prerelease_only | pattern
version_pattern = "^linux-msft-wsl-.*$"  # 正規表現

[[repositories]]
url = "docker/compose"
name = "Docker Compose"
enabled = true
filter = "stable_only"

[notifications]
enabled = true
channels = ["native", "discord", "webhook", "file"]

[notifications.native]
# OSネイティブ通知（Windows Toast/macOS/Linux自動検出）
enabled = true
duration = 10  # 表示時間（秒）
sound = true   # サウンド再生

[notifications.discord]
webhook_url = "${DISCORD_WEBHOOK_URL}"
mention_role_id = "123456789"
template = "discord_default"

[notifications.webhook]
url = "${WEBHOOK_URL}"
method = "POST"
headers = { "Authorization" = "Bearer ${WEBHOOK_TOKEN}" }

[notifications.email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
from = "watcher@example.com"
to = ["admin@example.com"]
subject_template = "New Release: {repo_name} {version}"

[notifications.file]
output_path = "/output/releases.json"
format = "json"  # json | markdown | csv

[logging]
level = "INFO"
file = "/output/watcher.log"
max_size_mb = 10
backup_count = 5

[state]
storage_path = "/data/state.json"
backup_enabled = true
```

### 2. 実行モード

#### a. 常駐モード（continuous）

```bash
# Docker Compose
docker compose up -d github-release-watcher

# 30分ごとにリポジトリをチェック
# 新しいリリースがあれば通知
```

#### b. ワンショットモード（oneshot）

```bash
# 一度だけチェックして終了
docker compose run --rm github-release-watcher python -m services.github_release_watcher.main --mode oneshot

# CI/CDでの使用例
docker run --rm \
  -v "$PWD/config.toml:/config/config.toml" \
  -e DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL" \
  ghcr.io/scottlz0310/mcp-docker:latest \
  python -m services.github_release_watcher.main --mode oneshot
```

#### c. スケジュールモード（scheduled）

```bash
# cron式でスケジュール実行
# config.tomlで設定
[general]
execution_mode = "scheduled"
schedule = "0 */6 * * *"  # 6時間ごと
```

### 3. 通知テンプレート

#### ネイティブ通知例（Windows Toast）

```
タイトル: 🚀 WSL2 Kernel v5.15.123.1
メッセージ: 新しいリリースが公開されました
クリックでリリースページを開く
表示時間: 10秒
サウンド: あり
```

#### Discord通知例

```markdown
🚀 **新しいリリース検出！**

**リポジトリ**: microsoft/WSL2-Linux-Kernel
**バージョン**: v5.15.123.1
**リリース日**: 2025-10-05 14:30 JST
**変更内容**:
- セキュリティアップデート
- パフォーマンス改善
- バグ修正

🔗 [リリースページを見る](https://github.com/microsoft/WSL2-Linux-Kernel/releases/tag/v5.15.123.1)
```

#### Webhook通知例（JSON）

```json
{
  "event": "new_release",
  "timestamp": "2025-10-05T14:30:00+09:00",
  "repository": {
    "url": "microsoft/WSL2-Linux-Kernel",
    "name": "WSL2 Kernel"
  },
  "release": {
    "tag_name": "v5.15.123.1",
    "name": "WSL2 Kernel v5.15.123.1",
    "published_at": "2025-10-05T05:30:00Z",
    "html_url": "https://github.com/microsoft/WSL2-Linux-Kernel/releases/tag/v5.15.123.1",
    "is_prerelease": false,
    "body": "## Changes\n- Security updates\n- Performance improvements"
  },
  "watcher": {
    "check_interval_minutes": 30,
    "last_check": "2025-10-05T14:00:00+09:00"
  }
}
```

### 4. バージョン比較ロジック

```python
# comparator.py

from packaging import version
import re

class ReleaseComparator:
    def is_newer(self, current: str, latest: str) -> bool:
        """セマンティックバージョニングで比較"""
        return version.parse(latest) > version.parse(current)

    def matches_pattern(self, tag: str, pattern: str) -> bool:
        """正規表現パターンマッチング"""
        return bool(re.match(pattern, tag))

    def is_stable(self, tag: str) -> bool:
        """プレリリースかどうか判定"""
        # rc, alpha, beta, preview などを検出
        return not any(x in tag.lower() for x in ['rc', 'alpha', 'beta', 'preview', 'pre'])
```

### 5. 状態管理

```json
// state.json
{
  "last_check": "2025-10-05T14:30:00+09:00",
  "repositories": {
    "microsoft/WSL2-Linux-Kernel": {
      "latest_version": "v5.15.123.1",
      "last_notified": "2025-10-05T14:30:00+09:00",
      "check_count": 1250,
      "notification_history": [
        {
          "version": "v5.15.123.1",
          "notified_at": "2025-10-05T14:30:00+09:00",
          "channels": ["discord", "webhook"]
        }
      ]
    }
  },
  "statistics": {
    "total_checks": 2500,
    "total_releases_detected": 15,
    "total_notifications_sent": 45
  }
}
```

---

## 実装計画

### フェーズ1: コア機能の移植（1-2日）

**タスク**:
1. ✅ WSL-kernel-watcherのコードベースを分析
2. 🔄 GitHub APIクライアントを汎用化
   - `github_api.py` → `github_client.py`
   - WSL固有のロジックを削除
   - 複数リポジトリ対応
3. 🔄 スケジューラーを汎用化
   - `scheduler.py` の再実装
   - 複数リポジトリのスケジューリング
4. 🔄 設定管理の拡張
   - TOML形式対応
   - 環境変数展開
   - 複数リポジトリ設定

**成果物**:
- `services/github-release-watcher/github_client.py`
- `services/github-release-watcher/scheduler.py`
- `services/github-release-watcher/config.py`

### フェーズ2: 通知システムの実装（2-3日）

**タスク**:
1. 通知基底クラスの設計
2. 各通知チャネルの実装
   - Webhook通知
   - Discord通知
   - Slack通知
   - メール通知
   - ファイル出力
3. 通知テンプレートシステム
4. エラーハンドリングとリトライ機構

**成果物**:
- `services/github-release-watcher/notification/` 配下のモジュール

### フェーズ3: Docker化と統合（1日）

**タスク**:
1. Dockerfileの作成（マルチステージビルド）
2. docker-compose.ymlへの統合
3. 環境変数とボリューム設定
4. ヘルスチェック実装

**成果物**:
- `Dockerfile` の `github-release-watcher` ターゲット
- `docker-compose.yml` の `github-release-watcher` サービス定義

### フェーズ4: examples/ とドキュメント（1日）

**タスク**:
1. `examples/github-release-watcher/` 作成
2. 使用例の作成
   - 単一リポジトリ監視
   - 複数リポジトリ監視
   - WSL2カーネル監視（互換性）
3. README.mdの作成
4. トラブルシューティングガイド

**成果物**:
- `examples/github-release-watcher/README.md`
- 設定ファイル例

### フェーズ5: テストと検証（1-2日）

**タスク**:
1. ユニットテスト作成
2. 統合テスト作成
3. E2Eテスト（実際のGitHub APIを使用）
4. CI/CD統合テスト
5. パフォーマンステスト

**成果物**:
- `tests/services/github-release-watcher/` 配下のテスト

### フェーズ6: リリース準備（1日）

**タスク**:
1. Dockerイメージのビルドとpush
2. GitHub Actionsワークフロー作成
3. バージョニング設定
4. CHANGELOGの更新
5. リリースノート作成

**成果物**:
- GitHub Container Registryへのイメージpush
- リリースタグ

**合計**: 約7-10日

---

## 使用例

### 例1: WSL2カーネルの監視（元の用途）

```bash
# examples/github-release-watcher/config/wsl-kernel.toml

[general]
execution_mode = "continuous"
check_interval_minutes = 30

[[repositories]]
url = "microsoft/WSL2-Linux-Kernel"
name = "WSL2 Kernel"
enabled = true
filter = "stable_only"
version_pattern = "^linux-msft-wsl-.*$"

[notifications]
enabled = true
channels = ["native", "discord"]

[notifications.native]
# Windows Toast通知を使用
enabled = true
duration = 10
sound = true

[notifications.discord]
webhook_url = "${DISCORD_WEBHOOK_URL}"
template = """
🐧 **WSL2カーネル更新！**
バージョン: {version}
リリース日: {published_at}
[リリースページ]({html_url})
"""
```

```bash
# 実行
docker compose -f examples/github-release-watcher/docker-compose.yml up -d
```

### 例2: 複数リポジトリの監視

```bash
# examples/github-release-watcher/config/multi-repo.toml

[[repositories]]
url = "docker/compose"
name = "Docker Compose"
enabled = true
filter = "stable_only"

[[repositories]]
url = "kubernetes/kubernetes"
name = "Kubernetes"
enabled = true
filter = "stable_only"

[[repositories]]
url = "python/cpython"
name = "Python"
enabled = true
filter = "stable_only"
version_pattern = "^v3\\."  # Python 3.xのみ
```

### 例3: CI/CDでの使用

```yaml
# .github/workflows/check-dependencies.yml

name: Dependency Update Check
on:
  schedule:
    - cron: '0 */6 * * *'  # 6時間ごと
  workflow_dispatch:

jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - name: Check for updates
        run: |
          docker run --rm \
            -v "$PWD/config.toml:/config/config.toml" \
            -e WEBHOOK_URL="${{ secrets.WEBHOOK_URL }}" \
            -e DISCORD_WEBHOOK_URL="${{ secrets.DISCORD_WEBHOOK_URL }}" \
            ghcr.io/scottlz0310/mcp-docker:latest \
            python -m services.github_release_watcher.main --mode oneshot
```

### 例4: Slack通知

```toml
[notifications.slack]
webhook_url = "${SLACK_WEBHOOK_URL}"
channel = "#releases"
username = "Release Watcher"
icon_emoji = ":rocket:"
template = """
:rocket: *新しいリリース: {repo_name}*
バージョン: `{version}`
リリース日: {published_at}
<{html_url}|詳細を見る>
"""
```

---

## 移行ガイド

### WSL-kernel-watcherからの移行

#### 1. 設定ファイルの変換

**元の設定（config.toml）**:
```toml
[general]
execution_mode = "oneshot"
check_interval_minutes = 30
repository_url = "microsoft/WSL2-Linux-Kernel"

[notification]
enabled = true
```

**新しい設定（config.toml）**:
```toml
[general]
execution_mode = "oneshot"
check_interval_minutes = 30

[[repositories]]
url = "microsoft/WSL2-Linux-Kernel"
name = "WSL2 Kernel"
enabled = true
filter = "stable_only"

[notifications]
enabled = true
channels = ["native", "discord"]  # ネイティブ通知を追加

[notifications.native]
# Windows Toast通知（元の機能を維持）
enabled = true
duration = 10
sound = true

[notifications.discord]
webhook_url = "${DISCORD_WEBHOOK_URL}"
```

#### 2. 通知方法の変更

| 元の通知 | 新しい通知 | 設定例 |
|---------|----------|-------|
| Windowsトースト | **ネイティブ通知（Windows Toast維持）** | `[notifications.native]` |
| - | Discord Webhook | `[notifications.discord]` |
| - | Slack Webhook | `[notifications.slack]` |
| - | メール | `[notifications.email]` |
| - | ファイル出力 | `[notifications.file]` |

#### 3. 実行方法の変更

**元の実行**:
```powershell
# Windows
uv run wsl-kernel-watcher
```

**新しい実行**:
```bash
# Docker
docker compose up -d github-release-watcher

# または
docker run --rm \
  -v "$PWD/config.toml:/config/config.toml" \
  ghcr.io/scottlz0310/mcp-docker:latest \
  python -m services.github_release_watcher.main
```

#### 4. 互換性スクリプト

```bash
#!/bin/bash
# migrate-to-docker.sh

echo "WSL-kernel-watcher → GitHub Release Watcher 移行スクリプト"

# 既存の設定を読み込み
if [ -f "config.toml" ]; then
    echo "既存の設定ファイルを検出しました"

    # 新しい形式に変換
    cat > new-config.toml << EOF
[general]
execution_mode = "$(grep execution_mode config.toml | cut -d'"' -f2)"
check_interval_minutes = $(grep check_interval_minutes config.toml | cut -d'=' -f2 | tr -d ' ')

[[repositories]]
url = "$(grep repository_url config.toml | cut -d'"' -f2)"
name = "WSL2 Kernel"
enabled = true
filter = "stable_only"

[notifications]
enabled = true
channels = ["discord"]

[notifications.discord]
webhook_url = "\${DISCORD_WEBHOOK_URL}"
EOF

    echo "✅ 新しい設定ファイル 'new-config.toml' を作成しました"
    echo "📝 内容を確認して、必要に応じて編集してください"
fi

# Docker Composeファイルをコピー
cp ~/workspace/Mcp-Docker/examples/github-release-watcher/docker-compose.yml .

echo "✅ 移行完了！"
echo "実行: docker compose up -d"
```

---

## 付録

### A. 環境変数リファレンス

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|----------|------|
| `CONFIG_FILE` | ❌ | `/config/config.toml` | 設定ファイルパス |
| `EXECUTION_MODE` | ❌ | `continuous` | 実行モード |
| `CHECK_INTERVAL` | ❌ | `30` | チェック間隔（分） |
| `GITHUB_TOKEN` | ⚠️ | - | GitHub API トークン（レート制限緩和） |
| `DISCORD_WEBHOOK_URL` | ⚠️ | - | Discord Webhook URL |
| `SLACK_WEBHOOK_URL` | ⚠️ | - | Slack Webhook URL |
| `WEBHOOK_URL` | ⚠️ | - | カスタムWebhook URL |
| `SMTP_HOST` | ⚠️ | - | SMTPサーバーホスト |
| `SMTP_PORT` | ⚠️ | `587` | SMTPサーバーポート |
| `SMTP_USER` | ⚠️ | - | SMTPユーザー名 |
| `SMTP_PASSWORD` | ⚠️ | - | SMTPパスワード |
| `LOG_LEVEL` | ❌ | `INFO` | ログレベル |
| `STATE_FILE` | ❌ | `/data/state.json` | 状態保存ファイル |

⚠️ = 使用する通知チャネルに応じて必須

### B. CLI リファレンス

```bash
# 基本的な実行
python -m services.github_release_watcher.main

# オプション
--mode {continuous|oneshot|scheduled}  # 実行モード
--config PATH                          # 設定ファイルパス
--repository OWNER/REPO                # 単一リポジトリ監視（設定ファイル不要）
--filter {all|stable|prerelease}       # フィルター
--notify CHANNEL                       # 通知チャネル
--state-file PATH                      # 状態ファイルパス
--log-level {DEBUG|INFO|WARNING|ERROR} # ログレベル
--version                              # バージョン表示
--help                                 # ヘルプ表示
```

### C. トラブルシューティング

#### GitHub APIレート制限

```bash
# GitHub トークンを設定
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"

# レート制限を確認
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

#### 通知が届かない

```bash
# ログを確認
docker compose logs github-release-watcher

# Discord Webhookをテスト
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'
```

#### 状態ファイルのリセット

```bash
# 状態をリセット（全リポジトリを再チェック）
docker compose run --rm github-release-watcher \
  python -m services.github_release_watcher.main --reset-state
```

---

## 次のステップ

1. ✅ 設計書の確認・承認
2. 🔄 フェーズ1の実装開始
3. 🔄 コードレビューとテスト
4. 🔄 ドキュメント作成
5. 🔄 リリース準備

---

**更新履歴**:
- 2025-10-05: 初版作成（設計段階）
