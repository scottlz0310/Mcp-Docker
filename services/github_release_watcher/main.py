"""
GitHub Release Watcher - メインエントリーポイント
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import Config
from .github_client import GitHubClient
from .logger import setup_logger
from .scheduler import ReleaseScheduler
from .state import StateManager


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="GitHub Release Watcher - Monitor GitHub releases and send notifications"
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Configuration file path (default: config.toml)",
    )

    parser.add_argument(
        "-s",
        "--state",
        type=Path,
        default=Path("state.json"),
        help="State file path (default: state.json)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path (optional)",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: run forever)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit",
    )

    return parser.parse_args()


def validate_config(config: Config) -> bool:
    """
    設定を検証

    Args:
        config: 設定オブジェクト

    Returns:
        検証成功フラグ
    """
    errors = config.validate()

    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("Configuration validation successful")
    return True


async def main_async(args: argparse.Namespace) -> int:
    """
    非同期メイン処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    # .env ファイルを読み込み
    load_dotenv()

    # ロガーセットアップ
    logger = setup_logger(
        level=args.log_level,
        log_file=args.log_file,
    )

    # 設定ファイル読み込み
    try:
        config = Config(args.config)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        return 1

    # 設定検証
    if not validate_config(config):
        return 1

    # --validate フラグ時は検証のみで終了
    if args.validate:
        return 0

    # 状態管理初期化
    state_manager = StateManager(args.state)

    # GitHubクライアント初期化
    github_token = config.get_github_token()
    github_client = GitHubClient(token=github_token)

    # 通知マネージャー初期化
    notification_manager = None
    if config.is_notification_enabled():
        from .notification import NotificationManager

        notification_config = config.get_notification_config()
        notification_manager = NotificationManager(notification_config)
        logger.info(f"Notification manager initialized with channels: {notification_manager.get_enabled_channels()}")
    else:
        logger.info("Notifications are disabled")

    # スケジューラー初期化
    scheduler = ReleaseScheduler(
        config=config,
        state_manager=state_manager,
        github_client=github_client,
        notification_manager=notification_manager,
    )

    # 実行
    try:
        if args.once:
            await scheduler.run_once()
        else:
            await scheduler.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        scheduler.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0


def main() -> int:
    """
    メインエントリーポイント

    Returns:
        終了コード
    """
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
