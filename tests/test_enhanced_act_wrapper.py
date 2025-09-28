#!/usr/bin/env python3
"""
Enhanced Act Wrapper テスト

EnhancedActWrapperクラスの機能をテストします。
診断機能、デッドロック検出、安全なサブプロセス管理をカバーします。
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# テスト対象のインポート
import sys

sys.path.append(str(Path(__file__).parent.parent / "services"))
sys.path.append(str(Path(__file__).parent.parent / "services" / "actions"))

# モジュールを直接インポート
from services.actions.enhanced_act_wrapper import (
    EnhancedActWrapper,
    DeadlockIndicator,
    StreamResult,
    MonitoredProcess,
    DetailedResult,
)
from services.actions.execution_tracer import ExecutionTracer
from services.actions.logger import ActionsLogger


class TestEnhancedActWrapper(unittest.TestCase):
    """EnhancedActWrapperのテストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = Path(self.temp_dir)

        # テスト用のワークフローファイルを作成
        self.workflow_file = (
            self.working_directory / ".github" / "workflows" / "test.yml"
        )
        self.workflow_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.workflow_file, "w") as f:
            f.write("""
name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test step
        run: echo "Hello World"
""")

        # ロガーとトレーサーをモック
        self.mock_logger = Mock(spec=ActionsLogger)
        self.mock_logger.verbose = True
        self.mock_tracer = Mock(spec=ExecutionTracer)

        # 環境変数を設定（モックモード）
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

    def tearDown(self):
        """テストクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # 環境変数をクリア
        if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
            del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_enhanced_act_wrapper_initialization(self):
        """EnhancedActWrapperの初期化テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=True,
        )

        self.assertEqual(wrapper.working_directory, self.working_directory)
        self.assertTrue(wrapper.enable_diagnostics)
        self.assertEqual(wrapper.deadlock_detection_interval, 10.0)
        self.assertEqual(wrapper.output_stall_threshold, 60.0)

    def test_enhanced_act_wrapper_without_diagnostics(self):
        """診断機能無効でのEnhancedActWrapper初期化テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        self.assertFalse(wrapper.enable_diagnostics)
        self.assertIsNone(wrapper._diagnostic_service)

    def test_run_workflow_with_diagnostics_mock_mode(self):
        """モックモードでの診断付きワークフロー実行テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,  # 診断を無効にしてシンプルにテスト
        )

        result = wrapper.run_workflow_with_diagnostics(
            workflow_file=".github/workflows/test.yml",
            dry_run=True,
            verbose=True,
        )

        self.assertIsInstance(result, DetailedResult)
        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertIn("シミュレーション実行", result.stdout)
        self.assertIsNotNone(result.trace_id)

    @patch("services.actions.enhanced_act_wrapper.subprocess.Popen")
    def test_create_monitored_subprocess(self, mock_popen):
        """監視付きサブプロセス作成テスト"""
        # モックプロセスを設定
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process

        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        # 実際のactバイナリの代わりにechoコマンドを使用
        wrapper.act_binary = "echo"

        cmd = ["echo", "test"]
        env = {"TEST": "value"}
        timeout_seconds = 60.0

        monitored_process = wrapper._create_monitored_subprocess(
            cmd, env, timeout_seconds
        )

        self.assertIsInstance(monitored_process, MonitoredProcess)
        self.assertEqual(monitored_process.process, mock_process)
        self.assertEqual(monitored_process.command, cmd)
        self.assertEqual(monitored_process.timeout_seconds, timeout_seconds)
        self.assertIn(mock_process.pid, wrapper._active_processes)

    def test_detect_deadlock_conditions_no_issues(self):
        """デッドロック条件検出テスト - 問題なし"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["echo", "test"],
            start_time=time.time(),
            timeout_seconds=600.0,
            last_output_time=time.time(),  # 最近出力があった
        )

        indicators = wrapper.detect_deadlock_conditions(monitored_process)
        self.assertEqual(len(indicators), 0)

    def test_detect_deadlock_conditions_output_stalled(self):
        """デッドロック条件検出テスト - 出力停止"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            output_stall_threshold=30.0,  # 短いしきい値でテスト
        )

        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["echo", "test"],
            start_time=time.time(),
            timeout_seconds=600.0,
            last_output_time=time.time() - 60.0,  # 60秒前に最後の出力
            output_stalled_threshold=30.0,
        )

        indicators = wrapper.detect_deadlock_conditions(monitored_process)
        self.assertEqual(len(indicators), 1)
        self.assertEqual(indicators[0].indicator_type, "output_stalled")
        self.assertEqual(indicators[0].severity, "medium")

    def test_detect_deadlock_conditions_process_hung(self):
        """デッドロック条件検出テスト - プロセスハング"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["echo", "test"],
            start_time=time.time() - 500.0,  # 500秒前に開始
            timeout_seconds=600.0,
            last_output_time=time.time(),
        )

        indicators = wrapper.detect_deadlock_conditions(monitored_process)
        self.assertEqual(len(indicators), 1)
        self.assertEqual(indicators[0].indicator_type, "process_hung")
        self.assertEqual(indicators[0].severity, "high")

    def test_build_enhanced_command(self):
        """拡張コマンド構築テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        # 実際のactバイナリの代わりにechoコマンドを使用
        wrapper.act_binary = "echo"

        cmd = wrapper._build_enhanced_command(
            workflow_file="test.yml",
            job="test-job",
            dry_run=True,
            verbose=True,
            env_vars={"TEST": "value"},
        )

        self.assertIn("echo", cmd)
        self.assertIn("-W", cmd)
        self.assertIn("test.yml", cmd)
        self.assertIn("-j", cmd)
        self.assertIn("test-job", cmd)
        self.assertIn("--dryrun", cmd)
        self.assertIn("--verbose", cmd)
        self.assertIn("--rm", cmd)
        self.assertIn("--env", cmd)
        self.assertIn("TEST=value", cmd)

    def test_force_terminate_process(self):
        """プロセス強制終了テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 最初は実行中

        # kill()呼び出し後は終了状態にする
        def mock_kill():
            mock_process.poll.return_value = 0

        mock_process.kill.side_effect = mock_kill

        wrapper._force_terminate_process(mock_process)

        # kill()が呼ばれたことを確認
        mock_process.kill.assert_called_once()

    def test_stop_all_monitoring(self):
        """監視停止テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        # モックプロセスを追加
        mock_process = Mock()
        mock_process.pid = 12345
        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["echo", "test"],
            start_time=time.time(),
            timeout_seconds=600.0,
        )
        wrapper._active_processes[12345] = monitored_process

        # モック監視スレッドを追加
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        wrapper._monitoring_threads.append(mock_thread)

        wrapper._stop_all_monitoring()

        self.assertEqual(len(wrapper._active_processes), 0)
        self.assertEqual(len(wrapper._monitoring_threads), 0)

    def test_analyze_execution_failure_timeout(self):
        """実行失敗分析テスト - タイムアウト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        result = {
            "returncode": -1,
            "stderr": "Execution timeout",
            "stream_result": None,
        }

        analysis = wrapper._analyze_execution_failure(result)

        self.assertEqual(analysis["failure_type"], "timeout")
        self.assertIn("実行タイムアウト", analysis["probable_causes"])
        self.assertIn("タイムアウト時間を延長してください", analysis["recommendations"])

    def test_analyze_execution_failure_docker_error(self):
        """実行失敗分析テスト - Dockerエラー"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        result = {
            "returncode": 1,
            "stderr": "Docker daemon connection failed",
            "stream_result": None,
        }

        analysis = wrapper._analyze_execution_failure(result)

        self.assertEqual(analysis["failure_type"], "execution_error")
        self.assertIn("Docker関連の問題", analysis["probable_causes"])
        self.assertIn(
            "Docker daemonが実行されているか確認してください",
            analysis["recommendations"],
        )

    def test_analyze_execution_failure_deadlock(self):
        """実行失敗分析テスト - デッドロック"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
        )

        mock_stream_result = Mock()
        mock_stream_result.deadlock_detected = True

        result = {
            "returncode": 0,
            "stderr": "",
            "stream_result": mock_stream_result,
        }

        analysis = wrapper._analyze_execution_failure(result)

        self.assertEqual(analysis["failure_type"], "deadlock")
        self.assertIn("デッドロック検出", analysis["probable_causes"])
        self.assertIn(
            "出力ストリーミングの問題を確認してください", analysis["recommendations"]
        )

    def test_stream_result_initialization(self):
        """StreamResult初期化テスト"""
        stream_result = StreamResult()

        self.assertEqual(len(stream_result.stdout_lines), 0)
        self.assertEqual(len(stream_result.stderr_lines), 0)
        self.assertEqual(stream_result.stdout_bytes, 0)
        self.assertEqual(stream_result.stderr_bytes, 0)
        self.assertFalse(stream_result.threads_completed)
        self.assertFalse(stream_result.deadlock_detected)
        self.assertEqual(len(stream_result.deadlock_indicators), 0)

    def test_deadlock_indicator_creation(self):
        """DeadlockIndicator作成テスト"""
        indicator = DeadlockIndicator(
            indicator_type="test_type",
            severity="high",
            description="Test description",
            thread_id=12345,
            process_id=67890,
            details={"key": "value"},
        )

        self.assertEqual(indicator.indicator_type, "test_type")
        self.assertEqual(indicator.severity, "high")
        self.assertEqual(indicator.description, "Test description")
        self.assertEqual(indicator.thread_id, 12345)
        self.assertEqual(indicator.process_id, 67890)
        self.assertEqual(indicator.details["key"], "value")
        self.assertIsNotNone(indicator.detected_at)

    def test_detailed_result_creation(self):
        """DetailedResult作成テスト"""
        result = DetailedResult(
            success=True,
            returncode=0,
            stdout="Test output",
            stderr="",
            command="echo test",
            execution_time_ms=1000.0,
            trace_id="test_trace_123",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Test output")
        self.assertEqual(result.command, "echo test")
        self.assertEqual(result.execution_time_ms, 1000.0)
        self.assertEqual(result.trace_id, "test_trace_123")
        self.assertEqual(len(result.diagnostic_results), 0)
        self.assertEqual(len(result.deadlock_indicators), 0)


class TestEnhancedActWrapperIntegration(unittest.TestCase):
    """EnhancedActWrapperの統合テスト"""

    def setUp(self):
        """統合テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = Path(self.temp_dir)

        # 環境変数を設定（モックモード）
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"
        os.environ["ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS"] = "0.1"

    def tearDown(self):
        """統合テストクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # 環境変数をクリア
        for env_var in [
            "ACTIONS_SIMULATOR_ENGINE",
            "ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS",
        ]:
            if env_var in os.environ:
                del os.environ[env_var]

    def test_full_workflow_execution_mock_mode(self):
        """モックモードでの完全なワークフロー実行テスト"""
        # テスト用のワークフローファイルを作成
        workflow_file = (
            self.working_directory / ".github" / "workflows" / "integration_test.yml"
        )
        workflow_file.parent.mkdir(parents=True, exist_ok=True)

        with open(workflow_file, "w") as f:
            f.write("""
