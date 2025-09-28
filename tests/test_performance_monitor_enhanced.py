#!/usr/bin/env python3
"""
拡張パフォーマンス監視機能のテスト

このテストファイルは拡張されたパフォーマンス監視機能の動作を検証します。
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import json

# パフォーマンス監視モジュールをインポート
sys.path.append(str(Path(__file__).parent.parent / "src"))
from performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    ExecutionStage,
    BottleneckAnalysis,
    OptimizationOpportunity,
)


class TestEnhancedPerformanceMonitor:
    """拡張パフォーマンス監視のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.monitor = PerformanceMonitor(monitoring_interval=0.1)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        if self.monitor.is_monitoring():
            self.monitor.stop_monitoring()

    def test_get_summary_metrics_compatibility(self):
        """SimulationServiceとの互換性テスト"""
        self.monitor.start_monitoring()
        time.sleep(0.2)
        self.monitor.stop_monitoring()

        # get_summary_metricsメソッドが存在し、正しく動作することを確認
        summary = self.monitor.get_summary_metrics()
        assert isinstance(summary, dict)
        assert "monitoring_duration_seconds" in summary
        assert "cpu_usage" in summary
        assert "memory_usage" in summary

    def test_analyze_bottlenecks_method(self):
        """analyze_bottlenecksメソッドのテスト"""
        self.monitor.start_monitoring()

        # 高CPU使用率のメトリクスを模擬
        with patch.object(self.monitor, "_collect_current_metrics") as mock_collect:
            high_cpu_metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=95.0,
                memory_rss_mb=100.0,
                memory_vms_mb=200.0,
                memory_percent=30.0,
                disk_io_read_mb=10.0,
                disk_io_write_mb=5.0,
                network_bytes_sent=1000.0,
                network_bytes_recv=2000.0,
            )
            mock_collect.return_value = high_cpu_metrics

            # メトリクスを追加
            for _ in range(10):
                self.monitor.metrics_history.append(high_cpu_metrics)

        # analyze_bottlenecksメソッドをテスト
        bottlenecks = self.monitor.analyze_bottlenecks()
        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) > 0
        assert all(isinstance(b, BottleneckAnalysis) for b in bottlenecks)

        self.monitor.stop_monitoring()

    def test_identify_optimization_opportunities_method(self):
        """identify_optimization_opportunitiesメソッドのテスト"""
        self.monitor.start_monitoring()

        # 多数のDocker操作を模擬
        for i in range(60):
            self.monitor.record_docker_operation(f"operation_{i}")

        # identify_optimization_opportunitiesメソッドをテスト
        opportunities = self.monitor.identify_optimization_opportunities()
        assert isinstance(opportunities, list)
        assert len(opportunities) > 0
        assert all(isinstance(o, OptimizationOpportunity) for o in opportunities)

        self.monitor.stop_monitoring()

    def test_start_monitoring_with_stage_name(self):
        """段階名付きでの監視開始テスト"""
        self.monitor.start_monitoring("initial_setup")

        assert self.monitor.is_monitoring()
        assert self.monitor.current_stage is not None
        assert self.monitor.current_stage.stage_name == "initial_setup"

        self.monitor.stop_monitoring()

    def test_record_workflow_stage(self):
        """ワークフロー段階記録のテスト"""
        self.monitor.start_monitoring()

        # ワークフロー段階を記録
        self.monitor.record_workflow_stage("job1", "workflow")
        assert self.monitor.current_stage.stage_name == "workflow:job1"

        time.sleep(0.1)

        self.monitor.record_workflow_stage("job2", "workflow")
        assert self.monitor.current_stage.stage_name == "workflow:job2"
        assert len(self.monitor.execution_stages) == 2

        self.monitor.stop_monitoring()

    def test_get_real_time_metrics(self):
        """リアルタイムメトリクス取得のテスト"""
        self.monitor.start_monitoring()
        time.sleep(0.3)  # メトリクス履歴を蓄積

        real_time_metrics = self.monitor.get_real_time_metrics()

        assert isinstance(real_time_metrics, dict)
        assert "current_metrics" in real_time_metrics
        assert "trends" in real_time_metrics
        assert "monitoring_status" in real_time_metrics

        # 現在のメトリクス
        current = real_time_metrics["current_metrics"]
        assert "timestamp" in current
        assert "cpu_percent" in current
        assert "memory_percent" in current

        # 監視状態
        status = real_time_metrics["monitoring_status"]
        assert status["is_active"] is True
        assert status["metrics_collected"] > 0

        self.monitor.stop_monitoring()

    def test_detect_performance_issues(self):
        """パフォーマンス問題検出のテスト"""
        self.monitor.start_monitoring()

        # 高CPU使用率を模擬
        with patch.object(self.monitor, "get_current_metrics") as mock_get_current:
            high_cpu_metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=95.0,
                memory_rss_mb=100.0,
                memory_vms_mb=200.0,
                memory_percent=30.0,
                disk_io_read_mb=10.0,
                disk_io_write_mb=5.0,
                network_bytes_sent=1000.0,
                network_bytes_recv=2000.0,
            )
            mock_get_current.return_value = high_cpu_metrics

            issues = self.monitor.detect_performance_issues()

            assert isinstance(issues, list)
            assert len(issues) > 0

            # 高CPU使用率の問題が検出されることを確認
            cpu_issue = next((i for i in issues if i["type"] == "HIGH_CPU_USAGE"), None)
            assert cpu_issue is not None
            assert cpu_issue["severity"] in ["HIGH", "CRITICAL"]
            assert "recommendations" in cpu_issue

        self.monitor.stop_monitoring()

    def test_detect_long_running_stage_issue(self):
        """長時間実行段階の問題検出テスト"""
        self.monitor.start_monitoring()
        self.monitor.start_stage("long_running_test")

        # 段階の開始時刻を過去に設定（長時間実行を模擬）
        self.monitor.current_stage.start_time = time.time() - 70  # 70秒前

        issues = self.monitor.detect_performance_issues()

        # 長時間実行段階の問題が検出されることを確認
        long_stage_issue = next((i for i in issues if i["type"] == "LONG_RUNNING_STAGE"), None)
        assert long_stage_issue is not None
        assert long_stage_issue["severity"] == "MEDIUM"
        assert "stage_name" in long_stage_issue

        self.monitor.stop_monitoring()

    def test_generate_performance_report(self):
        """パフォーマンスレポート生成のテスト"""
        self.monitor.start_monitoring()

        # 複数の段階を実行
        self.monitor.start_stage("stage1")
        time.sleep(0.1)
        self.monitor.end_stage()

        self.monitor.start_stage("stage2")
        self.monitor.record_docker_operation("test_operation")
        time.sleep(0.1)
        self.monitor.end_stage()

        self.monitor.stop_monitoring()

        report = self.monitor.generate_performance_report()

        assert isinstance(report, dict)
        assert "report_metadata" in report
        assert "system_performance" in report
        assert "execution_analysis" in report
        assert "bottlenecks" in report
        assert "optimization_opportunities" in report
        assert "recommendations" in report

        # メタデータの確認
        metadata = report["report_metadata"]
        assert "generated_at" in metadata
        assert "performance_score" in metadata
        assert 0 <= metadata["performance_score"] <= 100

        # 実行分析の確認
        execution = report["execution_analysis"]
        assert execution["total_stages"] == 2
        assert len(execution["stage_details"]) == 2

        # 推奨事項の確認
        assert isinstance(report["recommendations"], list)
        assert len(report["recommendations"]) > 0

    def test_enhanced_bottleneck_detection(self):
        """拡張ボトルネック検出のテスト"""
        self.monitor.start_monitoring()

        # 長時間実行段階を模擬
        long_stage = ExecutionStage(
            stage_name="slow_stage",
            start_time=time.time() - 150,  # 150秒前に開始
        )
        long_stage.end_time = time.time()
        long_stage.duration_ms = 150000  # 150秒
        long_stage.peak_cpu = 80.0
        long_stage.peak_memory_mb = 512.0
        long_stage.docker_operations = 5

        self.monitor.execution_stages.append(long_stage)

        # 高ディスクI/Oメトリクスを模擬
        high_io_metrics = []
        for i in range(10):
            metrics = PerformanceMetrics(
                timestamp=time.time() + i,
                cpu_percent=50.0,
                memory_rss_mb=256.0,
                memory_vms_mb=512.0,
                memory_percent=50.0,
                disk_io_read_mb=100.0 + i * 200,  # 高い読み込み速度
                disk_io_write_mb=50.0,
                network_bytes_sent=1000.0,
                network_bytes_recv=2000.0,
            )
            high_io_metrics.append(metrics)
            self.monitor.metrics_history.append(metrics)

        self.monitor.stop_monitoring()

        # ボトルネックが検出されることを確認
        assert len(self.monitor.bottlenecks) > 0

        # 長時間実行段階のボトルネックが検出されることを確認
        slow_stage_bottleneck = next(
            (b for b in self.monitor.bottlenecks if b.bottleneck_type == "STAGE_SLOW_EXECUTION"),
            None
        )
        assert slow_stage_bottleneck is not None
        assert slow_stage_bottleneck.severity in ["HIGH", "MEDIUM"]

    def test_enhanced_optimization_opportunities(self):
        """拡張最適化機会検出のテスト"""
        self.monitor.start_monitoring()

        # 複数の長時間段階を模擬
        for i in range(4):
            stage = ExecutionStage(
                stage_name=f"long_stage_{i}",
                start_time=time.time() - 20 - i,
            )
            stage.end_time = time.time() - i
            stage.duration_ms = 20000  # 20秒
            stage.docker_operations = 15 if i < 2 else 2  # 最初の2つはDocker集約
            self.monitor.execution_stages.append(stage)

        # 低リソース使用率メトリクスを模擬
        for i in range(10):
            low_usage_metrics = PerformanceMetrics(
                timestamp=time.time() + i,
                cpu_percent=25.0,  # 低CPU使用率
                memory_rss_mb=100.0,
                memory_vms_mb=400.0,
                memory_percent=25.0,  # 低メモリ使用率
                disk_io_read_mb=10.0,
                disk_io_write_mb=5.0,
                network_bytes_sent=1000.0,
                network_bytes_recv=2000.0,
            )
            self.monitor.metrics_history.append(low_usage_metrics)

        self.monitor.stop_monitoring()

        # 最適化機会が検出されることを確認
        assert len(self.monitor.optimization_opportunities) > 0

        # 実行時間最適化の機会が検出されることを確認
        execution_time_opt = next(
            (o for o in self.monitor.optimization_opportunities
             if o.opportunity_type == "EXECUTION_TIME_OPTIMIZATION"),
            None
        )
        assert execution_time_opt is not None

        # リソース使用率最適化の機会が検出されることを確認
        resource_opt = next(
            (o for o in self.monitor.optimization_opportunities
             if o.opportunity_type == "RESOURCE_UNDERUTILIZATION"),
            None
        )
        assert resource_opt is not None

    def test_performance_score_calculation(self):
        """パフォーマンススコア計算のテスト"""
        # 良好なパフォーマンス
        good_cpu_stats = {"average": 30.0}
        good_memory_stats = {"average": 40.0}
        good_docker_stats = {"operations_per_minute": 5.0, "peak_containers": 3}

        good_score = self.monitor._calculate_performance_score(
            good_cpu_stats, good_memory_stats, good_docker_stats
        )
        assert 70 <= good_score <= 100

        # 悪いパフォーマンス
        bad_cpu_stats = {"average": 90.0}
        bad_memory_stats = {"average": 85.0}
        bad_docker_stats = {"operations_per_minute": 50.0, "peak_containers": 20}

        bad_score = self.monitor._calculate_performance_score(
            bad_cpu_stats, bad_memory_stats, bad_docker_stats
        )
        assert 0 <= bad_score <= 50

    def test_overall_recommendations_generation(self):
        """全体的な推奨事項生成のテスト"""
        # 高リソース使用率の場合
        high_cpu_stats = {"average": 80.0}
        high_memory_stats = {"average": 90.0}
        high_docker_stats = {"operations_per_minute": 20.0, "peak_containers": 15}

        recommendations = self.monitor._generate_overall_recommendations(
            high_cpu_stats, high_memory_stats, high_docker_stats
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # CPU、メモリ、Dockerに関する推奨事項が含まれることを確認
        cpu_rec = any("CPU" in rec for rec in recommendations)
        memory_rec = any("メモリ" in rec for rec in recommendations)
        docker_rec = any("Docker" in rec for rec in recommendations)

        assert cpu_rec or memory_rec or docker_rec

    def test_export_enhanced_metrics(self, tmp_path):
        """拡張メトリクスエクスポートのテスト"""
        self.monitor.start_monitoring()

        # 段階とDocker操作を実行
        self.monitor.start_stage("export_test")
        self.monitor.record_docker_operation("test_op")
        time.sleep(0.2)
        self.monitor.end_stage()

        self.monitor.stop_monitoring()

        # エクスポート
        export_path = tmp_path / "enhanced_metrics.json"
        success = self.monitor.export_metrics(export_path, format="json")

        assert success
        assert export_path.exists()

        # エクスポートされたデータの確認
        with open(export_path, "r", encoding="utf-8") as f:
            exported_data = json.load(f)

        assert "analysis" in exported_data
        analysis = exported_data["analysis"]

        # 拡張分析データが含まれることを確認
        assert "bottlenecks" in analysis
        assert "optimization_opportunities" in analysis
        assert "execution_stages" in analysis

        # 実行段階の詳細が含まれることを確認
        stages = analysis["execution_stages"]
        assert len(stages) == 1
        assert stages[0]["stage_name"] == "export_test"
        assert stages[0]["docker_operations"] == 1

    def test_concurrent_monitoring_with_enhancements(self):
        """拡張機能での並行監視テスト"""
        def worker_with_stages():
            """段階付きワーカー関数"""
            self.monitor.record_workflow_stage("worker_job", "test")
            for i in range(500):
                _ = i ** 2
                if i % 100 == 0:
                    self.monitor.record_docker_operation(f"worker_op_{i}")

        self.monitor.start_monitoring("concurrent_enhanced_test")

        # 複数のワーカーを実行
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_with_stages)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # リアルタイムメトリクスを取得
        real_time_metrics = self.monitor.get_real_time_metrics()
        assert real_time_metrics["monitoring_status"]["is_active"]

        # パフォーマンス問題を検出
        issues = self.monitor.detect_performance_issues()
        assert isinstance(issues, list)

        self.monitor.stop_monitoring()

        # 最終レポートを生成
        report = self.monitor.generate_performance_report()
        assert report["execution_analysis"]["total_stages"] > 0
        assert report["system_performance"]["docker_statistics"]["total_operations"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
