"""
汎用Webhook通知
"""

from typing import Any, cast

import httpx

from .base import NotificationBase, NotificationMessage


class WebhookNotification(NotificationBase):
    """汎用Webhook通知"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        url_value = config.get("url")
        self.method = cast(str, config.get("method", "POST"))
        self.headers = cast(dict[str, str], config.get("headers", {}))
        self.timeout = cast(int, config.get("timeout", 30))

        if not url_value:
            raise ValueError("Webhook URL is required")
        self.url: str = cast(str, url_value)

    def send(self, message: NotificationMessage) -> bool:
        """
        Webhook通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            payload = self._build_payload(message)

            # デフォルトヘッダー設定
            headers = {
                "Content-Type": "application/json",
                **self.headers,
            }

            response = httpx.request(
                method=self.method,
                url=self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            print(f"Webhook HTTP error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"Error sending webhook notification: {e}")
            return False

    def _build_payload(self, message: NotificationMessage) -> dict:
        """
        Webhookペイロードを構築

        Args:
            message: 通知メッセージ

        Returns:
            ペイロード辞書
        """
        payload = {
            "title": message.title,
            "body": message.body,
            "repository": {
                "owner": message.owner,
                "repo": message.repo,
                "url": f"https://github.com/{message.owner}/{message.repo}" if message.owner and message.repo else None,
            },
            "release": {
                "version": message.version,
                "name": message.release_name,
                "url": message.url,
                "published_at": message.published_at,
            },
        }

        return payload
