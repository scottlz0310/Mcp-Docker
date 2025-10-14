"""
GitHub Actions Simulator - 実行トレースと監視機能
サブプロセス実行、Docker通信、スレッドライフサイクルを追跡し、
詳細なログとリソース使用量監視を提供します。
"""

from __future__ import annotations

import json
import psutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import ActionsLogger


class ExecutionStage(Enum):
    """実行段階の定義"""

    INITIALIZATION = "initialization"
    SUBPROCESS_CREATION = "subprocess_creation"
    DOCKER_COMMUNICATION = "docker_communication"
    OUTPUT_STREAMING = "output_streaming"
    PROCESS_MONITORING = "process_monitoring"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ThreadState(Enum):
    """スレッドの状態"""

    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class ResourceUsage:
    """リソース使用量の情報"""

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_io_sent_mb: float = 0.0
    network_io_recv_mb: float = 0.0
    open_files: int = 0
    threads_count: int = 0


@dataclass
class DockerOperation:
    """Docker操作の記録"""

    operation_type: str  # "command", "api_call", "socket_access"
    command: Optional[List[str]] = None
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = False
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreadTrace:
    """スレッドのトレース情報"""

    thread_id: int
    thread_name: str
    state: ThreadState
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    target_function: Optional[str] = None
    is_daemon: bool = False
    is_alive: bool = True
    exception: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessTrace:
    """プロセスのトレース情報"""

    command: List[str]
    pid: Optional[int] = None
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    return_code: Optional[int] = None
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    thread_states: Dict[str, ThreadState] = field(default_factory=dict)
    docker_operations: List[DockerOperation] = field(default_factory=list)
    resource_snapshots: List[ResourceUsage] = field(default_factory=list)
    heartbeat_logs: List[str] = field(default_factory=list)
    hang_detected: bool = False
    hang_point: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ExecutionTrace:
    """実行全体のトレース情報"""

    trace_id: str
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    stages: List[ExecutionStage] = field(default_factory=list)
    current_stage: ExecutionStage = ExecutionStage.INITIALIZATION
    hang_point: Optional[str] = None
    resource_usage: List[ResourceUsage] = field(default_factory=list)
    process_traces: List[ProcessTrace] = field(default_factory=list)
    thread_traces: List[ThreadTrace] = field(default_factory=list)
    docker_operations: List[DockerOperation] = field(default_factory=list)
    heartbeat_interval: float = 30.0
    last_heartbeat: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionTracer:
    """
    実行トレースと監視機能を提供するクラス
    サブプロセス実行、Docker通信、スレッドライフサイクルを追跡し、
    ハートビートログとリソース使用量監視を実装します。
    """

    def __init__(
        self,
        logger: Optional[ActionsLogger] = None,
        heartbeat_interval: float = 30.0,
        resource_monitoring_interval: float = 5.0,
        enable_detailed_logging: bool = True,
    ):
        """
        ExecutionTracerを初期化

        Args:
            logger: ログ出力用のロガー
            heartbeat_interval: ハートビートログの間隔（秒）
            resource_monitoring_interval: リソース監視の間隔（秒）
            enable_detailed_logging: 詳細ログを有効にするかどうか
        """
        self.logger = logger or ActionsLogger(verbose=True)
        self.heartbeat_interval = heartbeat_interval
        self.resource_monitoring_interval = resource_monitoring_interval
        self.enable_detailed_logging = enable_detailed_logging

        # 現在のトレース
        self._current_trace: Optional[ExecutionTrace] = None
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._trace_lock = threading.Lock()

        # プロセス監視用
        self._monitored_processes: Dict[int, psutil.Process] = {}
        self._thread_registry: Dict[int, ThreadTrace] = {}

    def start_trace(self, trace_id: Optional[str] = None) -> ExecutionTrace:
        """
        新しい実行トレースを開始

        Args:
            trace_id: トレースID（指定しない場合は自動生成）

        Returns:
            ExecutionTrace: 開始されたトレース
        """
        if trace_id is None:
            trace_id = f"trace_{int(time.time() * 1000)}"

        with self._trace_lock:
            self._current_trace = ExecutionTrace(trace_id=trace_id, heartbeat_interval=self.heartbeat_interval)

        self.logger.info(f"実行トレースを開始しました: {trace_id}")

        # リソース監視スレッドを開始
        self._start_resource_monitoring()

        # 初期リソース使用量を記録
        self._record_resource_usage()

        return self._current_trace

    def end_trace(self) -> Optional[ExecutionTrace]:
        """
        現在の実行トレースを終了

        Returns:
            ExecutionTrace: 終了されたトレース
        """
        with self._trace_lock:
            if self._current_trace is None:
                return None

            self._current_trace.end_time = datetime.now(timezone.utc).isoformat()

            # 実行時間を計算
            start_dt = datetime.fromisoformat(self._current_trace.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self._current_trace.end_time.replace("Z", "+00:00"))
            self._current_trace.duration_ms = (end_dt - start_dt).total_seconds() * 1000

            # 現在のステージを完了に設定
            self._current_trace.current_stage = ExecutionStage.COMPLETED
            if ExecutionStage.COMPLETED not in self._current_trace.stages:
                self._current_trace.stages.append(ExecutionStage.COMPLETED)

            trace = self._current_trace
            self._current_trace = None

        # リソース監視を停止
        self._stop_resource_monitoring()

        self.logger.info(f"実行トレースを終了しました: {trace.trace_id} (実行時間: {trace.duration_ms:.2f}ms)")
        return trace

    def set_stage(self, stage: ExecutionStage, details: Optional[Dict[str, Any]] = None) -> None:
        """
        現在の実行段階を設定

        Args:
            stage: 実行段階
            details: 追加の詳細情報
        """
        with self._trace_lock:
            if self._current_trace is None:
                return

            self._current_trace.current_stage = stage
            if stage not in self._current_trace.stages:
                self._current_trace.stages.append(stage)

            if details:
                self._current_trace.metadata.update(details)

        if self.enable_detailed_logging:
            self.logger.debug(f"実行段階を変更: {stage.value}")

    def trace_subprocess_execution(
        self,
        cmd: List[str],
        process: Optional[subprocess.Popen] = None,
        working_directory: Optional[str] = None,
    ) -> ProcessTrace:
        """
        サブプロセス実行をトレース

        Args:
            cmd: 実行コマンド
            process: サブプロセスオブジェクト
            working_directory: 作業ディレクトリ

        Returns:
            ProcessTrace: プロセストレース情報
        """
        process_trace = ProcessTrace(command=cmd)

        if process:
            process_trace.pid = process.pid

            # プロセス監視に追加
            try:
                psutil_process = psutil.Process(process.pid)
                self._monitored_processes[process.pid] = psutil_process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 現在のトレースに追加
        with self._trace_lock:
            if self._current_trace:
                self._current_trace.process_traces.append(process_trace)

        if self.enable_detailed_logging:
            self.logger.debug(f"サブプロセス実行をトレース開始: {' '.join(cmd)} (PID: {process_trace.pid})")

        return process_trace

    def update_process_trace(
        self,
        process_trace: ProcessTrace,
        return_code: Optional[int] = None,
        stdout_bytes: Optional[int] = None,
        stderr_bytes: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        プロセストレース情報を更新

        Args:
            process_trace: 更新するプロセストレース
            return_code: 終了コード
            stdout_bytes: 標準出力のバイト数
            stderr_bytes: 標準エラーのバイト数
            error_message: エラーメッセージ
        """
        if return_code is not None:
            process_trace.return_code = return_code
            process_trace.end_time = datetime.now(timezone.utc).isoformat()

            # 実行時間を計算
            start_dt = datetime.fromisoformat(process_trace.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(process_trace.end_time.replace("Z", "+00:00"))
            process_trace.duration_ms = (end_dt - start_dt).total_seconds() * 1000

        if stdout_bytes is not None:
            process_trace.stdout_bytes = stdout_bytes

        if stderr_bytes is not None:
            process_trace.stderr_bytes = stderr_bytes

        if error_message is not None:
            process_trace.error_message = error_message

        # プロセス監視から削除
        if process_trace.pid and process_trace.pid in self._monitored_processes:
            del self._monitored_processes[process_trace.pid]

        if self.enable_detailed_logging:
            self.logger.debug(f"プロセストレースを更新: PID {process_trace.pid}, 終了コード: {return_code}")

    def monitor_docker_communication(self, operation_type: str, command: Optional[List[str]] = None) -> DockerOperation:
        """
        Docker通信を監視

        Args:
            operation_type: 操作タイプ
            command: 実行コマンド

        Returns:
            DockerOperation: Docker操作の記録
        """
        docker_op = DockerOperation(operation_type=operation_type, command=command)

        # 現在のトレースに追加
        with self._trace_lock:
            if self._current_trace:
                self._current_trace.docker_operations.append(docker_op)

        if self.enable_detailed_logging:
            cmd_str = " ".join(command) if command else "N/A"
            self.logger.debug(f"Docker通信を監視開始: {operation_type} - {cmd_str}")

        return docker_op

    def update_docker_operation(
        self,
        docker_op: DockerOperation,
        success: bool,
        return_code: Optional[int] = None,
        stdout: str = "",
        stderr: str = "",
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Docker操作の記録を更新

        Args:
            docker_op: 更新するDocker操作
            success: 成功フラグ
            return_code: 終了コード
            stdout: 標準出力
            stderr: 標準エラー
            error_message: エラーメッセージ
            details: 追加の詳細情報
        """
        docker_op.end_time = datetime.now(timezone.utc).isoformat()
        docker_op.success = success
        docker_op.return_code = return_code
        docker_op.stdout = stdout
        docker_op.stderr = stderr
        docker_op.error_message = error_message

        if details:
            docker_op.details.update(details)

        # 実行時間を計算
        start_dt = datetime.fromisoformat(docker_op.start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(docker_op.end_time.replace("Z", "+00:00"))
        docker_op.duration_ms = (end_dt - start_dt).total_seconds() * 1000

        if self.enable_detailed_logging:
            self.logger.debug(
                f"Docker操作を更新: {docker_op.operation_type}, 成功: {success}, 実行時間: {docker_op.duration_ms:.2f}ms"
            )

    def track_thread_lifecycle(self, thread: threading.Thread, target_function: Optional[str] = None) -> ThreadTrace:
        """
        スレッドライフサイクルを追跡

        Args:
            thread: 追跡するスレッド
            target_function: ターゲット関数名

        Returns:
            ThreadTrace: スレッドトレース情報
        """
        thread_trace = ThreadTrace(
            thread_id=thread.ident or 0,
            thread_name=thread.name,
            state=ThreadState.CREATED,
            target_function=target_function,
            is_daemon=thread.daemon,
            is_alive=thread.is_alive(),
        )

        # スレッドレジストリに追加
        if thread.ident:
            self._thread_registry[thread.ident] = thread_trace

        # 現在のトレースに追加
        with self._trace_lock:
            if self._current_trace:
                self._current_trace.thread_traces.append(thread_trace)

        if self.enable_detailed_logging:
            self.logger.debug(f"スレッドライフサイクル追跡開始: {thread.name} (ID: {thread.ident})")

        return thread_trace

    def update_thread_state(
        self,
        thread_trace: ThreadTrace,
        state: ThreadState,
        exception: Optional[str] = None,
    ) -> None:
        """
        スレッドの状態を更新

        Args:
            thread_trace: 更新するスレッドトレース
            state: 新しい状態
            exception: 例外情報
        """
        thread_trace.state = state

        if state == ThreadState.TERMINATED:
            thread_trace.end_time = datetime.now(timezone.utc).isoformat()
            thread_trace.is_alive = False

            # 実行時間を計算
            start_dt = datetime.fromisoformat(thread_trace.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(thread_trace.end_time.replace("Z", "+00:00"))
            thread_trace.duration_ms = (end_dt - start_dt).total_seconds() * 1000

        if exception:
            thread_trace.exception = exception
            thread_trace.state = ThreadState.ERROR

        if self.enable_detailed_logging:
            self.logger.debug(f"スレッド状態を更新: {thread_trace.thread_name} -> {state.value}")

    def log_heartbeat(
        self,
        message: Optional[str] = None,
        process_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        ハートビートログを記録

        Args:
            message: ハートビートメッセージ
            process_info: プロセス情報
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if message is None:
            message = f"ハートビート - {timestamp}"

        # プロセス情報を含める
        if process_info:
            message += f" | プロセス情報: {json.dumps(process_info, ensure_ascii=False)}"

        with self._trace_lock:
            if self._current_trace:
                self._current_trace.last_heartbeat = timestamp
                # 現在のプロセストレースにハートビートを追加
                for process_trace in self._current_trace.process_traces:
                    if process_trace.end_time is None:  # 実行中のプロセスのみ
                        process_trace.heartbeat_logs.append(message)

        self.logger.info(message)

    def detect_hang_condition(self, timeout_seconds: float = 600.0) -> Optional[str]:
        """
        ハングアップ条件を検出

        Args:
            timeout_seconds: タイムアウト時間（秒）

        Returns:
            Optional[str]: ハングアップが検出された場合はその詳細、そうでなければNone
        """
        with self._trace_lock:
            if self._current_trace is None:
                return None

            # 最後のハートビートからの経過時間をチェック
            if self._current_trace.last_heartbeat:
                last_heartbeat_dt = datetime.fromisoformat(self._current_trace.last_heartbeat.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                elapsed = (now - last_heartbeat_dt).total_seconds()

                if elapsed > timeout_seconds:
                    hang_point = f"最後のハートビートから{elapsed:.1f}秒経過 (タイムアウト: {timeout_seconds}秒)"
                    self._current_trace.hang_point = hang_point

                    # 実行中のプロセスにハングフラグを設定
                    for process_trace in self._current_trace.process_traces:
                        if process_trace.end_time is None:
                            process_trace.hang_detected = True
                            process_trace.hang_point = hang_point

                    return hang_point

            # 長時間同じステージに留まっているかチェック
            start_dt = datetime.fromisoformat(self._current_trace.start_time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            total_elapsed = (now - start_dt).total_seconds()

            if total_elapsed > timeout_seconds:
                hang_point = (
                    f"実行開始から{total_elapsed:.1f}秒経過、現在のステージ: {self._current_trace.current_stage.value}"
                )
                self._current_trace.hang_point = hang_point
                return hang_point

        return None

    def get_current_trace(self) -> Optional[ExecutionTrace]:
        """
        現在のトレースを取得

        Returns:
            Optional[ExecutionTrace]: 現在のトレース
        """
        with self._trace_lock:
            return self._current_trace

    def export_trace(self, trace: ExecutionTrace, output_path: Path) -> None:
        """
        トレース情報をファイルにエクスポート

        Args:
            trace: エクスポートするトレース
            output_path: 出力ファイルパス
        """
        try:
            # データクラスを辞書に変換
            trace_dict = self._trace_to_dict(trace)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(trace_dict, f, ensure_ascii=False, indent=2)

            self.logger.info(f"トレース情報をエクスポートしました: {output_path}")

        except Exception as e:
            self.logger.error(f"トレース情報のエクスポートに失敗しました: {e}")

    def _start_resource_monitoring(self) -> None:
        """リソース監視スレッドを開始"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._resource_monitoring_loop,
            name="ExecutionTracer-ResourceMonitor",
            daemon=True,
        )
        self._monitoring_thread.start()

        if self.enable_detailed_logging:
            self.logger.debug("リソース監視スレッドを開始しました")

    def _stop_resource_monitoring(self) -> None:
        """リソース監視スレッドを停止"""
        self._stop_monitoring.set()

        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)

        if self.enable_detailed_logging:
            self.logger.debug("リソース監視スレッドを停止しました")

    def _resource_monitoring_loop(self) -> None:
        """リソース監視のメインループ"""
        last_heartbeat = time.time()

        while not self._stop_monitoring.is_set():
            try:
                # リソース使用量を記録
                self._record_resource_usage()

                # ハートビートログ
                now = time.time()
                if now - last_heartbeat >= self.heartbeat_interval:
                    self._log_monitoring_heartbeat()
                    last_heartbeat = now

                # 監視対象プロセスの状態をチェック
                self._check_monitored_processes()

                # 指定間隔で待機
                self._stop_monitoring.wait(self.resource_monitoring_interval)

            except Exception as e:
                self.logger.error(f"リソース監視中にエラーが発生しました: {e}")
                time.sleep(1.0)

    def _record_resource_usage(self) -> None:
        """現在のリソース使用量を記録"""
        try:
            # システム全体のリソース使用量
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            # 現在のプロセスの情報
            current_process = psutil.Process()
            process_info = current_process.as_dict(["memory_info", "num_threads", "num_fds"])

            resource_usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=memory.used / (1024 * 1024),
                memory_percent=memory.percent,
                disk_io_read_mb=(disk_io.read_bytes / (1024 * 1024)) if disk_io else 0.0,
                disk_io_write_mb=(disk_io.write_bytes / (1024 * 1024)) if disk_io else 0.0,
                network_io_sent_mb=(network_io.bytes_sent / (1024 * 1024)) if network_io else 0.0,
                network_io_recv_mb=(network_io.bytes_recv / (1024 * 1024)) if network_io else 0.0,
                open_files=process_info.get("num_fds", 0),
                threads_count=process_info.get("num_threads", 0),
            )

            with self._trace_lock:
                if self._current_trace:
                    self._current_trace.resource_usage.append(resource_usage)

        except Exception as e:
            if self.enable_detailed_logging:
                self.logger.debug(f"リソース使用量の記録に失敗しました: {e}")

    def _log_monitoring_heartbeat(self) -> None:
        """監視ハートビートログを出力"""
        try:
            # 監視対象プロセスの情報を収集
            process_info = {}
            for pid, process in self._monitored_processes.items():
                try:
                    if process.is_running():
                        process_info[str(pid)] = {
                            "status": process.status(),
                            "cpu_percent": process.cpu_percent(),
                            "memory_mb": process.memory_info().rss / (1024 * 1024),
                            "threads": process.num_threads(),
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_info[str(pid)] = {"status": "terminated"}

            self.log_heartbeat(message="監視ハートビート", process_info=process_info)

        except Exception as e:
            if self.enable_detailed_logging:
                self.logger.debug(f"監視ハートビートログの出力に失敗しました: {e}")

    def _check_monitored_processes(self) -> None:
        """監視対象プロセスの状態をチェック"""
        terminated_pids = []

        for pid, process in self._monitored_processes.items():
            try:
                if not process.is_running():
                    terminated_pids.append(pid)
                    if self.enable_detailed_logging:
                        self.logger.debug(f"監視対象プロセスが終了しました: PID {pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                terminated_pids.append(pid)

        # 終了したプロセスを監視対象から削除
        for pid in terminated_pids:
            del self._monitored_processes[pid]

    def _trace_to_dict(self, trace: ExecutionTrace) -> Dict[str, Any]:
        """ExecutionTraceを辞書に変換"""
        from typing import cast as cast_fn

        def convert_dataclass(obj: Any) -> Any:
            if hasattr(obj, "__dataclass_fields__"):
                result: dict[str, Any] = {}
                for field_name, field_value in obj.__dict__.items():
                    if isinstance(field_value, list):
                        result[field_name] = [convert_dataclass(item) for item in field_value]
                    elif isinstance(field_value, dict):
                        result[field_name] = {k: convert_dataclass(v) for k, v in field_value.items()}
                    elif isinstance(field_value, Enum):
                        result[field_name] = field_value.value
                    else:
                        result[field_name] = field_value
                return result
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj

        return cast_fn(Dict[str, Any], convert_dataclass(trace))
