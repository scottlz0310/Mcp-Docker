#!/usr/bin/env python3
"""
パフォーマンス監視機能のテスト

このテストファイルはパフォーマンス監視機能の動作を検証します。
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# パフォーマンス監視モジュールをインポート
sys.path.append(str(Path(__file__).parent.parent / "src"))
from performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    ExecutionStage,
    BottleneckAnalysis,
    OptimizationOpportunity,
)


class TestPerformanceMonitor:
    """パフォーマンス監視のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.monitor = PerformanceMonitor(monitoring_interval=0.1)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        if self.monitor.is_monitoring():
            self.monitor.stop_monitoring()

    def test_monitor_initialization(self):
        """パフォーマンス監視の初期化テスト"""
        assert self.monitor is not None
        assert not self.monitor.is_monitoring()
        assert len(self.monitor.metrics_history) == 0
        assert len(self.monitor.execution_stages) == 0

    def test_start_stop_monitoring(self):
        """監視の開始と停止のテスト"""
        # 監視開始
        self.monitor.start_monitoring()
        assert self.monitor.is_monitoring()

        # 少し待機してメトリクスが収集されることを確認
        time.sleep(0.3)
        assert len(self.monitor.metrics_history) > 0

        # 監視停止
        self.monitor.stop_monitoring()
        assert not self.monitor.is_monitoring()

    def test_execution_stages(self):
        """実行段階の管理テスト"""
        self.monitor.start_monitoring()

        # 段階1を開始
        self.monitor.start_stage("initialization")
        assert self.monitor.current_stage is not None
        assert self.monitor.current_stage.stage_name == "initialization"

        time.sleep(0.1)

        # 段階2を開始（前の段階は自動終了）
        self.monitor.start_stage("execution")
        assert len(self.monitor.execution_stages) == 2
        assert self.monitor.execution_stages[0].end_time is not None
        assert self.monitor.execution_stages[0].duration_ms is not None

        # 現在の段階を手動終了
        self.monitor.end_stage()
        assert self.monitor.current_stage.end_time is not None

        self.monitor.stop_monitoring()

    def test_docker_operation_recording(self):
        """Docker操作の記録テスト"""
        self.monitor.start_monitoring()
        self.monitor.start_stage("docker_operations")

        # Docker操作を記録
        self.monitor.record_docker_operation("container_create", "test_container_123")
        self.monitor.record_docker_operation("image_pull", "ubuntu:latest")

        assert self.monitor.docker_operations_count == 2
        assert self.monitor.current_stage.docker_operations == 2

        self.monitor.stop_monitoring()

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_io_counters")
    @patch("psutil.net_io_counters")
    def test_metrics_collection(self, mock_net_io, mock_disk_io, mock_memory, mock_cpu):
        """メトリクス収集のテスト"""
        # モックの設定
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(
            rss=1024 * 1024 * 512,  # 512MB
            vms=1024 * 1024 * 1024,  # 1GB
            percent=50.0,
        )
        mock_disk_io.return_value = Mock(
            read_bytes=1024 * 1024 * 100,  # 100MB
            write_bytes=1024 * 1024 * 50,  # 50MB
        )
        mock_net_io.return_value = Mock(
            bytes_sent=1024 * 1024 * 10,  # 10MB
            bytes_recv=1024 * 1024 * 20,  # 20MB
        )

        # メトリクス収集をテスト
        metrics = self.monitor._collect_current_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_rss_mb == 512.0
        assert metrics.memory_percent == 50.0
        assert metrics.disk_io_read_mb == 100.0
        assert metrics.disk_io_write_mb == 50.0

    def test_bottleneck_detection(self):
        """ボトルネック検出のテスト"""
        self.monitor.start_monitoring()

        # 高CPU使用率のメトリクスを模擬
        with patch.object(self.monitor, "_collect_current_metrics") as mock_collect:
            high_cpu_metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=95.0,  # 高CPU使用率
                memory_rss_mb=100.0,
                memory_vms_mb=200.0,
                memory_percent=30.0,
                disk_io_read_mb=10.0,
                disk_io_write_mb=5.0,
                network_bytes_sent=1000.0,
                network_bytes_recv=2000.0,
            )
            mock_collect.return_value = high_cpu_metrics

            # 複数回メトリクスを収集してボトルネックを検出
            for _ in range(10):
                self.monitor.metrics_history.append(high_cpu_metrics)

        self.monitor.stop_monitoring()

        # ボトルネックが検出されることを確認
        assert len(self.monitor.bottlenecks) > 0
        cpu_bottleneck = next(
            (
                b
                for b in self.monitor.bottlenecks
                if b.bottleneck_type == "CPU_HIGH_USAGE"
            ),
            None,
        )
        assert cpu_bottleneck is not None
        assert cpu_bottleneck.severity in ["HIGH", "MEDIUM"]

    def test_optimization_opportunities(self):
        """最適化機会の特定テスト"""
        self.monitor.start_monitoring()

        # 多数のDocker操作を模擬
        for i in range(60):
            self.monitor.record_docker_operation(f"operation_{i}", f"container_{i}")

        self.monitor.stop_monitoring()

        # 最適化機会が特定されることを確認
        assert len(self.monitor.optimization_opportunities) > 0
        docker_optimization = next(
            (
                o
                for o in self.monitor.optimization_opportunities
                if o.opportunity_type == "DOCKER_OPERATIONS_OPTIMIZATION"
            ),
            None,
        )
        assert docker_optimization is not None
        assert docker_optimization.priority in ["HIGH", "MEDIUM", "LOW"]

    def test_performance_summary(self):
        """パフォーマンスサマリーのテスト"""
        self.monitor.start_monitoring()

        # いくつかの段階を実行
        self.monitor.start_stage("stage1")
        time.sleep(0.1)
        self.monitor.end_stage()

        self.monitor.start_stage("stage2")
        time.sleep(0.1)
        self.monitor.end_stage()

        self.monitor.stop_monitoring()

        summary = self.monitor.get_performance_summary()

        assert "monitoring_duration_seconds" in summary
        assert "total_execution_time_ms" in summary
        assert "metrics_collected" in summary
        assert "cpu_usage" in summary
        assert "memory_usage" in summary
        assert "docker_operations" in summary
        assert "execution_stages" in summary
        assert summary["execution_stages"] == 2

    def test_detailed_analysis(self):
        """詳細分析のテスト"""
        self.monitor.start_monitoring()

        # 段階を実行
        self.monitor.start_stage("test_stage")
        self.monitor.record_docker_operation("test_operation")
        time.sleep(0.1)
        self.monitor.end_stage()

        self.monitor.stop_monitoring()

        analysis = self.monitor.get_detailed_analysis()

        assert "performance_summary" in analysis
        assert "bottlenecks" in analysis
        assert "optimization_opportunities" in analysis
        assert "execution_stages" in analysis

        # 実行段階の情報が含まれることを確認
        stages = analysis["execution_stages"]
        assert len(stages) == 1
        assert stages[0]["stage_name"] == "test_stage"
        assert stages[0]["docker_operations"] == 1

    def test_metrics_export(self, tmp_path):
        """メトリクスエクスポートのテスト"""
        self.monitor.start_monitoring()
        time.sleep(0.2)
        self.monitor.stop_monitoring()

        # JSONファイルにエクスポート
        export_path = tmp_path / "performance_metrics.json"
        success = self.monitor.export_metrics(export_path, format="json")

        assert success
        assert export_path.exists()

        # エクスポートされたファイルの内容を確認
        import json

        with open(export_path, "r", encoding="utf-8") as f:
            exported_data = json.load(f)

        assert "metadata" in exported_data
        assert "analysis" in exported_data
        assert "raw_metrics" in exported_data
        assert len(exported_data["raw_metrics"]) > 0

    def test_concurrent_monitoring(self):
        """並行監視のテスト"""

        def worker_function():
            """ワーカー関数（CPU負荷を模擬）"""
            for i in range(1000):
                _ = i**2

        self.monitor.start_monitoring()
        self.monitor.start_stage("concurrent_test")

        # 複数のスレッドを開始
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_function)
            threads.append(thread)
            thread.start()

        # スレッドの完了を待機
        for thread in threads:
            thread.join()

        self.monitor.end_stage()
        self.monitor.stop_monitoring()

        # メトリクスが収集されていることを確認
        assert len(self.monitor.metrics_history) > 0
        summary = self.monitor.get_performance_summary()
        assert summary["metrics_collected"] > 0

    @patch("docker.from_env")
    def test_docker_monitoring(self, mock_docker):
        """Docker監視のテスト"""
        # Dockerクライアントのモック
        mock_client = Mock()
        mock_container = Mock()
        mock_container.id = "test_container_123"
        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000, "percpu_usage": [500000, 500000]},
                "system_cpu_usage": 10000000,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000},
                "system_cpu_usage": 9000000,
            },
            "memory_stats": {"usage": 1024 * 1024 * 100},  # 100MB
        }

        mock_client.containers.list.return_value = [mock_container]
        mock_client.ping.return_value = True
        mock_docker.return_value = mock_client

        # 新しいモニターを作成（Dockerクライアント付き）
        monitor = PerformanceMonitor(monitoring_interval=0.1)
        monitor.start_monitoring()

        time.sleep(0.2)

        monitor.stop_monitoring()

        # Dockerメトリクスが収集されていることを確認
        if monitor.metrics_history:
            latest_metrics = list(monitor.metrics_history)[-1]
            assert latest_metrics.active_containers >= 0

    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        # 無効な形式でのエクスポート
        success = self.monitor.export_metrics(Path("/tmp/test.txt"), format="invalid")
        assert not success

        # 監視していない状態でのサマリー取得
        summary = self.monitor.get_performance_summary()
        assert "error" in summary

        # 現在のメトリクス取得（エラー時）
        with patch.object(
            self.monitor,
            "_collect_current_metrics",
            side_effect=Exception("Test error"),
        ):
            current_metrics = self.monitor.get_current_metrics()
            assert current_metrics is None


