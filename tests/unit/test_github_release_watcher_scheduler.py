"""
GitHub Release Watcher - Scheduler ユニットテスト
"""

import pytest

from services.github_release_watcher.github_client import GitHubClient
from services.github_release_watcher.notification import NotificationManager
from services.github_release_watcher.scheduler import ReleaseScheduler
from services.github_release_watcher.state import StateManager


class TestReleaseScheduler:
    """ReleaseScheduler のテスト"""

    @pytest.mark.asyncio
    async def test_first_check_saves_state(self, tmp_path, temp_config, mocker):
        """初回チェック時に状態を保存"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": False, "channels": []},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)

        # GitHub API レスポンスをモック
        mock_release = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "html_url": "https://github.com/test/repo1/releases/tag/v1.0.0",
            "published_at": "2024-01-01T00:00:00Z",
        }
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_release)

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 状態が保存されたことを確認
        saved_version = state_manager.get_latest_version(repo_config["url"])
        assert saved_version == "1.0.0"

        # メタデータも保存されていることを確認
        state = state_manager.state
        repo_state = state["repositories"][repo_config["url"]]
        assert repo_state["metadata"]["release_name"] == "Release 1.0.0"
        assert repo_state["metadata"]["release_url"] == "https://github.com/test/repo1/releases/tag/v1.0.0"

    @pytest.mark.asyncio
    async def test_new_version_triggers_notification(self, tmp_path, temp_config, mocker):
        """新しいバージョンが検知されたら通知を送信"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": True, "channels": ["file"]},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)
        notification_manager = mocker.Mock(spec=NotificationManager)

        # 初回リリース（v1.0.0）を状態に保存
        state_manager.update_latest_version(
            "https://github.com/test/repo1",
            "1.0.0",
            ["file"],
            metadata={"release_name": "Release 1.0.0"},
        )

        # GitHub API レスポンスをモック（新バージョン v1.1.0）
        mock_release = {
            "tag_name": "v1.1.0",
            "name": "Release 1.1.0",
            "html_url": "https://github.com/test/repo1/releases/tag/v1.1.0",
            "published_at": "2024-01-02T00:00:00Z",
        }
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_release)

        # 通知マネージャーのモック
        notification_manager.send = mocker.Mock(return_value={"file": True})

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client, notification_manager)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 通知が送信されたことを確認
        notification_manager.send.assert_called_once()
        call_args = notification_manager.send.call_args[0][0]
        assert call_args.version == "1.1.0"
        assert call_args.owner == "test"
        assert call_args.repo == "repo1"

        # 状態が更新されたことを確認
        saved_version = state_manager.get_latest_version("https://github.com/test/repo1")
        assert saved_version == "1.1.0"

    @pytest.mark.asyncio
    async def test_same_version_skips_notification(self, tmp_path, temp_config, mocker):
        """同じバージョンの場合は通知をスキップ"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": True, "channels": ["file"]},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)
        notification_manager = mocker.Mock(spec=NotificationManager)

        # 既存バージョン（v1.0.0）を状態に保存
        state_manager.update_latest_version(
            "https://github.com/test/repo1",
            "1.0.0",
            ["file"],
        )

        # GitHub API レスポンスをモック（同じバージョン v1.0.0）
        mock_release = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "html_url": "https://github.com/test/repo1/releases/tag/v1.0.0",
            "published_at": "2024-01-01T00:00:00Z",
        }
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_release)

        # 通知マネージャーのモック
        notification_manager.send = mocker.Mock(return_value={"file": True})

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client, notification_manager)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 通知が送信されていないことを確認
        notification_manager.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_older_version_skips_notification(self, tmp_path, temp_config, mocker):
        """古いバージョンの場合は通知をスキップ"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": True, "channels": ["file"]},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)
        notification_manager = mocker.Mock(spec=NotificationManager)

        # 既存バージョン（v1.5.0）を状態に保存
        state_manager.update_latest_version(
            "https://github.com/test/repo1",
            "1.5.0",
            ["file"],
        )

        # GitHub API レスポンスをモック（古いバージョン v1.0.0）
        mock_release = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "html_url": "https://github.com/test/repo1/releases/tag/v1.0.0",
            "published_at": "2024-01-01T00:00:00Z",
        }
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_release)

        # 通知マネージャーのモック
        notification_manager.send = mocker.Mock(return_value={"file": True})

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client, notification_manager)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 通知が送信されていないことを確認
        notification_manager.send.assert_not_called()

        # 状態が更新されていないことを確認
        saved_version = state_manager.get_latest_version("https://github.com/test/repo1")
        assert saved_version == "1.5.0"

    @pytest.mark.asyncio
    async def test_no_release_found(self, tmp_path, temp_config, mocker):
        """リリースが見つからない場合の処理"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": True, "channels": ["file"]},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)
        notification_manager = mocker.Mock(spec=NotificationManager)

        # GitHub API レスポンスをモック（リリースなし）
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=None)

        # 通知マネージャーのモック
        notification_manager.send = mocker.Mock(return_value={"file": True})

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client, notification_manager)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 通知が送信されていないことを確認
        notification_manager.send.assert_not_called()

        # 状態が保存されていないことを確認
        saved_version = state_manager.get_latest_version("https://github.com/test/repo1")
        assert saved_version is None

    @pytest.mark.asyncio
    async def test_notification_failure_recorded_in_history(self, tmp_path, temp_config, mocker):
        """通知失敗時も履歴に記録"""
        # テスト用の状態ファイル
        state_file = tmp_path / "state.json"

        # モック設定
        config_data = {
            "github": {"token": "test_token", "check_interval": 300},
            "repositories": [{"owner": "test", "repo": "repo1", "url": "https://github.com/test/repo1"}],
            "notifications": {"enabled": True, "channels": ["file"]},
        }
        config = temp_config(config_data)
        state_manager = StateManager(state_file)
        github_client = mocker.Mock(spec=GitHubClient)
        notification_manager = mocker.Mock(spec=NotificationManager)

        # 初回リリース（v1.0.0）を状態に保存
        state_manager.update_latest_version(
            "https://github.com/test/repo1",
            "1.0.0",
            ["file"],
        )

        # GitHub API レスポンスをモック（新バージョン v1.1.0）
        mock_release = {
            "tag_name": "v1.1.0",
            "name": "Release 1.1.0",
            "html_url": "https://github.com/test/repo1/releases/tag/v1.1.0",
            "published_at": "2024-01-02T00:00:00Z",
        }
        github_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_release)

        # 通知マネージャーのモック（失敗を返す）
        notification_manager.send = mocker.Mock(return_value={"file": False})

        # スケジューラー作成
        scheduler = ReleaseScheduler(config, state_manager, github_client, notification_manager)

        # リポジトリをチェック
        repo_config = config_data["repositories"][0]
        await scheduler.check_repository(repo_config)

        # 通知が送信されたことを確認
        notification_manager.send.assert_called_once()

        # 通知履歴に失敗が記録されていることを確認
        state = state_manager.state
        history = state["repositories"]["https://github.com/test/repo1"]["notification_history"]
        assert len(history) > 0
        latest_notification = history[-1]
        assert latest_notification["version"] == "1.1.0"
        assert latest_notification["success"] is False
