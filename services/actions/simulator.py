"""
ワークフローシミュレーター
========================

解析されたワークフローを実際に実行するシミュレーターです。
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .logger import ActionsLogger


class SimulationError(Exception):
    """シミュレーション実行エラー"""
    pass


class WorkflowSimulator:
    """ワークフロー実行シミュレーター"""

    def __init__(self, logger: Optional['ActionsLogger'] = None):
        """
        初期化

        Args:
            logger: ロガーインスタンス
        """
        self.logger = logger or ActionsLogger()
        self.env_vars = {}
        self.workspace_path = Path.cwd()
        self.current_job = None
        self.current_step = None

        # デフォルト環境変数
        self._setup_default_env()

    def _setup_default_env(self) -> None:
        """デフォルト環境変数の設定"""
        self.env_vars.update({
            'GITHUB_WORKSPACE': str(self.workspace_path),
            'GITHUB_REPOSITORY': 'local/test',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_SHA': '0' * 40,
            'GITHUB_ACTOR': 'simulator',
            'RUNNER_OS': 'Linux',
            'RUNNER_TEMP': '/tmp',
        })

    def load_env_file(self, env_file: Path) -> None:
        """環境変数ファイルを読み込み"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env_vars[key] = value

            self.logger.info(f"環境変数ファイルを読み込みました: {env_file}")

        except Exception as e:
            raise SimulationError(f"環境変数ファイル読み込みエラー: {e}")

    def dry_run(self, workflow_data: Dict[str, Any], job_name: Optional[str] = None) -> int:
        """ドライラン実行"""
        self.logger.info("=== ドライラン実行 ===")
        self.logger.info(f"ワークフロー: {workflow_data.get('name', 'Unnamed')}")

        jobs = workflow_data.get('jobs', {})

        if job_name:
            if job_name not in jobs:
                self.logger.error(f"指定されたジョブが見つかりません: {job_name}")
                return 1
            jobs = {job_name: jobs[job_name]}

        for job_id, job_data in jobs.items():
            self._dry_run_job(job_id, job_data)

        self.logger.info("ドライラン実行が完了しました")
        return 0

    def _dry_run_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """ジョブのドライラン"""
        job_name = job_data.get('name', job_id)
        runs_on = job_data.get('runs-on', 'unknown')

        self.logger.info(f"ジョブ: {job_name} ({job_id})")
        self.logger.info(f"  実行環境: {runs_on}")

        steps = job_data.get('steps', [])
        for i, step in enumerate(steps, 1):
            step_name = step.get('name', f'Step {i}')
            self.logger.info(f"  ステップ {i}: {step_name}")

            if 'run' in step:
                command = step['run'].strip()
                self.logger.info(f"    実行: {command[:50]}{'...' if len(command) > 50 else ''}")
            elif 'uses' in step:
                action = step['uses']
                self.logger.info(f"    アクション: {action}")

        print()

    def run(self, workflow_data: Dict[str, Any], job_name: Optional[str] = None) -> int:
        """ワークフロー実行"""
        self.logger.info("=== ワークフロー実行開始 ===")
        self.logger.info(f"ワークフロー: {workflow_data.get('name', 'Unnamed')}")

        jobs = workflow_data.get('jobs', {})

        if job_name:
            if job_name not in jobs:
                self.logger.error(f"指定されたジョブが見つかりません: {job_name}")
                return 1
            jobs = {job_name: jobs[job_name]}

        start_time = time.time()
        success = True

        try:
            for job_id, job_data in jobs.items():
                result = self._run_job(job_id, job_data)
                if result != 0:
                    success = False
                    break

        except Exception as e:
            self.logger.error(f"実行中にエラーが発生しました: {e}")
            success = False

        end_time = time.time()
        duration = end_time - start_time

        if success:
            self.logger.success(f"ワークフロー実行が完了しました (実行時間: {duration:.2f}s)")
            return 0
        else:
            self.logger.error(f"ワークフロー実行が失敗しました (実行時間: {duration:.2f}s)")
            return 1

    def _run_job(self, job_id: str, job_data: Dict[str, Any]) -> int:
        """ジョブの実行"""
        job_name = job_data.get('name', job_id)
        self.current_job = job_id

        self.logger.info(f"ジョブ実行開始: {job_name} ({job_id})")

        # ジョブレベルの環境変数設定
        job_env = self.env_vars.copy()
        if 'env' in job_data:
            job_env.update(job_data['env'])

        steps = job_data.get('steps', [])

        for i, step in enumerate(steps, 1):
            self.current_step = i

            result = self._run_step(step, i, job_env)
            if result != 0:
                self.logger.error(f"ステップ {i} で失敗しました")
                return result

        self.logger.info(f"ジョブ完了: {job_name}")
        return 0

    def _run_step(self, step: Dict[str, Any], step_number: int, env_vars: Dict[str, str]) -> int:
        """ステップの実行"""
        step_name = step.get('name', f'Step {step_number}')
        self.logger.info(f"  ステップ {step_number}: {step_name}")

        # ステップレベルの環境変数
        step_env = env_vars.copy()
        if 'env' in step:
            step_env.update(step['env'])

        # 条件チェック
        if 'if' in step:
            # 簡単な条件評価（実際は複雑）
            condition = step['if']
            if condition == 'false' or condition == '${{ false }}':
                self.logger.info(f"    スキップ: 条件 '{condition}' により")
                return 0

        if 'run' in step:
            return self._execute_command(step['run'], step_env)
        elif 'uses' in step:
            return self._execute_action(step['uses'], step.get('with', {}), step_env)

        return 0

    def _execute_command(self, command: str, env_vars: Dict[str, str]) -> int:
        """コマンド実行"""
        self.logger.debug(f"    実行: {command}")

        try:
            # 環境変数を設定してコマンド実行
            full_env = os.environ.copy()
            full_env.update(env_vars)

            result = subprocess.run(
                command,
                shell=True,
                env=full_env,
                cwd=str(self.workspace_path),  # Path objectを文字列に変換
                capture_output=True,
                text=True
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    self.logger.info(f"    {line}")

            if result.stderr and result.returncode != 0:
                for line in result.stderr.strip().split('\n'):
                    self.logger.error(f"    {line}")

            return result.returncode

        except Exception as e:
            self.logger.error(f"    コマンド実行エラー: {e}")
            return 1

    def _execute_action(self, action: str, inputs: Dict[str, Any], env_vars: Dict[str, str]) -> int:
        """アクション実行（簡易実装）"""
        self.logger.info(f"    アクション実行: {action}")

        # 一般的なアクションの簡易シミュレーション
        if action.startswith('actions/checkout'):
            self.logger.info("    リポジトリをチェックアウト")
            return 0
        elif action.startswith('actions/setup-'):
            setup_type = action.split('/')[-1]
            self.logger.info(f"    {setup_type} をセットアップ")
            return 0
        else:
            self.logger.warning(f"    未対応のアクション: {action}")
            # デフォルトは成功扱い
            return 0
