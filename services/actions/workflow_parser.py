"""
ワークフロー解析モジュール
=======================

GitHub Actions ワークフローYAMLファイルを解析し、
実行可能な形式に変換します。
"""

import copy
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import yaml


class WorkflowParseError(Exception):
    """ワークフロー解析エラー"""


class WorkflowParser:
    """GitHub Actions ワークフロー解析クラス"""

    def __init__(self):
        """初期化"""
        self.required_fields = ["name", "on", "jobs"]
        self.supported_events = [
            "push",
            "pull_request",
            "schedule",
            "workflow_dispatch",
            "workflow_call",
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
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow_data = yaml.safe_load(f)

            # 基本検証
            self._validate_basic_structure(workflow_data)

            # マトリックス戦略の展開
            self._expand_matrix_jobs(workflow_data)

            return workflow_data

        except yaml.YAMLError as exc:
            raise WorkflowParseError(f"YAML解析エラー: {exc}") from exc
        except FileNotFoundError as exc:
            raise WorkflowParseError(
                f"ファイルが見つかりません: {workflow_path}"
            ) from exc
        except Exception as exc:
            raise WorkflowParseError(f"予期しないエラー: {exc}") from exc

    def _validate_basic_structure(self, workflow_data: Dict[str, Any]) -> None:
        """基本構造の検証"""
        if not workflow_data or not isinstance(workflow_data, dict):
            raise WorkflowParseError(
                "ワークフローはYAMLオブジェクトである必要があります"
            )

        # GitHub Actions YAML特有の問題への対処
        # YAMLパーサーが 'on:' を True キーとして解釈する問題を修正
        workflow_data = self._normalize_github_actions_yaml(workflow_data)

        # 必須フィールドの確認
        for field in self.required_fields:
            if field not in workflow_data:
                raise WorkflowParseError(f"必須フィールド '{field}' がありません")

        # ジョブの検証
        jobs = workflow_data.get("jobs", {})
        if not jobs:
            raise WorkflowParseError("少なくとも1つのジョブが必要です")

        for job_id, job_data in jobs.items():
            self._validate_job(job_id, job_data)

    def _normalize_github_actions_yaml(
        self, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        GitHub Actions YAML特有の問題を正規化

        YAMLパーサーが 'on:' キーワードを True として解釈する問題に対処
        これはYAML仕様に従った正常な動作だが、GitHub Actionsでは文字列キーとして扱う必要がある

        Args:
            workflow_data: 解析されたYAMLデータ

        Returns:
            正規化されたワークフローデータ
        """
        # 辞書のコピーを作成（元データを変更しない）
        normalized_data = workflow_data.copy()

        # 'on' キーが True として解釈されている場合の修正
        # 型チェッカー向け: Dict[str, Any]だがYAMLパーサーの仕様上boolキーが存在する
        bool_keys = [k for k in normalized_data.keys() if isinstance(k, bool)]
        for bool_key in bool_keys:
            if bool_key is True and "on" not in normalized_data:
                normalized_data["on"] = normalized_data[bool_key]
                del normalized_data[bool_key]

        return normalized_data

    def _validate_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """ジョブの検証"""
        if not isinstance(job_data, dict):
            raise WorkflowParseError(
                f"ジョブ '{job_id}' は有効なオブジェクトではありません"
            )

        # runs-onの確認
        if "runs-on" not in job_data:
            raise WorkflowParseError(
                f"ジョブ '{job_id}' に 'runs-on' が指定されていません"
            )

        # stepsの確認
        steps = job_data.get("steps", [])
        if not steps:
            raise WorkflowParseError(f"ジョブ '{job_id}' にステップがありません")

        for i, step in enumerate(steps):
            self._validate_step(job_id, i, step)

    def _validate_step(
        self, job_id: str, step_index: int, step: Dict[str, Any]
    ) -> None:
        """ステップの検証"""
        if not isinstance(step, dict):
            raise WorkflowParseError(
                f"ジョブ '{job_id}' のステップ {step_index + 1} が無効です"
            )

        # runまたはusesのどちらかは必須
        if "run" not in step and "uses" not in step:
            raise WorkflowParseError(
                f"ジョブ '{job_id}' のステップ {step_index + 1} に "
                "'run' または 'uses' が必要です"
            )

    def _normalize_needs(self, needs: Any) -> List[str]:
        """needs フィールドをリスト形式に正規化"""
        if needs in (None, [], ""):
            return []

        if isinstance(needs, str):
            return [needs]

        if isinstance(needs, list):
            normalized: List[str] = []
            for dep in needs:
                if not isinstance(dep, str) or not dep:
                    raise WorkflowParseError(
                        "needs には空でない文字列のみ指定してください"
                    )
                normalized.append(dep)
            return normalized

        raise WorkflowParseError("needs フィールドの形式が無効です")

    def _expand_matrix_jobs(self, workflow_data: Dict[str, Any]) -> None:
        """strategy.matrix を展開して個別ジョブに変換"""
        jobs_field = workflow_data.get("jobs", {})
        if not isinstance(jobs_field, dict):
            raise WorkflowParseError("jobs フィールドが無効です")

        jobs: Dict[str, Dict[str, Any]] = {}
        for job_id, job_data in jobs_field.items():
            if not isinstance(job_data, dict):
                raise WorkflowParseError(f"ジョブ '{job_id}' の定義が無効です")
            jobs[job_id] = job_data

        expanded_jobs: Dict[str, Dict[str, Any]] = {}
        expansion_map: Dict[str, List[str]] = {}
        base_lookup: Dict[str, str] = {}

        for job_id, job_data in jobs.items():
            strategy_obj = job_data.get("strategy")
            strategy_dict: Optional[Dict[str, Any]] = (
                cast(Dict[str, Any], strategy_obj)
                if isinstance(strategy_obj, dict)
                else None
            )
            matrix_def = strategy_dict.get("matrix") if strategy_dict else None

            if not matrix_def:
                expanded_jobs[job_id] = job_data
                expansion_map[job_id] = [job_id]
                base_lookup[job_id] = job_id
                continue

            if not isinstance(matrix_def, dict):
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' の strategy.matrix はマップである必要があります"
                )

            combinations = self._generate_matrix_combinations(
                job_id,
                cast(Dict[str, Any], matrix_def),
            )
            if not combinations:
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' の matrix 定義に展開可能な組み合わせがありません"
                )

            variant_ids: List[str] = []
            for index, combo in enumerate(combinations, start=1):
                new_job_id = self._build_matrix_job_id(
                    job_id,
                    combo,
                    index,
                    expanded_jobs,
                )
                matrix_job = copy.deepcopy(job_data)

                # strategy から matrix を除去
                if isinstance(matrix_job.get("strategy"), dict):
                    new_strategy = copy.deepcopy(matrix_job["strategy"])
                    new_strategy.pop("matrix", None)
                    if new_strategy:
                        matrix_job["strategy"] = new_strategy
                    else:
                        matrix_job.pop("strategy", None)

                base_name = job_data.get("name", job_id)
                matrix_summary = ", ".join(
                    f"{matrix_key}={combo[matrix_key]}" for matrix_key in sorted(combo)
                )
                matrix_job["name"] = (
                    f"{base_name} [{matrix_summary}]" if matrix_summary else base_name
                )

                job_env = copy.deepcopy(job_data.get("env", {}))
                job_env.update(
                    {
                        f"MATRIX_{matrix_key.upper()}": str(value)
                        for matrix_key, value in combo.items()
                    }
                )
                matrix_job["env"] = job_env

                matrix_job["matrix"] = combo
                matrix_job["base_job_id"] = job_id

                expanded_jobs[new_job_id] = matrix_job
                variant_ids.append(new_job_id)
                base_lookup[new_job_id] = job_id

            expansion_map[job_id] = variant_ids

        # needs の展開
        for job_id, job_data in expanded_jobs.items():
            original_needs = job_data.get("needs")
            normalized_needs = self._normalize_needs(original_needs)

            if not normalized_needs:
                if "needs" in job_data:
                    job_data.pop("needs", None)
                continue

            expanded_needs: List[str] = []
            for dependency in normalized_needs:
                target_variants = expansion_map.get(dependency)
                if target_variants:
                    expanded_needs.extend(target_variants)
                else:
                    expanded_needs.append(dependency)

            job_data["needs"] = expanded_needs

            if (
                job_id in jobs
                and isinstance(original_needs, str)
                and len(expanded_needs) == 1
            ):
                job_data["needs"] = expanded_needs[0]

        workflow_data["jobs"] = expanded_jobs
        workflow_data.setdefault("_simulator", {})["matrix"] = {
            "expansions": expansion_map,
            "base_lookup": base_lookup,
        }

    def _generate_matrix_combinations(
        self, job_id: str, matrix_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """matrix 定義から組み合わせを生成"""
        include_raw = matrix_def.get("include", [])
        exclude_raw = matrix_def.get("exclude", [])

        include_items: List[Dict[str, Any]] = []
        if include_raw:
            if not isinstance(include_raw, list):
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' の matrix.include が無効です"
                )
            typed_include_raw = cast(List[Any], include_raw)
            for include_entry_raw in typed_include_raw:
                if not isinstance(include_entry_raw, dict):
                    raise WorkflowParseError(
                        f"ジョブ '{job_id}' の matrix.include エントリが無効です"
                    )
                include_entry = cast(Dict[str, Any], include_entry_raw)
                include_items.append(include_entry)

        exclude_items: List[Dict[str, Any]] = []
        if exclude_raw:
            if not isinstance(exclude_raw, list):
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' の matrix.exclude が無効です"
                )
            typed_exclude_raw = cast(List[Any], exclude_raw)
            for exclude_entry_raw in typed_exclude_raw:
                if not isinstance(exclude_entry_raw, dict):
                    raise WorkflowParseError(
                        f"ジョブ '{job_id}' の matrix.exclude エントリが無効です"
                    )
                exclude_entry = cast(Dict[str, Any], exclude_entry_raw)
                exclude_items.append(exclude_entry)

        axes: Dict[str, List[Any]] = {}
        for key, raw_values in matrix_def.items():
            if key in {"include", "exclude"}:
                continue
            if not isinstance(raw_values, list) or not raw_values:
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' の matrix.{key} が無効です"
                )
            typed_values = cast(List[Any], raw_values)
            axes[key] = list(typed_values)

        axis_keys: List[str] = list(axes.keys())
        axis_values: List[List[Any]] = [axes[key] for key in axis_keys]

        combinations: List[Dict[str, Any]] = []
        if axis_values:
            for values_tuple in product(*axis_values):
                combinations.append(dict(zip(axis_keys, values_tuple)))

        def matches(
            combo: Dict[str, Any],
            criteria: Dict[str, Any],
            *,
            keys: Optional[set[str]] = None,
        ) -> bool:
            relevant_items = (
                (criteria_key, criteria_value)
                for criteria_key, criteria_value in criteria.items()
                if keys is None or criteria_key in keys
            )
            return all(
                combo.get(criteria_key) == criteria_value
                for criteria_key, criteria_value in relevant_items
            )

        if exclude_items:
            filtered: List[Dict[str, Any]] = []
            for combo in combinations:
                if any(matches(combo, exclusion) for exclusion in exclude_items):
                    continue
                filtered.append(combo)
            combinations = filtered

        if include_items:
            axis_key_set = set(axis_keys)
            for include_entry in include_items:
                entry_axes = {
                    axis_key: include_entry[axis_key]
                    for axis_key in axis_key_set
                    if axis_key in include_entry
                }

                matched = False
                if entry_axes and combinations:
                    for combo in combinations:
                        if matches(combo, entry_axes):
                            combo.update(include_entry)
                            matched = True
                if not matched:
                    combinations.append(dict(include_entry))

        # 重複排除（順序維持）
        unique_combinations: List[Dict[str, Any]] = []
        seen: set[Tuple[Tuple[str, Any], ...]] = set()
        for combo in combinations:
            combo_key: Tuple[Tuple[str, str], ...] = tuple(
                sorted(
                    (
                        str(matrix_key),
                        self._stringify_matrix_value(value),
                    )
                    for matrix_key, value in combo.items()
                )
            )
            if combo_key in seen:
                continue
            seen.add(combo_key)
            unique_combinations.append(combo)

        return unique_combinations

    @staticmethod
    def _stringify_matrix_value(value: Any) -> str:
        """組み合わせの比較用に値を文字列化"""
        return repr(value)

    def _build_matrix_job_id(
        self,
        base_job_id: str,
        combo: Dict[str, Any],
        index: int,
        existing_jobs: Dict[str, Dict[str, Any]],
    ) -> str:
        """マトリックス展開されたジョブIDを生成"""
        parts = [base_job_id]
        for key in sorted(combo):
            sanitized_value = self._sanitize_identifier(str(combo[key]))
            parts.append(f"{key}-{sanitized_value}")

        candidate = "__".join(parts)
        if candidate in existing_jobs:
            candidate = f"{candidate}__{index}"
        return candidate

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        """ジョブIDに使用できるよう値をサニタイズ"""
        allowed: List[str] = []
        for char in value:
            if char.isalnum() or char in ("-", "_"):
                allowed.append(char)
            else:
                allowed.append("-")
        sanitized = "".join(allowed)
        return sanitized.strip("-") or "value"

    def strict_validate(self, workflow_data: Dict[str, Any]) -> None:
        """厳密な検証"""
        # 基本検証
        self._validate_basic_structure(workflow_data)

        # イベント検証
        events_value = workflow_data.get("on")
        events_list: List[str]
        if isinstance(events_value, str):
            events_list = [events_value]
        elif isinstance(events_value, dict):
            events_list = []
            for key in cast(Dict[Any, Any], events_value).keys():
                events_list.append(str(key))
        elif isinstance(events_value, list):
            events_list = []
            for item in cast(List[Any], events_value):
                if isinstance(item, str):
                    events_list.append(item)
        else:
            events_list = []

        for event in events_list:
            if event not in self.supported_events:
                raise WorkflowParseError(f"サポートされていないイベント: {event}")

        # 環境変数の検証
        jobs = workflow_data.get("jobs", {})
        for job_id, job_data in jobs.items():
            self._strict_validate_job(job_id, job_data)

    def _strict_validate_job(
        self,
        job_id: str,
        job_data: Dict[str, Any],
    ) -> None:
        """ジョブの厳密な検証"""
        # タイムアウトの確認
        timeout = job_data.get("timeout-minutes")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のタイムアウト値が無効です: {timeout}"
                )

        # 環境変数の確認
        env = job_data.get("env", {})
        if not isinstance(env, dict):
            raise WorkflowParseError(f"ジョブ '{job_id}' の環境変数が無効です")

        # ステップの厳密な検証
        steps = job_data.get("steps", [])
        for i, step in enumerate(steps):
            self._strict_validate_step(job_id, i, step)

    def _strict_validate_step(
        self,
        job_id: str,
        step_index: int,
        step: Dict[str, Any],
    ) -> None:
        """ステップの厳密な検証"""
        # 基本検証
        self._validate_step(job_id, step_index, step)

        # nameの確認（推奨）
        if "name" not in step:
            # 警告として記録（ここでは省略）
            pass

        # 条件式の検証
        if "if" in step:
            condition = step["if"]
            if not isinstance(condition, str):
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のステップ {step_index + 1} の条件式が無効です"
                )

        # usesの場合のバージョン確認
        if "uses" in step:
            uses = step["uses"]
            if not isinstance(uses, str) or not uses.strip():
                raise WorkflowParseError(
                    f"ジョブ '{job_id}' のステップ {step_index + 1} の 'uses' が無効です"
                )

    def get_jobs_summary(
        self,
        workflow_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """ジョブの概要情報を取得"""
        jobs = workflow_data.get("jobs", {})
        summary: List[Dict[str, Any]] = []

        for job_id, job_data in jobs.items():
            summary.append(
                {
                    "id": job_id,
                    "name": job_data.get("name", job_id),
                    "runs_on": job_data.get("runs-on"),
                    "steps_count": len(job_data.get("steps", [])),
                    "timeout_minutes": job_data.get("timeout-minutes"),
                    "needs": job_data.get("needs", []),
                }
            )
        return summary
