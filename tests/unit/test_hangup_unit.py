#!/usr/bin/env python3
"""
ハングアップ対策機能の単体テスト

このファイルは高速実行を目的とした軽量な単体テストのみを含みます。
PreCommitフックで実行され、開発速度を向上させます。
"""

import os
from conftest import PROJECT_ROOT
from unittest.mock import Mock, patch

import pytest

# sys.path設定はconftest.pyで自動実行
project_root = PROJECT_ROOT

# ruff: noqa: E402
from src.diagnostic_service import DiagnosticService
from src.execution_tracer import ExecutionTracer
from src.process_monitor import ProcessMonitor


class TestDiagnosticServiceUnit:
    """DiagnosticServiceの単体テスト（高速実行用）"""

    def test_diagnostic_service_initialization(self):
        """DiagnosticServiceの初期化テスト"""
        service = DiagnosticService()
        assert service is not None
        assert hasattr(service, "check_system_health")
        assert hasattr(service, "detect_hangup_conditions")

    def test_system_health_check_basic(self):
        """基本的なシステムヘルスチェック"""
        service = DiagnosticService()

        # モックを使用して高速実行
        with (
            patch("psutil.cpu_percent", return_value=50.0),
            patch("psutil.virtual_memory") as mock_memory,
        ):
            mock_memory.return_value.percent = 60.0
            health_status = service.check_system_health()

            assert "cpu_usage" in health_status
            assert "memory_usage" in health_status
            assert health_status["cpu_usage"] == 50.0
            assert health_status["memory_usage"] == 60.0

    def test_hangup_detection_basic(self):
        """基本的なハングアップ検出テスト"""
        service = DiagnosticService()

        # 正常状態のテスト
        conditions = service.detect_hangup_conditions()
        assert isinstance(conditions, dict)
        assert "detected" in conditions
        assert "conditions" in conditions


class TestProcessMonitorUnit:
    """ProcessMonitorの単体テスト（高速実行用）"""

    def test_process_monitor_initialization(self):
        """ProcessMonitorの初期化テスト"""
        monitor = ProcessMonitor()
        assert monitor is not None
        assert hasattr(monitor, "start_monitoring")
        assert hasattr(monitor, "stop_monitoring")

    def test_process_monitoring_start_stop(self):
        """プロセス監視の開始・停止テスト"""
        monitor = ProcessMonitor()

        # モックプロセスで高速テスト
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.is_running.return_value = True

        with patch("psutil.Process", return_value=mock_process):
            # 監視開始
            result = monitor.start_monitoring(12345)
            assert result is True
            assert monitor.is_monitoring(12345)

            # 監視停止（スレッドの開始を待たずに即座に停止）
            monitor.monitoring_active = False  # 強制停止
            monitor.stop_monitoring(12345)
            assert not monitor.is_monitoring(12345)

    def test_process_status_check(self):
        """プロセス状態チェックテスト"""
        monitor = ProcessMonitor()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.is_running.return_value = True
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 25.0
        mock_process.memory_info.return_value.rss = 1024 * 1024  # 1MB
        mock_process.memory_info.return_value.vms = 2048 * 1024  # 2MB
        mock_process.num_threads.return_value = 4

        with patch("psutil.Process", return_value=mock_process):
            # まず監視を開始する必要がある
            monitor.start_monitoring(12345)
            status = monitor.get_process_status(12345)

            assert status["pid"] == 12345
            assert status["status"] == "running"
            assert status["cpu_percent"] == 25.0

            monitor.stop_monitoring()


class TestExecutionTracerUnit:
    """ExecutionTracerの単体テスト（高速実行用）"""

    def test_execution_tracer_initialization(self):
        """ExecutionTracerの初期化テスト"""
        tracer = ExecutionTracer()
        assert tracer is not None
        assert hasattr(tracer, "start_trace")
        assert hasattr(tracer, "stop_trace")

    def test_trace_start_stop(self):
        """トレース開始・停止テスト"""
        tracer = ExecutionTracer()

        tracer.start_trace()
        assert tracer.is_tracing()

        tracer.stop_trace()
        assert not tracer.is_tracing()

    def test_trace_event_recording(self):
        """トレースイベント記録テスト"""
        tracer = ExecutionTracer()

        tracer.start_trace()
        tracer.record_event("test_event", {"data": "test"})

        events = tracer.get_events()
        assert len(events) > 0
        assert events[-1]["event"] == "test_event"
        assert events[-1]["data"]["data"] == "test"

        tracer.stop_trace()

    def test_trace_performance_metrics(self):
        """トレースパフォーマンスメトリクステスト"""
        tracer = ExecutionTracer()

        # スリープを避けて高速実行
        with patch("time.time", side_effect=[1000.0, 1000.1, 1000.2]):
            tracer.start_trace()
            tracer.stop_trace()

            metrics = tracer.get_performance_metrics()
            assert "duration" in metrics
            assert metrics["duration"] >= 0


class TestIntegrationBasic:
    """基本的な統合テスト（高速実行用）"""

    def test_diagnostic_process_monitor_integration(self):
        """DiagnosticServiceとProcessMonitorの基本統合テスト"""
        diagnostic = DiagnosticService()
        monitor = ProcessMonitor()

        # 現在のプロセスを監視対象として使用
        current_pid = os.getpid()

        with (
            patch("psutil.Process") as mock_process_class,
            patch("psutil.cpu_percent", return_value=50.0),
            patch("psutil.virtual_memory") as mock_memory,
        ):
            mock_memory.return_value.percent = 60.0
            mock_process = Mock()
            mock_process.pid = current_pid
            mock_process.is_running.return_value = True
            mock_process.status.return_value = "running"
            mock_process.cpu_percent.return_value = 10.0
            mock_process.memory_info.return_value.rss = 1024 * 1024
            mock_process.memory_info.return_value.vms = 2048 * 1024
            mock_process.num_threads.return_value = 4
            mock_process_class.return_value = mock_process

            # 診断サービスのテスト
            health = diagnostic.check_system_health()
            assert health is not None
            assert "cpu_usage" in health

            # プロセス監視のテスト（スレッド開始を避ける）
            monitor.monitored_processes[current_pid] = mock_process
            status = monitor.get_process_status(current_pid)

            assert status is not None
            assert status["pid"] == current_pid

            # クリーンアップ
            monitor.monitored_processes.clear()

    def test_all_components_initialization(self):
        """全コンポーネントの初期化テスト"""
        diagnostic = DiagnosticService()
        monitor = ProcessMonitor()
        tracer = ExecutionTracer()

        assert diagnostic is not None
        assert monitor is not None
        assert tracer is not None

        # 基本機能の動作確認（モック使用）
        with (
            patch("psutil.cpu_percent", return_value=50.0),
            patch("psutil.virtual_memory") as mock_memory,
        ):
            mock_memory.return_value.percent = 60.0
            health = diagnostic.check_system_health()
            assert health is not None
            assert "cpu_usage" in health

        # トレーサーの基本動作確認
        tracer.start_trace()
        assert tracer.is_tracing()
        tracer.stop_trace()
        assert not tracer.is_tracing()


if __name__ == "__main__":
    # 高速実行のための設定
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-x",  # 最初の失敗で停止
            "--disable-warnings",
            "--no-header",
            "--no-summary",
        ]
    )
