#!/usr/bin/env python3
"""
SimulationServiceとEnhancedActWrapper統合のテスト

このテストはタスク10の要件を検証します:
- SimulationServiceにEnhancedActWrapperと診断機能を統合
- 実行前診断チェックと詳細結果レポート機能を追加
- パフォーマンスメトリクスと実行トレースの統合を実装
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from services.actions.service import (
    SimulationService,
    SimulationParameters,
    SimulationResult,
)
from services.actions.logger import ActionsLogger


class TestSimulationServiceIntegration:
    """SimulationService統合テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.logger = ActionsLogger(verbose=True)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workflow_file = self.temp_dir / "test.yml"
        self.workflow_file.write_text("""
name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: echo "Hello World"
""")

    def test_enhanced_simulation_service_initialization(self):
        """拡張SimulationServiceの初期化テスト"""
        service = SimulationService(
            use_enhanced_wrapper=True,
            enable_diagnostics=True,
            enable_performance_monitoring=True,
            pre_execution_diagnostics=True,
            detailed_result_reporting=True,
        )

        status = service.get_simulation_status()

        assert status["service_initialized"] is True
        assert status["enhanced_wrapper_enabled"] is True
        assert status["diagnostics_enabled"] is True
        assert status["performance_monitoring_enabled"] is True
        assert status["pre_execution_diagnostics_enabled"] is True
        assert status["detailed_result_reporting_enabled"] is True

    def test_enable_enhanced_features(self):
        """拡張機能の有効化テスト"""
        service = SimulationService()

        # 初期状態では無効
        status = service.get_simulation_status()
        assert status["enhanced_wrapper_enabled"] is False
        assert status["diagnostics_enabled"] is False

        # 拡張機能を有効化
        service.enable_enhanced_features(
            enable_diagnostics=True,
            enable_performance_monitoring=True,
            enable_detailed_reporting=True,
        )

        # 有効化後の状態確認
        status = service.get_simulation_status()
        assert status["enhanced_wrapper_enabled"] is True
        assert status["diagnostics_enabled"] is True
        assert status["performance_monitoring_enabled"] is True

    @patch("services.actions.service.DiagnosticService")
    @patch("services.actions.service.PerformanceMonitor")
    @patch("services.actions.service.ExecutionTracer")
    def test_pre_execution_diagnostics(self, mock_tracer, mock_perf_monitor, mock_diagnostic):
        """実行前診断チェックのテスト"""
        # モックの設定
        mock_diagnostic_instance = Mock()
        mock_diagnostic_instance.check_system_health.return_value = {
            "status": "healthy",
            "cpu_usage": 25.0,
            "memory_usage": 45.0,
        }
        mock_diagnostic_instance.check_docker_connectivity.return_value = {
            "status": "ok",
            "docker_available": True,
        }
        mock_diagnostic_instance.check_act_binary.return_value = {
            "status": "ok",
            "act_version": "0.2.26",
        }
        mock_diagnostic_instance.check_container_permissions.return_value = {
            "status": "ok",
            "permissions": "valid",
        }
        mock_diagnostic.return_value = mock_diagnostic_instance

        mock_perf_instance = Mock()
        mock_perf_instance.start_monitoring.return_value = None
        mock_perf_instance.stop_monitoring.return_value = None
        mock_perf_instance.get_summary_metrics.return_value = {
            "avg_cpu": 30.0,
            "peak_memory_mb": 512.0,
        }
        mock_perf_monitor.return_value = mock_perf_instance

        mock_tracer_instance = Mock()
        mock_tracer_instance.get_trace_summary.return_value = {
            "total_events": 15,
            "execution_stages": ["init", "subprocess", "output", "complete"],
        }
        mock_tracer.return_value = mock_tracer_instance

        # EnhancedActWrapperをモック
        with patch("services.actions.service.EnhancedActWrapper") as mock_wrapper:
            mock_wrapper_instance = Mock()
            mock_wrapper_instance.run_workflow_with_diagnostics.return_value = Mock(
                success=True,
                returncode=0,
                stdout="Test output",
                stderr="",
                command="act test.yml",
                execution_time_ms=1500.0,
                diagnostic_results=[],
                deadlock_indicators=[],
                stream_result=None,
                hang_analysis=None,
                resource_usage=[],
                trace_id="test_trace_123",
            )
            mock_wrapper.return_value = mock_wrapper_instance

            service = SimulationService(
                use_enhanced_wrapper=True,
                enable_diagnostics=True,
                enable_performance_monitoring=True,
                pre_execution_diagnostics=True,
                detailed_result_reporting=True,
            )

            params = SimulationParameters(workflow_file=self.workflow_file, verbose=True)

            result = service.run_simulation(params)

            # 結果の検証
            assert isinstance(result, SimulationResult)
            assert result.success is True
            assert result.execution_time_ms > 0
            assert len(result.diagnostic_results) > 0
            assert isinstance(result.performance_metrics, dict)
            assert isinstance(result.execution_trace, dict)

            # 診断チェックが実行されたことを確認
            mock_diagnostic_instance.check_system_health.assert_called()

    @patch("services.actions.service.DiagnosticService")
    def test_pre_execution_diagnostics_failure(self, mock_diagnostic):
        """実行前診断チェック失敗時のテスト"""
        # 診断チェックが失敗するように設定
        mock_diagnostic_instance = Mock()
        mock_diagnostic_instance.check_system_health.return_value = {
            "status": "error",
            "error": "Docker daemon not running",
        }
        mock_diagnostic.return_value = mock_diagnostic_instance

        service = SimulationService(
            use_enhanced_wrapper=True,
            enable_diagnostics=True,
            pre_execution_diagnostics=True,
        )

        # _run_pre_execution_diagnosticsをモックして失敗を返す
        with patch.object(service, "_run_pre_execution_diagnostics") as mock_pre_check:
            mock_pre_check.return_value = {
                "overall_status": "ERROR",
                "summary": "Docker daemon not running",
                "timestamp": 1234567890.0,
            }

            params = SimulationParameters(workflow_file=self.workflow_file, verbose=True)

            result = service.run_simulation(params)

            # 失敗結果の検証
            assert result.success is False
            assert result.return_code == -1
            assert "重大な問題が検出されました" in result.stderr
            assert len(result.diagnostic_results) > 0

    @patch("services.actions.service.EnhancedActWrapper")
    @patch("services.actions.service.DiagnosticService")
    @patch("services.actions.service.PerformanceMonitor")
    def test_detailed_result_reporting(self, mock_perf_monitor, mock_diagnostic, mock_wrapper):
        """詳細結果レポートのテスト"""
        # モックの設定
        mock_diagnostic_instance = Mock()
        mock_diagnostic_instance.check_system_health.return_value = {"status": "healthy"}
        mock_diagnostic.return_value = mock_diagnostic_instance

        mock_perf_instance = Mock()
        mock_perf_instance.start_monitoring.return_value = None
        mock_perf_instance.stop_monitoring.return_value = None
        mock_perf_instance.get_summary_metrics.return_value = {
            "avg_cpu": 35.0,
            "peak_memory_mb": 768.0,
            "total_duration_ms": 2500.0,
        }
        # ボトルネック分析のモック設定
        bottleneck_mock = Mock()
        bottleneck_mock.bottleneck_type = "cpu_intensive"
        bottleneck_mock.severity = "MEDIUM"
        bottleneck_mock.description = "CPU使用率が高い期間が検出されました"
        bottleneck_mock.recommendations = ["並列処理の最適化を検討してください"]
        mock_perf_instance.analyze_bottlenecks.return_value = [bottleneck_mock]

        # 最適化機会のモック設定
        opportunity_mock = Mock()
        opportunity_mock.opportunity_type = "caching"
        opportunity_mock.priority = "HIGH"
        opportunity_mock.title = "キャッシュ最適化"
        opportunity_mock.description = "依存関係のキャッシュを有効化"
        opportunity_mock.recommendations = ["actions/cache@v3を使用してください"]
        mock_perf_instance.identify_optimization_opportunities.return_value = [opportunity_mock]
        mock_perf_monitor.return_value = mock_perf_instance

        mock_wrapper_instance = Mock()
        mock_wrapper_instance.run_workflow_with_diagnostics.return_value = Mock(
            success=True,
            returncode=0,
            stdout="Detailed test output",
            stderr="",
            command="act test.yml --verbose",
            execution_time_ms=2500.0,
            diagnostic_results=[{"phase": "wrapper", "status": "OK"}],
            deadlock_indicators=[],
            stream_result=Mock(
                stdout_bytes=1024,
                stderr_bytes=0,
                threads_completed=True,
                deadlock_detected=False,
                stream_duration_ms=2000.0,
                error_message=None,
            ),
            hang_analysis=None,
            resource_usage=[{"timestamp": 1234567890, "cpu": 30.0, "memory_mb": 512}],
            trace_id="detailed_trace_456",
        )
        mock_wrapper.return_value = mock_wrapper_instance

        service = SimulationService(
            use_enhanced_wrapper=True,
            enable_diagnostics=True,
            enable_performance_monitoring=True,
            detailed_result_reporting=True,
        )

        params = SimulationParameters(workflow_file=self.workflow_file, verbose=True)

        result = service.run_simulation(params)

        # 詳細結果の検証
        assert result.success is True
        assert result.execution_time_ms > 0
        assert len(result.diagnostic_results) > 0
        assert result.performance_metrics is not None
        assert result.execution_trace is not None
        assert len(result.bottlenecks_detected) > 0
        assert len(result.optimization_opportunities) > 0

        # メタデータの検証
        assert result.metadata["detailed_reporting_enabled"] is True
        assert result.metadata["diagnostics_enabled"] is True
        assert result.metadata["performance_monitoring_enabled"] is True
        assert "execution_time_ms" in result.metadata
        assert "bottlenecks_count" in result.metadata
        assert "optimization_opportunities_count" in result.metadata

        # ボトルネック分析の検証
        bottleneck = result.bottlenecks_detected[0]
        assert bottleneck["type"] == "cpu_intensive"
        assert bottleneck["severity"] == "MEDIUM"
        assert len(bottleneck["recommendations"]) > 0

        # 最適化機会の検証
        opportunity = result.optimization_opportunities[0]
        assert opportunity["type"] == "caching"
        assert opportunity["priority"] == "HIGH"
        assert len(opportunity["recommendations"]) > 0

    def test_simulation_service_backward_compatibility(self):
        """既存機能との後方互換性テスト"""
        # 拡張機能を無効にした通常のSimulationService
        service = SimulationService(
            use_enhanced_wrapper=False,
            enable_diagnostics=False,
            enable_performance_monitoring=False,
        )

        with patch("services.actions.service.ActWrapper") as mock_wrapper:
            mock_wrapper_instance = Mock()
            mock_wrapper_instance.run_workflow.return_value = {
                "success": True,
                "returncode": 0,
                "stdout": "Basic output",
                "stderr": "",
                "command": "act test.yml",
            }
            mock_wrapper.return_value = mock_wrapper_instance

            params = SimulationParameters(workflow_file=self.workflow_file, verbose=False)

            result = service.run_simulation(params)

            # 基本機能の動作確認
            assert result.success is True
            assert result.return_code == 0
            assert result.stdout == "Basic output"
            assert result.metadata["enhanced_wrapper"] is False

            # 拡張機能が無効でも基本的な詳細レポートは生成される
            assert result.execution_time_ms > 0.0  # 実行時間は常に測定される
            assert len(result.diagnostic_results) == 0  # 診断は無効
            assert result.performance_metrics == {}  # パフォーマンス監視は無効
            assert result.execution_trace == {}  # 実行トレースは無効

    def teardown_method(self):
        """テストクリーンアップ"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
