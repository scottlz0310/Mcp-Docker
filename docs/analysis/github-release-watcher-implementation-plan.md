# GitHub Release Watcher 実装計画

**作成日**: 2025-10-05
**目的**: WSL-kernel-watcherをDocker版として再構成し、Mcp-Dockerに統合
**推定期間**: 7-10日
**優先度**: Medium

---

## 📋 目次

- [プロジェクト概要](#プロジェクト概要)
- [実装フェーズ](#実装フェーズ)
- [技術スタック](#技術スタック)
- [成功指標](#成功指標)
- [リスクと対策](#リスクと対策)

---

## プロジェクト概要

### 背景

WSL-kernel-watcherは、Windows環境専用のWSL2カーネルリリース監視ツールです。これを以下の方針でDocker版として再構成します：

1. **汎用化**: WSL2カーネル専用 → 任意のGitHubリポジトリ監視
2. **プラットフォーム非依存**: Windows専用 → Docker（Linux/Mac/Windows）
3. **通知の多様化**: Windowsトースト → Webhook/Discord/Slack/メール
4. **Mcp-Docker統合**: 既存サービスと同一構造

### 目標

- ✅ WSL-kernel-watcherの機能を100%カバー
- ✅ 新機能: 複数リポジトリ監視、複数通知チャネル
- ✅ Docker化によるクロスプラットフォーム対応
- ✅ Mcp-Dockerの統一アーキテクチャに準拠
- ✅ 他リポジトリへの簡単な導入（examples/構造）

---

## 実装フェーズ

### フェーズ1: コア機能の移植（1-2日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 1.1 | コードベースの分析 | WSL-kernel-watcherのコード構造を理解 | 2時間 | 高 |
| 1.2 | GitHub APIクライアント汎用化 | `github_api.py` → `github_client.py` | 4時間 | 高 |
| 1.3 | スケジューラーの汎用化 | `scheduler.py` の再実装 | 4時間 | 高 |
| 1.4 | 設定管理の拡張 | TOML形式、複数リポジトリ対応 | 3時間 | 高 |
| 1.5 | バージョン比較ロジック | `comparator.py` の実装 | 2時間 | 高 |
| 1.6 | 状態管理システム | `state.py` の実装 | 2時間 | 高 |
| 1.7 | ロガーの移植 | `logger.py` の移植 | 1時間 | 中 |

#### 詳細設計

**1.2 GitHub APIクライアント汎用化**

```python
# services/github-release-watcher/github_client.py

from typing import List, Optional
from dataclasses import dataclass
import requests

@dataclass
class Release:
    tag_name: str
    name: str
    published_at: str
    html_url: str
    is_prerelease: bool
    body: str

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_latest_release(
        self,
        owner: str,
        repo: str,
        include_prerelease: bool = False
    ) -> Optional[Release]:
        """最新リリースを取得"""
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        response = self.session.get(url)
        response.raise_for_status()

        releases = response.json()
        for release in releases:
            if not include_prerelease and release.get("prerelease"):
                continue
            return Release(
                tag_name=release["tag_name"],
                name=release["name"],
                published_at=release["published_at"],
                html_url=release["html_url"],
                is_prerelease=release["prerelease"],
                body=release["body"]
            )
        return None

    def get_rate_limit(self) -> dict:
        """レート制限情報を取得"""
        url = "https://api.github.com/rate_limit"
        response = self.session.get(url)
        return response.json()
```

**1.3 スケジューラーの汎用化**

```python
# services/github-release-watcher/scheduler.py

import time
import schedule
from typing import Callable, List
from .config import Config, RepositoryConfig
from .github_client import GitHubClient

class Scheduler:
    def __init__(
        self,
        config: Config,
        github_client: GitHubClient,
        on_new_release: Callable
    ):
        self.config = config
        self.github_client = github_client
        self.on_new_release = on_new_release
        self._running = False

    def start(self):
        """スケジューリング開始"""
        self._running = True

        if self.config.execution_mode == "continuous":
            # 定期実行
            schedule.every(self.config.check_interval_minutes).minutes.do(
                self.check_all_repositories
            )
            # 即座に1回実行
            self.check_all_repositories()

            while self._running:
                schedule.run_pending()
                time.sleep(1)

        elif self.config.execution_mode == "oneshot":
            # 一度だけ実行
            self.check_all_repositories()

    def check_all_repositories(self):
        """全リポジトリをチェック"""
        for repo_config in self.config.repositories:
            if not repo_config.enabled:
                continue

            self.check_repository(repo_config)

    def check_repository(self, repo_config: RepositoryConfig):
        """単一リポジトリをチェック"""
        owner, repo = repo_config.url.split("/")
        latest = self.github_client.get_latest_release(
            owner, repo,
            include_prerelease=(repo_config.filter != "stable_only")
        )

        if latest:
            # バージョン比較・通知処理
            self.on_new_release(repo_config, latest)

    def stop(self):
        """スケジューリング停止"""
        self._running = False
```

**1.4 設定管理の拡張**

```python
# services/github-release-watcher/config.py

from dataclasses import dataclass
from typing import List, Optional
import tomli
from pathlib import Path
import os

@dataclass
class RepositoryConfig:
    url: str
    name: str
    enabled: bool = True
    filter: str = "stable_only"  # all | stable_only | prerelease_only | pattern
    version_pattern: Optional[str] = None

@dataclass
class NotificationConfig:
    enabled: bool = True
    channels: List[str] = None

    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None

@dataclass
class Config:
    execution_mode: str = "continuous"
    check_interval_minutes: int = 30
    repositories: List[RepositoryConfig] = None
    notifications: NotificationConfig = None

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """設定ファイルから読み込み"""
        with open(path, "rb") as f:
            data = tomli.load(f)

        # 環境変数展開
        data = cls._expand_env_vars(data)

        repositories = [
            RepositoryConfig(**repo) for repo in data.get("repositories", [])
        ]

        notifications = NotificationConfig(
            **data.get("notifications", {})
        )

        return cls(
            execution_mode=data["general"]["execution_mode"],
            check_interval_minutes=data["general"]["check_interval_minutes"],
            repositories=repositories,
            notifications=notifications,
        )

    @staticmethod
    def _expand_env_vars(data: dict) -> dict:
        """環境変数を展開（${VAR_NAME}形式）"""
        import re

        def expand(value):
            if isinstance(value, str):
                # ${VAR_NAME} を展開
                return re.sub(
                    r'\$\{(\w+)\}',
                    lambda m: os.getenv(m.group(1), m.group(0)),
                    value
                )
            elif isinstance(value, dict):
                return {k: expand(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand(v) for v in value]
            return value

        return expand(data)
```

**1.5 バージョン比較ロジック**

```python
# services/github-release-watcher/comparator.py

from packaging import version
import re
from typing import Optional

class ReleaseComparator:
    """リリースバージョンの比較・フィルタリング"""

    def is_newer(self, current: str, latest: str) -> bool:
        """セマンティックバージョニングで比較"""
        try:
            return version.parse(latest) > version.parse(current)
        except Exception:
            # セマンティックバージョニングでない場合は文字列比較
            return latest > current

    def matches_pattern(self, tag: str, pattern: str) -> bool:
        """正規表現パターンマッチング"""
        if not pattern:
            return True
        return bool(re.match(pattern, tag))

    def is_stable(self, tag: str, prerelease_flag: bool = False) -> bool:
        """安定版かどうか判定"""
        # GitHub API の prerelease フラグを優先
        if prerelease_flag:
            return False

        # タグ名からもチェック（補助的）
        prerelease_keywords = ['rc', 'alpha', 'beta', 'preview', 'pre', 'dev', 'nightly']
        tag_lower = tag.lower()
        return not any(keyword in tag_lower for keyword in prerelease_keywords)

    def filter_releases(
        self,
        releases: list,
        filter_mode: str,
        version_pattern: Optional[str] = None
    ) -> list:
        """リリースリストをフィルタリング"""
        filtered = []

        for release in releases:
            # パターンマッチング
            if version_pattern and not self.matches_pattern(release.tag_name, version_pattern):
                continue

            # フィルタモード
            if filter_mode == "stable_only" and not self.is_stable(release.tag_name, release.is_prerelease):
                continue
            elif filter_mode == "prerelease_only" and self.is_stable(release.tag_name, release.is_prerelease):
                continue

            filtered.append(release)

        return filtered
```

**1.6 状態管理システム**

```python
# services/github-release-watcher/state.py

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from threading import Lock

@dataclass
class NotificationRecord:
    """通知履歴レコード"""
    version: str
    notified_at: str
    channels: List[str]

@dataclass
class RepositoryState:
    """リポジトリごとの状態"""
    latest_version: str
    last_notified: str
    check_count: int
    notification_history: List[NotificationRecord]

class StateManager:
    """状態管理（スレッドセーフ）"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.lock = Lock()
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """状態ファイルから読み込み"""
        if not self.state_file.exists():
            return {
                "last_check": None,
                "repositories": {},
                "statistics": {
                    "total_checks": 0,
                    "total_releases_detected": 0,
                    "total_notifications_sent": 0
                }
            }

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return self._load_state.__defaults__[0]

    def save_state(self):
        """状態ファイルに保存"""
        with self.lock:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)

    def get_latest_version(self, repo_url: str) -> Optional[str]:
        """最新バージョンを取得"""
        with self.lock:
            repo_state = self.state["repositories"].get(repo_url)
            return repo_state["latest_version"] if repo_state else None

    def update_latest_version(
        self,
        repo_url: str,
        version: str,
        channels: List[str]
    ):
        """最新バージョンを更新"""
        with self.lock:
            now = datetime.now().isoformat()

            if repo_url not in self.state["repositories"]:
                self.state["repositories"][repo_url] = {
                    "latest_version": version,
                    "last_notified": now,
                    "check_count": 0,
                    "notification_history": []
                }

            repo_state = self.state["repositories"][repo_url]
            repo_state["latest_version"] = version
            repo_state["last_notified"] = now
            repo_state["notification_history"].append({
                "version": version,
                "notified_at": now,
                "channels": channels
            })

            # 統計を更新
            self.state["statistics"]["total_releases_detected"] += 1
            self.state["statistics"]["total_notifications_sent"] += len(channels)

            self.save_state()

    def increment_check_count(self, repo_url: str):
        """チェック回数をインクリメント"""
        with self.lock:
            if repo_url in self.state["repositories"]:
                self.state["repositories"][repo_url]["check_count"] += 1
            self.state["statistics"]["total_checks"] += 1
            self.state["last_check"] = datetime.now().isoformat()
            self.save_state()

    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        with self.lock:
            return self.state["statistics"].copy()
```

#### 成果物

- ✅ `services/github-release-watcher/github_client.py`
- ✅ `services/github-release-watcher/scheduler.py`
- ✅ `services/github-release-watcher/config.py`
- ✅ `services/github-release-watcher/comparator.py` **← バージョン比較ロジック**
- ✅ `services/github-release-watcher/state.py` **← 状態管理システム**
- ✅ `services/github-release-watcher/logger.py`

---

### フェーズ2: 通知システムの実装（2-3日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 2.1 | 通知基底クラス設計 | 抽象基底クラス `NotificationBase` | 2時間 | 高 |
| 2.2 | ネイティブ通知実装 | Windows Toast/macOS/Linux | 4時間 | **最優先** |
| 2.3 | Webhook通知実装 | 汎用Webhook POST | 3時間 | 高 |
| 2.4 | Discord通知実装 | Discord Webhook | 3時間 | 高 |
| 2.5 | Slack通知実装 | Slack Incoming Webhook | 3時間 | 中 |
| 2.6 | メール通知実装 | SMTP送信 | 4時間 | 中 |
| 2.7 | ファイル出力実装 | JSON/Markdown出力 | 2時間 | 中 |
| 2.8 | 通知マネージャー | 複数チャネル管理 | 3時間 | 高 |
| 2.9 | テンプレートシステム | カスタムテンプレート | 2時間 | 低 |

#### 詳細設計

**2.1 通知基底クラス設計**

```python
# services/github-release-watcher/notification/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class NotificationMessage:
    """通知メッセージのデータクラス"""
    repository_name: str
    repository_url: str
    version: str
    published_at: str
    html_url: str
    is_prerelease: bool
    body: str

class NotificationBase(ABC):
    """通知の抽象基底クラス"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """通知を送信"""
        pass

    def format_message(self, message: NotificationMessage, template: str) -> str:
        """テンプレートからメッセージを整形"""
        return template.format(
            repo_name=message.repository_name,
            repo_url=message.repository_url,
            version=message.version,
            published_at=message.published_at,
            html_url=message.html_url,
            is_prerelease="Yes" if message.is_prerelease else "No",
            body=message.body
        )
```

**2.2 ネイティブ通知実装**

```python
# services/github-release-watcher/notification/native.py

import platform
from .base import NotificationBase, NotificationMessage

class NativeNotification(NotificationBase):
    """OSネイティブ通知（マルチプラットフォーム対応）"""

    def __init__(self, config):
        super().__init__(config)
        self.system = platform.system()
        self.duration = config.get("duration", 10)
        self.sound = config.get("sound", True)

    def send(self, message: NotificationMessage) -> bool:
        if self.system == "Windows":
            return self._send_windows(message)
        elif self.system == "Darwin":  # macOS
            return self._send_macos(message)
        elif self.system == "Linux":
            return self._send_linux(message)
        return False

    def _send_windows(self, message: NotificationMessage) -> bool:
        """Windows Toast通知"""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                title=f"🚀 {message.repository_name} {message.version}",
                msg=f"新しいリリースが公開されました\n{message.html_url}",
                duration=self.duration,
                threaded=True,
                callback_on_click=lambda: self._open_url(message.html_url)
            )
            return True
        except Exception as e:
            print(f"Windows Toast通知エラー: {e}")
            return False

    def _send_macos(self, message: NotificationMessage) -> bool:
        """macOS通知センター"""
        try:
            import pync
            pync.notify(
                f"新しいリリース: {message.version}",
                title=f"🚀 {message.repository_name}",
                open=message.html_url,
                sound=self.sound
            )
            return True
        except Exception as e:
            print(f"macOS通知エラー: {e}")
            return False

    def _send_linux(self, message: NotificationMessage) -> bool:
        """Linux libnotify"""
        try:
            from plyer import notification
            notification.notify(
                title=f"🚀 {message.repository_name} {message.version}",
                message=f"新しいリリースが公開されました\n{message.html_url}",
                timeout=self.duration
            )
            return True
        except Exception as e:
            print(f"Linux通知エラー: {e}")
            return False

    def _open_url(self, url: str):
        """URLを開く"""
        import webbrowser
        webbrowser.open(url)
```

**2.3 Webhook通知実装**

```python
# services/github-release-watcher/notification/webhook.py

import requests
from .base import NotificationBase, NotificationMessage

class WebhookNotification(NotificationBase):
    def send(self, message: NotificationMessage) -> bool:
        try:
            url = self.config.get("url")
            method = self.config.get("method", "POST")
            headers = self.config.get("headers", {})

            payload = {
                "event": "new_release",
                "repository": {
                    "name": message.repository_name,
                    "url": message.repository_url,
                },
                "release": {
                    "version": message.version,
                    "published_at": message.published_at,
                    "html_url": message.html_url,
                    "is_prerelease": message.is_prerelease,
                    "body": message.body,
                }
            }

            response = requests.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return True

        except Exception as e:
            print(f"Webhook送信エラー: {e}")
            return False
```

**2.4 Discord通知実装**

```python
# services/github-release-watcher/notification/discord.py

import requests
from .base import NotificationBase, NotificationMessage

class DiscordNotification(NotificationBase):
    def send(self, message: NotificationMessage) -> bool:
        try:
            webhook_url = self.config.get("webhook_url")
            template = self.config.get("template", self._default_template())

            content = self.format_message(message, template)

            payload = {
                "content": content,
                "embeds": [
                    {
                        "title": f"🚀 {message.repository_name} {message.version}",
                        "description": message.body[:500],  # 500文字まで
                        "url": message.html_url,
                        "color": 0x00FF00 if not message.is_prerelease else 0xFFA500,
                        "fields": [
                            {
                                "name": "バージョン",
                                "value": message.version,
                                "inline": True
                            },
                            {
                                "name": "リリース日",
                                "value": message.published_at,
                                "inline": True
                            }
                        ],
                        "timestamp": message.published_at
                    }
                ]
            }

            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            return True

        except Exception as e:
            print(f"Discord通知エラー: {e}")
            return False

    def _default_template(self) -> str:
        return """
🚀 **新しいリリース検出！**

**リポジトリ**: {repo_name}
**バージョン**: {version}
**リリース日**: {published_at}

🔗 [リリースページを見る]({html_url})
"""
```

**2.8 通知マネージャー**

```python
# services/github-release-watcher/notification/manager.py

from typing import List, Dict, Any
from .base import NotificationBase, NotificationMessage
from .native import NativeNotification
from .webhook import WebhookNotification
from .discord import DiscordNotification
from .slack import SlackNotification
from .email import EmailNotification
from .file import FileNotification

class NotificationManager:
    """複数の通知チャネルを管理"""

    CHANNEL_MAP = {
        "native": NativeNotification,  # OSネイティブ通知（最優先）
        "webhook": WebhookNotification,
        "discord": DiscordNotification,
        "slack": SlackNotification,
        "email": EmailNotification,
        "file": FileNotification,
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels: List[NotificationBase] = []

        # 有効な通知チャネルを初期化
        enabled_channels = config.get("channels", [])
        for channel_name in enabled_channels:
            if channel_name in self.CHANNEL_MAP:
                channel_config = config.get(channel_name, {})
                channel_class = self.CHANNEL_MAP[channel_name]
                self.channels.append(channel_class(channel_config))

    def send_all(self, message: NotificationMessage) -> Dict[str, bool]:
        """全チャネルに通知を送信"""
        results = {}
        for channel in self.channels:
            channel_name = channel.__class__.__name__
            success = channel.send(message)
            results[channel_name] = success

        return results
```

#### 成果物

- ✅ `services/github-release-watcher/notification/base.py`
- ✅ `services/github-release-watcher/notification/native.py` **← Windows Toast含むネイティブ通知**
- ✅ `services/github-release-watcher/notification/webhook.py`
- ✅ `services/github-release-watcher/notification/discord.py`
- ✅ `services/github-release-watcher/notification/slack.py`
- ✅ `services/github-release-watcher/notification/email.py`
- ✅ `services/github-release-watcher/notification/file.py`
- ✅ `services/github-release-watcher/notification/manager.py`

---

### フェーズ3: Docker化と統合（1日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 3.1 | Dockerfileマルチステージ | `github-release-watcher` ターゲット追加 | 2時間 | 高 |
| 3.2 | docker-compose統合 | サービス定義追加 | 2時間 | 高 |
| 3.3 | 環境変数設定 | `.env.example` 更新 | 1時間 | 高 |
| 3.4 | ヘルスチェック実装 | Docker healthcheck | 1時間 | 中 |
| 3.5 | ボリューム設定 | 状態保存・ログ出力 | 1時間 | 中 |

#### 詳細設計

**3.1 Dockerfileマルチステージ**

```dockerfile
# Dockerfile

# ... 既存のステージ ...

# ==============================================================================
# GitHub Release Watcher
# ==============================================================================
FROM python-base AS github-release-watcher

WORKDIR /app

# 依存関係をインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# アプリケーションコードをコピー
COPY services/github-release-watcher ./services/github-release-watcher

# 状態・ログディレクトリを作成
RUN mkdir -p /data /output

# ヘルスチェック
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# デフォルトコマンド
CMD ["uv", "run", "python", "-m", "services.github_release_watcher.main"]
```

**3.2 docker-compose統合**

```yaml
# docker-compose.yml

services:
  # ... 既存サービス ...

  github-release-watcher:
    build:
      context: .
      dockerfile: Dockerfile
      target: github-release-watcher
    container_name: ${RELEASE_WATCHER_CONTAINER_NAME:-mcp-release-watcher}
    user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
    volumes:
      - ./examples/github-release-watcher/config:/config:ro  # 設定ファイル（読み取り専用）
      - ./output:/output:rw  # 出力ファイル
      - release-watcher-data:/data:rw  # 状態保存
    environment:
      - CONFIG_FILE=/config/config.toml
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    restart: unless-stopped
    networks:
      - mcp-network
    profiles:
      - tools

volumes:
  # ... 既存ボリューム ...
  release-watcher-data:
```

#### 成果物

- ✅ `Dockerfile` 更新（`github-release-watcher` ターゲット）
- ✅ `docker-compose.yml` 更新（サービス追加）
- ✅ `.env.example` 更新（環境変数追加）

---

### フェーズ4: examples/ とドキュメント（1日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 4.1 | examples/構造作成 | ディレクトリ・ファイル作成 | 1時間 | 高 |
| 4.2 | README作成 | 使用方法ドキュメント | 2時間 | 高 |
| 4.3 | 設定例作成 | 単一・複数・WSL監視例 | 2時間 | 高 |
| 4.4 | docker-compose.yml作成 | 単体実行用 | 1時間 | 高 |
| 4.5 | トラブルシューティング | FAQ作成 | 1時間 | 中 |

#### ディレクトリ構造

```
examples/github-release-watcher/
├── README.md                          # 使用方法
├── docker-compose.yml                 # 単体実行用Compose
├── .env.example                       # 環境変数テンプレート
├── config/
│   ├── single-repo.toml              # 単一リポジトリ監視例
│   ├── multi-repo.toml               # 複数リポジトリ監視例
│   ├── wsl-kernel.toml               # WSL2カーネル監視例
│   └── ci-cd.toml                    # CI/CD用設定例
└── scripts/
    ├── migrate-from-wsl-watcher.sh   # 移行スクリプト
    └── test-notification.sh          # 通知テストスクリプト
```

#### 成果物

- ✅ `examples/github-release-watcher/README.md`
- ✅ `examples/github-release-watcher/docker-compose.yml`
- ✅ `examples/github-release-watcher/.env.example`
- ✅ `examples/github-release-watcher/config/*.toml`
- ✅ `examples/github-release-watcher/scripts/*.sh`

---

### フェーズ5: テストと検証（1-2日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 5.1 | ユニットテスト | 各モジュールのテスト | 4時間 | 高 |
| 5.2 | 統合テスト | サービス統合テスト | 3時間 | 高 |
| 5.3 | E2Eテスト | 実際のGitHub API使用 | 3時間 | 中 |
| 5.4 | 通知テスト | 各チャネルの動作確認 | 2時間 | 高 |
| 5.5 | パフォーマンステスト | 負荷テスト | 2時間 | 低 |

#### テスト計画

**モック層設計**

```python
# tests/services/github-release-watcher/conftest.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

@pytest.fixture
def mock_github_api():
    """GitHub API モック"""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[
            {
                "tag_name": "v1.0.0",
                "name": "Release v1.0.0",
                "published_at": "2025-10-05T00:00:00Z",
                "html_url": "https://github.com/test/repo/releases/tag/v1.0.0",
                "prerelease": False,
                "body": "Test release"
            }
        ])
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        yield mock_session

@pytest.fixture
def mock_discord_webhook():
    """Discord Webhook モック"""
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 204
        yield mock_post

@pytest.fixture
def mock_native_notification():
    """ネイティブ通知モック"""
    with patch('win10toast.ToastNotifier') as mock_toast, \
         patch('pync.notify') as mock_pync, \
         patch('plyer.notification.notify') as mock_plyer:
        yield {
            'windows': mock_toast,
            'macos': mock_pync,
            'linux': mock_plyer
        }
```

**ユニットテスト**

```python
# tests/services/github-release-watcher/test_github_client.py

import pytest
from services.github_release_watcher.github_client import GitHubClient

@pytest.mark.asyncio
async def test_get_latest_release_with_cache(mock_github_api):
    """キャッシュ機能のテスト"""
    client = GitHubClient()

    # 初回アクセス
    release1 = await client.get_latest_release_async("docker", "compose")
    assert release1 is not None
    assert release1.tag_name == "v1.0.0"

    # 2回目（キャッシュから取得）
    release2 = await client.get_latest_release_async("docker", "compose")
    assert release2 == release1
    # API呼び出しは1回のみ
    assert mock_github_api.call_count == 1

@pytest.mark.asyncio
async def test_parallel_repository_check(mock_github_api):
    """並列チェックのテスト"""
    client = GitHubClient()
    repos = ["docker/compose", "kubernetes/kubernetes", "python/cpython"]

    releases = await client.check_multiple_repositories_async(repos)
    assert len(releases) == 3
    assert all(r.tag_name == "v1.0.0" for r in releases)
```

**統合テスト**

```python
# tests/services/github-release-watcher/test_notification_integration.py

import pytest
from services.github_release_watcher.notification import NotificationManager
from services.github_release_watcher.notification.base import NotificationMessage

def test_multiple_channels_notification(
    mock_discord_webhook,
    mock_native_notification
):
    """複数チャネル統合テスト"""
    config = {
        "channels": ["native", "discord"],
        "native": {"enabled": True, "duration": 10},
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"}
    }

    manager = NotificationManager(config)
    message = NotificationMessage(
        repository_name="Test Repo",
        repository_url="test/repo",
        version="v1.0.0",
        published_at="2025-10-05T00:00:00Z",
        html_url="https://github.com/test/repo",
        is_prerelease=False,
        body="Test"
    )

    results = manager.send_all(message)
    assert results["NativeNotification"] == True
    assert results["DiscordNotification"] == True
```

**E2Eテスト（限定的）**

```python
# tests/services/github-release-watcher/test_e2e.py

import pytest
import os

@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set"
)
async def test_real_github_api():
    """実際のGitHub APIを使用したE2Eテスト"""
    client = GitHubClient(token=os.getenv("GITHUB_TOKEN"))
    release = await client.get_latest_release_async("docker", "compose")
    assert release is not None
    # 実際のリリース情報を検証
```

#### テストカバレッジ目標

| カテゴリ | カバレッジ目標 | 重点項目 |
|---------|--------------|---------|
| **ユニットテスト** | 90%+ | ロジック、バージョン比較、状態管理 |
| **統合テスト** | 80%+ | 通知チャネル、GitHub API連携 |
| **E2Eテスト** | 限定的 | 主要フロー（1-2シナリオ） |

#### 成果物

- ✅ `tests/services/github-release-watcher/conftest.py` **← モック層設計**
- ✅ `tests/services/github-release-watcher/test_github_client.py`
- ✅ `tests/services/github-release-watcher/test_notification.py`
- ✅ `tests/services/github-release-watcher/test_notification_integration.py`
- ✅ `tests/services/github-release-watcher/test_comparator.py`
- ✅ `tests/services/github-release-watcher/test_state.py`
- ✅ `tests/services/github-release-watcher/test_e2e.py` **← 限定的E2E**
- ✅ テストカバレッジ: ユニット90%+、統合80%+

---

### フェーズ6: リリース準備（1日）

#### タスク一覧

| # | タスク | 説明 | 所要時間 | 優先度 |
|---|--------|------|----------|--------|
| 6.1 | Dockerイメージビルド | GHCRへのpush | 1時間 | 高 |
| 6.2 | GitHub Actionsワークフロー | CI/CD設定 | 2時間 | 高 |
| 6.3 | バージョニング | セマンティックバージョニング | 1時間 | 高 |
| 6.4 | CHANGELOG更新 | 変更履歴記載 | 1時間 | 高 |
| 6.5 | リリースノート作成 | GitHub Release | 1時間 | 高 |

#### 成果物

- ✅ GitHub Container Registryイメージ
- ✅ `.github/workflows/release-watcher-ci.yml`
- ✅ `CHANGELOG.md` 更新
- ✅ GitHub Releases作成

---

## 技術スタック

### 使用技術

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|----------|------|
| **言語** | Python | 3.13+ | メインロジック |
| **依存管理** | uv | latest | 高速な依存関係管理 |
| **設定** | TOML | - | 設定ファイル形式 |
| **HTTP** | requests | latest | GitHub API、Webhook |
| **スケジューリング** | schedule | latest | 定期実行 |
| **コンテナ** | Docker | 20.10+ | 実行環境 |
| **オーケストレーション** | Docker Compose | 2.0+ | サービス管理 |
| **テスト** | pytest | latest | ユニット・統合テスト |
| **Lint/Format** | ruff | latest | コード品質 |
| **型チェック** | mypy | latest | 型安全性 |

### 新規依存関係

```toml
# pyproject.toml

[project]
dependencies = [
    "requests>=2.31.0",
    "schedule>=1.2.0",
    "tomli>=2.0.0",  # Python 3.11以降はtomllib標準モジュール
    "packaging>=23.0",  # バージョン比較
]

[project.optional-dependencies]
email = [
    "aiosmtplib>=3.0.0",  # 非同期SMTP
]
```

---

## 成功指標

### 機能要件

- ✅ 任意のGitHubリポジトリの監視
- ✅ 複数リポジトリの同時監視
- ✅ プレリリース・安定版のフィルタリング
- ✅ バージョンパターンマッチング
- ✅ 複数通知チャネル（**ネイティブ通知**/Webhook/Discord/Slack/メール/ファイル）
  - **Windows Toast通知（WSL-kernel-watcherからの継承）**
  - macOS通知センター
  - Linux libnotify
- ✅ 常駐・ワンショット・スケジュール実行モード
- ✅ 状態保存・復元機能
- ✅ WSL-kernel-watcherとの互換性（設定移行）

### 非機能要件

- ✅ Docker化（Linux/Mac/Windows対応）
- ✅ Mcp-Docker統合（docker-compose.yml）
- ✅ examples/構造（他リポジトリへの導入容易性）
- ✅ テストカバレッジ80%以上
- ✅ ドキュメント完備
- ✅ GitHub APIレート制限対応
- ✅ エラーハンドリング・リトライ機構

### パフォーマンス

- ✅ チェック実行時間: <5秒/リポジトリ
- ✅ メモリ使用量: <100MB
- ✅ 起動時間: <10秒
- ✅ 通知遅延: <30秒

---

## リスクと対策

### リスク管理表

| # | リスク | 影響度 | 発生確率 | 対策 |
|---|-------|--------|----------|------|
| R1 | GitHub APIレート制限 | 高 | 中 | トークン認証、**キャッシング実装**、**非同期化** |
| R2 | 通知チャネルの障害 | 中 | 中 | リトライ機構、複数チャネル設定 |
| R3 | Dockerイメージサイズ | 低 | 低 | マルチステージビルド最適化 |
| R4 | 既存WSL-watcherとの互換性 | 中 | 低 | 移行スクリプト提供、設定変換ツール |
| R5 | 複雑な設定ファイル | 低 | 中 | 豊富な例、バリデーション機能 |
| R6 | パフォーマンス劣化 | 中 | 中 | **並列処理、非同期I/O、キャッシュ戦略** |
| R7 | 認証情報漏洩 | 高 | 低 | **Secret Manager統合、環境変数暗号化** |
| R8 | テストの不十分性 | 中 | 中 | **モック層設計、統合テスト強化** |

### 対策詳細

**R1: GitHub APIレート制限**

```python
# GitHub API レート制限対応 + キャッシング + 非同期化

import asyncio
import aiohttp
from cachetools import TTLCache
from datetime import datetime, timedelta

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        # キャッシュ: 最大100リポジトリ、TTL 5分
        self.cache = TTLCache(maxsize=100, ttl=300)
        # トークン使用時: 5000 req/hour
        # 未認証: 60 req/hour

    async def get_latest_release_async(
        self,
        owner: str,
        repo: str,
        use_cache: bool = True
    ) -> Optional[Release]:
        """非同期でリリース取得（キャッシュ対応）"""
        cache_key = f"{owner}/{repo}"

        # キャッシュチェック
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        # レート制限チェック
        await self._check_rate_limit_async()

        # API呼び出し
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            async with session.get(url, headers=headers) as response:
                releases = await response.json()
                latest = self._parse_latest(releases)

                # キャッシュに保存
                if latest:
                    self.cache[cache_key] = latest

                return latest

    async def _check_rate_limit_async(self):
        """非同期レート制限チェック"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            url = "https://api.github.com/rate_limit"
            async with session.get(url, headers=headers) as response:
                rate_info = await response.json()
                remaining = rate_info["resources"]["core"]["remaining"]
                reset_time = rate_info["resources"]["core"]["reset"]

                if remaining < 10:
                    sleep_time = reset_time - datetime.now().timestamp()
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

    async def check_multiple_repositories_async(
        self,
        repositories: List[str]
    ) -> List[Optional[Release]]:
        """複数リポジトリを並列チェック"""
        tasks = [
            self.get_latest_release_async(*repo.split("/"))
            for repo in repositories
        ]
        return await asyncio.gather(*tasks)
```

**依存関係追加**:
```toml
[project.dependencies]
aiohttp = ">=3.9.0"  # 非同期HTTP
cachetools = ">=5.3.0"  # キャッシング
```

**R2: 通知チャネルの障害**

```python
# リトライ機構

from tenacity import retry, stop_after_attempt, wait_exponential

class NotificationBase:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def send(self, message: NotificationMessage) -> bool:
        # 最大3回リトライ、指数バックオフ
        ...
```

---

## マイルストーン

### Week 1 (Day 1-3)

- ✅ フェーズ1完了: コア機能の移植
- ✅ フェーズ2完了: 通知システムの実装

### Week 2 (Day 4-7)

- ✅ フェーズ3完了: Docker化と統合
- ✅ フェーズ4完了: examples/とドキュメント
- ✅ フェーズ5完了: テストと検証
- ✅ フェーズ6完了: リリース準備

### 最終目標

- ✅ v1.0.0リリース
- ✅ GitHub Container Registryへのpush
- ✅ ドキュメント公開
- ✅ Mcp-Docker v1.3.0への統合

---

## 次のアクション

### 即座に実行

1. **プロジェクトディレクトリ作成**
   ```bash
   mkdir -p services/github-release-watcher/notification
   mkdir -p examples/github-release-watcher/config
   mkdir -p tests/services/github-release-watcher
   ```

2. **コードベースのコピー**
   ```bash
   # WSL-kernel-watcherから必要なコードを移植
   cp ~/workspace/WSL-kernel-watcher/src/github_api.py \
      services/github-release-watcher/github_client.py
   ```

3. **依存関係の追加**
   ```bash
   # pyproject.tomlに依存関係を追加
   uv add requests schedule tomli packaging
   ```

### 確認事項

- [ ] 設計書の承認
- [ ] 実装計画の承認
- [ ] リソース確保（開発時間）
- [ ] 優先度の確認

---

**更新履歴**:
- 2025-10-05: 初版作成（実装計画）