name: Integration Test Workflow
on: [push]
jobs:
  integration-test:
    runs-on: ubuntu-latest
    steps:
      - name: Integration test step
        run: echo "Integration test successful"
      - name: Another step
        run: echo "Another step completed"
""")

        # EnhancedActWrapperを作成
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            enable_diagnostics=False,  # 統合テストでは診断を無効にしてシンプルに
        )

        # ワークフローを実行
        result = wrapper.run_workflow_with_diagnostics(
            workflow_file=".github/workflows/integration_test.yml",
            job="integration-test",
            verbose=True,
        )

        # 結果を検証
        self.assertIsInstance(result, DetailedResult)
        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Integration Test Workflow", result.stdout)
        self.assertIn("integration-test", result.stdout)
        self.assertIsNotNone(result.trace_id)
        self.assertGreater(result.execution_time_ms, 0)

    def test_workflow_execution_with_environment_variables(self):
        """環境変数付きワークフロー実行テスト"""
        # テスト用のワークフローファイルを作成
        workflow_file = (
            self.working_directory / ".github" / "workflows" / "env_test.yml"
        )
        workflow_file.parent.mkdir(parents=True, exist_ok=True)

        with open(workflow_file, "w") as f:
            f.write("""
name: Environment Test Workflow
on: [push]
jobs:
  env-test:
    runs-on: ubuntu-latest
    steps:
      - name: Environment test step
        run: echo "Testing environment variables"
