"""
ログ出力モジュール
================

GitHub Actions Simulatorのログ出力を管理します。
"""

import logging
import sys
from typing import Optional
from datetime import datetime


class ActionsLogger:
    """Actions用カスタムロガー"""

    def __init__(self, verbose: bool = False, name: str = "actions-simulator"):
        """
        初期化

        Args:
            verbose: 詳細ログを有効にするかどうか
            name: ロガー名
        """
        self.logger = logging.getLogger(name)
        self.verbose = verbose

        # ログレベル設定
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # ハンドラー設定
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.propagate = False

    def info(self, message: str) -> None:
        """情報ログ"""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """デバッグログ"""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """警告ログ"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """エラーログ"""
        self.logger.error(message)

    def success(self, message: str) -> None:
        """成功ログ（緑色で表示）"""
        # ANSI color codes for green text
        GREEN = '\033[92m'
        ENDC = '\033[0m'

        if sys.stdout.isatty():
            print(f"{GREEN}✓ {message}{ENDC}")
        else:
            print(f"✓ {message}")

    def step_start(self, step_name: str, step_number: int) -> None:
        """ステップ開始ログ"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ▶ Step {step_number}: {step_name}")

    def step_end(self, step_number: int, success: bool = True) -> None:
        """ステップ終了ログ"""
        if success:
            print(f"  ✓ Step {step_number} completed")
        else:
            print(f"  ✗ Step {step_number} failed")

    def job_start(self, job_name: str) -> None:
        """ジョブ開始ログ"""
        print(f"\n{'='*60}")
        print(f"🚀 Job: {job_name}")
        print(f"{'='*60}")

    def job_end(self, job_name: str, success: bool = True) -> None:
        """ジョブ終了ログ"""
        if success:
            print(f"\n✓ Job '{job_name}' completed successfully")
        else:
            print(f"\n✗ Job '{job_name}' failed")
        print("-" * 60)

    def workflow_summary(self, total_jobs: int, successful_jobs: int, duration: float) -> None:
        """ワークフロー実行サマリー"""
        print(f"\n{'='*60}")
        print("📊 Workflow Summary")
        print(f"{'='*60}")
        print(f"Total jobs: {total_jobs}")
        print(f"Successful: {successful_jobs}")
        print(f"Failed: {total_jobs - successful_jobs}")
        print(f"Duration: {duration:.2f}s")

        if successful_jobs == total_jobs:
            self.success("All jobs completed successfully! 🎉")
        else:
            print(f"\n❌ {total_jobs - successful_jobs} job(s) failed")
