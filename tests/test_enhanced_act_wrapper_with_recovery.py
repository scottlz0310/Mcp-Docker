"""
GitHub Actions Simulator - EnhancedActWrapper with AutoRecovery 統合テスト
自動復旧機能が統合されたEnhancedActWrapperの機能をテストします。
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.logger import ActionsLogger


class TestEnhancedActWrapperWithRecovery(unittest.TestCase):
    """EnhancedActWrapper with AutoRecovery統合テスト"""

    def setUp(self):
        """テストセットアップ"""
        self.logger = ActionsLogger(verbose=False)
        self.enhanced_wrapper = EnhancedActWrapper(
            logger=self.logger,
            enable_diagnostics=True
        )

    def test_auto_recovery_initialization(self):
        """自動復旧機能の初期化テスト"""
        self.assertIsNotNone(self.enhanced_wrapper.auto_recovery)
        self.assertEqual(self.enhanced_wrapper.auto_recovery.max_recovery_attempts, 3)
        self.assertTrue(self.enhanced_wrapper.auto_recovery.enable_fallback_mode)

    def test_get_auto_recovery_statistics(self):
        """自動復旧統計取得テスト"""
        stats = self.enhanced_wrapper.get_auto_recovery_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_sessions", stats)
        self.assertIn("successful_sessions", stats)
        self.assertIn("success_rate", stats)
        self.assertEqual(stats["total_sessions"], 0)  # 初期状態では0

    def test_build_act_command(self):
        """actコマンド構築テスト"""
        cmd = self.enhanced_wrapper._build_act_command(
            workflow_file="test.yml",
            event="push",
            job="test-job",
            dry_run=True,
            verbose=True,
            env_vars={"TEST_VAR": "test_value"}
        )

        expected_elements = ["act", "push", "-j", "test-job", "-W", "test.yml", "--dry-run", "--verbose", "--env", "TEST_VAR=test_value"]

        # 順序は重要でないので、全ての要素が含まれているかチェック
        for element in expected_elements:
            self.assertIn(element, cmd)

    @patch('services.actions.enhanced_act_wrapper.EnhancedActWrapper.run_workflow_with_diagnostics')
    def test_run_workflow_with_auto_recovery_success(self, mock_run_diagnostics):
        """自動復旧付きワークフロー実行成功テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("name: test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
            workflow_file = f.name

        try:
            # プライマリ実行が成功する場合
            from services.actions.enhanced_act_wrapper import DetailedResult
            mock_result = DetailedResult(
                success=True,
                returncode=0,
                stdout="test output",
                stderr="",
                command="act",
                execution_time_ms=1000.0
            )
            mock_run_diagnostics.return_value = mock_result

            result = self.enhanced_wrapper.run_workflow_with_auto_recovery(
                workflow_file=workflow_file,
                enable_recovery=True
            )

            self.assertTrue(result.success)
            self.assertEqual(result.stdout, "test output")
            mock_run_diagnostics.assert_called_once()

        finally:
            Path(workflow_file).unlink()

    @patch('services.actions.enhanced_act_wrapper.EnhancedActWrapper.run_workflow_with_diagnostics')
    def test_run_workflow_with_auto_recovery_failure_no_recovery(self, mock_run_diagnostics):
        """自動復旧無効時の失敗テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("name: test")
            workflow_file = f.name

        try:
            # プライマリ実行が失敗する場合
            from services.actions.enhanced_act_wrapper import DetailedResult
            mock_result = DetailedResult(
                success=False,
                returncode=1,
                stdout="",
                stderr="test error",
                command="act",
                execution_time_ms=1000.0
            )
            mock_run_diagnostics.return_value = mock_result

            result = self.enhanced_wrapper.run_workflow_with_auto_recovery(
                workflow_file=workflow_file,
                enable_recovery=False  # 復旧無効
            )

            self.assertFalse(result.success)
            self.assertEqual(result.stderr, "test error")
            mock_run_diagnostics.assert_called_once()

        finally:
            Path(workflow_file).unlink()

    @patch('services.actions.enhanced_act_wrapper.EnhancedActWrapper.run_workflow_with_diagnostics')
    @patch('services.actions.auto_recovery.AutoRecovery.run_comprehensive_recovery')
    def test_run_workflow_with_auto_recovery_with_recovery(self, mock_recovery, mock_run_diagnostics):
        """自動復旧付きワークフロー実行（復旧あり）テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("name: test")
            workflow_file = f.name

        try:
            # プライマリ実行が失敗、復旧後の再実行が成功
            from services.actions.enhanced_act_wrapper import DetailedResult
            from services.actions.auto_recovery import RecoverySession, RecoveryAttempt, RecoveryType, RecoveryStatus

            failed_result = DetailedResult(
                success=False,
                returncode=1,
                stdout="",
                stderr="test error",
                command="act",
                execution_time_ms=1000.0
            )

            success_result = DetailedResult(
                success=True,
                returncode=0,
                stdout="recovery success",
                stderr="",
                command="act",
                execution_time_ms=1000.0
            )

            mock_run_diagnostics.side_effect = [failed_result, success_result]

            # 復旧セッションをモック
            recovery_session = RecoverySession(session_id="test_session")
            recovery_session.overall_success = True
            recovery_session.attempts = [
                RecoveryAttempt(
                    recovery_type=RecoveryType.DOCKER_RECONNECTION,
                    status=RecoveryStatus.SUCCESS
                )
            ]
            mock_recovery.return_value = recovery_session

            result = self.enhanced_wrapper.run_workflow_with_auto_recovery(
                workflow_file=workflow_file,
                enable_recovery=True,
                max_recovery_attempts=1
            )

            self.assertTrue(result.success)
            self.assertEqual(result.stdout, "recovery success")
            self.assertEqual(mock_run_diagnostics.call_count, 2)  # 初回 + 復旧後
            mock_recovery.assert_called_once()

        finally:
            Path(workflow_file).unlink()

    @patch('services.actions.enhanced_act_wrapper.EnhancedActWrapper.run_workflow_with_diagnostics')
    @patch('services.actions.auto_recovery.AutoRecovery.run_comprehensive_recovery')
    @patch('services.actions.auto_recovery.AutoRecovery.execute_fallback_mode')
    def test_run_workflow_with_fallback_execution(self, mock_fallback, mock_recovery, mock_run_diagnostics):
        """フォールバック実行テスト"""
        # 一時的なワークフローファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("name: test")
            workflow_file = f.name

        try:
            # プライマリ実行が失敗、復旧も失敗、フォールバックが成功
            from services.actions.enhanced_act_wrapper import DetailedResult
            from services.actions.auto_recovery import RecoverySession, FallbackExecutionResult

            failed_result = DetailedResult(
                success=False,
                returncode=1,
                stdout="",
                stderr="test error",
                command="act",
                execution_time_ms=1000.0
            )

            mock_run_diagnostics.side_effect = [failed_result, failed_result]  # 初回と復旧後も失敗

            # 復旧セッションは失敗
            recovery_session = RecoverySession(session_id="test_session")
            recovery_session.overall_success = False
            mock_recovery.return_value = recovery_session

            # フォールバック実行は成功
            fallback_result = FallbackExecutionResult(
                success=True,
                returncode=0,
                stdout="fallback success",
                stderr="",
                execution_time_ms=500.0,
                fallback_method="dry_run_mode",
                limitations=["ドライランモードでの実行"],
                warnings=["完全な機能は利用できません"]
            )
            mock_fallback.return_value = fallback_result

            result = self.enhanced_wrapper.run_workflow_with_auto_recovery(
                workflow_file=workflow_file,
                enable_recovery=True,
                max_recovery_attempts=1
            )

            self.assertTrue(result.success)
            self.assertEqual(result.stdout, "fallback success")
            mock_fallback.assert_called_once()

        finally:
            Path(workflow_file).unlink()

    def test_integration_with_existing_components(self):
        """既存コンポーネントとの統合テスト"""
        # 各コンポーネントが正しく初期化されているかテスト
        self.assertIsNotNone(self.enhanced_wrapper.diagnostic_service)
        self.assertIsNotNone(self.enhanced_wrapper.process_monitor)
        self.assertIsNotNone(self.enhanced_wrapper.docker_integration_checker)
        self.assertIsNotNone(self.enhanced_wrapper.hangup_detector)
        self.assertIsNotNone(self.enhanced_wrapper.auto_recovery)

        # AutoRecoveryがDockerIntegrationCheckerを使用していることを確認
        self.assertEqual(
            self.enhanced_wrapper.auto_recovery.docker_checker,
            self.enhanced_wrapper.docker_integration_checker
        )

    def test_auto_recovery_configuration(self):
        """自動復旧設定テスト"""
        # カスタム設定でEnhancedActWrapperを作成
        custom_wrapper = EnhancedActWrapper(
            logger=self.logger,
            enable_diagnostics=True
        )

        # AutoRecoveryの設定を確認
        auto_recovery = custom_wrapper.auto_recovery
        self.assertEqual(auto_recovery.max_recovery_attempts, 3)
        self.assertEqual(auto_recovery.recovery_timeout, 60.0)
        self.assertTrue(auto_recovery.enable_fallback_mode)

    def test_error_handling_in_recovery_method(self):
        """復旧メソッドでのエラーハンドリングテスト"""
        # 無効なワークフローファイルでテスト
        result = self.enhanced_wrapper.run_workflow_with_auto_recovery(
            workflow_file="/nonexistent/workflow.yml",
            enable_recovery=False  # 復旧を無効にして基本エラーハンドリングをテスト
        )

        # エラーが適切にハンドリングされることを確認
        self.assertFalse(result.success)
        self.assertIn("エラー", result.stderr)


if __name__ == '__main__':
    unittest.main()
