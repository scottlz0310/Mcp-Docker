"""
通知システム - マルチチャネル通知サポート

サポートする通知チャネル:
- ネイティブ通知 (Windows Toast/macOS/Linux)
- Discord Webhook
- Slack Webhook
- メール (SMTP)
- Webhook (汎用)
- ファイル出力 (JSON/Markdown)
- Windows Bridge (WSL→Windows Toast通知)
"""

from .base import NotificationBase, NotificationMessage
from .discord import DiscordNotification
from .email import EmailNotification
from .file import FileNotification
from .manager import NotificationManager
from .native import NativeNotification
from .slack import SlackNotification
from .webhook import WebhookNotification
from .windows_bridge import WindowsBridgeNotification

__all__ = [
    "NotificationBase",
    "NotificationMessage",
    "NotificationManager",
    "NativeNotification",
    "DiscordNotification",
    "SlackNotification",
    "WebhookNotification",
    "EmailNotification",
    "FileNotification",
    "WindowsBridgeNotification",
]
