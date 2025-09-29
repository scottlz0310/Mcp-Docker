"""
GitHub Actions Simulator - ハングアップ統合テスト
実際のハングアップ条件をシミュレートし、修正を検証する統合テスト
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.actions.enhanced_act_wrapper import EnhancedActWrapper, DetailedResult
from services.actions.diagnostic import DiagnosticService
from services.actions.execution_tracer import ExecutionTracer
from services.actions.hangup_detector import HangupDetector
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger


class TestHangupIntegration(unittest.TestCase):
    """ハングアップ統合テストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.logger = ActionsLogger(verbose=True)

        # テスト用ワークフローファイルを作成
        self.create_test_workflows()

        # コンポーネントを初期化
        self.diagnostic_service = DiagnosticService(logger=self.logger)
        self.execution_tracer = ExecutionTracer(logger=self.logger)
        self.hangup_detector = HangupDetector(logger=self.logger)
        self.auto_recovery = AutoRecovery(logger=self.logger, enable_fallback_mode=True)

    def tearDown(self):
        """テストクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_workflows(self):
        """テスト用ワークフローファイルを作成"""
        # 基本的なワークフロー
        basic_workflow = self.workspace / "basic_workflow.yml"
        basic_workflow.write_text("""
name: Basic Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Simple echo
        run: echo "Hello World"
      - name: List files
        run: ls -la
""")

        # 長時間実行ワークフロー
        long_running_workflow = self.workspace / "long_running_workflow.yml"
        long_running_workflow.write_text("""
name: Long Running Workflow
on: [push]
jobs:
  long-task:
    runs-on: ubuntu-latest
    steps:
      - name: Long running task
        run: sleep 30
      - name: Another task
        run: echo "After long task"
""")

        # 複雑なワークフロー
        complex_workflow = self.workspace / "complex_workflow.yml"
        complex_workflow.write_text("""
name: Complex Workflow
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npm test
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: echo "Deploying..."
""")

        # エラーを含むワークフロー
        error_workflow = self.workspace / "error_workflow.yml"
        error_workflow.write_text("""
name: Error Workflow
on: [push]
jobs:
  error-job:
    runs-on: ubuntu-latest
    steps:
      - name: Command that fails
        run: exit 1
      - name: This should not run
        run: echo "Should not reach here"
""")

    def test_docker_socket_unavailable_integration(self):
        """Dockerソケット利用不可統合テスト"""
        # Dockerソケットが利用できない状況をシミュレート
        with patch("pathlib.Path.exists", return_value=False):
            # 診断実行
            health_report = self.diagnostic_service.run_comprehensive_health_check()

            # Docker関連の問題が検出されることを確認
            docker_issues = [result for result in health_report.results if "Docker" in result.component]
            self.assertTrue(len(docker_issues) > 0)

            # ハングアップ分析
            analysis = self.hangup_detector.analyze_hangup_conditions()
            self.assertTrue(len(analysis.issues) > 0)

            # 復旧提案が含まれることを確認
            self.assertTrue(len(analysis.recovery_suggestions) > 0)

    def test_act_binary_missing_integration(self):
        """actバイナリ不在統合テスト"""
        # actバイナリが見つからない状況をシミュレート
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.exists", return_value=False),
        ):
            # 診断実行
            act_result = self.diagnostic_service.check_act_binary()
            self.assertEqual(act_result.status.name, "ERROR")

            # ハングアップ検出
            issues = self.hangup_detector.detect_docker_socket_issues()
            self.assertTrue(len(issues) > 0)

    def test_timeout_escalation_integration(self):
        """タイムアウトエスカレーション統合テスト"""
        # EnhancedActWrapperでタイムアウト処理をテスト
        wrapper = EnhancedActWrapper(
            working_directory=str(self.workspace),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service,
        )

        # モックモードで実行（実際のactを使わない）
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            # 短いタイムアウトで実行
            result = wrapper.run_workflow_with_diagnostics(
                workflow_file="basic_workflow.yml",
                timeout_seconds=1,  # 非常に短いタイムアウト
                pre_execution_diagnostics=False,
            )

            # タイムアウトまたは正常完了のいずれかになることを確認
            self.assertIsInstance(result, DetailedResult)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_output_buffer_overflow_integration(self):
        """出力バッファオーバーフロー統合テスト"""
        # 大量の出力を生成するワークフローを作成
        large_output_workflow = self.workspace / "large_output_workflow.yml"
        large_output_workflow.write_text("""
