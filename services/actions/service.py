"""High-level simulation service shared by CLI and API layers."""

from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
import time
import sys

from .act_wrapper import ActWrapper
from .enhanced_act_wrapper import EnhancedActWrapper, DetailedResult
from .logger import ActionsLogger

# 遅延インポートでサイクル依存を回避
try:
    sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
    from diagnostic_service import DiagnosticService, DiagnosticResult, DiagnosticStatus
    from execution_tracer import ExecutionTracer
    from performance_monitor import PerformanceMonitor
except ImportError as e:
    DiagnosticService = None
    DiagnosticResult = None
    DiagnosticStatus = None
    ExecutionTracer = None
    PerformanceMonitor = None


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
        logger_factory: Callable[[bool], ActionsLogger] | None = None,
        config: Mapping[str, Any] | None = None,
        execution_tracer: Optional[ExecutionTracer] = None,
        use_enhanced_wrapper: bool = False,
        enable_diagnostics: bool = False,
        enable_performance_monitoring: bool = False,
        diagnostic_service: Optional[DiagnosticService] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        pre_execution_diagnostics: bool = True,
        detailed_result_reporting: bool = True,
    ) -> None:
        self._logger_factory: Callable[[bool], ActionsLogger] = (
            logger_factory or self._default_logger_factory
        )
        self._config: dict[str, Any] = dict(config) if config else {}
        self._execution_tracer = execution_tracer
        self._use_enhanced_wrapper = use_enhanced_wrapper
        self._enable_diagnostics = enable_diagnostics
        self._enable_performance_monitoring = enable_performance_monitoring
        self._diagnostic_service = diagnostic_service
        self._performance_monitor = performance_monitor
        self._pre_execution_diagnostics = pre_execution_diagnostics
        self._detailed_result_reporting = detailed_result_reporting

        # 診断サービスとパフォーマンス監視の初期化
        self._initialize_services()

    @staticmethod
    def _default_logger_factory(verbose: bool) -> ActionsLogger:
        return ActionsLogger(verbose=verbose)

    def _initialize_services(self) -> None:
        """診断サービスとパフォーマンス監視を初期化"""
        logger = self._logger_factory(False)

        # 診断サービスの初期化
        if self._enable_diagnostics and DiagnosticService and not self._diagnostic_service:
            try:
                self._diagnostic_service = DiagnosticService(logger=logger)
                logger.debug("診断サービスを初期化しました")
            except Exception as e:
                logger.warning(f"診断サービスの初期化に失敗しました: {e}")
                self._enable_diagnostics = False

        # パフォーマンス監視の初期化
        if self._enable_performance_monitoring and PerformanceMonitor and not self._performance_monitor:
            try:
                self._performance_monitor = PerformanceMonitor(logger=logger)
                logger.debug("パフォーマンス監視を初期化しました")
            except Exception as e:
                logger.warning(f"パフォーマンス監視の初期化に失敗しました: {e}")
                self._enable_performance_monitoring = False

        # 実行トレーサーの初期化
        if ExecutionTracer and not self._execution_tracer:
            try:
                self._execution_tracer = ExecutionTracer(logger=logger)
                logger.debug("実行トレーサーを初期化しました")
            except Exception as e:
                logger.warning(f"実行トレーサーの初期化に失敗しました: {e}")
                self._execution_tracer = None

    def set_config(self, config: Mapping[str, Any] | None) -> None:
        self._config = dict(config) if config else {}

    def run_simulation(
        self,
        params: SimulationParameters,
        *,
        logger: ActionsLogger | None = None,
        capture_output: bool = False,
    ) -> SimulationResult:
        """Run the workflow simulation and return a structured result."""
        start_time = time.time()
        runner_logger = logger or self._logger_factory(params.verbose)

        # 実行前診断チェック
        pre_execution_results = []
        if self._pre_execution_diagnostics and self._enable_diagnostics and self._diagnostic_service:
            runner_logger.info("実行前診断チェックを開始します...")
            try:
                pre_check = self._run_pre_execution_diagnostics(runner_logger)
                pre_execution_results.append({
                    "phase": "pre_execution",
                    "timestamp": time.time(),
                    "results": pre_check
                })

                # 重大な問題がある場合は実行を中止
                if pre_check.get("overall_status") == "ERROR":
                    error_msg = f"実行前診断で重大な問題が検出されました: {pre_check.get('summary', '不明なエラー')}"
                    runner_logger.error(error_msg)
                    return self._create_failed_result(
                        error_msg,
                        start_time,
                        diagnostic_results=pre_execution_results
                    )
            except Exception as e:
                runner_logger.warning(f"実行前診断チェックでエラーが発生しました: {e}")

        # パフォーマンス監視を開始
        if self._enable_performance_monitoring and self._performance_monitor:
            try:
                self._performance_monitor.start_monitoring("workflow_execution")
                runner_logger.debug("パフォーマンス監視を開始しました")
            except Exception as e:
                runner_logger.warning(f"パフォーマンス監視の開始に失敗しました: {e}")

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
                    result = self._run_with_act(params, runner_logger)
                except SimulationServiceError:
                    raise
                except Exception as exc:  # noqa: BLE001 - defensive
                    raise SimulationServiceError(f"Unexpected error: {exc}") from exc

            if capture_output:
                extra_stdout = stdout_io.getvalue() if stdout_io else ""
                extra_stderr = stderr_io.getvalue() if stderr_io else ""
                if extra_stdout:
                    result.stdout = f"{extra_stdout}{result.stdout}"
                if extra_stderr:
                    result.stderr = f"{extra_stderr}{result.stderr}"

            # 実行後診断チェック
            post_execution_results = []
            if self._enable_diagnostics and self._diagnostic_service:
                try:
                    post_check = self._run_post_execution_diagnostics(runner_logger, result)
                    post_execution_results.append({
                        "phase": "post_execution",
                        "timestamp": time.time(),
                        "results": post_check
                    })
                except Exception as e:
                    runner_logger.warning(f"実行後診断チェックでエラーが発生しました: {e}")

            # 詳細結果レポートの生成
            if self._detailed_result_reporting:
                result = self._enhance_result_with_detailed_reporting(
                    result,
                    start_time,
                    pre_execution_results + post_execution_results,
                    runner_logger
                )

            return result

        finally:
            # パフォーマンス監視を停止
            if self._enable_performance_monitoring and self._performance_monitor:
                try:
                    self._performance_monitor.stop_monitoring()
                    runner_logger.debug("パフォーマンス監視を停止しました")
                except Exception as e:
                    runner_logger.warning(f"パフォーマンス監視の停止に失敗しました: {e}")

    def _run_with_act(
        self,
        params: SimulationParameters,
        logger: ActionsLogger,
    ) -> SimulationResult:
        workflow_path = params.workflow_file

        if not workflow_path.exists():
            raise SimulationServiceError(
                f"ワークフローファイルが見つかりません: {workflow_path}"
            )

        env_vars: dict[str, str] | None = None
        if params.env_file:
            if params.env_file.exists():
                env_vars = _load_env_file_as_dict(params.env_file, logger)
            else:
                logger.warning(f"環境変数ファイルが見つかりません: {params.env_file}")

        if params.env_vars:
            env_vars = {**(env_vars or {}), **params.env_vars}

        # ExecutionTracerを作成（まだ存在しない場合）
        tracer = self._execution_tracer or ExecutionTracer(logger=logger)

        # EnhancedActWrapperまたは通常のActWrapperを選択
        if self._use_enhanced_wrapper:
            wrapper_factory = EnhancedActWrapper
            wrapper_kwargs = {
                "working_directory": str(workflow_path.parent),
                "config": self._config,
                "logger": logger,
                "execution_tracer": tracer,
                "enable_diagnostics": self._enable_diagnostics,
            }
        else:
            wrapper_factory = ActWrapper
            wrapper_kwargs = {
                "working_directory": str(workflow_path.parent),
                "config": self._config,
                "logger": logger,
                "execution_tracer": tracer,
            }

        try:
            wrapper = wrapper_factory(**wrapper_kwargs)
        except TypeError:
            try:
                wrapper = wrapper_factory(str(workflow_path.parent))
            except Exception as exc:  # pragma: no cover - defensive
                raise SimulationServiceError(str(exc)) from exc
            if hasattr(wrapper, "config"):
                setattr(wrapper, "config", self._config)
            if hasattr(wrapper, "logger"):
                setattr(wrapper, "logger", logger)
            if hasattr(wrapper, "execution_tracer"):
                setattr(
                    wrapper,
                    "execution_tracer",
                    self._execution_tracer or ExecutionTracer(logger=logger),
                )
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc)) from exc

        # EnhancedActWrapperの場合は診断機能付きメソッドを使用
        if self._use_enhanced_wrapper and hasattr(wrapper, "run_workflow_with_diagnostics"):
            detailed_result = wrapper.run_workflow_with_diagnostics(
                workflow_file=workflow_path.name,
                job=params.job,
                dry_run=params.dry_run,
                verbose=params.verbose,
                env_vars=env_vars,
            )

            # DetailedResultをSimulationResultに変換
            result = {
                "success": detailed_result.success,
                "returncode": detailed_result.returncode,
                "stdout": detailed_result.stdout,
                "stderr": detailed_result.stderr,
                "command": detailed_result.command,
            }

            # 追加の診断情報をメタデータに含める
            metadata = {
                "command": detailed_result.command,
                "execution_time_ms": detailed_result.execution_time_ms,
                "enhanced_wrapper": True,
                "trace_id": detailed_result.trace_id,
            }

            # 診断結果の統合
            if detailed_result.diagnostic_results:
                metadata["wrapper_diagnostic_results"] = detailed_result.diagnostic_results

            # デッドロック指標の統合
            if detailed_result.deadlock_indicators:
                metadata["deadlock_indicators"] = [
                    {
                        "type": di.indicator_type,
                        "severity": di.severity,
                        "description": di.description,
                        "detected_at": di.detected_at,
                        "details": di.details,
                    }
                    for di in detailed_result.deadlock_indicators
                ]

            # ハングアップ分析の統合
            if detailed_result.hang_analysis:
                metadata["hang_analysis"] = detailed_result.hang_analysis

            # ストリーム結果の統合
            if detailed_result.stream_result:
                stream_result = detailed_result.stream_result
                metadata["stream_analysis"] = {
                    "stdout_bytes": stream_result.stdout_bytes,
                    "stderr_bytes": stream_result.stderr_bytes,
                    "threads_completed": stream_result.threads_completed,
                    "deadlock_detected": stream_result.deadlock_detected,
                    "stream_duration_ms": stream_result.stream_duration_ms,
                    "error_message": stream_result.error_message,
                }

            # リソース使用量の統合
            if detailed_result.resource_usage:
                metadata["resource_usage"] = detailed_result.resource_usage

        else:
            # 通常のActWrapperを使用
            result = wrapper.run_workflow(
                workflow_file=workflow_path.name,
                job=params.job,
                dry_run=params.dry_run,
                verbose=params.verbose,
                env_vars=env_vars,
            )
            metadata = {"command": result.get("command"), "enhanced_wrapper": False}

        success = bool(result.get("success"))
        return_code = int(result.get("returncode", 1))
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        if success:
            logger.success("act でのワークフロー実行が完了しました ✓")
        else:
            logger.error(f"act 実行が失敗しました (returncode={return_code})")

        return SimulationResult(
            success=success,
            return_code=return_code,
            engine="act",
            stdout=stdout,
            stderr=stderr,
            metadata=metadata,
        )

    def _run_pre_execution_diagnostics(self, logger: ActionsLogger) -> dict[str, Any]:
        """実行前診断チェックを実行"""
        if not self._diagnostic_service:
            return {"overall_status": "SKIPPED", "message": "診断サービスが利用できません"}

        try:
            # システムヘルスチェック
            health_check = self._diagnostic_service.check_system_health()

            # Docker接続性チェック
            docker_check = {}
            if hasattr(self._diagnostic_service, 'check_docker_connectivity'):
                docker_result = self._diagnostic_service.check_docker_connectivity()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(docker_result, 'status'):
                    docker_check = {
                        "status": docker_result.status.value if hasattr(docker_result.status, 'value') else str(docker_result.status),
                        "message": docker_result.message,
                        "details": docker_result.details
                    }
                else:
                    docker_check = docker_result

            # act バイナリチェック
            act_check = {}
            if hasattr(self._diagnostic_service, 'check_act_binary'):
                act_result = self._diagnostic_service.check_act_binary()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(act_result, 'status'):
                    act_check = {
                        "status": act_result.status.value if hasattr(act_result.status, 'value') else str(act_result.status),
                        "message": act_result.message,
                        "details": act_result.details
                    }
                else:
                    act_check = act_result

            # 権限チェック
            permission_check = {}
            if hasattr(self._diagnostic_service, 'check_container_permissions'):
                permission_result = self._diagnostic_service.check_container_permissions()
                # DiagnosticResultオブジェクトの場合は辞書に変換
                if hasattr(permission_result, 'status'):
                    permission_check = {
                        "status": permission_result.status.value if hasattr(permission_result.status, 'value') else str(permission_result.status),
                        "message": permission_result.message,
                        "details": permission_result.details
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
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"実行前診断チェック中にエラーが発生しました: {e}")
            return {
                "overall_status": "ERROR",
                "summary": f"診断チェック実行エラー: {str(e)}",
                "error": str(e),
                "timestamp": time.time()
            }

    def _run_post_execution_diagnostics(self, logger: ActionsLogger, result: SimulationResult) -> dict[str, Any]:
        """実行後診断チェックを実行"""
        if not self._diagnostic_service:
            return {"overall_status": "SKIPPED", "message": "診断サービスが利用できません"}

        try:
            # システムヘルスチェック
            health_check = self._diagnostic_service.check_system_health()

            # ハングアップ条件の検出
            hangup_check = {}
            if hasattr(self._diagnostic_service, 'detect_hangup_conditions'):
                hangup_check = self._diagnostic_service.detect_hangup_conditions()

            # 実行結果の分析
            execution_analysis = {
                "success": result.success,
                "return_code": result.return_code,
                "has_output": bool(result.stdout or result.stderr),
                "enhanced_wrapper_used": result.metadata.get("enhanced_wrapper", False)
            }

            return {
                "overall_status": "OK" if result.success else "WARNING",
                "summary": "実行後診断完了",
                "health_check": health_check,
                "hangup_check": hangup_check,
                "execution_analysis": execution_analysis,
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"実行後診断チェック中にエラーが発生しました: {e}")
            return {
                "overall_status": "ERROR",
                "summary": f"診断チェック実行エラー: {str(e)}",
                "error": str(e),
                "timestamp": time.time()
            }

    def _enhance_result_with_detailed_reporting(
        self,
        result: SimulationResult,
        start_time: float,
        diagnostic_results: list[dict[str, Any]],
        logger: ActionsLogger
    ) -> SimulationResult:
        """詳細結果レポートで結果を拡張"""
        try:
            execution_time_ms = (time.time() - start_time) * 1000

            # パフォーマンスメトリクスの収集
            performance_metrics = {}
            if self._enable_performance_monitoring and self._performance_monitor:
                try:
                    performance_metrics = self._performance_monitor.get_summary_metrics()
                except Exception as e:
                    logger.warning(f"パフォーマンスメトリクスの取得に失敗しました: {e}")

            # 実行トレースの収集
            execution_trace = {}
            if self._execution_tracer:
                try:
                    execution_trace = self._execution_tracer.get_trace_summary()
                except Exception as e:
                    logger.warning(f"実行トレースの取得に失敗しました: {e}")

            # ボトルネック分析
            bottlenecks_detected = []
            optimization_opportunities = []
            if self._enable_performance_monitoring and self._performance_monitor:
                try:
                    if hasattr(self._performance_monitor, 'analyze_bottlenecks'):
                        bottlenecks = self._performance_monitor.analyze_bottlenecks()
                        bottlenecks_detected = [
                            {
                                "type": b.bottleneck_type,
                                "severity": b.severity,
                                "description": b.description,
                                "recommendations": b.recommendations
                            } for b in bottlenecks
                        ]

                    if hasattr(self._performance_monitor, 'identify_optimization_opportunities'):
                        opportunities = self._performance_monitor.identify_optimization_opportunities()
                        optimization_opportunities = [
                            {
                                "type": o.opportunity_type,
                                "priority": o.priority,
                                "title": o.title,
                                "description": o.description,
                                "recommendations": o.recommendations
                            } for o in opportunities
                        ]
                except Exception as e:
                    logger.warning(f"ボトルネック分析に失敗しました: {e}")

            # ハングアップ分析（失敗時のみ）
            hang_analysis = {}
            if not result.success and hasattr(result, 'metadata') and result.metadata:
                hang_analysis = result.metadata.get('hang_analysis', {})

            # 拡張結果を作成
            result.execution_time_ms = execution_time_ms
            result.diagnostic_results = diagnostic_results
            result.performance_metrics = performance_metrics
            result.execution_trace = execution_trace
            result.bottlenecks_detected = bottlenecks_detected
            result.optimization_opportunities = optimization_opportunities
            result.hang_analysis = hang_analysis

            # メタデータに詳細情報を追加
            result.metadata.update({
                "detailed_reporting_enabled": True,
                "diagnostics_enabled": self._enable_diagnostics,
                "performance_monitoring_enabled": self._enable_performance_monitoring,
                "execution_time_ms": execution_time_ms,
                "diagnostic_checks_count": len(diagnostic_results),
                "bottlenecks_count": len(bottlenecks_detected),
                "optimization_opportunities_count": len(optimization_opportunities)
            })

            logger.info(f"詳細結果レポートを生成しました (実行時間: {execution_time_ms:.1f}ms)")

        except Exception as e:
            logger.error(f"詳細結果レポートの生成中にエラーが発生しました: {e}")

        return result

    def _create_failed_result(
        self,
        error_message: str,
        start_time: float,
        diagnostic_results: list[dict[str, Any]] = None
    ) -> SimulationResult:
        """失敗結果を作成"""
        execution_time_ms = (time.time() - start_time) * 1000

        return SimulationResult(
            success=False,
            return_code=-1,
            engine="act",
            stdout="",
            stderr=error_message,
            metadata={
                "enhanced_wrapper": self._use_enhanced_wrapper,
                "diagnostics_enabled": self._enable_diagnostics,
                "failure_reason": "pre_execution_diagnostics_failed"
            },
            execution_time_ms=execution_time_ms,
            diagnostic_results=diagnostic_results or [],
            performance_metrics={},
            execution_trace={},
            bottlenecks_detected=[],
            optimization_opportunities=[],
            hang_analysis={"failure_type": "pre_execution_check", "error": error_message}
        )


    def get_simulation_status(self) -> dict[str, Any]:
        """シミュレーションサービスの現在の状態を取得"""
        status = {
            "service_initialized": True,
            "enhanced_wrapper_enabled": self._use_enhanced_wrapper,
            "diagnostics_enabled": self._enable_diagnostics,
            "performance_monitoring_enabled": self._enable_performance_monitoring,
            "pre_execution_diagnostics_enabled": self._pre_execution_diagnostics,
            "detailed_result_reporting_enabled": self._detailed_result_reporting,
            "components": {
                "diagnostic_service": self._diagnostic_service is not None,
                "performance_monitor": self._performance_monitor is not None,
                "execution_tracer": self._execution_tracer is not None,
            },
            "config_keys": list(self._config.keys()) if self._config else [],
            "timestamp": time.time()
        }

        # 診断サービスの状態
        if self._diagnostic_service:
            try:
                health = self._diagnostic_service.check_system_health()
                status["system_health"] = health
            except Exception as e:
                status["system_health"] = {"error": str(e)}

        # パフォーマンス監視の状態
        if self._performance_monitor:
            try:
                status["performance_monitor_active"] = getattr(
                    self._performance_monitor, 'monitoring_active', False
                )
            except Exception as e:
                status["performance_monitor_error"] = str(e)

        return status

    def enable_enhanced_features(
        self,
        enable_diagnostics: bool = True,
        enable_performance_monitoring: bool = True,
        enable_detailed_reporting: bool = True
    ) -> None:
        """拡張機能を有効化"""
        self._use_enhanced_wrapper = True
        self._enable_diagnostics = enable_diagnostics
        self._enable_performance_monitoring = enable_performance_monitoring
        self._detailed_result_reporting = enable_detailed_reporting
        self._pre_execution_diagnostics = enable_diagnostics

        # サービスを再初期化
        self._initialize_services()


def _load_env_file_as_dict(
    env_file: Path,
    logger: ActionsLogger,
) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    try:
        with env_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    logger.warning(
                        f"環境変数ファイルの形式が無効です (無視します): {line}"
                    )
                    continue
                key, value = line.split("=", 1)
                env_vars[key] = value
    except OSError as exc:
        logger.error(f"環境変数ファイルの読み込みに失敗しました: {exc}")

    return env_vars
