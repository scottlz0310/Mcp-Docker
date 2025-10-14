"""
通知マネージャー - すべての通知チャネルを統合管理
"""

from typing import Any, cast

from .base import NotificationBase, NotificationMessage
from .discord import DiscordNotification
from .email import EmailNotification
from .file import FileNotification
from .native import NativeNotification
from .slack import SlackNotification
from .webhook import WebhookNotification
from .windows_bridge import WindowsBridgeNotification


class NotificationManager:
    """通知マネージャー"""

    def __init__(self, config: dict[str, Any]):
        """
        Args:
            config: 通知設定辞書
        """
        self.config = config
        self.enabled = cast(bool, config.get("enabled", False))
        self.channels = cast(list[str], config.get("channels", []))
        self.notifiers: dict[str, NotificationBase] = {}

        # 通知チャネルを初期化
        self._init_channels()

    def _init_channels(self) -> None:
        """有効な通知チャネルを初期化"""
        if not self.enabled:
            return

        # 各チャネルの設定を取得して初期化
        for channel in self.channels:
            try:
                if channel == "native":
                    native_config = self.config.get("native", {})
                    native_config["enabled"] = True
                    self.notifiers["native"] = NativeNotification(native_config)

                elif channel == "discord":
                    discord_config = self.config.get("discord", {})
                    discord_config["enabled"] = True
                    self.notifiers["discord"] = DiscordNotification(discord_config)

                elif channel == "slack":
                    slack_config = self.config.get("slack", {})
                    slack_config["enabled"] = True
                    self.notifiers["slack"] = SlackNotification(slack_config)

                elif channel == "webhook":
                    webhook_config = self.config.get("webhook", {})
                    webhook_config["enabled"] = True
                    self.notifiers["webhook"] = WebhookNotification(webhook_config)

                elif channel == "email":
                    email_config = self.config.get("email", {})
                    email_config["enabled"] = True
                    self.notifiers["email"] = EmailNotification(email_config)

                elif channel == "file":
                    file_config = self.config.get("file", {})
                    file_config["enabled"] = True
                    self.notifiers["file"] = FileNotification(file_config)

                elif channel == "windows_bridge":
                    bridge_config = self.config.get("windows_bridge", {})
                    bridge_config["enabled"] = True
                    self.notifiers["windows_bridge"] = WindowsBridgeNotification(bridge_config)

                else:
                    print(f"Unknown notification channel: {channel}")

            except Exception as e:
                print(f"Failed to initialize {channel} notification: {e}")

    def send(self, message: NotificationMessage) -> dict[str, bool]:
        """
        すべての有効なチャネルに通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            チャネル名: 送信成功フラグの辞書
        """
        if not self.enabled:
            print("Notifications are disabled")
            return {}

        results = {}

        for channel, notifier in self.notifiers.items():
            try:
                if notifier.is_enabled():
                    success = notifier.send(message)
                    results[channel] = success
                    if success:
                        print(f"Notification sent successfully via {channel}")
                    else:
                        print(f"Failed to send notification via {channel}")
                else:
                    print(f"Notification channel {channel} is disabled")
                    results[channel] = False
            except Exception as e:
                print(f"Error sending notification via {channel}: {e}")
                results[channel] = False

        return results

    def send_to_channel(self, channel: str, message: NotificationMessage) -> bool:
        """
        特定のチャネルのみに通知を送信

        Args:
            channel: チャネル名
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.enabled:
            print("Notifications are disabled")
            return False

        if channel not in self.notifiers:
            print(f"Notification channel not found: {channel}")
            return False

        notifier = self.notifiers[channel]

        try:
            if notifier.is_enabled():
                return notifier.send(message)
            else:
                print(f"Notification channel {channel} is disabled")
                return False
        except Exception as e:
            print(f"Error sending notification via {channel}: {e}")
            return False

    def get_enabled_channels(self) -> list[str]:
        """
        有効な通知チャネルリストを取得

        Returns:
            チャネル名リスト
        """
        return [channel for channel, notifier in self.notifiers.items() if notifier.is_enabled()]

    def is_enabled(self) -> bool:
        """通知マネージャーが有効か確認"""
        return self.enabled