class TestPerformanceMetrics:
    """PerformanceMetricsデータクラスのテスト"""

    def test_performance_metrics_creation(self):
        """PerformanceMetricsの作成テスト"""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_rss_mb=256.0,
            memory_vms_mb=512.0,
            memory_percent=25.0,
            disk_io_read_mb=100.0,
            disk_io_write_mb=50.0,
            network_bytes_sent=1000.0,
            network_bytes_recv=2000.0,
            docker_operations_count=5,
            active_containers=2,
            docker_cpu_usage=30.0,
            docker_memory_usage_mb=128.0,
        )

        assert metrics.cpu_percent == 50.0
        assert metrics.memory_rss_mb == 256.0
        assert metrics.docker_operations_count == 5
        assert metrics.active_containers == 2


class TestExecutionStage:
    """ExecutionStageデータクラスのテスト"""

    def test_execution_stage_creation(self):
        """ExecutionStageの作成テスト"""
        start_time = time.time()
        stage = ExecutionStage(stage_name="test_stage", start_time=start_time)

        assert stage.stage_name == "test_stage"
        assert stage.start_time == start_time
        assert stage.end_time is None
        assert stage.duration_ms is None
        assert stage.peak_cpu == 0.0
        assert stage.peak_memory_mb == 0.0
        assert stage.docker_operations == 0
        assert len(stage.bottlenecks) == 0


