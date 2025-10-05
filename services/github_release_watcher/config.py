"""
設定管理 - TOML設定ファイルの読み込みと環境変数展開
"""

import os
import re
import tomllib
from pathlib import Path
from typing import Any, Optional


class Config:
    """設定管理クラス"""

    def __init__(self, config_path: Path):
        """
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """設定ファイルを読み込み"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "rb") as f:
            config = tomllib.load(f)

        # 環境変数展開
        return self._expand_env_vars(config)

    def _expand_env_vars(self, obj: Any) -> Any:
        """
        再帰的に環境変数を展開

        ${VAR_NAME} または $VAR_NAME 形式の環境変数を展開
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # ${VAR_NAME} 形式
            pattern1 = re.compile(r"\$\{([^}]+)\}")
            # $VAR_NAME 形式
            pattern2 = re.compile(r"\$([A-Z_][A-Z0-9_]*)")

            result = obj
            # ${VAR_NAME} を展開
            for match in pattern1.finditer(obj):
                var_name = match.group(1)
                var_value = os.getenv(var_name, "")
                result = result.replace(match.group(0), var_value)

            # $VAR_NAME を展開（${} で展開されなかった部分のみ）
            for match in pattern2.finditer(result):
                var_name = match.group(1)
                var_value = os.getenv(var_name, "")
                result = result.replace(match.group(0), var_value)

            return result
        else:
            return obj

    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得（ドット記法対応）

        Args:
            key: 設定キー（例: "github.token", "notifications.enabled"）
            default: デフォルト値

        Returns:
            設定値
        """
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_repositories(self) -> list[dict[str, Any]]:
        """監視リポジトリリストを取得"""
        return self.get("repositories", [])

    def get_github_token(self) -> Optional[str]:
        """GitHub APIトークンを取得"""
        return self.get("github.token")

    def get_check_interval(self) -> int:
        """チェック間隔（秒）を取得"""
        return self.get("github.check_interval", 300)

    def get_notification_config(self) -> dict[str, Any]:
        """通知設定を取得"""
        return self.get("notifications", {})

    def is_notification_enabled(self) -> bool:
        """通知が有効か確認"""
        return self.get("notifications.enabled", False)

    def get_enabled_channels(self) -> list[str]:
        """有効な通知チャネルリストを取得"""
        return self.get("notifications.channels", [])

    def get_channel_config(self, channel: str) -> dict[str, Any]:
        """
        特定チャネルの設定を取得

        Args:
            channel: チャネル名（例: "discord", "slack"）

        Returns:
            チャネル設定辞書
        """
        return self.get(f"notifications.{channel}", {})

    def validate(self) -> list[str]:
        """
        設定を検証

        Returns:
            エラーメッセージリスト（空の場合は検証成功）
        """
        errors = []

        # リポジトリリストが存在するか
        repos = self.get_repositories()
        if not repos:
            errors.append("No repositories configured")

        # 各リポジトリの必須フィールドチェック
        for i, repo in enumerate(repos):
            if "url" not in repo:
                errors.append(f"Repository {i}: missing 'url' field")
            if "owner" not in repo:
                errors.append(f"Repository {i}: missing 'owner' field")
            if "repo" not in repo:
                errors.append(f"Repository {i}: missing 'repo' field")

        # 通知設定チェック
        if self.is_notification_enabled():
            channels = self.get_enabled_channels()
            if not channels:
                errors.append("Notifications enabled but no channels configured")

            # Webhook設定チェック
            if "webhook" in channels:
                webhook_config = self.get_channel_config("webhook")
                if not webhook_config.get("url"):
                    errors.append("Webhook channel enabled but no URL configured")

            # Discord設定チェック
            if "discord" in channels:
                discord_config = self.get_channel_config("discord")
                if not discord_config.get("webhook_url"):
                    errors.append("Discord channel enabled but no webhook_url configured")

            # Slack設定チェック
            if "slack" in channels:
                slack_config = self.get_channel_config("slack")
                if not slack_config.get("webhook_url"):
                    errors.append("Slack channel enabled but no webhook_url configured")

            # Email設定チェック
            if "email" in channels:
                email_config = self.get_channel_config("email")
                if not email_config.get("smtp_server"):
                    errors.append("Email channel enabled but no smtp_server configured")
                if not email_config.get("to"):
                    errors.append("Email channel enabled but no 'to' address configured")

        return errors
