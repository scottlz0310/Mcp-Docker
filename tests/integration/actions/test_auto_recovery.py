"""
GitHub Actions Simulator - AutoRecovery テスト
自動復旧メカニズムの機能をテストします。
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.actions.auto_recovery import (
    AutoRecovery,
    FallbackExecutionResult,
    RecoveryAttempt,
    RecoverySession,
    RecoveryStatus,
    RecoveryType,
)
from services.actions.docker_integration_checker import DockerConnectionStatus
from services.actions.logger import ActionsLogger


class TestAutoRecovery(unittest.TestCase):
    """AutoRecoveryクラスのテスト"""

    def setUp(self):
        """テストセットアップ"""
        self.logger = ActionsLogger(verbose=False)
        self.mock_docker_checker = Mock()
        self.auto_recovery = AutoRecovery(
            logger=self.logger,
            docker_checker=self.mock_docker_checker,
            max_recovery_attempts=2,
            recovery_timeout=30.0,
            enable_fallback_mode=True,
        )

    def test_init(self):
        """初期化テスト"""
        self.assertIsNotNone(self.auto_recovery.logger)
        self.assertIsNotNone(self.auto_recovery.docker_checker)
        self.assertEqual(self.auto_recovery.max_recovery_attempts, 2)
        self.assertEqual(self.auto_recovery.recovery_timeout, 30.0)
        self.assertTrue(self.auto_recovery.enable_fallback_mode)

    @patch("subprocess.run")
    def test_attempt_docker_reconnection_success(self, mock_run):
        """Docker再接続成功テスト"""
        # Docker接続が既に正常な場合
        self.mock_docker_checker.test_docker_daemon_connection_with_retry.return_value = Mock(
            status=DockerConnectionStatus.CONNECTED
        )

        result = self.auto_recovery.attempt_docker_reconnection()
        self.assertTrue(result)

    @patch("subprocess.run")
    def test_attempt_docker_reconnection_with_restart(self, mock_run):
        """Docker再接続（再起動付き）テスト"""
        # 最初は接続失敗、再起動後に成功
        self.mock_docker_checker.test_docker_daemon_connection_with_retry.side_effect = [
            Mock(status=DockerConnectionStatus.DISCONNECTED),  # 最初は失敗
            Mock(status=DockerConnectionStatus.CONNECTED),  # 再起動後は成功
        ]

        # Docker daemon再起動コマンドが成功
        mock_run.return_value = Mock(returncode=0)

        result = self.auto_recovery.attempt_docker_reconnection()
        self.assertTrue(result)

    def test_restart_hung_subprocess_already_terminated(self):
        """既に終了したプロセスの再起動テスト"""
        # 既に終了したプロセスをモック
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # 既に終了

        result = self.auto_recovery.restart_hung_subprocess(mock_process)
        self.assertTrue(result)

    def test_restart_hung_subprocess_sigterm_success(self):
        """SIGTERM成功テスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, 0]  # 最初は実行中、terminate後に終了
        mock_process.wait.return_value = None  # SIGTERM後に正常終了

        result = self.auto_recovery.restart_hung_subprocess(mock_process)
        self.assertTrue(result)
        mock_process.terminate.assert_called_once()

    def test_restart_hung_subprocess_sigkill_required(self):
        """SIGKILL必要テスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [
            None,
            None,
            0,
        ]  # SIGTERM後も実行中、SIGKILL後に終了
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("", 5), None]

        result = self.auto_recovery.restart_hung_subprocess(mock_process)
        self.assertTrue(result)
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_restart_hung_subprocess_null_process(self):
        """Nullプロセステスト"""
        result = self.auto_recovery.restart_hung_subprocess(None)
        self.assertFalse(result)

    @patch("os.sync")
    @patch("sys.stdout")
    @patch("sys.stderr")
    def test_clear_output_buffers(self, mock_stderr, mock_stdout, mock_sync):
        """出力バッファクリアテスト"""
        mock_stdout.flush.return_value = None
        mock_stderr.flush.return_value = None
        mock_sync.return_value = None

        self.auto_recovery.clear_output_buffers()

        mock_stdout.flush.assert_called_once()
        mock_stderr.flush.assert_called_once()
        mock_sync.assert_called_once()

    @patch("subprocess.run")
    def test_reset_container_state_success(self, mock_run):
        """コンテナ状態リセット成功テスト"""
        # 全てのDockerコマンドが成功
        mock_run.return_value = Mock(returncode=0, stdout="container123\n")

        result = self.auto_recovery.reset_container_state()
        self.assertTrue(result)

    @patch("subprocess.run")
    def test_reset_container_state_partial_success(self, mock_run):
        """コンテナ状態リセット部分成功テスト"""
        # 一部のDockerコマンドが失敗するが、いくつかは成功
        mock_run.side_effect = [
            Mock(returncode=0, stdout="container123\n"),  # ps成功
            Mock(returncode=0),  # stop成功
            Mock(returncode=1, stderr="error"),  # container prune失敗
            Mock(returncode=0),  # network prune成功
            Mock(returncode=0),  # volume prune成功
            Mock(returncode=0),  # system prune成功
        ]

        result = self.auto_recovery.reset_container_state()
        # 部分的成功でもTrueを返すことを確認（成功指標があるため）
        self.assertTrue(result)

    def test_execute_fallback_mode_disabled(self):
        """フォールバックモード無効テスト"""
        auto_recovery = AutoRecovery(logger=self.logger, enable_fallback_mode=False)

        workflow_file = Path("/tmp/test_workflow.yml")
        original_command = ["act", "--list"]

        result = auto_recovery.execute_fallback_mode(workflow_file, original_command)

        self.assertFalse(result.success)
        self.assertEqual(result.fallback_method, "disabled")
        self.assertIn("フォールバックモードが無効です", result.stderr)

    @patch("subprocess.run")
    def test_execute_fallback_mode_direct_docker_success(self, mock_run):
        """フォールバック直接Docker実行成功テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
            workflow_file = Path(f.name)

        try:
            # Docker runコマンドが成功
            mock_run.return_value = Mock(
                returncode=0,
                stdout="ワークフローファイル解析: test.yml\nname: test",
                stderr="",
            )

            result = self.auto_recovery.execute_fallback_mode(workflow_file, ["act"])

            self.assertTrue(result.success)
            self.assertEqual(result.fallback_method, "direct_docker_run")
            self.assertIn("ワークフローファイル解析", result.stdout)

        finally:
            workflow_file.unlink()

    @patch("subprocess.run")
    def test_execute_fallback_mode_all_methods_fail(self, mock_run):
        """全フォールバック方法失敗テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test")
            workflow_file = Path(f.name)

        try:
            # 全てのDockerコマンドが失敗（ドライランモードは除く）
            mock_run.return_value = Mock(returncode=1, stderr="Docker error")

            # ドライランモードを無効にするため、フォールバック方法を制限
            original_methods = self.auto_recovery._fallback_methods
            self.auto_recovery._fallback_methods = [
                "direct_docker_run",
                "simplified_act_execution",
            ]

            result = self.auto_recovery.execute_fallback_mode(workflow_file, ["act"])

            self.assertFalse(result.success)
            self.assertEqual(result.fallback_method, "all_failed")

            # 元の設定を復元
            self.auto_recovery._fallback_methods = original_methods

        finally:
            workflow_file.unlink()

    def test_run_comprehensive_recovery(self):
        """包括的復旧処理テスト"""
        # モックプロセス
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0

        # Docker接続が成功
        self.mock_docker_checker.test_docker_daemon_connection_with_retry.return_value = Mock(
            status=DockerConnectionStatus.CONNECTED
        )

        # 一時的なワークフローファイル
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test")
            workflow_file = Path(f.name)

        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="")

                session = self.auto_recovery.run_comprehensive_recovery(
                    failed_process=mock_process,
                    workflow_file=workflow_file,
                    original_command=["act"],
                )

                self.assertIsNotNone(session.session_id)
                self.assertIsNotNone(session.start_time)
                self.assertIsNotNone(session.end_time)
                self.assertGreater(len(session.attempts), 0)

        finally:
            workflow_file.unlink()

    def test_get_recovery_statistics_empty(self):
        """復旧統計（空）テスト"""
        stats = self.auto_recovery.get_recovery_statistics()

        self.assertEqual(stats["total_sessions"], 0)
        self.assertEqual(stats["successful_sessions"], 0)
        self.assertEqual(stats["success_rate"], 0.0)
        self.assertFalse(stats["current_session_active"])
        self.assertIsNone(stats["last_session_time"])

    def test_get_recovery_statistics_with_history(self):
        """復旧統計（履歴あり）テスト"""
        # 手動で復旧履歴を追加
        session1 = RecoverySession(session_id="test1")
        session1.overall_success = True
        session1.attempts = [
            RecoveryAttempt(
                recovery_type=RecoveryType.DOCKER_RECONNECTION,
                status=RecoveryStatus.SUCCESS,
            )
        ]

        session2 = RecoverySession(session_id="test2")
        session2.overall_success = False
        session2.attempts = [
            RecoveryAttempt(
                recovery_type=RecoveryType.DOCKER_RECONNECTION,
                status=RecoveryStatus.FAILED,
            )
        ]

        self.auto_recovery._recovery_history = [session1, session2]

        stats = self.auto_recovery.get_recovery_statistics()

        self.assertEqual(stats["total_sessions"], 2)
        self.assertEqual(stats["successful_sessions"], 1)
        self.assertEqual(stats["success_rate"], 0.5)
        self.assertIn("docker_reconnection", stats["recovery_type_statistics"])

    @patch("subprocess.run")
    def test_private_methods_docker_operations(self, mock_run):
        """プライベートメソッド（Docker操作）テスト"""
        # Docker daemon再起動
        mock_run.return_value = Mock(returncode=0)
        result = self.auto_recovery._restart_docker_daemon()
        self.assertTrue(result)

        # Docker socket権限修正
        mock_run.return_value = Mock(returncode=0)
        result = self.auto_recovery._fix_docker_socket_permissions()
        self.assertTrue(result)

        # actコンテナ停止
        mock_run.side_effect = [
            Mock(returncode=0, stdout="container1\ncontainer2\n"),  # ps
            Mock(returncode=0),  # stop
            Mock(returncode=0),  # system prune用の追加モック
        ]
        result = self.auto_recovery._stop_act_containers()
        self.assertEqual(result, 2)

        # Docker system prune（新しいモックインスタンスで実行）
        mock_run.reset_mock()
        mock_run.return_value = Mock(returncode=0)
        result = self.auto_recovery._run_docker_system_prune()
        self.assertTrue(result)

    def test_fallback_methods(self):
        """フォールバック方法テスト"""
        # 一時的なワークフローファイル
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
            workflow_file = Path(f.name)

        try:
            # ドライランモード（常に成功するはず）
            result = self.auto_recovery._fallback_dry_run_mode(workflow_file)
            self.assertTrue(result.success)
            self.assertEqual(result.fallback_method, "dry_run_mode")
            self.assertIn("ドライランモード実行結果", result.stdout)

        finally:
            workflow_file.unlink()

    def test_recovery_attempt_dataclass(self):
        """RecoveryAttemptデータクラステスト"""
        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.BUFFER_CLEAR,
            status=RecoveryStatus.SUCCESS,
            message="テスト復旧",
        )

        self.assertEqual(attempt.recovery_type, RecoveryType.BUFFER_CLEAR)
        self.assertEqual(attempt.status, RecoveryStatus.SUCCESS)
        self.assertEqual(attempt.message, "テスト復旧")
        self.assertIsNotNone(attempt.start_time)

    def test_fallback_execution_result_dataclass(self):
        """FallbackExecutionResultデータクラステスト"""
        result = FallbackExecutionResult(
            success=True,
            returncode=0,
            stdout="test output",
            stderr="",
            execution_time_ms=100.0,
            fallback_method="test_method",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test output")
        self.assertEqual(result.fallback_method, "test_method")

    def test_recovery_session_dataclass(self):
        """RecoverySessionデータクラステスト"""
        session = RecoverySession(session_id="test_session")

        self.assertEqual(session.session_id, "test_session")
        self.assertIsNotNone(session.start_time)
        self.assertFalse(session.overall_success)
        self.assertFalse(session.fallback_mode_activated)

    @patch("time.sleep")
    def test_recovery_with_timeout(self, mock_sleep):
        """タイムアウト付き復旧テスト"""
        # タイムアウトが短い設定でテスト
        auto_recovery = AutoRecovery(
            logger=self.logger,
            docker_checker=self.mock_docker_checker,
            recovery_timeout=1.0,  # 1秒でタイムアウト
        )

        # Docker接続が成功
        self.mock_docker_checker.test_docker_daemon_connection_with_retry.return_value = Mock(
            status=DockerConnectionStatus.CONNECTED
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            session = auto_recovery.run_comprehensive_recovery()
            self.assertIsNotNone(session)

    def test_thread_safety(self):
        """スレッドセーフティテスト"""
        import threading

        results = []

        def recovery_worker():
            try:
                stats = self.auto_recovery.get_recovery_statistics()
                results.append(stats)
            except Exception as e:
                results.append(e)

        # 複数スレッドで同時実行
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=recovery_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 全てのスレッドが正常に完了することを確認
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
