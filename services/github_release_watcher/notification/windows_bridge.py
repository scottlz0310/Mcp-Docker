"""
Windows Bridge 通知 - WSLからWindowsホストへの通知ブリッジ
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import NotificationBase, NotificationMessage


class WindowsBridgeNotification(NotificationBase):
    """Windows Bridge 通知"""

    def __init__(self, config: dict):
        super().__init__(config)
        # Windowsホスト上のパスを取得（WSL環境を想定）
        self.bridge_path = self._get_bridge_path(config.get("bridge_path"))

        # ディレクトリが存在しない場合は作成
        if self.bridge_path:
            self.bridge_path.mkdir(parents=True, exist_ok=True)

    def _get_bridge_path(self, config_path: str | None) -> Path | None:
        """
        Windows Bridgeパスを取得

        Args:
            config_path: 設定で指定されたパス

        Returns:
            Bridgeパス、またはNone（非WSL環境の場合）
        """
        # 1. 環境変数 WINDOWS_BRIDGE_PATH を最優先（Dockerマウント用）
        env_bridge_path = os.environ.get("WINDOWS_BRIDGE_PATH")
        if env_bridge_path:
            return Path(env_bridge_path)

        # 2. 設定で明示的に指定されている場合
        if config_path:
            return Path(config_path)

        # 3. WSL環境の場合、Windowsユーザーディレクトリを使用
        if self._is_wsl():
            # USERPROFILE環境変数を取得（WSLからWindows環境変数を参照）
            userprofile = os.environ.get("USERPROFILE")
            if userprofile:
                # WSL形式に変換 (例: C:\Users\hiro → /mnt/c/Users/hiro)
                wsl_path = self._convert_to_wsl_path(userprofile)
                return Path(wsl_path) / ".github-release-watcher" / "notifications"

            # フォールバック: /mnt/c/Users/<username>
            username = os.environ.get("USER", "user")
            return Path(f"/mnt/c/Users/{username}/.github-release-watcher/notifications")

        # 4. 非WSL環境の場合はNone
        return None

    def _is_wsl(self) -> bool:
        """
        WSL環境かどうかを判定

        Returns:
            WSL環境の場合True
        """
        # /proc/version に Microsoft が含まれていればWSL
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except FileNotFoundError:
            return False

    def _convert_to_wsl_path(self, windows_path: str) -> str:
        """
        WindowsパスをWSLパスに変換

        Args:
            windows_path: Windowsパス (例: C:\\Users\\hiro)

        Returns:
            WSLパス (例: /mnt/c/Users/hiro)
        """
        # C:\Users\hiro → /mnt/c/Users/hiro
        if ":" in windows_path:
            drive, path = windows_path.split(":", 1)
            drive = drive.lower()
            path = path.replace("\\", "/")
            return f"/mnt/{drive}{path}"
        return windows_path

    def send(self, message: NotificationMessage) -> bool:
        """
        Windows Bridge通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        if not self.bridge_path:
            print("Warning: Windows Bridge path not configured (not running in WSL?)")
            return False

        try:
            # 通知データを構築
            notification_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "title": message.title,
                "body": message.body,
                "owner": message.owner,
                "repo": message.repo,
                "version": message.version,
                "release_name": message.release_name,
                "url": message.url,
                "published_at": message.published_at,
            }

            # タイムスタンプベースのファイル名
            filename = f"notification_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.json"
            filepath = self.bridge_path / filename

            # JSONファイルとして書き込み
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(notification_data, f, indent=2, ensure_ascii=False)

            print(f"Notification sent successfully via windows_bridge: {filepath}")
            return True

        except Exception as e:
            print(f"Error sending Windows Bridge notification: {e}")
            return False
