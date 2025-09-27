"""
GitHub Actions Simulator - EnhancedActWrapper テスト
改良されたActWrapperの診断機能、プロセス監視、デッドロック検出機能をテストします。
"""

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.actions.enhanced_act_wrapper import (
    DeadlockIndicator,
    DeadlockType,
    DetailedResult,
    EnhancedActWrapper,
    MonitoredProcess,
    ProcessMonitor,
)
from services.actions.diagnostic import DiagnosticService, DiagnosticStatus
from services.actions.execution_tracer import ExecutionTracer
from services.actions.logger import ActionsLogger


class TestProcessMonitor(unittest.TestCase):
    """ProcessMonitorクラスのテスト"""

    def setUp(self):
        """テストセットアップ"""
        self.logger = ActionsLogger(verbose=False)
        self.process_monitor = ProcessMonitor(
            logger=self.logger,
            deadlock_detection_interval=1.0,
            activity_timeout=5.0
        )

    def test_monitor_with_heartbeat_normal_completion(self):
        """正常完了時のプロセス監視テスト"""
        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        # 最初は実行中、その後完了を返すように設定
        poll_results = [None, None, 0, 0, 0]  # 十分な数の結果を用意
        mock_process.poll.side_effect = poll_results

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["echo", "test"],
            start_time=time.time()
        )

        # 短いタイムアウトで監視
        timed_out, deadlock_indicators = self.process_monitor.monitor_with_heartbeat(
            monitored_process, timeout=10
        )

        self.assertFalse(timed_out)
        self.assertEqual(len(deadlock_indicators), 0)

    def test_monitor_with_heartbeat_timeout(self):
        """タイムアウト時のプロセス監視テスト"""
        # モックプロセスを作成（常に実行中を返す）
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 常に実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["sleep", "100"],
            start_time=time.time()
        )

        # 短いタイムアウトで監視
        timed_out, deadlock_indicators = self.process_monitor.monitor_with_heartbeat(
            monitored_process, timeout=2
        )

        self.assertTrue(timed_out)

    def test_detect_deadlock_conditions_inactive_process(self):
        """非アクティブプロセスのデッドロック検出テスト"""
        mock_process = Mock()
        mock_process.pid = 12345

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test"],
            start_time=time.time(),
            last_activity=time.time() - 10.0  # 10秒前
        )

        indicators = self.process_monitor.detect_deadlock_conditions(monitored_process)

        # アクティビティタイムアウト（5秒）を超えているのでデッドロック検出
        self.assertTrue(len(indicators) > 0)
        self.assertTrue(any(
            indicator.deadlock_type == DeadlockType.PROCESS_WAIT
            for indicator in indicators
        ))

    def test_force_cleanup_on_timeout(self):
        """タイムアウト時の強制クリーンアップテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 実行中
        mock_process.terminate.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("test", 5)
        mock_process.kill.return_value = None

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test"],
            start_time=time.time()
        )

        # 強制クリーンアップを実行
        self.process_monitor.force_cleanup_on_timeout(monitored_process)

        # terminate と kill が呼ばれることを確認
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        self.assertTrue(monitored_process.force_killed)


class TestEnhancedActWrapper(unittest.TestCase):
    """EnhancedActWrapperクラスのテスト"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = Path(self.temp_dir)

        # テスト用のワークフローファイルを作成
        self.workflow_file = self.working_directory / "test_workflow.yml"
        self.workflow_file.write_text("""
name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test step
        run: echo "Hello, World!"
""")

        self.logger = ActionsLogger(verbose=False)
        self.execution_tracer = ExecutionTracer(logger=self.logger)
        self.diagnostic_service = DiagnosticService(logger=self.logger)

    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('services.actions.enhanced_act_wrapper.subprocess.Popen')
    def test_create_monitored_subprocess(self, mock_popen):
        """監視対象サブプロセス作成テスト"""
        # モックプロセスを設定
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service
        )

        # actバイナリをモックに設定
        wrapper.act_binary = "mock-act"

        cmd = ["mock-act", "--version"]
        process_env = {"TEST": "value"}

        monitored_process = wrapper._create_monitored_subprocess(cmd, process_env)

        self.assertEqual(monitored_process.process, mock_process)
        self.assertEqual(monitored_process.command, cmd)
        self.assertEqual(monitored_process.process.pid, 12345)

        # subprocess.Popenが正しい引数で呼ばれることを確認
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        self.assertEqual(call_args[0][0], cmd)
        self.assertEqual(call_args[1]['env'], process_env)

    def test_handle_output_streaming_safely(self):
        """安全な出力ストリーミング処理テスト"""
        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345

        # コンテキストマネージャーをサポートするモックを作成
        mock_stdout = Mock()
        mock_stdout.__enter__ = Mock(return_value=mock_stdout)
        mock_stdout.__exit__ = Mock(return_value=None)
        mock_stdout.__iter__ = Mock(return_value=iter(["line1\n", "line2\n"]))

        mock_stderr = Mock()
        mock_stderr.__enter__ = Mock(return_value=mock_stderr)
        mock_stderr.__exit__ = Mock(return_value=None)
        mock_stderr.__iter__ = Mock(return_value=iter(["error1\n", "error2\n"]))

        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test"],
            start_time=time.time()
        )

        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service
        )

        # 出力ストリーミングを実行
        result = wrapper._handle_output_streaming_safely(monitored_process)

        self.assertTrue(result["stdout_thread_started"])
        self.assertTrue(result["stderr_thread_started"])
        self.assertIsNotNone(monitored_process.stdout_thread)
        self.assertIsNotNone(monitored_process.stderr_thread)

        # スレッドの完了を待機
        if monitored_process.stdout_thread:
            monitored_process.stdout_thread.join(timeout=2.0)
        if monitored_process.stderr_thread:
            monitored_process.stderr_thread.join(timeout=2.0)

        # 出力が正しく収集されることを確認
        self.assertEqual(monitored_process.stdout_lines, ["line1\n", "line2\n"])
        self.assertEqual(monitored_process.stderr_lines, ["error1\n", "error2\n"])

    @patch('services.actions.enhanced_act_wrapper.subprocess.Popen')
    def test_run_workflow_with_diagnostics_mock_mode(self, mock_popen):
        """診断機能付きワークフロー実行テスト（モックモード）"""
        # モックモードを有効にする
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            wrapper = EnhancedActWrapper(
                working_directory=str(self.working_directory),
                logger=self.logger,
                execution_tracer=self.execution_tracer,
                diagnostic_service=self.diagnostic_service
            )

            result = wrapper.run_workflow_with_diagnostics(
                workflow_file="test_workflow.yml",
                dry_run=True,
                pre_execution_diagnostics=False  # 診断をスキップしてテストを高速化
            )

            self.assertIsInstance(result, DetailedResult)
            self.assertTrue(result.success)
            self.assertEqual(result.returncode, 0)
            self.assertIn("ドライラン実行", result.stdout)

        finally:
            # 環境変数をクリーンアップ
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_analyze_hang_condition(self):
        """ハングアップ条件分析テスト"""
        mock_process = Mock()
        mock_process.pid = 12345

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time() - 100,  # 100秒前に開始
            force_killed=True
        )

        # デッドロック指標を作成
        deadlock_indicators = [
            DeadlockIndicator(
                deadlock_type=DeadlockType.DOCKER_COMMUNICATION,
                process_pid=12345,
                details={"error": "connection timeout"},
                recommendations=["Docker daemonを確認してください"]
            ),
            DeadlockIndicator(
                deadlock_type=DeadlockType.STDOUT_THREAD,
                thread_name="stdout-thread",
                process_pid=12345,
                details={"thread_alive": False},
                recommendations=["出力バッファを確認してください"]
            )
        ]

        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service
        )

        analysis = wrapper._analyze_hang_condition(monitored_process, deadlock_indicators)

        # HangupAnalysisオブジェクトの属性をテスト
        self.assertIsNotNone(analysis.analysis_id)
        self.assertIsNotNone(analysis.start_time)
        self.assertIsInstance(analysis.issues, list)
        self.assertIsInstance(analysis.recovery_suggestions, list)
        self.assertIsInstance(analysis.prevention_measures, list)

    def test_build_command(self):
        """コマンド構築テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service
        )

        # actバイナリをモックに設定
        wrapper.act_binary = "mock-act"

        cmd = wrapper._build_command(
            workflow_file="test.yml",
            event="push",
            job="test-job",
            dry_run=True,
            verbose=True,
            env_vars={"TEST_VAR": "test_value"}
        )

        expected_elements = [
            "mock-act",
            "-W", "test.yml",
            "-j", "test-job",
            "--dryrun",
            "--verbose",
            "--env", "TEST_VAR=test_value"
        ]

        for element in expected_elements:
            self.assertIn(element, cmd)


class TestDeadlockIndicator(unittest.TestCase):
    """DeadlockIndicatorクラスのテスト"""

    def test_deadlock_indicator_creation(self):
        """デッドロック指標作成テスト"""
        indicator = DeadlockIndicator(
            deadlock_type=DeadlockType.STDOUT_THREAD,
            thread_name="test-thread",
            process_pid=12345,
            details={"test": "value"},
            severity="HIGH",
            recommendations=["recommendation1", "recommendation2"]
        )

        self.assertEqual(indicator.deadlock_type, DeadlockType.STDOUT_THREAD)
        self.assertEqual(indicator.thread_name, "test-thread")
        self.assertEqual(indicator.process_pid, 12345)
        self.assertEqual(indicator.details["test"], "value")
        self.assertEqual(indicator.severity, "HIGH")
        self.assertEqual(len(indicator.recommendations), 2)
        self.assertIsNotNone(indicator.detected_at)


class TestDetailedResult(unittest.TestCase):
    """DetailedResultクラスのテスト"""

    def test_detailed_result_creation(self):
        """詳細結果作成テスト"""
        diagnostic_results = [
            Mock(component="test", status=DiagnosticStatus.OK, message="test message")
        ]
        deadlock_indicators = [
            DeadlockIndicator(deadlock_type=DeadlockType.PROCESS_WAIT, process_pid=12345)
        ]

        result = DetailedResult(
            success=True,
            returncode=0,
            stdout="test output",
            stderr="",
            command="test command",
            execution_time_ms=1000.0,
            diagnostic_results=diagnostic_results,
            deadlock_indicators=deadlock_indicators,
            process_monitoring_data={"test": "data"},
            hang_analysis={"hang_detected": False}
        )

        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test output")
        self.assertEqual(result.execution_time_ms, 1000.0)
        self.assertEqual(len(result.diagnostic_results), 1)
        self.assertEqual(len(result.deadlock_indicators), 1)
        self.assertIsNotNone(result.process_monitoring_data)
        self.assertIsNotNone(result.hang_analysis)


if __name__ == "__main__":
    unittest.main()
