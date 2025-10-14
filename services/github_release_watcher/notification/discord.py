"""
Discord Webhook通知
"""

from typing import Any, cast

import httpx

from .base import NotificationBase, NotificationMessage


class DiscordNotification(NotificationBase):
    """Discord Webhook通知"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        webhook_url_value = config.get("webhook_url")
        self.username = cast(str, config.get("username", "GitHub Release Watcher"))
        self.avatar_url = cast(
            str,
            config.get(
                "avatar_url",
                "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            ),
        )
        self.color = cast(int, config.get("color", 0x0366D6))  # GitHub blue
        self.mention_users = cast(list[str], config.get("mention_users", []))
        self.timeout = cast(int, config.get("timeout", 30))

        if not webhook_url_value:
            raise ValueError("Discord webhook_url is required")
        self.webhook_url: str = cast(str, webhook_url_value)

    def send(self, message: NotificationMessage) -> bool:
        """
        Discord Webhook通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            payload = self._build_discord_payload(message)

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            print(f"Discord webhook HTTP error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
            return False

    def _build_discord_payload(self, message: NotificationMessage) -> dict[str, Any]:
        """
        Discord Webhookペイロードを構築

        Args:
            message: 通知メッセージ

        Returns:
            Discordペイロード辞書
        """
        # メンション文字列を構築
        mentions = " ".join([f"<@{user_id}>" for user_id in self.mention_users])
        content = mentions if mentions else None

        # Embedを構築
        fields: list[dict[str, Any]] = []
        embed: dict[str, Any] = {
            "title": message.title,
            "description": message.body,
            "color": self.color,
            "fields": fields,
        }

        # リポジトリ情報
        if message.owner and message.repo:
            embed["fields"].append(
                {
                    "name": "Repository",
                    "value": f"[{message.owner}/{message.repo}](https://github.com/{message.owner}/{message.repo})",
                    "inline": True,
                }
            )

        # バージョン情報
        if message.version:
            embed["fields"].append({"name": "Version", "value": message.version, "inline": True})

        # リリース名
        if message.release_name:
            embed["fields"].append({"name": "Release", "value": message.release_name, "inline": False})

        # URL
        if message.url:
            embed["url"] = message.url

        # 公開日時
        if message.published_at:
            embed["timestamp"] = message.published_at

        # Thumbnail（GitHubロゴ）
        embed["thumbnail"] = {"url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"}

        payload = {
            "username": self.username,
            "avatar_url": self.avatar_url,
            "embeds": [embed],
        }

        if content:
            payload["content"] = content

        return payload
