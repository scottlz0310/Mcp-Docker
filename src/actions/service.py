"""High-level simulation service shared by CLI and API layers."""

from __future__ import annotations

import os
import time
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import logging

from .act_bridge import ActBridgeRunner

# Type checking imports
if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class SimulationParameters:
    """Parameters that control a single simulation run."""

    workflow_file: Path
    job: str | None = None
    dry_run: bool = False
    env_file: Path | None = None
    env_vars: dict[str, str] | None = None
    verbose: bool = False


@dataclass(slots=True)
class SimulationResult:
    """Structured output returned by the simulation service."""

    success: bool
    return_code: int
    engine: str = "act"
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # 拡張診断情報
    execution_time_ms: float = 0.0
    diagnostic_results: list[dict[str, Any]] = field(default_factory=list)
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    execution_trace: dict[str, Any] = field(default_factory=dict)
    bottlenecks_detected: list[dict[str, Any]] = field(default_factory=list)
    optimization_opportunities: list[dict[str, Any]] = field(default_factory=list)
    hang_analysis: dict[str, Any] = field(default_factory=dict)


class SimulationServiceError(Exception):
    """Raised when the simulation service fails to execute a request."""


class SimulationService:
    """Execute workflow simulations via the act CLI."""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        use_act_bridge: bool | None = None,
        act_bridge_config: Mapping[str, Any] | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._config: dict[str, Any] = dict(config) if config else {}
        self._use_act_bridge = self._resolve_use_act_bridge(use_act_bridge)
        self._act_bridge_config: dict[str, Any] = dict(act_bridge_config) if act_bridge_config else {}
        self._act_bridge_runner: ActBridgeRunner | None = None

        if self._use_act_bridge:
            self._act_bridge_runner = ActBridgeRunner(settings=self._act_bridge_config)



    @staticmethod
    def _resolve_use_act_bridge(flag: bool | None) -> bool:
        if flag is not None:
            return flag
        env_value = os.getenv("ACTIONS_USE_ACT_BRIDGE")
        if env_value is None:
            return False
        return env_value.strip().lower() in {"1", "true", "yes", "on"}



    def set_config(self, config: Mapping[str, Any] | None) -> None:
        self._config = dict(config) if config else {}

    def run_simulation(
        self,
        params: SimulationParameters,
        *,
        capture_output: bool = False,
    ) -> SimulationResult:
        """Run the workflow simulation and return a structured result."""
        if self._use_act_bridge and self._act_bridge_runner:
            self._logger.info("act bridge モードを使用します")
            try:
                return self._act_bridge_runner.run(params)
            except NotImplementedError as exc:
                self._logger.debug(f"Act bridge runner は未実装: {exc}")
            except Exception as exc:
                self._logger.warning(f"Act bridge runner の実行に失敗: {exc}")

        stdout_io: StringIO | None = None
        stderr_io: StringIO | None = None

        try:
            with ExitStack() as stack:
                if capture_output:
                    stdout_io = StringIO()
                    stderr_io = StringIO()
                    stack.enter_context(redirect_stdout(stdout_io))
                    stack.enter_context(redirect_stderr(stderr_io))

                try:
                    result = self._run_with_act(params)
                except SimulationServiceError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise SimulationServiceError(f"Unexpected error: {exc}") from exc

            if capture_output:
                extra_stdout = stdout_io.getvalue() if stdout_io else ""
                extra_stderr = stderr_io.getvalue() if stderr_io else ""
                if extra_stdout:
                    result.stdout = f"{extra_stdout}{result.stdout}"
                if extra_stderr:
                    result.stderr = f"{extra_stderr}{result.stderr}"

            return result

        finally:
            pass  # cleanup if needed

    def _run_with_act(
        self,
        params: SimulationParameters,
    ) -> SimulationResult:
        # 簡易実装: act_bridgeに委譲
        raise SimulationServiceError("Legacy wrapper removed. Use act_bridge instead.")

    def _run_pre_execution_diagnostics(self) -> dict[str, Any]:
        """実行前診断チェックを実行"""
        if not self._diagnostic_service:
            return {"overall_status": "SKIPPED", "message": "診断サービスが利用できません"}

        try:
            # システムヘルスチェック
            health_check = self._diagnostic_service.check_system_health()

            # Docker接続性チェック
            docker_check = {}
            if hasattr(self._diagnostic_service, "check_docker_connectivity"):
                docker_result = self._diagnostic_service.check_docker_connectivity()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(docker_result, "status"):
                    docker_check = {
                        "status": docker_result.status.value
                        if hasattr(docker_result.status, "value")
                        else str(docker_result.status),
                        "message": docker_result.message,
                        "details": docker_result.details,
                    }
                else:
                    docker_check = docker_result

            # act バイナリチェック
            act_check = {}
            if hasattr(self._diagnostic_service, "check_act_binary"):
                act_result = self._diagnostic_service.check_act_binary()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(act_result, "status"):
                    act_check = {
                        "status": act_result.status.value
                        if hasattr(act_result.status, "value")
                        else str(act_result.status),
                        "message": act_result.message,
                        "details": act_result.details,
                    }
                else:
                    act_check = act_result

            # 権限チェック
            permission_check = {}
            if hasattr(self._diagnostic_service, "check_container_permissions"):
                permission_result = self._diagnostic_service.check_container_permissions()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(permission_result, "status"):
                    permission_check = {
                        "status": permission_result.status.value
                        if hasattr(permission_result.status, "value")
                        else str(permission_result.status),
                        "message": permission_result.message,
                        "details": permission_result.details,
                    }
                else:
                    permission_check = permission_result

            # 総合判定
            overall_status = "OK"
            issues = []

            # health_checkは辞書形式
            if isinstance(health_check, dict) and health_check.get("status") == "error":
                overall_status = "ERROR"
                issues.append("システムヘルスチェック失敗")

            if docker_check.get("status") == "ERROR":
                overall_status = "ERROR"
                issues.append("Docker接続性チェック失敗")

            if act_check.get("status") == "ERROR":
                overall_status = "ERROR"
                issues.append("actバイナリチェック失敗")

            if permission_check.get("status") == "ERROR":
                overall_status = "ERROR"
                issues.append("権限チェック失敗")

            return {
                "overall_status": overall_status,
                "summary": "; ".join(issues) if issues else "すべてのチェックが正常に完了しました",
                "health_check": health_check,
                "docker_check": docker_check,
                "act_check": act_check,
                "permission_check": permission_check,
                "timestamp": time.time(),
            }

        except Exception as e:
            self._logger.error(f"実行前診断チェック中にエラーが発生しました: {e}")
            return {
                "overall_status": "ERROR",
                "summary": f"診断チェック実行エラー: {str(e)}",
                "error": str(e),
                "timestamp": time.time(),
            }

    def _run_post_execution_diagnostics(self, result: SimulationResult) -> dict[str, Any]:
        """実行後診断チェックを実行"""
        if not self._diagnostic_service:
            return {"overall_status": "SKIPPED", "message": "診断サービスが利用できません"}

        try:
            # システムヘルスチェック
            health_check = self._diagnostic_service.check_system_health()

            # ハングアップ条件の検出
            hangup_check = {}
            if hasattr(self._diagnostic_service, "detect_hangup_conditions"):
                hangup_check = self._diagnostic_service.detect_hangup_conditions()

            # 実行結果の分析
            execution_analysis = {
                "success": result.success,
                "return_code": result.return_code,
                "has_output": bool(result.stdout or result.stderr),
                "enhanced_wrapper_used": result.metadata.get("enhanced_wrapper", False),
            }

            return {
                "overall_status": "OK" if result.success else "WARNING",
                "summary": "実行後診断完了",
                "health_check": health_check,
                "hangup_check": hangup_check,
                "execution_analysis": execution_analysis,
                "timestamp": time.time(),
            }

        except Exception as e:
            self._logger.error(f"実行後診断チェック中にエラーが発生しました: {e}")
            return {
                "overall_status": "ERROR",
                "summary": f"診断チェック実行エラー: {str(e)}",
                "error": str(e),
                "timestamp": time.time(),
            }

    def _enhance_result_with_detailed_reporting(
        self,
        result: SimulationResult,
        start_time: float,
        diagnostic_results: list[dict[str, Any]],
    ) -> SimulationResult:
        """詳細結果レポートで結果を拡張"""
        try:
            execution_time_ms = (time.time() - start_time) * 1000

            # パフォーマンスメトリクスの収集（未実装）
            performance_metrics = {}

            # 実行トレースの収集
            execution_trace = {}

            # ボトルネック分析（未実装）
            bottlenecks_detected = []
            optimization_opportunities = []

            # ハングアップ分析（失敗時のみ）
            hang_analysis = {}
            if not result.success and hasattr(result, "metadata") and result.metadata:
                hang_analysis = result.metadata.get("hang_analysis", {})

            # 拡張結果を作成
            result.execution_time_ms = execution_time_ms
            result.diagnostic_results = diagnostic_results
            result.performance_metrics = performance_metrics
            result.execution_trace = execution_trace
            result.bottlenecks_detected = bottlenecks_detected
            result.optimization_opportunities = optimization_opportunities
            result.hang_analysis = hang_analysis

            # メタデータに詳細情報を追加
            result.metadata.update(
                {
                    "detailed_reporting_enabled": True,
                    "diagnostics_enabled": self._enable_diagnostics,
                    "execution_time_ms": execution_time_ms,
                    "diagnostic_checks_count": len(diagnostic_results),
                }
            )

            self._logger.info(f"詳細結果レポートを生成しました (実行時間: {execution_time_ms:.1f}ms)")

        except Exception as e:
            self._logger.error(f"詳細結果レポートの生成中にエラーが発生しました: {e}")

        return result

    def _create_failed_result(
        self, error_message: str, diagnostic_results: list[dict[str, Any]] | None = None
    ) -> SimulationResult:
        """失敗結果を作成"""
        return SimulationResult(
            success=False,
            return_code=-1,
            engine="act",
            stdout="",
            stderr=error_message,
            metadata={"failure_reason": "pre_execution_diagnostics_failed"},
            diagnostic_results=diagnostic_results or [],
            hang_analysis={"failure_type": "pre_execution_check", "error": error_message},
        )

    def get_simulation_status(self) -> dict[str, Any]:
        """シミュレーションサービスの現在の状態を取得"""
        status = {
            "service_initialized": True,
            "act_bridge_enabled": self._use_act_bridge,
            "config_keys": list(self._config.keys()) if self._config else [],
            "timestamp": time.time(),
        }



        return status