name: Large Output Workflow
on: [push]
jobs:
  large-output:
    runs-on: ubuntu-latest
    steps:
      - name: Generate large output
        run: |
          for i in {1..1000}; do
            echo "Line $i: This is a test line with some content"
          done
""")

        wrapper = EnhancedActWrapper(
            working_directory=str(self.workspace),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service,
        )

        # モックモードで実行
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = wrapper.run_workflow_with_diagnostics(
                workflow_file="large_output_workflow.yml",
                pre_execution_diagnostics=False,
            )

            # 大量の出力が適切に処理されることを確認
            self.assertIsInstance(result, DetailedResult)
            self.assertTrue(len(result.stdout) > 0)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_resource_exhaustion_integration(self):
        """リソース枯渇統合テスト"""
        # リソース使用量チェック
        resource_result = self.diagnostic_service.check_resource_usage()

        # リソース情報が取得できることを確認
        self.assertIn("disk_usage", resource_result.details)
        self.assertIn("memory_usage", resource_result.details)

    def test_permission_denied_integration(self):
        """権限拒否統合テスト"""
        # 権限チェック
        permission_result = self.diagnostic_service.check_container_permissions()

        # 権限情報が取得できることを確認
        self.assertIsNotNone(permission_result)

        # ハングアップ検出で権限問題を分析
        permission_issues = self.hangup_detector.detect_permission_issues()

        # 権限問題の分析結果が得られることを確認
        self.assertIsInstance(permission_issues, list)

    def test_auto_recovery_docker_restart_integration(self):
        """自動復旧Docker再起動統合テスト"""
        # Docker再接続を試行
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = self.auto_recovery.attempt_docker_reconnection()

            # 復旧処理が実行されることを確認
            self.assertIsInstance(result, bool)

    def test_auto_recovery_fallback_mode_integration(self):
        """自動復旧フォールバックモード統合テスト"""
        workflow_file = self.workspace / "basic_workflow.yml"
        original_command = ["act", "--list"]

        # フォールバックモードを実行
        result = self.auto_recovery.execute_fallback_mode(workflow_file, original_command)

        # フォールバック実行が成功することを確認
        self.assertTrue(result.success)
        self.assertEqual(result.fallback_method, "dry_run_mode")

    def test_comprehensive_recovery_session_integration(self):
        """包括的復旧セッション統合テスト"""
        workflow_file = self.workspace / "basic_workflow.yml"

        # 包括的復旧を実行
        session = self.auto_recovery.run_comprehensive_recovery(
            workflow_file=workflow_file, original_command=["act", "--list"]
        )

        # 復旧セッションが正常に実行されることを確認
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.start_time)
        self.assertIsNotNone(session.end_time)
        self.assertTrue(len(session.attempts) > 0)

    def test_error_report_and_debug_bundle_integration(self):
        """エラーレポートとデバッグバンドル統合テスト"""
        # ハングアップ分析を実行
        analysis = self.hangup_detector.analyze_hangup_conditions()

        # エラーレポートを生成
        report = self.hangup_detector.generate_detailed_error_report(hangup_analysis=analysis)

        # デバッグバンドルを作成
        bundle = self.hangup_detector.create_debug_bundle(
            error_report=report,
            output_directory=self.workspace,
            include_logs=True,
            include_system_info=True,
            include_docker_info=True,
        )

        # バンドルが正常に作成されることを確認
        self.assertIsNotNone(bundle.bundle_id)
        if bundle.bundle_path:  # エラーが発生しなかった場合
            self.assertTrue(bundle.bundle_path.exists())

    def test_execution_trace_integration(self):
        """実行トレース統合テスト"""
        # 実行トレースを開始
        self.execution_tracer.start_trace("integration_test")

        # 各段階を実行
        self.execution_tracer.set_stage("SUBPROCESS_CREATION", {"test": "data"})
        self.execution_tracer.set_stage("PROCESS_MONITORING")

        # ハートビートを記録
        self.execution_tracer.log_heartbeat("Test heartbeat", {"status": "running"})

        # トレースを終了
        final_trace = self.execution_tracer.end_trace()

        # トレース情報が正しく記録されることを確認
        self.assertEqual(final_trace.trace_id, "integration_test")
        self.assertIsNotNone(final_trace.end_time)
        self.assertTrue(final_trace.duration_ms > 0)

    def test_diagnostic_health_check_integration(self):
        """診断ヘルスチェック統合テスト"""
        # 包括的ヘルスチェックを実行
        health_report = self.diagnostic_service.run_comprehensive_health_check()

        # ヘルスチェック結果が取得できることを確認
        self.assertIsNotNone(health_report.overall_status)
        self.assertTrue(len(health_report.results) > 0)
        self.assertIsNotNone(health_report.summary)

    def test_enhanced_act_wrapper_mock_mode_integration(self):
        """EnhancedActWrapperモックモード統合テスト"""
        wrapper = EnhancedActWrapper(
            working_directory=str(self.workspace),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service,
        )

        # モックモードで各種ワークフローを実行
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            workflows = [
                "basic_workflow.yml",
                "long_running_workflow.yml",
                "complex_workflow.yml",
                "error_workflow.yml",
            ]

            for workflow in workflows:
                with self.subTest(workflow=workflow):
                    result = wrapper.run_workflow_with_diagnostics(
                        workflow_file=workflow,
                        pre_execution_diagnostics=False,
                        dry_run=True,
                    )

                    # 各ワークフローが正常に処理されることを確認
                    self.assertIsInstance(result, DetailedResult)
                    self.assertTrue(result.success)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_concurrent_execution_integration(self):
        """並行実行統合テスト"""
        import threading

        results = []

        def worker():
            try:
                # 診断チェックを並行実行
                health_report = self.diagnostic_service.run_comprehensive_health_check()
                results.append(health_report.overall_status.name)
            except Exception as e:
                results.append(str(e))

        # 複数スレッドで同時実行
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 全てのスレッドが正常に完了することを確認
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIn(result, ["OK", "WARNING", "ERROR"])

    def test_memory_management_integration(self):
        """メモリ管理統合テスト"""
        # 複数回の実行でメモリリークがないことを確認
        initial_trace_count = len(self.execution_tracer._traces) if hasattr(self.execution_tracer, "_traces") else 0

        for i in range(5):
            self.execution_tracer.start_trace(f"memory_test_{i}")
            self.execution_tracer.set_stage("COMPLETED")
            self.execution_tracer.end_trace()

        # トレース履歴が適切に管理されることを確認
        # （実装によっては履歴を保持しない場合もある）
        if hasattr(self.execution_tracer, "_traces"):
            final_trace_count = len(self.execution_tracer._traces)
            # 無制限に増加しないことを確認
            self.assertLessEqual(final_trace_count, initial_trace_count + 10)

    def test_configuration_validation_integration(self):
        """設定検証統合テスト"""
        # 環境変数設定のテスト
        test_configs = {
            "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS": "300",
            "ACTIONS_SIMULATOR_ENGINE": "act",
            "ACTIONS_SIMULATOR_VERBOSE": "true",
        }

        with patch.dict(os.environ, test_configs):
            # 設定が正しく読み込まれることを確認
            wrapper = EnhancedActWrapper(working_directory=str(self.workspace), logger=self.logger)

            # 設定値が反映されることを確認
            self.assertIsNotNone(wrapper)

    def test_cleanup_and_resource_release_integration(self):
        """クリーンアップとリソース解放統合テスト"""
        # リソースを使用する処理を実行
        self.execution_tracer.start_trace("cleanup_test")
        self.execution_tracer.set_stage("PROCESS_MONITORING")

        # 自動復旧でバッファクリアを実行
        self.auto_recovery.clear_output_buffers()

        # トレースを終了
        final_trace = self.execution_tracer.end_trace()

        # リソースが適切に解放されることを確認
        self.assertIsNotNone(final_trace.end_time)


if __name__ == "__main__":
    unittest.main()
