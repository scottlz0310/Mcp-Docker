"""
通知基底クラス
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationMessage:
    """通知メッセージ"""

    title: str
    body: str
    url: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    version: Optional[str] = None
    release_name: Optional[str] = None
    published_at: Optional[str] = None


class NotificationBase(ABC):
    """通知基底クラス"""

    def __init__(self, config: dict):
        """
        Args:
            config: 通知チャネル設定
        """
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """
        通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        pass

    def is_enabled(self) -> bool:
        """通知が有効か確認"""
        return self.enabled

    def format_message(self, message: NotificationMessage) -> dict:
        """
        メッセージをフォーマット（各サブクラスでオーバーライド可能）

        Args:
            message: 通知メッセージ

        Returns:
            フォーマット済みメッセージ辞書
        """
        return {
            "title": message.title,
            "body": message.body,
            "url": message.url,
            "owner": message.owner,
            "repo": message.repo,
            "version": message.version,
            "release_name": message.release_name,
            "published_at": message.published_at,
        }
