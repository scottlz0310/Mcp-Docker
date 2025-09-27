"""
GitHub Actions Simulator - 改良されたActWrapper
診断機能、改良されたプロセス管理、デッドロック検出機能を持つ
EnhancedActWrapperクラスを提供します。
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .act_wrapper import ActWrapper
from .diagnostic import DiagnosticService, DiagnosticResult, DiagnosticStatus
from .execution_tracer import ExecutionTracer, ExecutionStage
from .logger import ActionsLogger


class DeadlockType(Enum):
    """デッドロックの種類"""
    STDOUT_THREAD = "stdout_thread"
    STDERR_THREAD = "stderr_thread"
    PROCESS_WAIT = "process_wait"
    DOCKER_COMMUNICATION = "docker_communication"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class DeadlockIndicator:
    """デッドロック検出の指標"""
    deadlock_type: DeadlockType
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    thread_name: Optional[str] = None
    process_pid: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MonitoredProcess:
    """監視対象プロセスの情報"""
    process: subprocess.Popen
    command: List[str]
    start_time: float
    stdout_thread: Optional[threading.Thread] = None
    stderr_thread: Optional[threading.Thread] = None
    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    force_killed: bool = False


@dataclass
class DetailedResult:
    """詳細な実行結果"""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    command: str
    execution_time_ms: float
    diagnostic_results: List[DiagnosticResult] = field(default_factory=list)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    process_monitoring_data: Dict[str, Any] = field(default_factory=dict)
    hang_analysis: Optional[Dict[str, Any]] = None


class ProcessMonitor:
    """
    改良されたプロセス監視とデッドロック検出を行うクラス
    細かいタイムアウト制御、タイムアウトエスカレーション、改良されたハートビートメカニズムを提供
    """

    def __init__(
        self,
        logger: Optional[ActionsLogger] = None,
        deadlock_detection_interval: float = 10.0,
        activity_timeout: float = 60.0,
        warning_timeout: float = 480.0,  # 8分で警告
        escalation_timeout: float = 540.0,  # 9分でエスカレーション
        heartbeat_interval: float = 30.0,
        detailed_logging: bool = True
    ):
        """
        ProcessMonitorを初期化

        Args:
            logger: ログ出力用のロガー
            deadlock_detection_interval: デッドロック検出の間隔（秒）
            activity_timeout: アクティビティタイムアウト（秒）
            warning_timeout: 警告タイムアウト（秒）
            escalation_timeout: エスカレーションタイムアウト（秒）
            heartbeat_interval: ハートビート間隔（秒）
            detailed_logging: 詳細ログを有効にするかどうか
        """
        self.logger = logger or ActionsLogger(verbose=True)
        self.deadlock_detection_interval = deadlock_detection_interval
        self.activity_timeout = activity_timeout
        self.warning_timeout = warning_timeout
        self.escalation_timeout = escalation_timeout
        self.heartbeat_interval = heartbeat_interval
        self.detailed_logging = detailed_logging

        # 監視状態
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # エスカレーション状態
        self._warning_sent = False
        self._escalation_started = False
        self._last_heartbeat = time.time()

        # リソース監視
        self._resource_snapshots: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[str, float] = {}

    def monitor_with_heartbeat(
        self,
        monitored_process: MonitoredProcess,
        timeout: int
    ) -> Tuple[bool, List[DeadlockIndicator]]:
        """
        改良されたハートビートメカニズムでプロセスを監視
        タイムアウトエスカレーション（警告 -> 強制終了）を実装

        Args:
            monitored_process: 監視対象プロセス
            timeout: 最終タイムアウト時間（秒）

        Returns:
            Tuple[bool, List[DeadlockIndicator]]: (タイムアウトフラグ, デッドロック指標リスト)
        """
        self.logger.info(f"改良されたプロセス監視を開始: PID {monitored_process.process.pid}, タイムアウト: {timeout}秒")

        start_time = time.time()
        self._last_heartbeat = start_time

        # タイムアウト段階の設定
        warning_deadline = start_time + self.warning_timeout if self.warning_timeout > 0 else None
        escalation_deadline = start_time + self.escalation_timeout if self.escalation_timeout > 0 else None
        final_deadline = start_time + timeout if timeout > 0 else None

        next_heartbeat = start_time + self.heartbeat_interval
        next_resource_check = start_time + 10.0  # 10秒ごとにリソースチェック

        # 状態をリセット
        self._warning_sent = False
        self._escalation_started = False

        # デッドロック検出スレッドを開始
        self._start_deadlock_detection(monitored_process)

        try:
            while True:
                return_code = monitored_process.process.poll()
                if return_code is not None:
                    elapsed = time.time() - start_time
                    self.logger.info(f"プロセスが正常終了: PID {monitored_process.process.pid}, 終了コード: {return_code}, 実行時間: {elapsed:.2f}秒")
                    break

                now = time.time()
                elapsed = now - start_time

                # タイムアウトエスカレーション処理
                timeout_result = self._handle_timeout_escalation(
                    monitored_process, now, elapsed,
                    warning_deadline, escalation_deadline, final_deadline
                )

                if timeout_result:
                    return timeout_result

                # 改良されたハートビートログ
                if now >= next_heartbeat:
                    self._log_enhanced_heartbeat(monitored_process, elapsed)
                    next_heartbeat = now + self.heartbeat_interval
                    self._last_heartbeat = now

                # リソース使用量チェック
                if now >= next_resource_check:
                    self._check_resource_usage(monitored_process)
                    next_resource_check = now + 10.0

                # デッドロック検出結果をチェック
                if monitored_process.deadlock_indicators:
                    self.logger.warning(f"デッドロックが検出されました: PID {monitored_process.process.pid}")
                    return True, monitored_process.deadlock_indicators

                time.sleep(1)

            return False, monitored_process.deadlock_indicators

        finally:
            # デッドロック検出を停止
            self._stop_deadlock_detection()
            # 最終リソース使用量を記録
            self._record_final_metrics(monitored_process, time.time() - start_time)

    def detect_deadlock_conditions(self, monitored_process: MonitoredProcess) -> List[DeadlockIndicator]:
        """
        デッドロック条件を検出

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            List[DeadlockIndicator]: 検出されたデッドロック指標のリスト
        """
        indicators = []
        now = time.time()

        # スレッドの応答性チェック
        if monitored_process.stdout_thread:
            if not self._is_thread_responsive(monitored_process.stdout_thread):
                indicators.append(DeadlockIndicator(
                    deadlock_type=DeadlockType.STDOUT_THREAD,
                    thread_name=monitored_process.stdout_thread.name,
                    process_pid=monitored_process.process.pid,
                    details={
                        "thread_alive": monitored_process.stdout_thread.is_alive(),
                        "last_activity": monitored_process.last_activity
                    },
                    recommendations=[
                        "標準出力スレッドが応答しません",
                        "プロセスを強制終了することを検討してください"
                    ]
                ))

        if monitored_process.stderr_thread:
            if not self._is_thread_responsive(monitored_process.stderr_thread):
                indicators.append(DeadlockIndicator(
                    deadlock_type=DeadlockType.STDERR_THREAD,
                    thread_name=monitored_process.stderr_thread.name,
                    process_pid=monitored_process.process.pid,
                    details={
                        "thread_alive": monitored_process.stderr_thread.is_alive(),
                        "last_activity": monitored_process.last_activity
                    },
                    recommendations=[
                        "標準エラースレッドが応答しません",
                        "プロセスを強制終了することを検討してください"
                    ]
                ))

        # プロセスの応答性チェック
        if now - monitored_process.last_activity > self.activity_timeout:
            indicators.append(DeadlockIndicator(
                deadlock_type=DeadlockType.PROCESS_WAIT,
                process_pid=monitored_process.process.pid,
                details={
                    "inactive_duration": now - monitored_process.last_activity,
                    "timeout_threshold": self.activity_timeout
                },
                recommendations=[
                    f"プロセスが{self.activity_timeout}秒間非アクティブです",
                    "Docker通信の問題またはリソース不足の可能性があります"
                ]
            ))

        # リソース枯渇の検出
        try:
            import psutil
            process = psutil.Process(monitored_process.process.pid)
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent()

            if memory_percent > 90.0:
                indicators.append(DeadlockIndicator(
                    deadlock_type=DeadlockType.RESOURCE_EXHAUSTION,
                    process_pid=monitored_process.process.pid,
                    details={
                        "memory_percent": memory_percent,
                        "cpu_percent": cpu_percent
                    },
                    severity="HIGH",
                    recommendations=[
                        f"メモリ使用率が異常に高いです: {memory_percent:.1f}%",
                        "メモリリークまたはリソース枯渇の可能性があります"
                    ]
                ))

        except (ImportError, Exception):
            # psutilが利用できない場合はスキップ
            pass

        return indicators

    def force_cleanup_on_timeout(self, monitored_process: MonitoredProcess) -> None:
        """
        改良されたタイムアウト時の強制クリーンアップ
        段階的なプロセス終了とリソース解放を保証

        Args:
            monitored_process: クリーンアップ対象プロセス
        """
        self.logger.warning(f"改良されたプロセス強制クリーンアップを開始: PID {monitored_process.process.pid}")

        cleanup_start = time.time()

        try:
            # ステップ1: 穏やかな終了を試行 (SIGTERM)
            if monitored_process.process.poll() is None:
                self.logger.info("ステップ1: SIGTERMでプロセス終了を試行")
                monitored_process.process.terminate()

                # 5秒待機
                try:
                    monitored_process.process.wait(timeout=5)
                    self.logger.info("プロセスがSIGTERMで正常に終了しました")
                    return
                except subprocess.TimeoutExpired:
                    self.logger.warning("SIGTERM後のタイムアウト、次のステップに進みます")

            # ステップ2: プロセスグループ全体を終了
            if monitored_process.process.poll() is None:
                self.logger.info("ステップ2: プロセスグループの終了を試行")
                try:
                    import os
                    import signal
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(monitored_process.process.pid), signal.SIGTERM)
                        time.sleep(2)

                        if monitored_process.process.poll() is None:
                            os.killpg(os.getpgid(monitored_process.process.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    self.logger.debug("プロセスグループ終了に失敗、個別プロセス終了に進みます")

            # ステップ3: 強制終了 (SIGKILL)
            if monitored_process.process.poll() is None:
                self.logger.warning("ステップ3: SIGKILLでプロセス強制終了")
                monitored_process.process.kill()
                monitored_process.force_killed = True

                # 最終確認
                try:
                    monitored_process.process.wait(timeout=3)
                    self.logger.info("プロセスがSIGKILLで強制終了されました")
                except subprocess.TimeoutExpired:
                    self.logger.error("プロセスの強制終了に失敗しました - ゾンビプロセスの可能性があります")

        except Exception as e:
            self.logger.error(f"プロセスクリーンアップ中にエラーが発生しました: {e}")

        # ステップ4: スレッドとリソースのクリーンアップ
        self.logger.info("ステップ4: スレッドとリソースのクリーンアップ")
        self._cleanup_threads(monitored_process)

        # ステップ5: 出力バッファのクリア
        self._clear_output_buffers(monitored_process)

        cleanup_duration = time.time() - cleanup_start
        self.logger.info(f"プロセスクリーンアップ完了: 実行時間 {cleanup_duration:.2f}秒")

    def _handle_timeout_escalation(
        self,
        monitored_process: MonitoredProcess,
        current_time: float,
        elapsed: float,
        warning_deadline: Optional[float],
        escalation_deadline: Optional[float],
        final_deadline: Optional[float]
    ) -> Optional[Tuple[bool, List[DeadlockIndicator]]]:
        """
        タイムアウトエスカレーション処理

        Args:
            monitored_process: 監視対象プロセス
            current_time: 現在時刻
            elapsed: 経過時間
            warning_deadline: 警告タイムアウト
            escalation_deadline: エスカレーションタイムアウト
            final_deadline: 最終タイムアウト

        Returns:
            Optional[Tuple[bool, List[DeadlockIndicator]]]: タイムアウト時の結果
        """
        # 警告段階
        if warning_deadline and current_time >= warning_deadline and not self._warning_sent:
            self._warning_sent = True
            self.logger.warning(
                f"⚠️  プロセス実行警告: {elapsed:.1f}秒経過 (PID: {monitored_process.process.pid})\n"
                f"   - 警告タイムアウト: {self.warning_timeout}秒\n"
                f"   - 最終タイムアウトまで: {final_deadline - current_time:.1f}秒\n"
                f"   - プロセスが長時間実行されています。Docker通信やリソース不足の可能性があります。"
            )

            # 警告時の詳細診断
            self._perform_warning_diagnostics(monitored_process)

        # エスカレーション段階
        if escalation_deadline and current_time >= escalation_deadline and not self._escalation_started:
            self._escalation_started = True
            self.logger.error(
                f"🚨 プロセス実行エスカレーション: {elapsed:.1f}秒経過 (PID: {monitored_process.process.pid})\n"
                f"   - エスカレーションタイムアウト: {self.escalation_timeout}秒\n"
                f"   - 最終タイムアウトまで: {final_deadline - current_time:.1f}秒\n"
                f"   - 強制終了の準備を開始します。"
            )

            # エスカレーション時の詳細診断
            self._perform_escalation_diagnostics(monitored_process)

        # 最終タイムアウト
        if final_deadline and current_time >= final_deadline:
            self.logger.error(
                f"💀 プロセス実行最終タイムアウト: {elapsed:.1f}秒経過 (PID: {monitored_process.process.pid})\n"
                f"   - プロセスを強制終了します。"
            )
            return True, monitored_process.deadlock_indicators

        return None

    def _log_enhanced_heartbeat(self, monitored_process: MonitoredProcess, elapsed: float) -> None:
        """
        改良されたハートビートログを出力

        Args:
            monitored_process: 監視対象プロセス
            elapsed: 経過時間
        """
        # 基本プロセス情報
        process_info = {
            "pid": monitored_process.process.pid,
            "elapsed_seconds": round(elapsed, 1),
            "return_code": monitored_process.process.poll(),
            "stdout_lines": len(monitored_process.stdout_lines),
            "stderr_lines": len(monitored_process.stderr_lines),
            "deadlock_indicators": len(monitored_process.deadlock_indicators),
            "force_killed": monitored_process.force_killed
        }

        # リソース情報を追加
        try:
            import psutil
            process = psutil.Process(monitored_process.process.pid)
            process_info.update({
                "cpu_percent": round(process.cpu_percent(), 2),
                "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "threads": process.num_threads(),
                "status": process.status()
            })
        except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # 段階的な詳細レベル
        if elapsed < 60:
            # 最初の1分は簡潔に
            self.logger.info(f"💓 プロセス監視: {elapsed:.0f}秒経過 | PID: {process_info['pid']}")
        elif elapsed < 300:
            # 5分まではやや詳細に
            self.logger.info(
                f"💓 プロセス監視: {elapsed:.0f}秒経過 | "
                f"PID: {process_info['pid']} | "
                f"出力: {process_info['stdout_lines']}行"
            )
        else:
            # 5分以降は詳細に
            self.logger.info(
                f"💓 プロセス監視ハートビート: {elapsed:.1f}秒経過\n"
                f"   📊 プロセス情報: {json.dumps(process_info, ensure_ascii=False)}"
            )

        # 長時間実行の場合は追加情報
        if elapsed > 300:  # 5分以上
            self._log_long_running_analysis(monitored_process, elapsed)

    def _check_resource_usage(self, monitored_process: MonitoredProcess) -> None:
        """
        リソース使用量をチェックして異常を検出

        Args:
            monitored_process: 監視対象プロセス
        """
        try:
            import psutil
            process = psutil.Process(monitored_process.process.pid)

            # リソース情報を取得
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = process.memory_percent()

            # スナップショットを保存
            snapshot = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_percent": memory_percent,
                "threads": process.num_threads()
            }
            self._resource_snapshots.append(snapshot)

            # 古いスナップショットを削除（最新20個のみ保持）
            if len(self._resource_snapshots) > 20:
                self._resource_snapshots = self._resource_snapshots[-20:]

            # 異常検出
            if memory_percent > 80.0:
                self.logger.warning(f"⚠️  高メモリ使用量を検出: {memory_percent:.1f}% ({memory_mb:.1f}MB)")

            if cpu_percent > 90.0:
                self.logger.warning(f"⚠️  高CPU使用量を検出: {cpu_percent:.1f}%")

            # メモリリークの検出（過去5分間で50%以上増加）
            if len(self._resource_snapshots) >= 10:
                old_memory = self._resource_snapshots[-10]["memory_mb"]
                if memory_mb > old_memory * 1.5:
                    self.logger.warning(
                        f"⚠️  メモリリークの可能性: {old_memory:.1f}MB → {memory_mb:.1f}MB"
                    )

        except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def _perform_warning_diagnostics(self, monitored_process: MonitoredProcess) -> None:
        """
        警告段階での詳細診断

        Args:
            monitored_process: 監視対象プロセス
        """
        self.logger.info("🔍 警告段階診断を実行中...")

        # スレッド状態の確認
        if monitored_process.stdout_thread:
            self.logger.info(f"   - 標準出力スレッド: {'生存' if monitored_process.stdout_thread.is_alive() else '停止'}")
        if monitored_process.stderr_thread:
            self.logger.info(f"   - 標準エラースレッド: {'生存' if monitored_process.stderr_thread.is_alive() else '停止'}")

        # 最近の出力活動
        recent_stdout = len(monitored_process.stdout_lines)
        recent_stderr = len(monitored_process.stderr_lines)
        self.logger.info(f"   - 出力行数: stdout={recent_stdout}, stderr={recent_stderr}")

        # 最後の活動からの経過時間
        inactive_duration = time.time() - monitored_process.last_activity
        self.logger.info(f"   - 最後の活動からの経過時間: {inactive_duration:.1f}秒")

    def _perform_escalation_diagnostics(self, monitored_process: MonitoredProcess) -> None:
        """
        エスカレーション段階での詳細診断

        Args:
            monitored_process: 監視対象プロセス
        """
        self.logger.error("🚨 エスカレーション段階診断を実行中...")

        # プロセス詳細情報
        try:
            import psutil
            process = psutil.Process(monitored_process.process.pid)

            self.logger.error(f"   - プロセス状態: {process.status()}")
            self.logger.error(f"   - CPU使用率: {process.cpu_percent():.2f}%")
            self.logger.error(f"   - メモリ使用量: {process.memory_info().rss / (1024 * 1024):.2f}MB")
            self.logger.error(f"   - スレッド数: {process.num_threads()}")

            # 子プロセスの確認
            children = process.children(recursive=True)
            if children:
                self.logger.error(f"   - 子プロセス数: {len(children)}")
                for child in children[:5]:  # 最初の5個のみ表示
                    try:
                        self.logger.error(f"     - 子PID {child.pid}: {child.status()}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
            self.logger.error("   - プロセス詳細情報の取得に失敗")

        # デッドロック指標の詳細
        if monitored_process.deadlock_indicators:
            self.logger.error(f"   - デッドロック指標数: {len(monitored_process.deadlock_indicators)}")
            for indicator in monitored_process.deadlock_indicators[-3:]:  # 最新3個
                self.logger.error(f"     - {indicator.deadlock_type.value}: {indicator.details}")

    def _log_long_running_analysis(self, monitored_process: MonitoredProcess, elapsed: float) -> None:
        """
        長時間実行プロセスの分析ログ

        Args:
            monitored_process: 監視対象プロセス
            elapsed: 経過時間
        """
        if self.detailed_logging:
            analysis = []

            # 実行時間の分析
            if elapsed > 600:  # 10分以上
                analysis.append("⏰ 長時間実行中 - Docker通信やネットワークの問題の可能性")
            elif elapsed > 300:  # 5分以上
                analysis.append("⏱️  通常より長い実行時間")

            # 出力活動の分析
            if len(monitored_process.stdout_lines) == 0 and len(monitored_process.stderr_lines) == 0:
                analysis.append("🔇 出力なし - プロセスがハングしている可能性")
            elif time.time() - monitored_process.last_activity > 120:  # 2分間活動なし
                analysis.append("💤 長時間非アクティブ")

            if analysis:
                self.logger.info(f"   📈 長時間実行分析: {'; '.join(analysis)}")

    def _record_final_metrics(self, monitored_process: MonitoredProcess, total_duration: float) -> None:
        """
        最終的なパフォーマンスメトリクスを記録

        Args:
            monitored_process: 監視対象プロセス
            total_duration: 総実行時間
        """
        self._performance_metrics.update({
            "total_duration_seconds": total_duration,
            "stdout_lines_total": len(monitored_process.stdout_lines),
            "stderr_lines_total": len(monitored_process.stderr_lines),
            "deadlock_indicators_count": len(monitored_process.deadlock_indicators),
            "force_killed": monitored_process.force_killed,
            "resource_snapshots_count": len(self._resource_snapshots)
        })

        if self.detailed_logging:
            self.logger.info(
                f"📊 最終パフォーマンスメトリクス: "
                f"{json.dumps(self._performance_metrics, ensure_ascii=False)}"
            )

    def _clear_output_buffers(self, monitored_process: MonitoredProcess) -> None:
        """
        出力バッファをクリア

        Args:
            monitored_process: 監視対象プロセス
        """
        try:
            # パイプが残っている場合はクローズ
            if monitored_process.process.stdout and not monitored_process.process.stdout.closed:
                monitored_process.process.stdout.close()
            if monitored_process.process.stderr and not monitored_process.process.stderr.closed:
                monitored_process.process.stderr.close()

            self.logger.debug("出力バッファをクリアしました")
        except Exception as e:
            self.logger.debug(f"出力バッファクリア中にエラー: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンスメトリクスを取得

        Returns:
            Dict[str, Any]: パフォーマンスメトリクス
        """
        return {
            "performance_metrics": self._performance_metrics.copy(),
            "resource_snapshots": self._resource_snapshots.copy(),
            "monitoring_config": {
                "deadlock_detection_interval": self.deadlock_detection_interval,
                "activity_timeout": self.activity_timeout,
                "warning_timeout": self.warning_timeout,
                "escalation_timeout": self.escalation_timeout,
                "heartbeat_interval": self.heartbeat_interval
            }
        }

    def _start_deadlock_detection(self, monitored_process: MonitoredProcess) -> None:
        """デッドロック検出スレッドを開始"""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._deadlock_detection_loop,
            args=(monitored_process,),
            name="ProcessMonitor-DeadlockDetection",
            daemon=True
        )
        self._monitor_thread.start()

    def _stop_deadlock_detection(self) -> None:
        """デッドロック検出スレッドを停止"""
        self._monitoring_active = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

    def _deadlock_detection_loop(self, monitored_process: MonitoredProcess) -> None:
        """デッドロック検出のメインループ"""
        while self._monitoring_active and not self._stop_event.is_set():
            try:
                # デッドロック条件をチェック
                new_indicators = self.detect_deadlock_conditions(monitored_process)
                monitored_process.deadlock_indicators.extend(new_indicators)

                # 新しいデッドロック指標があればログ出力
                for indicator in new_indicators:
                    self.logger.warning(f"デッドロック指標を検出: {indicator.deadlock_type.value}")

                # 指定間隔で待機
                self._stop_event.wait(self.deadlock_detection_interval)

            except Exception as e:
                self.logger.error(f"デッドロック検出中にエラーが発生しました: {e}")
                time.sleep(1.0)

    def _is_thread_responsive(self, thread: threading.Thread) -> bool:
        """
        スレッドが応答しているかチェック

        Args:
            thread: チェック対象スレッド

        Returns:
            bool: 応答している場合True
        """
        if not thread.is_alive():
            return False

        # 簡単な応答性チェック（実装は簡略化）
        # 実際の実装では、スレッド固有の応答性指標を使用する
        return True

    def _log_heartbeat(self, monitored_process: MonitoredProcess, elapsed_seconds: int) -> None:
        """
        ハートビートログを出力

        Args:
            monitored_process: 監視対象プロセス
            elapsed_seconds: 経過時間（秒）
        """
        process_info = {
            "pid": monitored_process.process.pid,
            "elapsed_seconds": elapsed_seconds,
            "return_code": monitored_process.process.poll(),
            "stdout_lines": len(monitored_process.stdout_lines),
            "stderr_lines": len(monitored_process.stderr_lines),
            "deadlock_indicators": len(monitored_process.deadlock_indicators)
        }

        self.logger.info(f"プロセス監視ハートビート: {elapsed_seconds}秒経過 | {json.dumps(process_info, ensure_ascii=False)}")

    def _cleanup_threads(self, monitored_process: MonitoredProcess) -> None:
        """
        スレッドのクリーンアップ

        Args:
            monitored_process: クリーンアップ対象プロセス
        """
        threads_to_cleanup = []
        if monitored_process.stdout_thread:
            threads_to_cleanup.append(monitored_process.stdout_thread)
        if monitored_process.stderr_thread:
            threads_to_cleanup.append(monitored_process.stderr_thread)

        for thread in threads_to_cleanup:
            if thread.is_alive():
                self.logger.debug(f"スレッドの終了を待機: {thread.name}")
                thread.join(timeout=2.0)
                if thread.is_alive():
                    self.logger.warning(f"スレッドが終了しませんでした: {thread.name}")


