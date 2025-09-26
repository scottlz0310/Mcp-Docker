"""
ワークフローシミュレーター
========================

解析されたワークフローを実際に実行するシミュレーターです。
"""

import glob
import hashlib
import json
import os
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Set

from .expression import (
    ExpressionEvaluationError,
    ExpressionEvaluator,
)
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
        self.env_vars: Dict[str, str] = {}
        self.workspace_path = Path.cwd()
        self.current_job: Optional[str] = None
        self.current_step: Optional[int] = None

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
            'GITHUB_EVENT_NAME': 'push',
            'GITHUB_EVENT_ACTION': '',
            'RUNNER_OS': 'Linux',
            'RUNNER_ARCH': 'X64',
            'RUNNER_TEMP': '/tmp',
        })

    def _build_needs_context(
        self,
        job_data: Dict[str, Any],
        job_results: Dict[str, Optional[int]],
    ) -> Dict[str, Dict[str, Any]]:
        dependencies = self._normalize_needs(job_data.get('needs', []))
        needs_context: Dict[str, Dict[str, Any]] = {}
        for dependency in dependencies:
            result = job_results.get(dependency)
            if result == 0:
                status = 'success'
            elif result is None:
                status = 'skipped'
            else:
                status = 'failure'
            needs_context[dependency] = {
                'result': status,
                'status': status,
                'outcome': status,
                'conclusion': status,
                'outputs': {},
            }
        return needs_context

    def _build_base_expression_context(
        self,
        job_id: str,
        job_name: str,
        job_env: Dict[str, str],
        matrix_values: Optional[Dict[str, Any]],
        needs_context: Dict[str, Dict[str, Any]],
        *,
        job_strategy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if isinstance(matrix_values, dict):
            matrix_context: Dict[str, Any] = dict(matrix_values)
        else:
            matrix_context = {}
        runner_context = {
            'os': self.env_vars.get('RUNNER_OS'),
            'arch': self.env_vars.get('RUNNER_ARCH'),
            'temp': self.env_vars.get('RUNNER_TEMP'),
        }
        github_context = {
            'ref': self.env_vars.get('GITHUB_REF'),
            'repository': self.env_vars.get('GITHUB_REPOSITORY'),
            'actor': self.env_vars.get('GITHUB_ACTOR'),
            'sha': self.env_vars.get('GITHUB_SHA'),
            'event_name': self.env_vars.get('GITHUB_EVENT_NAME', 'push'),
            'event': {
                'name': self.env_vars.get('GITHUB_EVENT_NAME', 'push'),
                'action': self.env_vars.get('GITHUB_EVENT_ACTION'),
            },
        }
        strategy_context = (
            job_strategy if isinstance(job_strategy, dict) else {}
        )

        return {
            'env': job_env,
            'matrix': matrix_context,
            'job': {
                'id': job_id,
                'name': job_name,
                'status': 'success',
                'conclusion': 'success',
            },
            'status': 'success',
            'job_status': 'success',
            'step_status': 'success',
            'step_outcome': 'success',
            'needs': needs_context,
            'steps': {},
            'runner': runner_context,
            'github': github_context,
            'vars': {},
            'secrets': {},
            'inputs': {},
            'strategy': strategy_context,
        }

    def _compose_step_context(
        self,
        base_context: Dict[str, Any],
        step_env: Dict[str, str],
        step: Dict[str, Any],
        step_key: str,
        step_name: str,
    ) -> Dict[str, Any]:
        context = dict(base_context)
        context['env'] = step_env
        context['step'] = {
            'id': step_key,
            'name': step_name,
        }
        step_inputs = step.get('with')
        if not isinstance(step_inputs, dict):
            step_inputs = {}
        context['inputs'] = step_inputs
        return context

    def _evaluate_condition(
        self,
        expression: str,
        context: Dict[str, Any],
        description: str,
    ) -> bool:
        evaluator = ExpressionEvaluator(
            self._build_expression_functions(context)
        )
        try:
            return evaluator.evaluate(expression, context)
        except ExpressionEvaluationError as exc:
            self.logger.error(
                f"{description} の条件式を評価できません: {exc}"
            )
            return False

    def _build_expression_functions(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Callable[..., Any]]:
        def _status_values() -> List[str]:
            values: List[str] = []
            for key in ('status', 'job_status', 'step_status'):
                value = context.get(key)
                if isinstance(value, str):
                    values.append(value.lower())
            steps_data = context.get('steps')
            if isinstance(steps_data, Mapping):
                for step_info in steps_data.values():
                    if isinstance(step_info, Mapping):
                        outcome = (
                            step_info.get('outcome')
                            or step_info.get('conclusion')
                        )
                        if isinstance(outcome, str):
                            values.append(outcome.lower())
            return values

        def success() -> bool:
            statuses = _status_values()
            if not statuses:
                return True
            return all(
                status not in ('failure', 'cancelled')
                for status in statuses
            )

        def failure() -> bool:
            return any(status == 'failure' for status in _status_values())

        def cancelled() -> bool:
            return any(status == 'cancelled' for status in _status_values())

        def always() -> bool:
            return True

        def contains(container: Any, item: Any) -> bool:
            if container is None:
                return False
            if isinstance(container, str):
                return str(item) in container
            if isinstance(container, Mapping):
                return item in container.values() or item in container
            if isinstance(container, (list, tuple, set, frozenset)):
                return item in container
            return False

        def starts_with(string: Any, prefix: Any) -> bool:
            if not isinstance(string, str) or not isinstance(prefix, str):
                return False
            return string.startswith(prefix)

        def ends_with(string: Any, suffix: Any) -> bool:
            if not isinstance(string, str) or not isinstance(suffix, str):
                return False
            return string.endswith(suffix)

        def format_str(template: Any, *args: Any) -> str:
            try:
                return str(template).format(*args)
            except Exception as exc:  # noqa: BLE001 - defensive
                raise ExpressionEvaluationError(
                    f"format() failed: {exc}"
                ) from exc

        def join_values(values: Any, separator: Any = ',') -> str:
            if isinstance(values, Mapping):
                iterable = list(values.values())
            elif isinstance(values, (list, tuple, set, frozenset)):
                iterable = list(values)
            elif isinstance(values, str):
                iterable = [values]
            else:
                raise ExpressionEvaluationError(
                    "join() requires a sequence or mapping"
                )

            sep = '' if separator is None else str(separator)
            return sep.join(str(item) for item in iterable)

        def from_json(value: Any) -> Any:
            if value is None:
                return None
            if not isinstance(value, str):
                raise ExpressionEvaluationError(
                    "fromJSON() expects a string"
                )
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ExpressionEvaluationError(
                    f"fromJSON() failed: {exc}"
                ) from exc

        def to_json(value: Any) -> str:
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except TypeError as exc:
                raise ExpressionEvaluationError(
                    f"toJSON() failed: {exc}"
                ) from exc

        def hash_files(*patterns: Any) -> str:
            normalized: List[str] = []
            for pattern in patterns:
                if pattern is None:
                    continue
                if not isinstance(pattern, str) or not pattern:
                    raise ExpressionEvaluationError(
                        "hashFiles() expects string patterns"
                    )
                normalized.append(pattern)

            if not normalized:
                raise ExpressionEvaluationError(
                    "hashFiles() requires at least one pattern"
                )

            workspace_root = self.workspace_path.resolve()
            files: List[Path] = []
            for pattern in normalized:
                absolute_pattern = (
                    pattern if os.path.isabs(pattern)
                    else str(workspace_root / pattern)
                )
                for match in glob.glob(absolute_pattern, recursive=True):
                    candidate = Path(match)
                    if candidate.is_file():
                        files.append(candidate.resolve())

            unique_files = sorted({path for path in files})
            if not unique_files:
                return ''

            digest = hashlib.sha256()
            for file_path in unique_files:
                try:
                    with file_path.open('rb') as handle:
                        for chunk in iter(lambda: handle.read(8192), b''):
                            digest.update(chunk)
                except OSError as exc:
                    raise ExpressionEvaluationError(
                        f"hashFiles() failed to read {file_path}: {exc}"
                    ) from exc

            return digest.hexdigest()

        return {
            'success': success,
            'failure': failure,
            'cancelled': cancelled,
            'always': always,
            'contains': contains,
            'startsWith': starts_with,
            'endsWith': ends_with,
            'format': format_str,
            'join': join_values,
            'fromJSON': from_json,
            'toJSON': to_json,
            'hashFiles': hash_files,
        }

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

    def dry_run(
        self,
        workflow_data: Dict[str, Any],
        job_name: Optional[str] = None,
    ) -> int:
        """ドライラン実行"""
        self.logger.info("=== ドライラン実行 ===")
        self.logger.info(f"ワークフロー: {workflow_data.get('name', 'Unnamed')}")

        all_jobs = workflow_data.get('jobs', {})
        matrix_meta = self._get_matrix_metadata(workflow_data)

        if job_name:
            try:
                jobs = self._resolve_target_jobs(
                    all_jobs,
                    job_name,
                    matrix_meta,
                )
            except SimulationError as exc:
                self.logger.error(str(exc))
                return 1
        else:
            jobs = all_jobs

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

        raw_matrix = job_data.get('matrix')
        matrix_dict: Dict[str, Any] = {}
        if isinstance(raw_matrix, dict):
            matrix_dict = dict(raw_matrix)
        if matrix_dict:
            matrix_repr = ', '.join(
                f"{key}={value}" for key, value in matrix_dict.items()
            )
            self.logger.info(f"  マトリックス: {matrix_repr}")

        steps = job_data.get('steps', [])
        for i, step in enumerate(steps, 1):
            step_name = step.get('name', f'Step {i}')
            self.logger.info(f"  ステップ {i}: {step_name}")

            if 'run' in step:
                command = step['run'].strip()
                ellipsis = '...' if len(command) > 50 else ''
                preview = command[:50]
                self.logger.info(f"    実行: {preview}{ellipsis}")
            elif 'uses' in step:
                action = step['uses']
                self.logger.info(f"    アクション: {action}")

        print()

    def _normalize_needs(self, needs: Any) -> List[str]:
        """needs フィールドをリスト形式へ正規化"""
        if needs in (None, []):
            return []

        if isinstance(needs, str):
            return [needs]

        if isinstance(needs, list):
            normalized: List[str] = []
            for dep in needs:
                if not isinstance(dep, str) or not dep:
                    raise SimulationError(
                        f"needs には空でない文字列のみ指定してください: {needs}"
                    )
                normalized.append(dep)
            return normalized

        raise SimulationError(f"needs フィールドの形式が無効です: {needs}")

    def _resolve_job_batches(
        self,
        jobs: Dict[str, Dict[str, Any]],
    ) -> List[List[str]]:
        """依存関係を考慮したジョブの実行バッチを算出"""
        indegree: Dict[str, int] = {}
        dependents: Dict[str, Set[str]] = defaultdict(set)

        for job_id, job_data in jobs.items():
            normalized_needs = self._normalize_needs(job_data.get('needs', []))
            indegree[job_id] = len(normalized_needs)

            for dependency in normalized_needs:
                if dependency not in jobs:
                    raise SimulationError(
                        f"ジョブ '{job_id}' の依存先 '{dependency}' が見つかりません"
                    )
                dependents[dependency].add(job_id)

        zero_indegree = sorted(
            job_id
            for job_id, count in indegree.items()
            if count == 0
        )
        batches: List[List[str]] = []
        processed = 0
        remaining = indegree.copy()

        while zero_indegree:
            current_batch = list(zero_indegree)
            batches.append(current_batch)

            next_batch_candidates: Set[str] = set()
            for job_id in current_batch:
                processed += 1
                for dependent in dependents.get(job_id, set()):
                    remaining[dependent] -= 1
                    if remaining[dependent] == 0:
                        next_batch_candidates.add(dependent)

            zero_indegree = sorted(next_batch_candidates)

        if processed != len(jobs):
            unresolved = [
                job_id
                for job_id, count in remaining.items()
                if count > 0
            ]
            raise SimulationError(
                f"ジョブ依存関係に循環が存在します: {', '.join(unresolved)}"
            )

        return batches

    def _dependencies_succeeded(
        self,
        job_data: Dict[str, Any],
        job_results: Dict[str, Optional[int]]
    ) -> bool:
        """依存ジョブがすべて成功しているかを確認"""
        needs = self._normalize_needs(job_data.get('needs', []))
        return all(job_results.get(dep) == 0 for dep in needs)

    def _select_jobs_with_dependencies(
        self,
        all_jobs: Dict[str, Dict[str, Any]],
        target_job: str
    ) -> Dict[str, Dict[str, Any]]:
        """ターゲットジョブとその依存ジョブを再帰的に収集"""
        selected: Dict[str, Dict[str, Any]] = {}
        stack = [target_job]

        while stack:
            job_id = stack.pop()
            if job_id in selected:
                continue

            if job_id not in all_jobs:
                raise SimulationError(f"指定されたジョブが見つかりません: {job_id}")

            selected[job_id] = all_jobs[job_id]
            for dependency in self._normalize_needs(
                all_jobs[job_id].get('needs', [])
            ):
                if dependency not in all_jobs:
                    raise SimulationError(
                        f"ジョブ '{job_id}' の依存先 '{dependency}' が見つかりません"
                    )
                stack.append(dependency)

        return {job_id: all_jobs[job_id] for job_id in selected}

    def run(
        self,
        workflow_data: Dict[str, Any],
        job_name: Optional[str] = None,
    ) -> int:
        """ワークフロー実行"""
        self.logger.info("=== ワークフロー実行開始 ===")
        self.logger.info(f"ワークフロー: {workflow_data.get('name', 'Unnamed')}")

        jobs = workflow_data.get('jobs', {})
        matrix_meta = self._get_matrix_metadata(workflow_data)

        if job_name:
            try:
                jobs = self._resolve_target_jobs(
                    jobs,
                    job_name,
                    matrix_meta,
                )
            except SimulationError as exc:
                self.logger.error(str(exc))
                return 1

        start_time = time.time()
        success = True
        successful_jobs = 0
        job_results: Dict[str, Optional[int]] = {}

        try:
            job_batches = self._resolve_job_batches(jobs)

            for batch in job_batches:
                ready_jobs = []
                for job_id in batch:
                    job_data = jobs[job_id]
                    if not self._dependencies_succeeded(job_data, job_results):
                        self.logger.warning(
                            f"ジョブ '{job_id}' をスキップ: 依存ジョブが失敗しました"
                        )
                        job_results[job_id] = None
                        continue
                    ready_jobs.append(job_id)

                if not ready_jobs:
                    continue

                with ThreadPoolExecutor(
                    max_workers=len(ready_jobs)
                ) as executor:
                    futures = {
                        executor.submit(
                            self._run_job,
                            job_id,
                            jobs[job_id],
                            self._build_needs_context(
                                jobs[job_id],
                                job_results,
                            ),
                        ): job_id
                        for job_id in ready_jobs
                    }

                    for future in as_completed(futures):
                        job_id = futures[future]
                        try:
                            result = future.result()
                        except Exception as exc:  # noqa: BLE001
                            self.logger.error(
                                f"ジョブ '{job_id}' 実行中に未処理の例外が発生しました: {exc}"
                            )
                            result = 1

                        job_results[job_id] = result
                        if result == 0:
                            successful_jobs += 1
                        else:
                            success = False

        except SimulationError as e:
            self.logger.error(str(e))
            success = False
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"実行中にエラーが発生しました: {e}")
            success = False

        end_time = time.time()
        duration = end_time - start_time

        if success:
            self.logger.success(
                f"ワークフロー実行が完了しました (実行時間: {duration:.2f}s)"
            )
            self.logger.workflow_summary(len(jobs), successful_jobs, duration)
            return 0

        self.logger.error(
            f"ワークフロー実行が失敗しました (実行時間: {duration:.2f}s)"
        )
        self.logger.workflow_summary(len(jobs), successful_jobs, duration)
        return 1

    def _run_job(
        self,
        job_id: str,
        job_data: Dict[str, Any],
        needs_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> int:
        """ジョブの実行"""
        job_name = job_data.get('name', job_id)
        self.current_job = job_id

        self.logger.info(f"ジョブ実行開始: {job_name} ({job_id})")

        raw_matrix = job_data.get('matrix')
        matrix_dict: Dict[str, Any] = {}
        if isinstance(raw_matrix, dict):
            matrix_dict = dict(raw_matrix)
        if matrix_dict:
            matrix_repr = ', '.join(
                f"{key}={value}" for key, value in matrix_dict.items()
            )
            self.logger.info(f"  マトリックス: {matrix_repr}")

        # ジョブレベルの環境変数設定
        job_env = self.env_vars.copy()
        if 'env' in job_data:
            job_env.update(job_data['env'])

        if matrix_dict:
            for matrix_key, matrix_value in matrix_dict.items():
                env_key = f"MATRIX_{str(matrix_key).upper().replace('-', '_')}"
                job_env[env_key] = str(matrix_value)

        raw_strategy = job_data.get('strategy')
        strategy_dict: Optional[Dict[str, Any]] = (
            dict(raw_strategy)
            if isinstance(raw_strategy, dict)
            else None
        )

        base_context = self._build_base_expression_context(
            job_id,
            job_name,
            job_env,
            matrix_dict if matrix_dict else None,
            needs_context or {},
            job_strategy=strategy_dict,
        )

        job_condition = job_data.get('if')
        if isinstance(job_condition, str) and job_condition.strip():
            if not self._evaluate_condition(
                job_condition,
                base_context,
                f"ジョブ '{job_name}'",
            ):
                self.logger.info(
                    f"ジョブ '{job_name}' をスキップ: 条件 '{job_condition}'"
                )
                base_context['job']['status'] = 'skipped'
                base_context['job']['conclusion'] = 'skipped'
                base_context['status'] = 'skipped'
                base_context['job_status'] = 'skipped'
                return 0

        steps = job_data.get('steps', [])

        for i, step in enumerate(steps, 1):
            self.current_step = i

            result = self._run_step(step, i, job_env, base_context)
            if result != 0:
                self.logger.error(f"ステップ {i} で失敗しました")
                return result

        self.logger.info(f"ジョブ完了: {job_name}")
        return 0

    def _run_step(
        self,
        step: Dict[str, Any],
        step_number: int,
        env_vars: Dict[str, Any],
        base_context: Dict[str, Any],
    ) -> int:
        """ステップの実行"""
        step_name = step.get('name', f'Step {step_number}')
        self.logger.info(f"  ステップ {step_number}: {step_name}")

        step_key = step.get('id') if isinstance(step.get('id'), str) else None
        if not step_key:
            step_key = f"step_{step_number}"

        # ステップレベルの環境変数
        step_env = env_vars.copy()
        if 'env' in step:
            step_env.update(step['env'])

        evaluation_context = self._compose_step_context(
            base_context,
            step_env,
            step,
            step_key,
            step_name,
        )

        # 条件チェック
        condition = step.get('if')
        if isinstance(condition, str) and condition.strip():
            if not self._evaluate_condition(
                condition,
                evaluation_context,
                f"ステップ '{step_name}'",
            ):
                self.logger.info(f"    スキップ: 条件 '{condition}' により")
                base_context['steps'][step_key] = {
                    'outcome': 'skipped',
                    'status': 'skipped',
                    'conclusion': 'skipped',
                }
                base_context['step_status'] = 'skipped'
                base_context['step_outcome'] = 'skipped'
                return 0

        continue_raw = step.get('continue-on-error')
        allow_failure = False
        if isinstance(continue_raw, bool):
            allow_failure = continue_raw
        elif isinstance(continue_raw, str) and continue_raw.strip():
            allow_failure = self._evaluate_condition(
                continue_raw,
                evaluation_context,
                f"ステップ '{step_name}' の continue-on-error",
            )

        if 'run' in step:
            result = self._execute_command(step['run'], step_env)
        elif 'uses' in step:
            result = self._execute_action(
                step['uses'],
                step.get('with', {}),
                step_env,
            )
        else:
            result = 0

        if result == 0:
            base_context['steps'][step_key] = {
                'outcome': 'success',
                'status': 'success',
                'conclusion': 'success',
            }
            base_context['step_status'] = 'success'
            base_context['step_outcome'] = 'success'
            return 0

        if allow_failure:
            self.logger.warning(
                "    失敗しましたが continue-on-error を尊重して続行します"
            )
            base_context['steps'][step_key] = {
                'outcome': 'failure',
                'status': 'failure',
                'conclusion': 'failure',
            }
            base_context['step_status'] = 'failure'
            base_context['step_outcome'] = 'failure'
            return 0

        base_context['steps'][step_key] = {
            'outcome': 'failure',
            'status': 'failure',
            'conclusion': 'failure',
        }
        base_context['status'] = 'failure'
        base_context['job_status'] = 'failure'
        base_context['job']['status'] = 'failure'
        base_context['job']['conclusion'] = 'failure'
        base_context['step_status'] = 'failure'
        base_context['step_outcome'] = 'failure'
        return result

    def _get_matrix_metadata(
        self,
        workflow_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """パーサーが付与したマトリックスメタデータを抽出"""
        simulator_meta = workflow_data.get('_simulator', {})
        if not isinstance(simulator_meta, dict):
            return {'expansions': {}, 'base_lookup': {}}

        matrix_meta = simulator_meta.get('matrix', {})
        if not isinstance(matrix_meta, dict):
            return {'expansions': {}, 'base_lookup': {}}

        expansions = matrix_meta.get('expansions', {})
        base_lookup = matrix_meta.get('base_lookup', {})

        if not isinstance(expansions, dict):
            expansions = {}
        if not isinstance(base_lookup, dict):
            base_lookup = {}

        return {
            'expansions': expansions,
            'base_lookup': base_lookup,
        }

    def _resolve_target_jobs(
        self,
        all_jobs: Dict[str, Dict[str, Any]],
        target_job: str,
        matrix_meta: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """ジョブ指定をマトリックス展開を考慮して解決"""
        if target_job in all_jobs:
            return self._select_jobs_with_dependencies(all_jobs, target_job)

        expansions = matrix_meta.get('expansions', {})
        base_lookup = matrix_meta.get('base_lookup', {})

        variant_ids: List[str] = []
        if target_job in expansions:
            variants = expansions[target_job]
            if isinstance(variants, list):
                variant_ids.extend(str(variant) for variant in variants)
        elif target_job in base_lookup:
            variant_ids.append(target_job)

        if not variant_ids:
            raise SimulationError(f"指定されたジョブが見つかりません: {target_job}")

        selected: Dict[str, Dict[str, Any]] = {}
        for variant_id in variant_ids:
            variant_jobs = self._select_jobs_with_dependencies(
                all_jobs,
                variant_id,
            )
            selected.update(variant_jobs)

        return selected

    def _execute_command(self, command: str, env_vars: Dict[str, Any]) -> int:
        """コマンド実行"""
        self.logger.debug(f"    実行: {command}")

        try:
            # 環境変数を設定してコマンド実行
            full_env = os.environ.copy()
            normalized_env: Dict[str, str] = {}
            for raw_key, raw_value in env_vars.items():
                key = str(raw_key)
                value = "" if raw_value is None else str(raw_value)
                normalized_env[key] = value
            full_env.update(normalized_env)

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

    def _execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        env_vars: Dict[str, str],
    ) -> int:
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