""")

        # EnhancedActWrapperを作成
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            enable_diagnostics=False,
        )

        # 環境変数付きでワークフローを実行
        env_vars = {
            "TEST_VAR": "test_value",
            "ANOTHER_VAR": "another_value",
        }

        result = wrapper.run_workflow_with_diagnostics(
            workflow_file=".github/workflows/env_test.yml",
            env_vars=env_vars,
            verbose=True,
        )

        # 結果を検証
        self.assertTrue(result.success)
        self.assertIn("Environment Test Workflow", result.stdout)
        self.assertIn("TEST_VAR=test_value", result.stdout)
        self.assertIn("ANOTHER_VAR=another_value", result.stdout)


class TestEnhancedActWrapperWithAutoRecovery(unittest.TestCase):
    """EnhancedActWrapper自動復旧機能テスト"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = Path(self.temp_dir)

        # モックモードを設定
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        self.mock_logger = Mock(spec=ActionsLogger)
        self.mock_logger.verbose = True
        self.mock_tracer = Mock(spec=ExecutionTracer)

    def tearDown(self):
        """テストクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # 環境変数をクリア
        if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
            del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_auto_recovery_properties(self):
        """自動復旧関連プロパティテスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        # プロパティの存在確認
        self.assertIsNotNone(wrapper.diagnostic_service)  # Noneでも属性は存在
        self.assertIsNotNone(wrapper.process_monitor)
        # auto_recoveryとdocker_integration_checkerは依存関係により None の可能性あり

        # ハングアップ検出器はexecution_tracerを返すはず
        self.assertEqual(wrapper.hangup_detector, wrapper.execution_tracer)

    def test_get_auto_recovery_statistics_no_recovery(self):
        """自動復旧統計取得テスト（復旧機能なし）"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        stats = wrapper.get_auto_recovery_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_sessions", stats)
        self.assertIn("successful_sessions", stats)
        self.assertIn("success_rate", stats)
        self.assertIn("auto_recovery_available", stats)

    def test_build_act_command(self):
        """actコマンド構築テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        # 実際のactバイナリの代わりにechoコマンドを使用
        wrapper.act_binary = "echo"

        cmd = wrapper._build_act_command(
            workflow_file="test.yml",
            event="push",
            job="test-job",
            dry_run=True,
            verbose=True,
            env_vars={"TEST_VAR": "test_value"},
        )

        expected_elements = [
            "echo",
            "push",
            "-j",
            "test-job",
            "-W",
            "test.yml",
            "--dry-run",
            "--verbose",
            "--env",
            "TEST_VAR=test_value",
        ]

        # 順序は重要でないので、全ての要素が含まれているかチェック
        for element in expected_elements:
            self.assertIn(element, cmd)

    def test_run_workflow_with_auto_recovery_mock_mode(self):
        """自動復旧付きワークフロー実行テスト（モックモード）"""
        # テスト用のワークフローファイルを作成
        workflow_dir = self.working_directory / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_file = workflow_dir / "test.yml"
        with open(workflow_file, "w") as f:
            f.write("""
name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test step
        run: echo "Hello World"
""")

        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        result = wrapper.run_workflow_with_auto_recovery(
            workflow_file=".github/workflows/test.yml",
            dry_run=True,
            enable_recovery=False,  # 復旧を無効にしてシンプルにテスト
        )

        self.assertIsInstance(result, DetailedResult)
        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)

    def test_run_workflow_with_auto_recovery_disabled(self):
        """自動復旧無効時のテスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.working_directory),
            logger=self.mock_logger,
            execution_tracer=self.mock_tracer,
            enable_diagnostics=False,
        )

        # 存在しないワークフローファイルでテスト
        result = wrapper.run_workflow_with_auto_recovery(
            workflow_file="/nonexistent/workflow.yml",
            enable_recovery=False,
        )

        # エラーが適切にハンドリングされることを確認
        self.assertFalse(result.success)
        self.assertIsInstance(result, DetailedResult)


if __name__ == "__main__":
    # テストを実行
    unittest.main(verbosity=2)
