"""
ワークフロー解析モジュール
=======================

GitHub Actions ワークフローYAMLファイルを解析し、
実行可能な形式に変換します。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List


class WorkflowParseError(Exception):
    """ワークフロー解析エラー"""
    pass


class WorkflowParser:
    """GitHub Actions ワークフロー解析クラス"""

    def __init__(self):
        """初期化"""
        self.required_fields = ['name', 'on', 'jobs']
        self.supported_events = [
            'push', 'pull_request', 'schedule',
            'workflow_dispatch', 'workflow_call'
        ]

    def parse_file(self, workflow_path: Path) -> Dict[str, Any]:
        """
        ワークフローYAMLファイルを解析

        Args:
            workflow_path: ワークフローファイルのパス

        Returns:
            解析されたワークフローデータ

        Raises:
            WorkflowParseError: 解析エラー
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = yaml.safe_load(f)

            # 基本検証
            self._validate_basic_structure(workflow_data)

            return workflow_data

        except yaml.YAMLError as e:
            raise WorkflowParseError(f"YAML解析エラー: {e}")
        except FileNotFoundError:
            raise WorkflowParseError(f"ファイルが見つかりません: {workflow_path}")
        except Exception as e:
            raise WorkflowParseError(f"予期しないエラー: {e}")

    def _validate_basic_structure(self, workflow_data: Dict[str, Any]) -> None:
        """基本構造の検証"""
        if not isinstance(workflow_data, dict):
            raise WorkflowParseError("ワークフローはYAMLオブジェクトである必要があります")

        # 必須フィールドの確認（'on'は文字列または真偽値として解析される場合がある）
        for field in self.required_fields:
            if field == 'on':
                # 'on'キーは'on'または True として存在する可能性がある
                if 'on' not in workflow_data and True not in workflow_data:
                    raise WorkflowParseError(f"必須フィールド '{field}' がありません")
            else:
                if field not in workflow_data:
                    raise WorkflowParseError(f"必須フィールド '{field}' がありません")

        # ジョブの検証
        jobs = workflow_data.get('jobs', {})
        if not jobs:
            raise WorkflowParseError("少なくとも1つのジョブが必要です")

        for job_id, job_data in jobs.items():
            self._validate_job(job_id, job_data)

    def _validate_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """ジョブの検証"""
        if not isinstance(job_data, dict):
            raise WorkflowParseError(f"ジョブ '{job_id}' は有効なオブジェクトではありません")

        # runs-onの確認
        if 'runs-on' not in job_data:
            raise WorkflowParseError(f"ジョブ '{job_id}' に 'runs-on' が指定されていません")

        # stepsの確認
        steps = job_data.get('steps', [])
        if not steps:
            raise WorkflowParseError(f"ジョブ '{job_id}' にステップがありません")

        for i, step in enumerate(steps):
            self._validate_step(job_id, i, step)

    def _validate_step(self, job_id: str, step_index: int, step: Dict[str, Any]) -> None:
        """ステップの検証"""
        if not isinstance(step, dict):
            raise WorkflowParseError(
                f"ジョブ '{job_id}' のステップ {step_index + 1} が無効です"
            )

        # runまたはusesのどちらかは必須
        if 'run' not in step and 'uses' not in step:
            raise WorkflowParseError(
                f"ジョブ '{job_id}' のステップ {step_index + 1} に "
                "'run' または 'uses' が必要です"
            )

    def strict_validate(self, workflow_data: Dict[str, Any]) -> None:
        """厳密な検証"""
        # 基本検証
        self._validate_basic_structure(workflow_data)

        # イベント検証
        events = workflow_data.get('on')
        if isinstance(events, str):
            events = [events]
        elif isinstance(events, dict):
            events = list(events.keys())

        for event in events:
            if event not in self.supported_events:
                raise WorkflowParseError(f"サポートされていないイベント: {event}")

        # 環境変数の検証
        jobs = workflow_data.get('jobs', {})
        for job_id, job_data in jobs.items():
            self._strict_validate_job(job_id, job_data)

    def _strict_validate_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """ジョブの厳密な検証"""
        # タイムアウトの確認
        timeout = job_data.get('timeout-minutes')
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のタイムアウト値が無効です: {timeout}"
                )

        # 環境変数の確認
        env = job_data.get('env', {})
        if not isinstance(env, dict):
            raise WorkflowParseError(f"ジョブ '{job_id}' の環境変数が無効です")

        # ステップの厳密な検証
        steps = job_data.get('steps', [])
        for i, step in enumerate(steps):
            self._strict_validate_step(job_id, i, step)

    def _strict_validate_step(self, job_id: str, step_index: int, step: Dict[str, Any]) -> None:
        """ステップの厳密な検証"""
        # 基本検証
        self._validate_step(job_id, step_index, step)

        # nameの確認（推奨）
        if 'name' not in step:
            # 警告として記録（ここでは省略）
            pass

        # 条件式の検証
        if 'if' in step:
            condition = step['if']
            if not isinstance(condition, str):
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のステップ {step_index + 1} の条件式が無効です"
                )

        # usesの場合のバージョン確認
        if 'uses' in step:
            uses = step['uses']
            if not isinstance(uses, str) or not uses.strip():
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のステップ {step_index + 1} の 'uses' が無効です"
                )

    def get_jobs_summary(self, workflow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ジョブの概要情報を取得"""
        jobs = workflow_data.get('jobs', {})
        summary = []

        for job_id, job_data in jobs.items():
            summary.append({
                'id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on'),
                'steps_count': len(job_data.get('steps', [])),
                'timeout_minutes': job_data.get('timeout-minutes'),
                'needs': job_data.get('needs', [])
            })

        return summary
