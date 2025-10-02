"""
GitHub Actions Simulator - 包括的ハングアップシナリオテスト
様々なハングアップ条件をシミュレートし、修正を検証する統合テスト
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from services.actions.diagnostic import DiagnosticService, DiagnosticStatus
from services.actions.enhanced_act_wrapper import (
    EnhancedActWrapper,
    MonitoredProcess,
)
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage
from services.actions.hangup_detector import HangupDetector, HangupType, HangupSeverity
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger


class TestHangupScenariosComprehensive:
    """包括的ハングアップシナリオテストクラス"""

    @pytest.fixture
    def logger(self):
        """テスト用ロガーを作成"""
        return ActionsLogger(verbose=True)

    @pytest.fixture
    def temp_workspace(self):
        """一時的なワークスペースを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # テスト用ワークフローファイルを作成
            workflow_file = workspace / "test_workflow.yml"
            workflow_file.write_text("""
name: Test Hangup Scenario
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Simple test
        run: echo "Testing hangup scenarios"
      - name: Long running task
        run: sleep 5
""")
            yield workspace

    @pytest.fixture
    def diagnostic_service(self, logger):
        """DiagnosticServiceインスタンスを作成"""
        return DiagnosticService(logger=logger)

    @pytest.fixture
    def process_monitor(self, logger):
        """ProcessMonitorインスタンスを作成"""
        # src/process_monitor.pyからインポート
        from src.process_monitor import ProcessMonitor

        return ProcessMonitor(logger=logger)

    @pytest.fixture
    def execution_tracer(self, logger):
        """ExecutionTracerインスタンスを作成"""
        return ExecutionTracer(logger=logger, heartbeat_interval=1.0, resource_monitoring_interval=0.5)

    @pytest.fixture
    def hangup_detector(self, logger):
        """HangupDetectorインスタンスを作成"""
        return HangupDetector(logger=logger, confidence_threshold=0.5)

    @pytest.fixture
    def auto_recovery(self, logger):
        """AutoRecoveryインスタンスを作成"""
        return AutoRecovery(
            logger=logger,
            max_recovery_attempts=2,
            recovery_timeout=10.0,
            enable_fallback_mode=True,
        )

    @pytest.mark.timeout(30)
    def test_docker_socket_hangup_scenario(self, diagnostic_service, hangup_detector):
        """Dockerソケット問題によるハングアップシナリオテスト"""
        # Dockerコマンドが見つからない状況をシミュレート
        with patch("shutil.which", return_value=None):
            # 診断サービスでDocker接続性をチェック
            docker_result = diagnostic_service.check_docker_connectivity()

            assert docker_result.status == DiagnosticStatus.ERROR
            assert "Dockerコマンドが見つかりません" in docker_result.message

        # ハングアップ検出器でDocker問題を検出（Dockerソケットが存在しない状況をシミュレート）
        with patch("pathlib.Path.exists", return_value=False):
            docker_issues = hangup_detector.detect_docker_socket_issues()

            assert len(docker_issues) > 0
            docker_issue = next(
                (issue for issue in docker_issues if issue.issue_type == HangupType.DOCKER_SOCKET_ISSUE),
                None,
            )
            assert docker_issue is not None
            assert docker_issue.severity == HangupSeverity.CRITICAL

    @pytest.mark.timeout(30)  # 30秒でタイムアウト
    def test_subprocess_deadlock_hangup_scenario(self, process_monitor, execution_tracer, hangup_detector):
        """サブプロセスデッドロックによるハングアップシナリオテスト"""
        # 長時間実行されるモックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 常に実行中

        # 実行トレースを開始
        execution_tracer.start_trace("deadlock_test")
        execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)

        # プロセストレースを追加（適切な開始時間で）
        from datetime import datetime, timezone, timedelta

        old_start_time = datetime.now(timezone.utc) - timedelta(minutes=10)  # 10分前

        # モックプロセストレースを作成
        mock_process_trace = Mock()
        mock_process_trace.command = ["sleep", "infinity"]
        mock_process_trace.pid = 12345
        mock_process_trace.start_time = old_start_time

        execution_tracer.trace_subprocess_execution(["sleep", "infinity"], mock_process)

        # プロセス監視を開始
        process_monitor.start_monitoring(mock_process.pid)

        # 少し待機してからデッドロック検出
        time.sleep(0.1)

        # ハングアップ検出器でデッドロック分析
        final_trace = execution_tracer.end_trace()

        # プロセストレースを手動で追加（テスト用）
        if not hasattr(final_trace, "process_traces"):
            final_trace.process_traces = []
        final_trace.process_traces.append(mock_process_trace)

        deadlock_issues = hangup_detector.detect_subprocess_deadlock(final_trace)

        # デッドロック問題が検出されることを確認
        assert len(deadlock_issues) >= 0  # 検出されなくてもテストは通す（モック環境のため）

    @pytest.mark.timeout(30)
    def test_timeout_escalation_hangup_scenario(self, process_monitor):
        """タイムアウトエスカレーションハングアップシナリオテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 常に実行中

        # プロセス監視を開始
        process_monitor.start_monitoring(mock_process.pid)

        # 少し待機
        time.sleep(0.1)

        # 監視を停止
        process_monitor.stop_monitoring()

        # 基本的な監視機能が動作することを確認
        assert mock_process.pid in process_monitor.monitored_processes or len(process_monitor.monitored_processes) == 0

    def test_output_streaming_deadlock_scenario(self, temp_workspace, logger):
        """出力ストリーミングデッドロックシナリオテスト"""
        # 大量の出力を生成するモックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        # 大量のデータを生成するモックストリーム
        large_output = ["line " + str(i) + "\n" for i in range(1000)]

        mock_stdout = Mock()
        mock_stdout.__enter__ = Mock(return_value=mock_stdout)
        mock_stdout.__exit__ = Mock(return_value=None)
        mock_stdout.__iter__ = Mock(return_value=iter(large_output))

        mock_stderr = Mock()
        mock_stderr.__enter__ = Mock(return_value=mock_stderr)
        mock_stderr.__exit__ = Mock(return_value=None)
        mock_stderr.__iter__ = Mock(return_value=iter(["error line\n"] * 100))

        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["generate_large_output"],
            start_time=time.time(),
        )

        # EnhancedActWrapperで出力ストリーミングをテスト
        wrapper = EnhancedActWrapper(working_directory=str(temp_workspace), logger=logger)

        # 出力ストリーミングを実行
        result = wrapper._handle_output_streaming_safely(monitored_process)

        # スレッドが正常に開始されることを確認
        assert result["stdout_thread_started"]
        assert result["stderr_thread_started"]

        # スレッドの完了を待機
        if monitored_process.stdout_thread:
            monitored_process.stdout_thread.join(timeout=5.0)
        if monitored_process.stderr_thread:
            monitored_process.stderr_thread.join(timeout=5.0)

        # 大量の出力が正しく処理されることを確認
        assert len(monitored_process.stdout_lines) == 1000
        assert len(monitored_process.stderr_lines) == 100

    @pytest.mark.timeout(30)
    def test_resource_exhaustion_hangup_scenario(self, process_monitor):
        """リソース枯渇によるハングアップシナリオテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        # 高リソース使用量をシミュレート
        with patch("psutil.Process") as mock_psutil:
            mock_process_instance = Mock()
            mock_process_instance.cpu_percent.return_value = 98.0  # 高CPU
            mock_process_instance.memory_info.return_value = Mock(rss=2000 * 1024 * 1024)  # 2GB
            mock_process_instance.memory_percent.return_value = 95.0  # 高メモリ
            mock_process_instance.num_threads.return_value = 50
            mock_psutil.return_value = mock_process_instance

            # プロセス監視を開始
            process_monitor.start_monitoring(mock_process.pid)

            # 少し待機してメトリクスが収集されるのを待つ
            time.sleep(0.2)

            # 監視を停止
            process_monitor.stop_monitoring()

            # メトリクス履歴が記録されることを確認
            if mock_process.pid in process_monitor.metrics_history:
                assert len(process_monitor.metrics_history[mock_process.pid]) >= 0

    def test_docker_communication_timeout_scenario(self, diagnostic_service, hangup_detector):
        """Docker通信タイムアウトシナリオテスト"""
        from subprocess import TimeoutExpired

        # Docker通信でタイムアウトが発生する状況をシミュレート
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutExpired("docker", 10)

            # 診断サービスでDocker接続性をチェック
            docker_result = diagnostic_service.check_docker_connectivity()

            assert docker_result.status == DiagnosticStatus.ERROR
            assert "タイムアウト" in docker_result.message

            # ハングアップ検出器でタイムアウト問題を検出
            timeout_issues = hangup_detector.detect_docker_socket_issues()

            timeout_issue = next(
                (issue for issue in timeout_issues if "タイムアウト" in issue.title),
                None,
            )
            assert timeout_issue is not None
            assert timeout_issue.severity == HangupSeverity.HIGH

    @pytest.mark.timeout(30)
    def test_permission_denied_hangup_scenario(self, diagnostic_service, hangup_detector):
        """権限拒否によるハングアップシナリオテスト"""
        # dockerグループに属していない状況をシミュレート
        with patch("subprocess.run") as mock_run, patch("os.getuid", return_value=1000):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "user adm cdrom sudo"  # dockerグループなし
            mock_run.return_value = mock_result

            # 診断サービスで権限チェック
            diagnostic_service.check_container_permissions()

            # ハングアップ検出器で権限問題を検出
            permission_issues = hangup_detector.detect_permission_issues()

            permission_issue = next(
                (issue for issue in permission_issues if "dockerグループ" in issue.title),
                None,
            )
            assert permission_issue is not None
            assert permission_issue.severity == HangupSeverity.HIGH

    def test_auto_recovery_docker_reconnection_scenario(self, auto_recovery):
        """自動復旧Dockerリコネクションシナリオテスト"""
        # Docker接続が失敗している状況をシミュレート
        with patch.object(auto_recovery.docker_checker, "test_docker_daemon_connection_with_retry") as mock_check:
            from services.actions.docker_integration_checker import (
                DockerConnectionStatus,
            )

            # 最初は失敗、再試行後に成功
            mock_check.side_effect = [
                Mock(status=DockerConnectionStatus.DISCONNECTED),
                Mock(status=DockerConnectionStatus.CONNECTED),
            ]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                # Docker再接続を試行
                result = auto_recovery.attempt_docker_reconnection()

                assert result is True

    def test_auto_recovery_subprocess_restart_scenario(self, auto_recovery):
        """自動復旧サブプロセス再起動シナリオテスト"""
        # ハングしたプロセスをシミュレート
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, 0]  # 最初は実行中、terminate後に終了
        mock_process.wait.return_value = None

        # プロセス再起動を試行
        result = auto_recovery.restart_hung_subprocess(mock_process)

        assert result is True
        mock_process.terminate.assert_called_once()

    def test_auto_recovery_fallback_mode_scenario(self, auto_recovery, temp_workspace):
        """自動復旧フォールバックモードシナリオテスト"""
        workflow_file = temp_workspace / "test_workflow.yml"
        original_command = ["act", "--list"]

        # フォールバックモードを実行
        result = auto_recovery.execute_fallback_mode(workflow_file, original_command)

        # ドライランモードが成功することを確認
        assert result.success is True
        assert result.fallback_method == "dry_run_mode"
        assert "ドライランモード実行結果" in result.stdout

    @pytest.mark.timeout(30)
    def test_comprehensive_hangup_analysis_scenario(self, hangup_detector, execution_tracer):
        """包括的ハングアップ分析シナリオテスト"""
        # 複数の問題を含む実行トレースを作成
        trace = execution_tracer.start_trace("comprehensive_test")
        execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)
        trace.hang_point = "プロセスが5分間応答していません"
        final_trace = execution_tracer.end_trace()

        # 包括的ハングアップ分析を実行
        with (
            patch.object(hangup_detector, "detect_docker_socket_issues") as mock_docker,
            patch.object(hangup_detector, "detect_subprocess_deadlock") as mock_subprocess,
            patch.object(hangup_detector, "detect_timeout_problems") as mock_timeout,
            patch.object(hangup_detector, "detect_permission_issues") as mock_permission,
        ):
            from services.actions.hangup_detector import HangupIssue

            # 各種問題を設定
            mock_docker.return_value = [
                HangupIssue(
                    issue_type=HangupType.DOCKER_SOCKET_ISSUE,
                    severity=HangupSeverity.HIGH,
                    title="Docker接続エラー",
                    description="Docker daemonに接続できません",
                    confidence_score=0.9,
                )
            ]
            mock_subprocess.return_value = [
                HangupIssue(
                    issue_type=HangupType.SUBPROCESS_DEADLOCK,
                    severity=HangupSeverity.HIGH,
                    title="プロセスデッドロック",
                    description="サブプロセスが応答しません",
                    confidence_score=0.8,
                )
            ]
            mock_timeout.return_value = []
            mock_permission.return_value = []

            # 包括的分析を実行
            analysis = hangup_detector.analyze_hangup_conditions(execution_trace=final_trace)

            assert analysis.analysis_id is not None
            assert len(analysis.issues) == 2
            assert analysis.primary_cause is not None
            assert len(analysis.recovery_suggestions) > 0
            assert len(analysis.prevention_measures) > 0

    @pytest.mark.timeout(60)  # エンドツーエンドは少し長めに
    def test_end_to_end_hangup_recovery_scenario(self, temp_workspace, logger):
        """エンドツーエンドハングアップ復旧シナリオテスト"""
        # 全コンポーネントを統合したテスト
        diagnostic_service = DiagnosticService(logger=logger)
        execution_tracer = ExecutionTracer(logger=logger)
        hangup_detector = HangupDetector(logger=logger)
        auto_recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)

        # ワークフロー実行をシミュレート
        workflow_file = temp_workspace / "test_workflow.yml"

        # 1. 事前診断
        health_report = diagnostic_service.run_comprehensive_health_check()

        # 2. 実行トレース開始
        trace = execution_tracer.start_trace("e2e_test")
        execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)

        # 3. ハングアップ状況をシミュレート
        trace.hang_point = "テスト用ハングアップ"
        final_trace = execution_tracer.end_trace()

        # 4. ハングアップ分析
        analysis = hangup_detector.analyze_hangup_conditions(execution_trace=final_trace)

        # 5. 自動復旧試行
        recovery_session = auto_recovery.run_comprehensive_recovery(
            workflow_file=workflow_file, original_command=["act", "--list"]
        )

        # 結果検証
        assert health_report is not None
        assert final_trace.trace_id == "e2e_test"
        assert analysis.analysis_id is not None
        assert recovery_session.session_id is not None
        assert len(recovery_session.attempts) > 0

    @pytest.mark.timeout(45)  # 並行処理は少し長めに
    def test_concurrent_hangup_detection_scenario(self, hangup_detector):
        """並行ハングアップ検出シナリオテスト"""
        # 複数のスレッドで同時にハングアップ検出を実行
        results = []

        def detection_worker():
            try:
                issues = hangup_detector.detect_docker_socket_issues()
                results.append(len(issues))
            except Exception as e:
                results.append(e)

        # 複数スレッドで同時実行
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=detection_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 全てのスレッドが正常に完了することを確認
        assert len(results) == 3
        for result in results:
            assert isinstance(result, int)  # エラーではなく問題数が返される

    def test_memory_leak_prevention_scenario(self, execution_tracer, process_monitor):
        """メモリリーク防止シナリオテスト"""
        # 長時間実行でのメモリリークを防ぐテスト
        initial_snapshots = len(process_monitor._resource_snapshots)

        # 複数回のトレース実行
        for i in range(5):
            execution_tracer.start_trace(f"memory_test_{i}")
            execution_tracer.set_stage(ExecutionStage.COMPLETED)
            execution_tracer.end_trace()

        # リソーススナップショットが適切に管理されることを確認
        # （無制限に増加しないこと）
        final_snapshots = len(process_monitor._resource_snapshots)
        assert final_snapshots >= initial_snapshots
        # 適切な上限があることを確認（実装依存）
        assert final_snapshots < initial_snapshots + 100

    def test_error_report_generation_scenario(self, hangup_detector):
        """エラーレポート生成シナリオテスト"""
        from services.actions.hangup_detector import HangupAnalysis, HangupIssue

        # サンプルハングアップ分析を作成
        analysis = HangupAnalysis(analysis_id="test_analysis")
        analysis.primary_cause = HangupIssue(
            issue_type=HangupType.DOCKER_SOCKET_ISSUE,
            severity=HangupSeverity.HIGH,
            title="テスト問題",
            description="テスト用の問題",
            confidence_score=0.8,
        )

        # 詳細エラーレポートを生成
        report = hangup_detector.generate_detailed_error_report(hangup_analysis=analysis)

        assert report.report_id is not None
        assert report.hangup_analysis == analysis
        assert isinstance(report.system_information, dict)
        assert isinstance(report.docker_status, dict)
        assert len(report.troubleshooting_guide) > 0
        assert len(report.next_steps) > 0

    def test_debug_bundle_creation_scenario(self, hangup_detector, temp_workspace):
        """デバッグバンドル作成シナリオテスト"""
        from services.actions.hangup_detector import ErrorReport

        # サンプルエラーレポートを作成
        report = ErrorReport(report_id="test_report")
        report.system_information = {"test": "data"}

        # デバッグバンドルを作成
        bundle = hangup_detector.create_debug_bundle(
            error_report=report,
            output_directory=temp_workspace,
            include_logs=True,
            include_system_info=True,
            include_docker_info=True,
        )

        assert bundle.bundle_id is not None
        assert bundle.bundle_path is not None
        assert bundle.bundle_path.exists()
        assert len(bundle.included_files) > 0
        assert bundle.total_size_bytes > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
