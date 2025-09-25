"""
GitHub Actions Simulator - act wrapper
actバイナリとの統合を提供するモジュール
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .logger import ActionsLogger

# ログ設定
logger = ActionsLogger(verbose=True)


class ActWrapper:
    """nektos/act との統合を提供するクラス"""

    def __init__(self, working_directory: Optional[str] = None):
        """
        ActWrapperを初期化

        Args:
            working_directory: ワークディレクトリのパス
        """
        self.working_directory = working_directory or os.getcwd()
        self.act_binary = self._find_act_binary()

    def _find_act_binary(self) -> str:
        """
        actバイナリのパスを取得

        Returns:
            str: actバイナリのパス

        Raises:
            RuntimeError: actが見つからない場合
        """
        try:
            result = subprocess.run(
                ["which", "act"],
                capture_output=True,
                text=True,
                check=True
            )
            act_path = result.stdout.strip()
            logger.info(f"actバイナリが見つかりました: {act_path}")
            return act_path
        except subprocess.CalledProcessError:
            # brewのパスも確認
            brew_act = "/home/linuxbrew/.linuxbrew/bin/act"
            if Path(brew_act).exists():
                logger.info(f"brewのactが見つかりました: {brew_act}")
                return brew_act

            raise RuntimeError(
                "actが見つかりません。以下のコマンドでインストールしてください:\n"
                "  brew install act\n"
                "  curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
            )

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        利用可能なワークフローとジョブの一覧を取得

        Returns:
            List[Dict[str, Any]]: ワークフロー情報のリスト
        """
        try:
            cmd = [self.act_binary, "--list", "--json"]
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                check=True
            )

            # actの出力を解析
            workflows = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        workflow_data = json.loads(line)
                        workflows.append(workflow_data)
                    except json.JSONDecodeError:
                        logger.warning(f"JSONの解析に失敗: {line}")

            return workflows

        except subprocess.CalledProcessError as e:
            logger.error(f"actワークフロー一覧取得エラー: {e}")
            logger.error(f"stderr: {e.stderr}")
            return []

    def run_workflow(
        self,
        workflow_file: Optional[str] = None,
        event: str = "push",
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        ワークフローを実行

        Args:
            workflow_file: ワークフローファイルのパス
            event: トリガーイベント
            job: 実行するジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ出力
            env_vars: 環境変数

        Returns:
            Dict[str, Any]: 実行結果
        """
        cmd = [self.act_binary]

        # ワークフローファイル指定
        if workflow_file:
            cmd.extend(["-W", workflow_file])

        # ジョブ指定
        if job:
            cmd.extend(["-j", job])

        # ドライラン
        if dry_run:
            cmd.append("--dryrun")

        # 詳細ログ
        if verbose:
            cmd.append("--verbose")

        # 環境変数
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["--env", f"{key}={value}"])

        try:
            logger.info(f"actコマンド実行: {' '.join(cmd)}")

            # eventpathなしで実行（デフォルトのpushイベントを使用）
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=600  # 10分のタイムアウト
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": ' '.join(cmd)
            }

        except subprocess.TimeoutExpired:
            logger.error("actの実行がタイムアウトしました")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Execution timeout",
                "command": ' '.join(cmd)
            }
        except Exception as e:
            logger.error(f"act実行エラー: {e}")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": ' '.join(cmd)
            }

    def validate_workflow(self, workflow_file: str) -> Dict[str, Any]:
        """
        ワークフローファイルを検証

        Args:
            workflow_file: ワークフローファイルのパス

        Returns:
            Dict[str, Any]: 検証結果
        """
        return self.run_workflow(
            workflow_file=workflow_file,
            dry_run=True,
            verbose=True
        )

    def get_workflow_jobs(self, workflow_file: str) -> List[Dict[str, Any]]:
        """
        指定されたワークフローのジョブ一覧を取得

        Args:
            workflow_file: ワークフローファイルのパス

        Returns:
            List[Dict[str, Any]]: ジョブ情報のリスト
        """
        try:
            cmd = [self.act_binary, "--list", "-W", workflow_file]
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                check=True
            )

            jobs = []
            # act --listの出力を解析
            for line in result.stdout.strip().split('\n')[1:]:  # ヘッダーをスキップ
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        jobs.append({
                            "stage": parts[0],
                            "job_id": parts[1],
                            "job_name": parts[2],
                            "workflow_name": " ".join(parts[3:-2]),
                            "workflow_file": parts[-2],
                            "events": parts[-1]
                        })

            return jobs

        except subprocess.CalledProcessError as e:
            logger.error(f"ワークフロージョブ取得エラー: {e}")
            return []

    def check_requirements(self) -> Dict[str, Any]:
        """
        act実行に必要な要件をチェック

        Returns:
            Dict[str, Any]: 要件チェック結果
        """
        requirements = {
            "act_binary": False,
            "docker": False,
            "docker_running": False,
            "version": None,
            "issues": []
        }

        # actバイナリの確認
        try:
            self._find_act_binary()
            requirements["act_binary"] = True
        except RuntimeError as e:
            requirements["issues"].append(str(e))

        # Dockerの確認
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            requirements["docker"] = True
        except subprocess.CalledProcessError:
            requirements["issues"].append("Dockerがインストールされていません")

        # Docker daemonの確認
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                check=True
            )
            requirements["docker_running"] = True
        except subprocess.CalledProcessError:
            requirements["issues"].append("Dockerデーモンが実行されていません")

        # actバージョンの取得
        if requirements["act_binary"]:
            try:
                result = subprocess.run(
                    [self.act_binary, "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                requirements["version"] = result.stdout.strip()
            except subprocess.CalledProcessError:
                requirements["issues"].append("actバージョンの取得に失敗しました")

        return requirements
