"""
GitHub Release Watcher - Notification ユニットテスト
"""

from services.github_release_watcher.notification import (
    NotificationManager,
    NotificationMessage,
)


class TestNotificationMessage:
    """NotificationMessage のテスト"""

    def test_create_notification_message(self):
        """通知メッセージの作成"""
        message = NotificationMessage(
            title="Test Release",
            body="New version available",
            url="https://github.com/owner/repo/releases/tag/v1.0.0",
            owner="owner",
            repo="repo",
            version="1.0.0",
        )

        assert message.title == "Test Release"
        assert message.body == "New version available"
        assert message.url == "https://github.com/owner/repo/releases/tag/v1.0.0"
        assert message.owner == "owner"
        assert message.repo == "repo"
        assert message.version == "1.0.0"


class TestNotificationManager:
    """NotificationManager のテスト"""

    def test_manager_initialization(self, sample_config):
        """通知マネージャーの初期化"""
        manager = NotificationManager(sample_config["notifications"])

        assert manager.is_enabled()
        assert "native" in manager.get_enabled_channels()
        assert "discord" in manager.get_enabled_channels()

    def test_manager_disabled(self):
        """通知無効時のマネージャー"""
        config = {"enabled": False, "channels": []}
        manager = NotificationManager(config)

        assert not manager.is_enabled()
        assert len(manager.get_enabled_channels()) == 0

    def test_manager_send_to_all_channels(
        self, sample_config, mocker, mock_discord_notification, mock_native_notification
    ):
        """全チャネルへの通知送信"""
        # モックで通知クラスを置き換え
        mocker.patch(
            "services.github_release_watcher.notification.manager.DiscordNotification",
            return_value=mock_discord_notification,
        )
        mocker.patch(
            "services.github_release_watcher.notification.manager.NativeNotification",
            return_value=mock_native_notification,
        )

        manager = NotificationManager(sample_config["notifications"])

        message = NotificationMessage(
            title="Test Release",
            body="New version available",
            version="1.0.0",
        )

        results = manager.send(message)

        # 両方のチャネルが呼ばれたことを確認
        assert len(results) == 2
        assert results.get("discord") is True
        assert results.get("native") is True

    def test_manager_send_to_specific_channel(self, sample_config, mocker, mock_discord_notification):
        """特定チャネルのみに通知送信"""
        mocker.patch(
            "services.github_release_watcher.notification.manager.DiscordNotification",
            return_value=mock_discord_notification,
        )

        manager = NotificationManager(sample_config["notifications"])

        message = NotificationMessage(
            title="Test Release",
            body="New version available",
        )

        result = manager.send_to_channel("discord", message)
        assert result is True
