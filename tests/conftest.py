"""pytest共通設定 - プロジェクトルート取得を一元化"""

import os
import sys
from pathlib import Path

import pytest


def find_project_root(start_path: Path | None = None) -> Path:
    """プロジェクトルートを検出

    pyproject.toml, .git, setup.pyのいずれかが存在するディレクトリを
    プロジェクトルートとして返す。

    Args:
        start_path: 検索開始パス（デフォルト: このファイルの場所）

    Returns:
        プロジェクトルートのPath

    Raises:
        RuntimeError: プロジェクトルートが見つからない場合
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = start_path
    for _ in range(10):  # 最大10階層まで遡る
        markers = [
            current / "pyproject.toml",
            current / ".git",
            current / "setup.py",
        ]
        if any(marker.exists() for marker in markers):
            return current

        if current.parent == current:  # ルートディレクトリに到達
            break
        current = current.parent

    raise RuntimeError(f"プロジェクトルートが見つかりません（開始: {start_path}）")


# グローバル変数として公開
PROJECT_ROOT = find_project_root()

# Pythonパスに追加（絶対インポートを可能にする）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def worker_id(request):
    """pytest-xdistのworker IDを取得

    並列実行時はgw0, gw1, ...などのIDを返す
    非並列実行時は"master"を返す
    """
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


# =============================================================================
# タイムアウト設定 - マーカーに応じて動的に変更
# =============================================================================


def pytest_collection_modifyitems(config, items):
    """テスト収集後にマーカーに応じてタイムアウトを調整

    slowマーカーが付いたテストのタイムアウトを600秒に変更
    """
    for item in items:
        if item.get_closest_marker("slow"):
            # slowマーカーが付いている場合は600秒に設定
            item.add_marker(pytest.mark.timeout(600))


# =============================================================================
# GitHub Release Watcher - Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_github_api(mocker):
    """GitHub API のモック"""
    mock_response = {
        "tag_name": "v1.2.3",
        "name": "Release v1.2.3",
        "html_url": "https://github.com/owner/repo/releases/tag/v1.2.3",
        "published_at": "2025-01-01T00:00:00Z",
        "prerelease": False,
    }

    mock_client = mocker.Mock()
    mock_client.get_latest_release_async = mocker.AsyncMock(return_value=mock_response)
    mock_client.get_releases_async = mocker.AsyncMock(return_value=[mock_response])
    mock_client.check_multiple_repos_async = mocker.AsyncMock(
        return_value=[({"owner": "owner", "repo": "repo", "url": "https://github.com/owner/repo"}, mock_response)]
    )
    mock_client.get_rate_limit_async = mocker.AsyncMock(
        return_value={"resources": {"core": {"remaining": 5000, "reset": 1234567890}}}
    )

    return mock_client


@pytest.fixture
def mock_discord_notification(mocker):
    """Discord 通知のモック"""
    mock_discord = mocker.Mock()
    mock_discord.send = mocker.Mock(return_value=True)
    mock_discord.is_enabled = mocker.Mock(return_value=True)
    return mock_discord


@pytest.fixture
def mock_slack_notification(mocker):
    """Slack 通知のモック"""
    mock_slack = mocker.Mock()
    mock_slack.send = mocker.Mock(return_value=True)
    mock_slack.is_enabled = mocker.Mock(return_value=True)
    return mock_slack


@pytest.fixture
def mock_native_notification(mocker):
    """Native 通知のモック"""
    mock_native = mocker.Mock()
    mock_native.send = mocker.Mock(return_value=True)
    mock_native.is_enabled = mocker.Mock(return_value=True)
    return mock_native


@pytest.fixture
def sample_config():
    """サンプル設定データ"""
    return {
        "github": {
            "token": "test_token",
            "check_interval": 300,
        },
        "repositories": [
            {
                "owner": "microsoft",
                "repo": "WSL",
                "url": "https://github.com/microsoft/WSL",
                "filter_mode": "stable",
            }
        ],
        "notifications": {
            "enabled": True,
            "channels": ["native", "discord"],
            "native": {
                "enabled": True,
                "duration": 10,
                "sound": True,
            },
            "discord": {
                "enabled": True,
                "webhook_url": "https://discord.com/api/webhooks/test",
                "username": "Test Bot",
                "color": 0x0366D6,
            },
        },
    }


@pytest.fixture
def sample_release():
    """サンプルリリースデータ"""
    return {
        "tag_name": "v1.2.3",
        "name": "Release v1.2.3",
        "html_url": "https://github.com/owner/repo/releases/tag/v1.2.3",
        "published_at": "2025-01-01T00:00:00Z",
        "prerelease": False,
        "body": "This is a test release",
    }


@pytest.fixture
def temp_config(tmp_path):
    """一時的なConfig用のヘルパー関数を返すフィクスチャ

    使用例:
        config = temp_config({
            "github": {...},
            "repositories": [...],
            "notifications": {...}
        })
    """

    from services.github_release_watcher.config import Config

    def _create_config(config_data: dict) -> Config:
        """一時的な設定ファイルを作成してConfigインスタンスを返す"""
        config_file = tmp_path / "config.toml"

        # TOML形式で書き込み
        import toml  # type: ignore[import-untyped]

        with open(config_file, "w") as f:
            toml.dump(config_data, f)

        return Config(config_file)

    return _create_config
