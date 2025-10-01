#!/usr/bin/env python3
"""
実行トレーサー - 実行フローの追跡と分析

このモジュールは実行フローを追跡し、
パフォーマンスメトリクスとデバッグ情報を収集します。
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class TraceEvent:
    """トレースイベント"""

    event: str
    timestamp: float
    thread_id: int
    data: Dict[str, Any]
    duration: Optional[float] = None


class ExecutionTracer:
    """実行トレーサークラス"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.tracing_active = False
        self.events: List[TraceEvent] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.lock = threading.Lock()
        self.event_counters = defaultdict(int)
        self.performance_metrics = {}

    def start_trace(self, trace_id: Optional[str] = None):
        """トレースを開始"""
        with self.lock:
            self.tracing_active = True
            self.start_time = time.time()
            self.end_time = None
            self.events.clear()
            self.event_counters.clear()
            self.performance_metrics.clear()
        # trace_idは互換性のために受け取るが、この実装では使用しない
        self.record_event(
            "trace_started",
            {"start_time": self.start_time, "thread_id": threading.get_ident()},
        )
        self.logger.info("実行トレース開始")
        return self

    def stop_trace(self):
        """トレースを停止"""
        with self.lock:
            if not self.tracing_active:
                return

            self.end_time = time.time()
            self.tracing_active = False

            self.record_event(
                "trace_stopped",
                {
                    "end_time": self.end_time,
                    "duration": self.end_time - self.start_time if self.start_time else 0,
                    "total_events": len(self.events),
                },
            )

            self._calculate_performance_metrics()
            self.logger.info(f"実行トレース停止 - 総イベント数: {len(self.events)}")

    def end_trace(self):
        """トレースを終了（stop_traceのエイリアス）"""
        self.stop_trace()
        return self

    def set_stage(self, stage, details=None):
        """実行段階を設定（互換性のため）"""
        self.record_event("stage_change", {"stage": str(stage), "details": details})

    def monitor_docker_communication(self, operation_type, command=None, success=True, error_message=None):
        """Docker通信を監視（互換性のため）"""
        self.record_event(
            "docker_communication",
            {
                "operation_type": operation_type,
                "command": command,
                "success": success,
                "error_message": error_message,
            },
        )
        # 互換性のため、ダミーオブジェクトを返す
        return self

    def trace_subprocess_execution(self, cmd, process=None, working_directory=None):
        """サブプロセス実行をトレース（互換性のため）"""
        self.record_event(
            "subprocess_execution",
            {
                "command": cmd,
                "pid": process.pid if process else None,
                "working_directory": working_directory,
            },
        )
        # 互換性のため、ダミーオブジェクトを返す
        return self

    def track_thread_lifecycle(self, thread, target_function=None):
        """スレッドライフサイクルを追跡（互換性のため）"""
        self.record_event(
            "thread_lifecycle",
            {
                "thread_id": thread.ident if thread else None,
                "thread_name": thread.name if thread else None,
                "target_function": target_function,
            },
        )
        # 互換性のため、ダミーオブジェクトを返す
        return self

    def update_process_trace(self, process_trace, **kwargs):
        """プロセストレースを更新（互換性のため）"""
        self.record_event("process_trace_update", kwargs)
        return process_trace

    def update_docker_operation(self, docker_op, **kwargs):
        """Docker操作を更新（互換性のため）"""
        self.record_event("docker_operation_update", kwargs)
        return docker_op

    def update_thread_state(self, thread_trace, state=None, error_message=None):
        """スレッド状態を更新（互換性のため）"""
        self.record_event(
            "thread_state_update",
            {"state": str(state) if state else None, "error_message": error_message},
        )
        return thread_trace

    def log_heartbeat(self, message=None, details=None):
        """ハートビートログを記録（互換性のため）"""
        self.record_event("heartbeat", {"message": message, "details": details})

    def detect_hang_condition(self, timeout_seconds=600.0):
        """ハングアップ条件を検出（互換性のため）"""
        self.record_event("hang_detection", {"timeout_seconds": timeout_seconds})
        return None  # ハングアップなしとして返す

    def get_current_trace(self):
        """現在のトレースを取得（互換性のため）"""
        return self

    def export_trace(self, trace, output_path):
        """トレース情報をエクスポート（互換性のため）"""
        self.record_event("trace_export", {"output_path": str(output_path)})

    def is_tracing(self) -> bool:
        """トレース中かどうかを確認"""
        return self.tracing_active

    def record_event(self, event: str, data: Optional[Dict[str, Any]] = None):
        """イベントを記録"""
        if not self.tracing_active:
            return

        with self.lock:
            trace_event = TraceEvent(
                event=event,
                timestamp=time.time(),
                thread_id=threading.get_ident(),
                data=data or {},
            )

            self.events.append(trace_event)
            self.event_counters[event] += 1

    def record_function_call(
        self,
        function_name: str,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        """関数呼び出しを記録"""
        self.record_event(
            "function_call",
            {
                "function": function_name,
                "args_count": len(args) if args else 0,
                "kwargs_count": len(kwargs) if kwargs else 0,
            },
        )

    def record_performance_marker(self, marker: str, value: float, unit: str = "seconds"):
        """パフォーマンスマーカーを記録"""
        self.record_event("performance_marker", {"marker": marker, "value": value, "unit": unit})

    def get_events(self) -> List[Dict[str, Any]]:
        """記録されたイベントを取得"""
        with self.lock:
            return [asdict(event) for event in self.events]

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """指定されたタイプのイベントを取得"""
        with self.lock:
            return [asdict(event) for event in self.events if event.event == event_type]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクスを取得"""
        with self.lock:
            if self.tracing_active:
                # トレース中の場合は現在時刻までの情報を計算
                current_time = time.time()
                duration = current_time - self.start_time if self.start_time else 0
            else:
                # トレース停止済みの場合は保存されたメトリクスを返す
                duration = self.end_time - self.start_time if self.start_time and self.end_time else 0

            return {
                "duration": duration,
                "total_events": len(self.events),
                "events_per_second": len(self.events) / duration if duration > 0 else 0,
                "event_counts": dict(self.event_counters),
                "start_time": self.start_time,
                "end_time": self.end_time,
                "is_active": self.tracing_active,
                **self.performance_metrics,
            }

    def get_timeline(self) -> List[Dict[str, Any]]:
        """イベントのタイムラインを取得"""
        with self.lock:
            if not self.events:
                return []

            base_time = self.events[0].timestamp
            timeline = []

            for event in self.events:
                timeline.append(
                    {
                        "event": event.event,
                        "relative_time": event.timestamp - base_time,
                        "absolute_time": event.timestamp,
                        "thread_id": event.thread_id,
                        "data": event.data,
                    }
                )

            return timeline

    def _calculate_performance_metrics(self):
        """パフォーマンスメトリクスを計算"""
        if not self.events:
            return

        # スレッド別統計
        thread_stats: defaultdict[int, int] = defaultdict(int)
        for event in self.events:
            thread_stats[event.thread_id] += 1

        # イベント間隔の統計
        intervals = []
        for i in range(1, len(self.events)):
            interval = self.events[i].timestamp - self.events[i - 1].timestamp
            intervals.append(interval)

        self.performance_metrics.update(
            {
                "thread_count": len(thread_stats),
                "thread_stats": dict(thread_stats),
                "avg_event_interval": sum(intervals) / len(intervals) if intervals else 0,
                "max_event_interval": max(intervals) if intervals else 0,
                "min_event_interval": min(intervals) if intervals else 0,
            }
        )

    def clear_trace(self):
        """トレースデータをクリア"""
        with self.lock:
            self.events.clear()
            self.event_counters.clear()
            self.performance_metrics.clear()
            self.start_time = None
            self.end_time = None
            self.tracing_active = False

            self.logger.info("トレースデータクリア完了")

    def get_trace_summary(self) -> Dict[str, Any]:
        """トレースサマリーを取得"""
        if not self.events:
            return {}

        return {
            "total_events": len(self.events),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": (self.end_time - self.start_time) if (self.end_time and self.start_time) else 0,
            "event_types": dict(self.event_counters),
            "performance_metrics": self.performance_metrics,
            "tracing_active": self.tracing_active,
        }