class EnhancedActWrapper(ActWrapper):
    """
    診断機能を持つ改良されたActWrapper
    より良いエラーハンドリング、プロセス監視、デッドロック検出機能を提供します。
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[ActionsLogger] = None,
        execution_tracer: Optional[ExecutionTracer] = None,
        diagnostic_service: Optional[DiagnosticService] = None,
        enable_diagnostics: bool = True,
        deadlock_detection_interval: float = 10.0,
        activity_timeout: float = 60.0
    ) -> None:
        """
        EnhancedActWrapperを初期化

        Args:
            working_directory: 作業ディレクトリ
            config: 設定情報
            logger: ログ出力用のロガー
            execution_tracer: 実行トレーサー
            diagnostic_service: 診断サービス
            enable_diagnostics: 診断機能を有効にするかどうか
            deadlock_detection_interval: デッドロック検出の間隔（秒）
            activity_timeout: アクティビティタイムアウト（秒）
        """
        super().__init__(
            working_directory=working_directory,
            config=config,
            logger=logger,
            execution_tracer=execution_tracer
        )

        self.diagnostic_service = diagnostic_service or DiagnosticService(logger=self.logger)
        self.enable_diagnostics = enable_diagnostics
        self.process_monitor = ProcessMonitor(
            logger=self.logger,
            deadlock_detection_interval=deadlock_detection_interval,
            activity_timeout=activity_timeout
        )

    def run_workflow_with_diagnostics(
        self,
        workflow_file: Optional[str] = None,
        event: Optional[str] = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
        pre_execution_diagnostics: bool = True
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
            pre_execution_diagnostics: 実行前診断を行うかどうか

        Returns:
            DetailedResult: 詳細な実行結果
        """
        start_time = time.time()
        diagnostic_results = []

        try:
            # 実行前診断
            if self.enable_diagnostics and pre_execution_diagnostics:
                self.logger.info("実行前診断を開始します...")
                health_report = self.diagnostic_service.run_comprehensive_health_check()
                diagnostic_results.extend(health_report.results)

                # 重大なエラーがある場合は実行を中止
                if health_report.has_errors:
                    error_messages = [
                        result.message for result in health_report.results
                        if result.status == DiagnosticStatus.ERROR
                    ]
                    return DetailedResult(
                        success=False,
                        returncode=-1,
                        stdout="",
                        stderr=f"実行前診断でエラーが検出されました: {'; '.join(error_messages)}",
                        command="診断チェック",
                        execution_time_ms=0.0,
                        diagnostic_results=diagnostic_results
                    )

            # 改良されたプロセス管理で実行
            result = self._run_workflow_with_enhanced_monitoring(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return DetailedResult(
                success=result["success"],
                returncode=result["returncode"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                command=result["command"],
                execution_time_ms=execution_time_ms,
                diagnostic_results=diagnostic_results,
                deadlock_indicators=result.get("deadlock_indicators", []),
                process_monitoring_data=result.get("process_monitoring_data", {}),
                hang_analysis=result.get("hang_analysis")
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"ワークフロー実行中に予期しないエラーが発生しました: {e}")

            return DetailedResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"予期しないエラー: {str(e)}",
                command="不明",
                execution_time_ms=execution_time_ms,
                diagnostic_results=diagnostic_results
            )

    def _run_workflow_with_enhanced_monitoring(
        self,
        workflow_file: Optional[str] = None,
        event: Optional[str] = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        改良された監視機能でワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            Dict[str, Any]: 実行結果
        """
        # モックモードの場合は元の実装を使用
        if self._mock_mode:
            return super().run_workflow(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars
            )

        # 実行トレースを開始
        trace_id = f"enhanced_act_workflow_{int(time.time() * 1000)}"
        self.execution_tracer.start_trace(trace_id)

        try:
            # 初期化段階
            self.execution_tracer.set_stage(ExecutionStage.INITIALIZATION, {
                "workflow_file": workflow_file,
                "job": job,
                "dry_run": dry_run,
                "verbose": verbose,
                "enhanced_monitoring": True
            })

            # コマンドを構築
            cmd = self._build_command(workflow_file, event, job, dry_run, verbose, env_vars)
            process_env = self._build_process_env(event, env_vars)

            self.logger.info(f"改良されたactコマンド実行: {' '.join(cmd)}")

            # 安全なサブプロセス作成
            monitored_process = self._create_monitored_subprocess(cmd, process_env)

            # 出力ストリーミングを安全に処理
            self._handle_output_streaming_safely(monitored_process)

            # プロセス監視とタイムアウト処理
            timed_out, deadlock_indicators = self.process_monitor.monitor_with_heartbeat(
                monitored_process, self._timeout_seconds
            )

            # タイムアウト時の処理
            if timed_out:
                self.logger.error("プロセス実行がタイムアウトまたはデッドロックしました")
                self.process_monitor.force_cleanup_on_timeout(monitored_process)

                # ハングアップ分析
                hang_analysis = self._analyze_hang_condition(monitored_process, deadlock_indicators)

                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "".join(monitored_process.stdout_lines),
                    "stderr": "".join(monitored_process.stderr_lines) or "Execution timeout or deadlock",
                    "command": " ".join(cmd),
                    "deadlock_indicators": deadlock_indicators,
                    "hang_analysis": hang_analysis,
                    "process_monitoring_data": {
                        "force_killed": monitored_process.force_killed,
                        "execution_time": time.time() - monitored_process.start_time
                    }
                }

            # 正常終了の処理
            return_code = monitored_process.process.returncode or 0
            stdout_text = "".join(monitored_process.stdout_lines)
            stderr_text = "".join(monitored_process.stderr_lines)

            if return_code != 0:
                self.logger.error(f"act実行が失敗しました (returncode={return_code})")
                self.execution_tracer.set_stage(ExecutionStage.FAILED)
            else:
                self.execution_tracer.set_stage(ExecutionStage.COMPLETED)

            return {
                "success": return_code == 0,
                "returncode": return_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": " ".join(cmd),
                "deadlock_indicators": deadlock_indicators,
                "process_monitoring_data": {
                    "force_killed": monitored_process.force_killed,
                    "execution_time": time.time() - monitored_process.start_time
                }
            }

        finally:
            # トレースを終了
            final_trace = self.execution_tracer.end_trace()
            if final_trace and self.logger.verbose:
                self.logger.debug(f"改良された実行トレース完了: {final_trace.trace_id}")

    def _build_command(
        self,
        workflow_file: Optional[str],
        event: Optional[str],
        job: Optional[str],
        dry_run: bool,
        verbose: bool,
        env_vars: Optional[Dict[str, str]]
    ) -> List[str]:
        """
        実行コマンドを構築

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            List[str]: 構築されたコマンド
        """
        cmd = [self.act_binary]
        cmd.extend(self._compose_runner_flags())

        if workflow_file:
            cmd.extend(["-W", workflow_file])
        if job:
            cmd.extend(["-j", job])
        if dry_run:
            cmd.append("--dryrun")
        if verbose:
            cmd.append("--verbose")

        env_args = self._compose_env_args(env_vars)
        cmd.extend(env_args)

        return cmd

    def _create_monitored_subprocess(
        self,
        cmd: List[str],
        process_env: Dict[str, str]
    ) -> MonitoredProcess:
        """
        監視対象サブプロセスを安全に作成

        Args:
            cmd: 実行コマンド
            process_env: プロセス環境変数

        Returns:
            MonitoredProcess: 監視対象プロセス

        Raises:
            RuntimeError: プロセス作成に失敗した場合
        """
        self.execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)

        try:
            # プロセスを作成
            process = subprocess.Popen(
                cmd,
                cwd=self.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=process_env,
                # プロセスグループを作成して、子プロセスも含めて制御できるようにする
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            monitored_process = MonitoredProcess(
                process=process,
                command=cmd,
                start_time=time.time()
            )

            # プロセストレースを開始
            self.execution_tracer.trace_subprocess_execution(
                cmd, process, str(self.working_directory)
            )

            self.logger.debug(f"監視対象サブプロセスを作成しました: PID {process.pid}")
            return monitored_process

        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.error(f"サブプロセス作成エラー: {exc}")
            self.execution_tracer.set_stage(ExecutionStage.FAILED)
            raise RuntimeError(f"サブプロセスの作成に失敗しました: {exc}") from exc

    def _handle_output_streaming_safely(self, monitored_process: MonitoredProcess) -> Dict[str, Any]:
        """
        出力ストリーミングを安全に処理

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            Dict[str, Any]: ストリーミング結果
        """
        self.execution_tracer.set_stage(ExecutionStage.OUTPUT_STREAMING)

        def _safe_stream_output(
            pipe: Any,
            collector: List[str],
            label: str,
            monitored_process: MonitoredProcess
        ) -> None:
            """安全な出力ストリーミング関数"""
            try:
                if pipe is None:
                    return

                with pipe:
                    for raw_line in pipe:
                        collector.append(raw_line)
                        monitored_process.last_activity = time.time()

                        line = raw_line.rstrip("\n")
                        if line and self.logger.verbose:
                            self.logger.debug(f"[{label}] {line}")

            except Exception as e:
                self.logger.error(f"出力ストリーミング中にエラーが発生しました ({label}): {e}")
                # エラーをコレクターに記録
                collector.append(f"[ERROR] ストリーミングエラー: {str(e)}\n")

        # 標準出力スレッド
        if monitored_process.process.stdout:
            stdout_thread = threading.Thread(
                target=_safe_stream_output,
                args=(
                    monitored_process.process.stdout,
                    monitored_process.stdout_lines,
                    "act stdout",
                    monitored_process
                ),
                name="EnhancedActWrapper-StdoutStream",
                daemon=True
            )
            stdout_thread.start()
            monitored_process.stdout_thread = stdout_thread

            # スレッドトレースを開始
            self.execution_tracer.track_thread_lifecycle(stdout_thread, "_safe_stream_output")

        # 標準エラースレッド
        if monitored_process.process.stderr:
            stderr_thread = threading.Thread(
                target=_safe_stream_output,
                args=(
                    monitored_process.process.stderr,
                    monitored_process.stderr_lines,
                    "act stderr",
                    monitored_process
                ),
                name="EnhancedActWrapper-StderrStream",
                daemon=True
            )
            stderr_thread.start()
            monitored_process.stderr_thread = stderr_thread

            # スレッドトレースを開始
            self.execution_tracer.track_thread_lifecycle(stderr_thread, "_safe_stream_output")

        return {"stdout_thread_started": monitored_process.stdout_thread is not None,
                "stderr_thread_started": monitored_process.stderr_thread is not None}

    def _analyze_hang_condition(
        self,
        monitored_process: MonitoredProcess,
        deadlock_indicators: List[DeadlockIndicator]
    ) -> Dict[str, Any]:
        """
        ハングアップ条件を分析

        Args:
            monitored_process: 監視対象プロセス
            deadlock_indicators: デッドロック指標

        Returns:
            Dict[str, Any]: ハングアップ分析結果
        """
        analysis = {
            "hang_detected": True,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "process_info": {
                "pid": monitored_process.process.pid,
                "command": " ".join(monitored_process.command),
                "execution_time": time.time() - monitored_process.start_time,
                "force_killed": monitored_process.force_killed
            },
            "deadlock_indicators": [
                {
                    "type": indicator.deadlock_type.value,
                    "detected_at": indicator.detected_at,
                    "severity": indicator.severity,
                    "details": indicator.details,
                    "recommendations": indicator.recommendations
                }
                for indicator in deadlock_indicators
            ],
            "potential_causes": [],
            "recommendations": []
        }

        # 潜在的原因を分析
        if any(indicator.deadlock_type == DeadlockType.DOCKER_COMMUNICATION for indicator in deadlock_indicators):
            analysis["potential_causes"].append("Docker daemon通信の問題")
            analysis["recommendations"].extend([
                "Docker daemonが実行されているか確認してください",
                "Docker socketの権限を確認してください"
            ])

        if any(indicator.deadlock_type in [DeadlockType.STDOUT_THREAD, DeadlockType.STDERR_THREAD]
               for indicator in deadlock_indicators):
            analysis["potential_causes"].append("出力ストリーミングスレッドのデッドロック")
            analysis["recommendations"].extend([
                "出力バッファサイズを確認してください",
                "プロセスの出力量が多すぎる可能性があります"
            ])

        if any(indicator.deadlock_type == DeadlockType.RESOURCE_EXHAUSTION for indicator in deadlock_indicators):
            analysis["potential_causes"].append("システムリソースの枯渇")
            analysis["recommendations"].extend([
                "システムのメモリとCPU使用量を確認してください",
                "不要なプロセスを終了してください"
            ])

        # 診断サービスからの追加分析
        if self.enable_diagnostics:
            try:
                hangup_causes = self.diagnostic_service.identify_hangup_causes()
                analysis["diagnostic_causes"] = hangup_causes
            except Exception as e:
                self.logger.debug(f"診断サービスでのハングアップ分析に失敗しました: {e}")

        return analysis
