"""
GitHub Actions Simulator - Enhanced Act Wrapper
既存のActWrapperを拡張し、診断機能とデッドロック検出メカニズムを統合した
安全なサブプロセス作成と出力ストリーミング機能を提供します。
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from services.actions.act_wrapper import ActWrapper, ActRunnerSettings
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage, ThreadState
from services.actions.logger import ActionsLogger


@dataclass
class DeadlockIndicator:
    """デッドロック指標"""

    indicator_type: str  # "thread_blocked", "process_hung", "output_stalled"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamResult:
    """出力ストリーミング結果"""

    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    threads_completed: bool = False
    deadlock_detected: bool = False
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    stream_duration_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class MonitoredProcess:
    """監視対象プロセス"""

    process: subprocess.Popen
    command: List[str]
    start_time: float
    timeout_seconds: float
    heartbeat_interval: float = 30.0
    last_heartbeat: float = field(default_factory=time.time)
    output_stalled_threshold: float = 60.0  # 出力が停止したと判断する時間（秒）
    last_output_time: float = field(default_factory=time.time)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)


@dataclass
class DetailedResult:
    """詳細な実行結果"""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    command: str
    execution_time_ms: float = 0.0
    diagnostic_results: List[Dict[str, Any]] = field(default_factory=list)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    stream_result: Optional[StreamResult] = None
    hang_analysis: Optional[Dict[str, Any]] = None
    resource_usage: List[Dict[str, Any]] = field(default_factory=list)
    trace_id: Optional[str] = None


class EnhancedActWrapper(ActWrapper):
    """
    診断機能とデッドロック検出メカニズムを統合したActWrapperの拡張版

    主な機能:
    - 詳細な診断情報の収集
    - デッドロック検出と予防
    - 安全なサブプロセス管理
    - 出力ストリーミングの監視
    - ハングアップ分析
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        config: Mapping[str, Any] | None = None,
        logger: ActionsLogger | None = None,
        execution_tracer: Optional[ExecutionTracer] = None,
        enable_diagnostics: bool = True,
        deadlock_detection_interval: float = 10.0,
        output_stall_threshold: float = 60.0,
    ) -> None:
        """
        EnhancedActWrapperを初期化

        Args:
            working_directory: 作業ディレクトリ
            config: 設定情報
            logger: ロガー
            execution_tracer: 実行トレーサー
            enable_diagnostics: 診断機能を有効にするかどうか
            deadlock_detection_interval: デッドロック検出の間隔（秒）
            output_stall_threshold: 出力停止と判断する時間（秒）
        """
        # 親クラスを初期化
        super().__init__(
            working_directory=working_directory,
            config=config,
            logger=logger,
            execution_tracer=execution_tracer,
        )

        self.enable_diagnostics = enable_diagnostics
        self.deadlock_detection_interval = deadlock_detection_interval
        self.output_stall_threshold = output_stall_threshold

        # 診断サービスの初期化（遅延インポートでサイクル依存を回避）
        self._diagnostic_service = None
        if self.enable_diagnostics:
            self._initialize_diagnostic_service()

        # デッドロック検出用の状態管理
        self._active_processes: Dict[int, MonitoredProcess] = {}
        self._monitoring_threads: List[threading.Thread] = []
        self._stop_monitoring = threading.Event()

    def _initialize_diagnostic_service(self) -> None:
        """診断サービスを初期化"""
        try:
            # 遅延インポートでサイクル依存を回避
            import sys
            sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
            from diagnostic_service import DiagnosticService

            self._diagnostic_service = DiagnosticService(logger=self.logger)
            self.logger.debug("診断サービスを初期化しました")
        except (ImportError, ModuleNotFoundError) as e:
            self.logger.warning(f"診断サービスの初期化に失敗しました: {e}")
            self.enable_diagnostics = False
            self._diagnostic_service = None

    def run_workflow_with_diagnostics(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> DetailedResult:
        """
        診断機能付きでワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            DetailedResult: 詳細な実行結果
        """
        start_time = time.time()
        trace_id = f"enhanced_act_{int(start_time * 1000)}"

        # 実行前診断チェック
        diagnostic_results = []
        if self.enable_diagnostics and self._diagnostic_service:
            self.logger.info("実行前診断チェックを開始します...")
            pre_check = self._diagnostic_service.run_comprehensive_health_check()
            diagnostic_results.append({
                "phase": "pre_execution",
                "timestamp": time.time(),
                "results": pre_check
            })

            # 重大な問題がある場合は実行を中止
            if pre_check.get("overall_status") == "ERROR":
                error_msg = f"実行前診断で重大な問題が検出されました: {pre_check.get('summary')}"
                self.logger.error(error_msg)
                return DetailedResult(
                    success=False,
                    returncode=-1,
                    stdout="",
                    stderr=error_msg,
                    command="enhanced-act (診断失敗)",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    diagnostic_results=diagnostic_results,
                    trace_id=trace_id
                )

        try:
            # 通常のワークフロー実行（拡張監視付き）
            result = self._run_workflow_with_enhanced_monitoring(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
                trace_id=trace_id
            )

            # 実行後診断チェック
            if self.enable_diagnostics and self._diagnostic_service:
                self.logger.info("実行後診断チェックを開始します...")
                post_check = self._diagnostic_service.run_comprehensive_health_check()
                diagnostic_results.append({
                    "phase": "post_execution",
                    "timestamp": time.time(),
                    "results": post_check
                })

            # 詳細結果を構築
            execution_time_ms = (time.time() - start_time) * 1000
            detailed_result = DetailedResult(
                success=result.get("success", False),
                returncode=result.get("returncode", -1),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                command=result.get("command", ""),
                execution_time_ms=execution_time_ms,
                diagnostic_results=diagnostic_results,
                trace_id=trace_id
            )

            # ハングアップ分析を追加
            if not result.get("success", False):
                detailed_result.hang_analysis = self._analyze_execution_failure(result)

            return detailed_result

        except Exception as e:
            self.logger.error(f"拡張ワークフロー実行中にエラーが発生しました: {e}")
            return DetailedResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e),
                command="enhanced-act (実行エラー)",
                execution_time_ms=(time.time() - start_time) * 1000,
                diagnostic_results=diagnostic_results,
                trace_id=trace_id
            )

    def _run_workflow_with_enhanced_monitoring(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        拡張監視機能付きでワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数
            trace_id: トレースID

        Returns:
            Dict[str, Any]: 実行結果
        """
        # モックモードの場合は親クラスの実装を使用
        if self._mock_mode:
            return super().run_workflow(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
            )

        # 実行トレースを開始
        if trace_id:
            self.execution_tracer.start_trace(trace_id)

        try:
            # コマンドを構築
            cmd = self._build_enhanced_command(
                workflow_file=workflow_file,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars
            )

            process_env = self._build_process_env(event, env_vars)

            self.logger.info(f"拡張監視付きactコマンド実行: {' '.join(cmd)}")

            # 監視付きサブプロセスを作成
            monitored_process = self._create_monitored_subprocess(
                cmd, process_env, self._timeout_seconds
            )

            # 安全な出力ストリーミングを実行
            stream_result = self._handle_output_streaming_safely(monitored_process)

            # プロセス完了を待機
            return_code = self._wait_for_process_completion(monitored_process)

            # 結果を構築
            stdout_text = "".join(stream_result.stdout_lines)
            stderr_text = "".join(stream_result.stderr_lines)

            success = return_code == 0 and not stream_result.deadlock_detected
            if stream_result.deadlock_detected:
                stderr_text += f"\nデッドロックが検出されました: {len(stream_result.deadlock_indicators)}個の指標"

            return {
                "success": success,
                "returncode": return_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": " ".join(cmd),
                "stream_result": stream_result,
                "deadlock_indicators": stream_result.deadlock_indicators,
            }

        finally:
            # 監視を停止
            self._stop_all_monitoring()

            # トレースを終了
            if trace_id:
                self.execution_tracer.end_trace()

    def _build_enhanced_command(
        self,
        workflow_file: Optional[str] = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        拡張監視用のコマンドを構築

        Args:
            workflow_file: ワークフローファイル
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            List[str]: 構築されたコマンド
        """
        cmd: List[str] = [self.act_binary]
        cmd.extend(self._compose_runner_flags())

        if workflow_file:
            cmd.extend(["-W", workflow_file])
        if job:
            cmd.extend(["-j", job])
        if dry_run:
            cmd.append("--dryrun")
        if verbose:
            cmd.append("--verbose")

        # 拡張監視用のフラグを追加
        cmd.extend(["--rm"])  # コンテナの自動削除

        env_args = self._compose_env_args(env_vars)
        cmd.extend(env_args)

        return cmd

    def _create_monitored_subprocess(
        self, cmd: List[str], env: Dict[str, str], timeout_seconds: float
    ) -> MonitoredProcess:
        """
        監視付きサブプロセスを作成

        Args:
            cmd: 実行コマンド
            env: 環境変数
            timeout_seconds: タイムアウト時間

        Returns:
            MonitoredProcess: 監視対象プロセス
        """
        self.execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)

        try:
            # サブプロセスを作成
            process = subprocess.Popen(
                cmd,
                cwd=self.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,  # プロセスグループを作成
            )

            self.logger.info(f"監視付きプロセス開始: PID={process.pid}")

            # 監視対象プロセスを作成
            monitored_process = MonitoredProcess(
                process=process,
                command=cmd,
                start_time=time.time(),
                timeout_seconds=timeout_seconds,
                heartbeat_interval=30.0,
                output_stalled_threshold=self.output_stall_threshold,
            )

            # プロセス監視に追加
            self._active_processes[process.pid] = monitored_process

            # 実行トレースに追加
            self.execution_tracer.trace_subprocess_execution(
                cmd, process, str(self.working_directory)
            )

            # デッドロック監視スレッドを開始
            self._start_deadlock_monitoring(monitored_process)

            return monitored_process

        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.error(f"監視付きプロセス作成エラー: {exc}")
            self.execution_tracer.set_stage(ExecutionStage.FAILED)
            raise

    def _handle_output_streaming_safely(self, monitored_process: MonitoredProcess) -> StreamResult:
        """
        安全な出力ストリーミングを実行

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            StreamResult: ストリーミング結果
        """
        self.execution_tracer.set_stage(ExecutionStage.OUTPUT_STREAMING)

        start_time = time.time()
        stream_result = StreamResult()

        def _safe_stream_output(
            pipe: Any,
            collector: List[str],
            label: str,
            thread_trace,
        ) -> None:
            """安全な出力ストリーミング関数"""
            try:
                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.RUNNING
                )

                if pipe is None:
                    return

                with pipe:
                    for raw_line in pipe:
                        collector.append(raw_line)
                        line = raw_line.rstrip("\n")
                        if line:
                            # 出力時刻を更新
                            monitored_process.last_output_time = time.time()

                            # 出力を表示
                            print(f"[{label}] {line}")
                            if self.logger.verbose:
                                self.logger.debug(f"[{label}] {line}")

                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.TERMINATED
                )

            except Exception as e:
                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.ERROR, str(e)
                )
                stream_result.error_message = str(e)

        # 出力ストリーミングスレッドを作成
        threads: List[threading.Thread] = []
        thread_traces = []

        process = monitored_process.process

        if process.stdout:
            t_out = threading.Thread(
                target=_safe_stream_output,
                args=(process.stdout, stream_result.stdout_lines, "act stdout", None),
                daemon=True,
                name="EnhancedActWrapper-StdoutStream",
            )
            thread_trace_out = self.execution_tracer.track_thread_lifecycle(
                t_out, "_safe_stream_output"
            )
            # スレッド関数の引数を更新
            t_out = threading.Thread(
                target=_safe_stream_output,
                args=(process.stdout, stream_result.stdout_lines, "act stdout", thread_trace_out),
                daemon=True,
                name="EnhancedActWrapper-StdoutStream",
            )
            t_out.start()
            threads.append(t_out)
            thread_traces.append(thread_trace_out)

        if process.stderr:
            t_err = threading.Thread(
                target=_safe_stream_output,
                args=(process.stderr, stream_result.stderr_lines, "act stderr", None),
                daemon=True,
                name="EnhancedActWrapper-StderrStream",
            )
            thread_trace_err = self.execution_tracer.track_thread_lifecycle(
                t_err, "_safe_stream_output"
            )
            # スレッド関数の引数を更新
            t_err = threading.Thread(
                target=_safe_stream_output,
                args=(process.stderr, stream_result.stderr_lines, "act stderr", thread_trace_err),
                daemon=True,
                name="EnhancedActWrapper-StderrStream",
            )
            t_err.start()
            threads.append(t_err)
            thread_traces.append(thread_trace_err)

        # スレッド完了を待機（タイムアウト付き）
        thread_timeout = 5.0
        for thread in threads:
            thread.join(timeout=thread_timeout)
            if thread.is_alive():
                self.logger.warning(f"出力ストリーミングスレッドがタイムアウトしました: {thread.name}")
                stream_result.deadlock_detected = True
                stream_result.deadlock_indicators.append(
                    DeadlockIndicator(
                        indicator_type="thread_blocked",
                        severity="high",
                        description=f"出力ストリーミングスレッド '{thread.name}' がタイムアウトしました",
                        thread_id=thread.ident,
                    )
                )

        # 結果を更新
        stream_result.threads_completed = all(not t.is_alive() for t in threads)
        stream_result.stdout_bytes = sum(len(line.encode('utf-8')) for line in stream_result.stdout_lines)
        stream_result.stderr_bytes = sum(len(line.encode('utf-8')) for line in stream_result.stderr_lines)
        stream_result.stream_duration_ms = (time.time() - start_time) * 1000

        # デッドロック指標を統合
        stream_result.deadlock_indicators.extend(monitored_process.deadlock_indicators)

        return stream_result

    def _wait_for_process_completion(self, monitored_process: MonitoredProcess) -> int:
        """
        プロセス完了を待機

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            int: 終了コード
        """
        self.execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)

        process = monitored_process.process
        start_time = monitored_process.start_time
        timeout_seconds = monitored_process.timeout_seconds

        while True:
            return_code = process.poll()
            if return_code is not None:
                break

            now = time.time()
            elapsed = now - start_time

            # タイムアウトチェック
            if elapsed >= timeout_seconds:
                self.logger.error(f"プロセス実行がタイムアウトしました (PID: {process.pid})")

                # プロセスを強制終了
                self._force_terminate_process(process)

                # ハングアップ検出
                hang_info = self.execution_tracer.detect_hang_condition(timeout_seconds)
                if hang_info:
                    self.logger.error(f"ハングアップを検出: {hang_info}")

                self.execution_tracer.set_stage(ExecutionStage.TIMEOUT)
                return -1

            # ハートビートログ
            if now >= monitored_process.last_heartbeat + monitored_process.heartbeat_interval:
                process_info = {
                    "pid": process.pid,
                    "elapsed_seconds": int(elapsed),
                    "return_code": process.poll(),
                }
                self.execution_tracer.log_heartbeat(
                    f"拡張監視 - act 実行中... {int(elapsed)} 秒経過 (PID: {process.pid})",
                    process_info,
                )
                monitored_process.last_heartbeat = now

            time.sleep(1)

        # プロセス完了
        if process.poll() is None:
            process.wait()

        return_code = process.returncode or 0

        if return_code != 0:
            self.logger.error(f"act 実行が失敗しました (returncode={return_code})")
            self.execution_tracer.set_stage(ExecutionStage.FAILED)
        else:
            self.execution_tracer.set_stage(ExecutionStage.COMPLETED)

        return return_code

    def _start_deadlock_monitoring(self, monitored_process: MonitoredProcess) -> None:
        """
        デッドロック監視を開始

        Args:
            monitored_process: 監視対象プロセス
        """
        def _deadlock_monitoring_loop():
            """デッドロック監視ループ"""
            while not self._stop_monitoring.is_set():
                try:
                    # デッドロック条件をチェック
                    indicators = self.detect_deadlock_conditions(monitored_process)
                    if indicators:
                        monitored_process.deadlock_indicators.extend(indicators)
                        for indicator in indicators:
                            self.logger.warning(
                                f"デッドロック指標を検出: {indicator.indicator_type} - {indicator.description}"
                            )

                    # 指定間隔で待機
                    self._stop_monitoring.wait(self.deadlock_detection_interval)

                except Exception as e:
                    self.logger.error(f"デッドロック監視中にエラーが発生しました: {e}")
                    time.sleep(1.0)

        # 監視スレッドを開始
        monitor_thread = threading.Thread(
            target=_deadlock_monitoring_loop,
            name=f"DeadlockMonitor-{monitored_process.process.pid}",
            daemon=True,
        )
        monitor_thread.start()
        self._monitoring_threads.append(monitor_thread)

        self.logger.debug(f"デッドロック監視を開始しました: PID {monitored_process.process.pid}")

    def detect_deadlock_conditions(self, monitored_process: MonitoredProcess) -> List[DeadlockIndicator]:
        """
        デッドロック条件を検出

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            List[DeadlockIndicator]: 検出されたデッドロック指標
        """
        indicators = []
        now = time.time()
        process = monitored_process.process

        try:
            # プロセスが応答しているかチェック
            if process.poll() is None:  # プロセスが実行中
                # 出力が長時間停止しているかチェック
                output_stall_time = now - monitored_process.last_output_time
                if output_stall_time > monitored_process.output_stalled_threshold:
                    indicators.append(
                        DeadlockIndicator(
                            indicator_type="output_stalled",
                            severity="medium",
                            description=f"出力が {output_stall_time:.1f} 秒間停止しています",
                            process_id=process.pid,
                            details={"stall_duration": output_stall_time},
                        )
                    )

                # プロセスの実行時間が異常に長いかチェック
                execution_time = now - monitored_process.start_time
                if execution_time > monitored_process.timeout_seconds * 0.8:  # タイムアウトの80%
                    indicators.append(
                        DeadlockIndicator(
                            indicator_type="process_hung",
                            severity="high",
                            description=f"プロセスが {execution_time:.1f} 秒間実行中（タイムアウト間近）",
                            process_id=process.pid,
                            details={"execution_time": execution_time, "timeout": monitored_process.timeout_seconds},
                        )
                    )

        except Exception as e:
            indicators.append(
                DeadlockIndicator(
                    indicator_type="monitoring_error",
                    severity="low",
                    description=f"デッドロック監視中にエラーが発生しました: {str(e)}",
                    process_id=process.pid,
                    details={"error": str(e)},
                )
            )

        return indicators

    def _force_terminate_process(self, process: subprocess.Popen) -> None:
        """
        プロセスを強制終了

        Args:
            process: 終了するプロセス
        """
        try:
            if process.poll() is None:  # プロセスが実行中
                self.logger.warning(f"プロセスを強制終了します: PID {process.pid}")

                # まずSIGTERMを送信
                if hasattr(os, 'killpg') and hasattr(process, 'pid'):
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        time.sleep(2.0)  # 終了を待機
                    except (OSError, ProcessLookupError):
                        pass

                # まだ実行中の場合はSIGKILLを送信
                if process.poll() is None:
                    process.kill()
                    time.sleep(1.0)

                # 最終確認
                if process.poll() is None:
                    self.logger.error(f"プロセスの強制終了に失敗しました: PID {process.pid}")
                else:
                    self.logger.info(f"プロセスを正常に終了しました: PID {process.pid}")

        except Exception as e:
            self.logger.error(f"プロセス強制終了中にエラーが発生しました: {e}")

    def _stop_all_monitoring(self) -> None:
        """すべての監視を停止"""
        self._stop_monitoring.set()

        # 監視スレッドの終了を待機
        for thread in self._monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)

        # アクティブプロセスをクリア
        self._active_processes.clear()
        self._monitoring_threads.clear()
        self._stop_monitoring.clear()

        self.logger.debug("すべての監視を停止しました")

    def _analyze_execution_failure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        実行失敗の分析

        Args:
            result: 実行結果

        Returns:
            Dict[str, Any]: 失敗分析結果
        """
        analysis = {
            "failure_type": "unknown",
            "probable_causes": [],
            "recommendations": [],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        returncode = result.get("returncode", 0)
        stderr = result.get("stderr", "")
        stream_result = result.get("stream_result")

        # 終了コードによる分析
        if returncode == -1:
            analysis["failure_type"] = "timeout"
            analysis["probable_causes"].append("実行タイムアウト")
            analysis["recommendations"].extend([
                "タイムアウト時間を延長してください",
                "ワークフローの複雑さを確認してください",
                "システムリソースを確認してください"
            ])
        elif returncode != 0:
            analysis["failure_type"] = "execution_error"
            analysis["probable_causes"].append(f"act実行エラー (終了コード: {returncode})")

        # デッドロック分析
        if stream_result and stream_result.deadlock_detected:
            analysis["failure_type"] = "deadlock"
            analysis["probable_causes"].append("デッドロック検出")
            analysis["recommendations"].extend([
                "出力ストリーミングの問題を確認してください",
                "プロセス間通信の問題を調査してください"
            ])

        # エラーメッセージ分析
        if "docker" in stderr.lower():
            analysis["probable_causes"].append("Docker関連の問題")
            analysis["recommendations"].extend([
                "Docker daemonが実行されているか確認してください",
                "Docker権限を確認してください"
            ])

        if "permission" in stderr.lower():
            analysis["probable_causes"].append("権限の問題")
            analysis["recommendations"].append("ファイル・ディレクトリの権限を確認してください")

        return analysis

    def force_cleanup_on_timeout(self) -> None:
        """タイムアウト時の強制クリーンアップ"""
        self.logger.warning("タイムアウトによる強制クリーンアップを開始します")

        # すべてのアクティブプロセスを強制終了
        for pid, monitored_process in list(self._active_processes.items()):
            self._force_terminate_process(monitored_process.process)

        # 監視を停止
        self._stop_all_monitoring()

        self.logger.info("強制クリーンアップが完了しました")
