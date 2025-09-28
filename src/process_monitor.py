#!/usr/bin/env python3
"""
プロセスモニター - プロセスの監視と管理

このモジュールは指定されたプロセスを監視し、
ハングアップやリソース使用状況を追跡します。
"""

import psutil
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ProcessMetrics:
    """プロセスメトリクス"""

    pid: int
    status: str
    cpu_percent: float
    memory_rss: int
    memory_vms: int
    num_threads: int
    timestamp: float


class ProcessMonitor:
    """プロセス監視クラス"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.monitored_processes: Dict[int, psutil.Process] = {}
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_history: Dict[int, List[ProcessMetrics]] = {}
        self.lock = threading.Lock()

    def start_monitoring(self, pid: int) -> bool:
        """指定されたPIDのプロセス監視を開始"""
        try:
            process = psutil.Process(pid)

            with self.lock:
                self.monitored_processes[pid] = process
                self.metrics_history[pid] = []

            if not self.monitoring_active:
                self.monitoring_active = True
                self.monitor_thread = threading.Thread(
                    target=self._monitor_loop, daemon=True
                )
                self.monitor_thread.start()

            self.logger.info(f"プロセス監視開始: PID {pid}")
            return True

        except psutil.NoSuchProcess:
            self.logger.error(f"プロセスが見つかりません: PID {pid}")
            return False
        except Exception as e:
            self.logger.error(f"プロセス監視開始エラー: {e}")
            return False

    def stop_monitoring(self, pid: Optional[int] = None):
        """プロセス監視を停止"""
        with self.lock:
            if pid is not None:
                # 特定のプロセスの監視を停止
                if pid in self.monitored_processes:
                    del self.monitored_processes[pid]
                    self.logger.info(f"プロセス監視停止: PID {pid}")

                # 監視対象がなくなったら監視を停止
                if not self.monitored_processes:
                    self.monitoring_active = False
            else:
                # 全プロセスの監視を停止
                self.monitored_processes.clear()
                self.monitoring_active = False
                self.logger.info("全プロセス監視停止")

        # スレッドの終了を待機（タイムアウト付き）
        if (
            not self.monitoring_active
            and self.monitor_thread
            and self.monitor_thread.is_alive()
        ):
            self.monitor_thread.join(timeout=2.0)
            if self.monitor_thread.is_alive():
                self.logger.warning("監視スレッドの終了がタイムアウトしました")

    def is_monitoring(self, pid: Optional[int] = None) -> bool:
        """監視状態を確認"""
        if pid is not None:
            return pid in self.monitored_processes
        return self.monitoring_active and len(self.monitored_processes) > 0

    def get_process_status(self, pid: int) -> Dict[str, Any]:
        """プロセスの現在の状態を取得"""
        try:
            if pid not in self.monitored_processes:
                return {"error": f"PID {pid} は監視対象ではありません"}

            process = self.monitored_processes[pid]

            if not process.is_running():
                return {"pid": pid, "status": "terminated", "timestamp": time.time()}

            # プロセス情報を取得
            status = process.status()
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            num_threads = process.num_threads()

            return {
                "pid": pid,
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "num_threads": num_threads,
                "timestamp": time.time(),
            }

        except psutil.NoSuchProcess:
            return {"pid": pid, "status": "not_found", "timestamp": time.time()}
        except Exception as e:
            self.logger.error(f"プロセス状態取得エラー: {e}")
            return {"pid": pid, "error": str(e), "timestamp": time.time()}

    def get_metrics_history(self, pid: int) -> List[Dict[str, Any]]:
        """プロセスのメトリクス履歴を取得"""
        with self.lock:
            if pid not in self.metrics_history:
                return []

            return [
                {
                    "pid": m.pid,
                    "status": m.status,
                    "cpu_percent": m.cpu_percent,
                    "memory_rss": m.memory_rss,
                    "memory_vms": m.memory_vms,
                    "num_threads": m.num_threads,
                    "timestamp": m.timestamp,
                }
                for m in self.metrics_history[pid]
            ]

    def _monitor_loop(self):
        """監視ループ（バックグラウンドスレッド）"""
        while self.monitoring_active:
            try:
                with self.lock:
                    pids_to_remove = []

                    for pid, process in self.monitored_processes.items():
                        try:
                            if not process.is_running():
                                pids_to_remove.append(pid)
                                continue

                            # メトリクスを収集
                            metrics = ProcessMetrics(
                                pid=pid,
                                status=process.status(),
                                cpu_percent=process.cpu_percent(),
                                memory_rss=process.memory_info().rss,
                                memory_vms=process.memory_info().vms,
                                num_threads=process.num_threads(),
                                timestamp=time.time(),
                            )

                            # 履歴に追加（最新100件まで保持）
                            if pid not in self.metrics_history:
                                self.metrics_history[pid] = []

                            self.metrics_history[pid].append(metrics)
                            if len(self.metrics_history[pid]) > 100:
                                self.metrics_history[pid] = self.metrics_history[pid][
                                    -100:
                                ]

                        except psutil.NoSuchProcess:
                            pids_to_remove.append(pid)
                        except Exception as e:
                            self.logger.error(f"プロセス監視エラー PID {pid}: {e}")

                    # 終了したプロセスを削除
                    for pid in pids_to_remove:
                        del self.monitored_processes[pid]

                time.sleep(1)  # 1秒間隔で監視

            except Exception as e:
                self.logger.error(f"監視ループエラー: {e}")
                time.sleep(1)

    def detect_hanging_processes(self) -> List[Dict[str, Any]]:
        """ハングしている可能性のあるプロセスを検出"""
        hanging_processes = []

        with self.lock:
            for pid, history in self.metrics_history.items():
                if len(history) < 5:
                    continue

                recent_metrics = history[-5:]

                # CPU使用率が0%で状態が変わらない場合
                if all(m.cpu_percent == 0 for m in recent_metrics):
                    if all(
                        m.status == recent_metrics[0].status for m in recent_metrics
                    ):
                        hanging_processes.append(
                            {
                                "pid": pid,
                                "reason": "no_cpu_activity",
                                "duration": recent_metrics[-1].timestamp
                                - recent_metrics[0].timestamp,
                                "status": recent_metrics[0].status,
                            }
                        )

        return hanging_processes