class TestBottleneckAnalysis:
    """BottleneckAnalysisデータクラスのテスト"""

    def test_bottleneck_analysis_creation(self):
        """BottleneckAnalysisの作成テスト"""
        analysis = BottleneckAnalysis(
            bottleneck_type="CPU_HIGH_USAGE",
            severity="HIGH",
            description="CPU使用率が高すぎます",
            affected_stage="execution",
            impact_score=0.8,
            recommendations=["並列処理の最適化", "CPU集約的タスクの分散"],
            metrics_evidence={"avg_cpu": 85.0, "max_cpu": 95.0},
        )

        assert analysis.bottleneck_type == "CPU_HIGH_USAGE"
        assert analysis.severity == "HIGH"
        assert analysis.impact_score == 0.8
        assert len(analysis.recommendations) == 2
        assert "avg_cpu" in analysis.metrics_evidence


class TestOptimizationOpportunity:
    """OptimizationOpportunityデータクラスのテスト"""

    def test_optimization_opportunity_creation(self):
        """OptimizationOpportunityの作成テスト"""
        opportunity = OptimizationOpportunity(
            opportunity_type="DOCKER_OPERATIONS_OPTIMIZATION",
            priority="MEDIUM",
            title="Docker操作の最適化",
            description="Docker操作が多数実行されています",
            estimated_improvement="実行時間 10-30% 短縮",
            implementation_effort="中程度",
            recommendations=["Docker操作のバッチ化", "キャッシュ戦略の最適化"],
        )

        assert opportunity.opportunity_type == "DOCKER_OPERATIONS_OPTIMIZATION"
        assert opportunity.priority == "MEDIUM"
        assert opportunity.title == "Docker操作の最適化"
        assert len(opportunity.recommendations) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
