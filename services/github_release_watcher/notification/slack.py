"""
Slack Webhook通知
"""

from typing import Any, cast

import httpx

from .base import NotificationBase, NotificationMessage


class SlackNotification(NotificationBase):
    """Slack Webhook通知"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        webhook_url_value = config.get("webhook_url")
        self.username = cast(str, config.get("username", "GitHub Release Watcher"))
        self.icon_emoji = cast(str, config.get("icon_emoji", ":rocket:"))
        self.channel = config.get("channel")
        self.mention_users = cast(list[str], config.get("mention_users", []))
        self.timeout = cast(int, config.get("timeout", 30))

        if not webhook_url_value:
            raise ValueError("Slack webhook_url is required")
        self.webhook_url: str = cast(str, webhook_url_value)

    def send(self, message: NotificationMessage) -> bool:
        """
        Slack Webhook通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            payload = self._build_slack_payload(message)

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            # Slackは成功時に "ok" を返す
            if response.text != "ok":
                print(f"Slack webhook returned unexpected response: {response.text}")
                return False

            return True

        except httpx.HTTPStatusError as e:
            print(f"Slack webhook HTTP error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False

    def _build_slack_payload(self, message: NotificationMessage) -> dict:
        """
        Slack Webhookペイロードを構築

        Args:
            message: 通知メッセージ

        Returns:
            Slackペイロード辞書
        """
        # メンション文字列を構築
        mentions = " ".join([f"<@{user_id}>" for user_id in self.mention_users])

        # テキスト本文
        text = f"*{message.title}*\n{message.body}"
        if mentions:
            text = f"{mentions}\n{text}"

        # Attachmentを構築
        fields: list[dict] = []
        attachment = {
            "color": "#0366d6",  # GitHub blue
            "fields": fields,
        }

        # リポジトリ情報
        if message.owner and message.repo:
            repo_url = f"https://github.com/{message.owner}/{message.repo}"
            fields.append(
                {
                    "title": "Repository",
                    "value": f"<{repo_url}|{message.owner}/{message.repo}>",
                    "short": True,
                }
            )

        # バージョン情報
        if message.version:
            fields.append({"title": "Version", "value": message.version, "short": True})

        # リリース名
        if message.release_name:
            fields.append({"title": "Release", "value": message.release_name, "short": False})

        # URL
        if message.url:
            fields.append({"title": "Release URL", "value": f"<{message.url}>", "short": False})

        # 公開日時
        if message.published_at:
            attachment["footer"] = f"Published at {message.published_at}"

        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "text": text,
            "attachments": [attachment],
        }

        # チャンネル指定（オプション）
        if self.channel:
            payload["channel"] = self.channel

        return payload
