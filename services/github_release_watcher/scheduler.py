"""
スケジューラー - 定期的なリリースチェックと通知
"""

import asyncio
import re
import subprocess
from typing import TYPE_CHECKING, Optional

from .comparator import ReleaseComparator
from .config import Config
from .github_client import GitHubClient
from .logger import get_logger
from .state import StateManager

if TYPE_CHECKING:
    from .notification import NotificationManager


class ReleaseScheduler:
    """リリースチェックスケジューラー"""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        github_client: GitHubClient,
        notification_manager: Optional["NotificationManager"] = None,
    ):
        """
        Args:
            config: 設定オブジェクト
            state_manager: 状態管理オブジェクト
            github_client: GitHubクライアント
            notification_manager: 通知マネージャー（フェーズ2で実装）
        """
        self.config = config
        self.state = state_manager
        self.github = github_client
        self.notification_manager = notification_manager
        self.comparator = ReleaseComparator()
        self.logger = get_logger()
        self.running = False

    def _get_current_kernel_version(self) -> Optional[str]:
        """
        現在のシステムカーネルバージョンを取得 (uname -r)

        Returns:
            カーネルバージョン（例: "6.6.87.2"）、取得失敗時はNone
        """
        try:
            result = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                kernel_full = result.stdout.strip()
                # "6.6.87.2-microsoft-standard-WSL2" から "6.6.87.2" を抽出
                match = re.match(r"([\d.]+)", kernel_full)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get kernel version: {e}")
            return None

    async def check_repository(self, repo_config: dict) -> None:
        """
        単一リポジトリをチェック

        Args:
            repo_config: リポジトリ設定
        """
        owner = repo_config["owner"]
        repo = repo_config["repo"]
        repo_url = repo_config["url"]

        self.logger.info(f"Checking {owner}/{repo}...")

        # 最新リリースを取得
        release = await self.github.get_latest_release_async(owner, repo)

        if not release:
            self.logger.warning(f"No releases found for {owner}/{repo}")
            return

        latest_version = release.get("tag_name", "")
        if not latest_version:
            self.logger.warning(f"No tag_name in release for {owner}/{repo}")
            return

        # バージョン抽出
        version = self.comparator.extract_version(latest_version)

        # システムバージョンと比較する設定かチェック
        use_system_version = repo_config.get("use_system_version", False)

        # 比較対象バージョンを取得
        if use_system_version:
            # uname -r からシステムカーネルバージョンを取得
            current_version = self._get_current_kernel_version()
            if current_version is None:
                self.logger.warning(f"Could not get system kernel version for {owner}/{repo}")
                return
            self.logger.info(f"System kernel version: {current_version}")
        else:
            # state.json から前回チェック時のバージョンを取得
            current_version = self.state.get_latest_version(repo_url)

        # 新しいバージョンかチェック
        if current_version is None and not use_system_version:
            # 初回チェック
            self.logger.info(f"First check for {owner}/{repo}: version {version}")
            self.state.update_latest_version(
                repo_url,
                version,
                self.config.get_enabled_channels(),
                metadata={
                    "release_name": release.get("name", ""),
                    "release_url": release.get("html_url", ""),
                    "published_at": release.get("published_at", ""),
                },
            )
        elif current_version is not None and self.comparator.is_newer(current_version, version):
            # 新しいバージョンを発見
            self.logger.info(f"New release for {owner}/{repo}: {current_version} -> {version}")

            # 通知送信
            if self.notification_manager and self.config.is_notification_enabled():
                channels = self.config.get_enabled_channels()
                success = await self._send_notification(
                    repo_config, release, version, channels, current_version, use_system_version
                )

                # 通知履歴を記録
                self.state.add_notification_history(repo_url, version, channels, success)
            else:
                self.logger.info("Notification manager not configured, skipping notification")

            # 状態を更新（システムバージョン比較の場合は記録しない）
            if not use_system_version:
                self.state.update_latest_version(
                    repo_url,
                    version,
                    self.config.get_enabled_channels(),
                    metadata={
                        "release_name": release.get("name", ""),
                        "release_url": release.get("html_url", ""),
                        "published_at": release.get("published_at", ""),
                    },
                )
        else:
            self.logger.debug(f"No new release for {owner}/{repo} (current: {current_version})")

    async def _send_notification(
        self,
        repo_config: dict,
        release: dict,
        version: str,
        channels: list[str],
        current_version: str,
        use_system_version: bool,
    ) -> bool:
        """
        通知を送信

        Args:
            repo_config: リポジトリ設定
            release: リリース情報
            version: バージョン文字列
            channels: 通知チャネルリスト
            current_version: 現在のバージョン
            use_system_version: システムバージョン比較モードか

        Returns:
            送信成功フラグ
        """
        if not self.notification_manager:
            self.logger.warning("Notification manager not configured")
            return False

        # 通知メッセージを構築
        from .notification import NotificationMessage

        # システムバージョン比較の場合は特別なメッセージ
        if use_system_version:
            title = f"WSL2 Kernel Update Available: {version}"
            body = f"New kernel version {version} is available. Current system version: {current_version}. Please rebuild your WSL2 kernel."
        else:
            title = f"New Release: {repo_config['owner']}/{repo_config['repo']} {version}"
            body = f"A new release {version} is available for {repo_config['owner']}/{repo_config['repo']}"

        message = NotificationMessage(
            title=title,
            body=body,
            url=release.get("html_url"),
            owner=repo_config["owner"],
            repo=repo_config["repo"],
            version=version,
            release_name=release.get("name", ""),
            published_at=release.get("published_at", ""),
        )

        # 通知送信
        results = self.notification_manager.send(message)

        # すべてのチャネルが成功したかチェック
        success = all(results.values()) if results else False

        if success:
            self.logger.info(f"All notifications sent successfully for {repo_config['owner']}/{repo_config['repo']}")
        else:
            failed_channels = [ch for ch, res in results.items() if not res]
            self.logger.warning(
                f"Some notifications failed for {repo_config['owner']}/{repo_config['repo']}: {failed_channels}"
            )

        return success

    async def check_all_repositories(self) -> None:
        """全リポジトリをチェック"""
        repos = self.config.get_repositories()

        if not repos:
            self.logger.warning("No repositories configured")
            return

        # 並列チェック
        tasks = [self.check_repository(repo) for repo in repos]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_once(self) -> None:
        """1回だけチェックを実行"""
        self.logger.info("Starting single check...")
        await self.check_all_repositories()
        self.logger.info("Single check completed")

    async def run_forever(self) -> None:
        """無限ループでチェックを実行"""
        self.running = True
        interval = self.config.get_check_interval()

        self.logger.info(f"Starting scheduler with interval: {interval} seconds")

        while self.running:
            try:
                await self.check_all_repositories()
                self.logger.info(f"Sleeping for {interval} seconds...")
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, stopping...")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # エラー時も継続
                await asyncio.sleep(interval)

        self.logger.info("Scheduler stopped")

    def stop(self) -> None:
        """スケジューラーを停止"""
        self.running = False
