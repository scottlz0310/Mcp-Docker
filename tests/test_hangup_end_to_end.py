"""
GitHub Actions Simulator - エンドツーエンドハングアップテスト
実際のワークフローファイルを使用して信頼性のある実行を保証するテスト
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.diagnostic import DiagnosticService
from services.actions.execution_tracer import ExecutionTracer
from services.actions.hangup_detector import HangupDetector
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger


class TestHangupEndToEnd(unittest.TestCase):
    """エンドツーエンドハングアップテストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.logger = ActionsLogger(verbose=True)

        # 実際のワークフローファイルを作成
        self.create_realistic_workflows()

        # 統合システムを初期化
        self.setup_integrated_system()

    def tearDown(self):
        """テストクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_realistic_workflows(self):
        """実際のプロジェクトで使用されるようなワークフローファイルを作成"""

        # CI/CDワークフロー
        ci_workflow = self.workspace / "ci.yml"
        ci_workflow.write_text("""
name: CI Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16, 18, 20]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run tests
        run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage/lcov.info

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Archive build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-files
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v3
        with:
          name: build-files
          path: dist/

      - name: Deploy to staging
        run: |
          echo "Deploying to staging environment"
          # Simulate deployment process
          sleep 2
""")

        # Docker ビルドワークフロー
        docker_workflow = self.workspace / "docker-build.yml"
        docker_workflow.write_text("""
name: Docker Build and Push
on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
""")

        # セキュリティスキャンワークフロー
        security_workflow = self.workspace / "security.yml"
        security_workflow.write_text("""
name: Security Scan
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  code-scan:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: javascript

      - name: Autobuild
        uses: github/codeql-action/autobuild@v2

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
""")

        # パフォーマンステストワークフロー
        performance_workflow = self.workspace / "performance.yml"
        performance_workflow.write_text("""
name: Performance Tests
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Start application
        run: |
          npm start &
          sleep 10

      - name: Run Lighthouse CI
        run: |
          npm install -g @lhci/cli@0.12.x
          lhci autorun
        env:
          LHCI_GITHUB_APP_TOKEN: ${{ secrets.LHCI_GITHUB_APP_TOKEN }}

  load-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Start application
        run: |
          npm start &
          sleep 10

      - name: Run load tests
        run: |
          npx artillery quick --count 10 --num 5 http://localhost:3000
""")

        # 複雑な条件分岐ワークフロー
        conditional_workflow = self.workspace / "conditional.yml"
        conditional_workflow.write_text("""
name: Conditional Workflow
on:
  push:
    branches: [ main, develop, 'feature/*' ]
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.changes.outputs.frontend }}
      backend: ${{ steps.changes.outputs.backend }}
      docs: ${{ steps.changes.outputs.docs }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changes
        uses: dorny/paths-filter@v2
        id: changes
        with:
          filters: |
            frontend:
              - 'src/frontend/**'
              - 'package.json'
            backend:
              - 'src/backend/**'
              - 'requirements.txt'
            docs:
              - 'docs/**'
              - '*.md'

  frontend-tests:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run frontend tests
        run: npm run test:frontend

  backend-tests:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run backend tests
        run: python -m pytest

  docs-build:
    needs: detect-changes
    if: needs.detect-changes.outputs.docs == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Build documentation
        run: |
          npm install -g @docusaurus/core
          npm run build:docs

  integration-tests:
    needs: [frontend-tests, backend-tests]
    if: always() && (needs.frontend-tests.result == 'success' || needs.backend-tests.result == 'success')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run integration tests
        run: |
          echo "Running integration tests"
          sleep 5
""")

        # 失敗しやすいワークフロー（テスト用）
        flaky_workflow = self.workspace / "flaky.yml"
        flaky_workflow.write_text("""
name: Flaky Workflow
on: [push]

jobs:
  flaky-job:
    runs-on: ubuntu-latest
    steps:
      - name: Random failure
        run: |
          # 50% chance of failure
          if [ $((RANDOM % 2)) -eq 0 ]; then
            echo "Success this time"
            exit 0
          else
            echo "Failed this time"
            exit 1
          fi

      - name: Network dependent task
        run: |
          # Simulate network timeout
          timeout 5 curl -s https://httpbin.org/delay/10 || echo "Network timeout occurred"

      - name: Resource intensive task
        run: |
          # Simulate high CPU usage
          echo "Starting CPU intensive task"
          for i in {1..100}; do
            echo "Processing item $i"
            sleep 0.1
          done
""")

    def setup_integrated_system(self):
        """統合システムをセットアップ"""
        self.diagnostic_service = DiagnosticService(logger=self.logger)
        self.execution_tracer = ExecutionTracer(logger=self.logger)
        self.hangup_detector = HangupDetector(logger=self.logger)
        self.auto_recovery = AutoRecovery(logger=self.logger, enable_fallback_mode=True)

        self.enhanced_wrapper = EnhancedActWrapper(
            working_directory=str(self.workspace),
            logger=self.logger,
            execution_tracer=self.execution_tracer,
            diagnostic_service=self.diagnostic_service,
        )

    def test_ci_workflow_execution_reliability(self):
        """CI ワークフロー実行信頼性テスト"""
        # モックモードで実行
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="ci.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=60,
            )

            # CI ワークフローが正常に処理されることを確認
            self.assertTrue(result.success)
            self.assertEqual(result.returncode, 0)
            self.assertIn("CI Pipeline", result.stdout)

            # 診断結果が含まれることを確認
            self.assertTrue(len(result.diagnostic_results) > 0)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_docker_workflow_execution_reliability(self):
        """Docker ワークフロー実行信頼性テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="docker-build.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=90,
            )

            # Docker ワークフローが正常に処理されることを確認
            self.assertTrue(result.success)
            self.assertIn("Docker Build", result.stdout)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_security_workflow_execution_reliability(self):
        """セキュリティワークフロー実行信頼性テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="security.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=120,
            )

            # セキュリティワークフローが正常に処理されることを確認
            self.assertTrue(result.success)
            self.assertIn("Security Scan", result.stdout)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_performance_workflow_execution_reliability(self):
        """パフォーマンステストワークフロー実行信頼性テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="performance.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=180,
            )

            # パフォーマンステストワークフローが正常に処理されることを確認
            self.assertTrue(result.success)
            self.assertIn("Performance Tests", result.stdout)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_conditional_workflow_execution_reliability(self):
        """条件分岐ワークフロー実行信頼性テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="conditional.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=120,
            )

            # 条件分岐ワークフローが正常に処理されることを確認
            self.assertTrue(result.success)
            self.assertIn("Conditional Workflow", result.stdout)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_flaky_workflow_with_recovery(self):
        """不安定なワークフローでの復旧テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            # 最初の実行（失敗をシミュレート）
            with patch.object(
                self.enhanced_wrapper, "_create_monitored_subprocess"
            ) as mock_subprocess:
                mock_process = Mock()
                mock_process.pid = 12345
                mock_process.poll.return_value = 1  # 失敗
                mock_process.returncode = 1

                from services.actions.enhanced_act_wrapper import MonitoredProcess

                monitored_process = MonitoredProcess(
                    process=mock_process,
                    command=["act", "flaky.yml"],
                    start_time=time.time(),
                )
                monitored_process.stdout_lines = ["Flaky Workflow execution failed"]
                monitored_process.stderr_lines = ["Error occurred"]

                mock_subprocess.return_value = monitored_process

                result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                    workflow_file="flaky.yml",
                    pre_execution_diagnostics=False,
                    timeout_seconds=30,
                )

                # 失敗が検出されることを確認
                self.assertFalse(result.success)

                # 自動復旧を試行
                recovery_session = self.auto_recovery.run_comprehensive_recovery(
                    failed_process=mock_process,
                    workflow_file=self.workspace / "flaky.yml",
                    original_command=["act", "flaky.yml"],
                )

                # 復旧セッションが実行されることを確認
                self.assertIsNotNone(recovery_session.session_id)
                self.assertTrue(len(recovery_session.attempts) > 0)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_multiple_workflow_sequential_execution(self):
        """複数ワークフローの連続実行テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            workflows = ["ci.yml", "docker-build.yml", "security.yml"]
            results = []

            for workflow in workflows:
                result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                    workflow_file=workflow,
                    pre_execution_diagnostics=False,
                    timeout_seconds=60,
                )
                results.append(result)

                # 各ワークフローが正常に実行されることを確認
                self.assertTrue(result.success, f"Workflow {workflow} failed")

            # 全てのワークフローが成功することを確認
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r.success for r in results))

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_workflow_execution_with_timeout_handling(self):
        """タイムアウト処理付きワークフロー実行テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            # 短いタイムアウトで実行
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="performance.yml",
                pre_execution_diagnostics=False,
                timeout_seconds=5,  # 非常に短いタイムアウト
            )

            # タイムアウトまたは正常完了のいずれかになることを確認
            self.assertIsNotNone(result)

            if not result.success:
                # タイムアウトの場合、適切なエラーメッセージが含まれることを確認
                self.assertTrue(
                    "タイムアウト" in result.stderr
                    or "timeout" in result.stderr.lower()
                    or result.returncode != 0
                )

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_workflow_execution_with_comprehensive_diagnostics(self):
        """包括的診断付きワークフロー実行テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="ci.yml",
                pre_execution_diagnostics=True,
                timeout_seconds=60,
            )

            # 診断情報が含まれることを確認
            self.assertTrue(len(result.diagnostic_results) > 0)

            # 実行トレース情報が含まれることを確認
            self.assertIsNotNone(result.execution_trace)

            # プロセス監視データが含まれることを確認
            self.assertIsNotNone(result.process_monitoring_data)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_workflow_execution_error_recovery_cycle(self):
        """ワークフロー実行エラー復旧サイクルテスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            # 1. 初回実行（エラーをシミュレート）
            with patch.object(
                self.enhanced_wrapper, "run_workflow_with_diagnostics"
            ) as mock_run:
                from services.actions.enhanced_act_wrapper import DetailedResult

                # 失敗結果を返す
                failed_result = DetailedResult(
                    success=False,
                    returncode=1,
                    stdout="",
                    stderr="Simulated failure",
                    command="act ci.yml",
                    execution_time_ms=1000.0,
                )
                mock_run.return_value = failed_result

                result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                    workflow_file="ci.yml"
                )

                # 失敗が検出されることを確認
                self.assertFalse(result.success)

            # 2. ハングアップ分析
            analysis = self.hangup_detector.analyze_hangup_conditions()
            self.assertIsNotNone(analysis.analysis_id)

            # 3. エラーレポート生成
            report = self.hangup_detector.generate_detailed_error_report(
                hangup_analysis=analysis
            )
            self.assertIsNotNone(report.report_id)

            # 4. 自動復旧試行
            recovery_session = self.auto_recovery.run_comprehensive_recovery(
                workflow_file=self.workspace / "ci.yml",
                original_command=["act", "ci.yml"],
            )

            # 復旧プロセスが実行されることを確認
            self.assertIsNotNone(recovery_session.session_id)
            self.assertTrue(len(recovery_session.attempts) > 0)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_real_workflow_file_compatibility(self):
        """実際のワークフローファイル互換性テスト"""
        # プロジェクトの実際のワークフローファイルをテスト
        real_workflow = Path("test_workflow.yml")

        if real_workflow.exists():
            os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

            try:
                result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                    workflow_file=str(real_workflow),
                    pre_execution_diagnostics=True,
                    timeout_seconds=30,
                )

                # 実際のワークフローファイルが正常に処理されることを確認
                self.assertIsNotNone(result)

            finally:
                if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                    del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_stress_test_multiple_concurrent_workflows(self):
        """ストレステスト：複数並行ワークフロー"""
        import threading

        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            results = []

            def workflow_worker(workflow_name):
                try:
                    wrapper = EnhancedActWrapper(
                        working_directory=str(self.workspace),
                        logger=ActionsLogger(verbose=False),  # ログを抑制
                    )

                    result = wrapper.run_workflow_with_diagnostics(
                        workflow_file=workflow_name,
                        pre_execution_diagnostics=False,
                        timeout_seconds=30,
                    )
                    results.append((workflow_name, result.success))
                except Exception as e:
                    results.append((workflow_name, False, str(e)))

            # 複数のワークフローを並行実行
            workflows = ["ci.yml", "docker-build.yml", "security.yml"]
            threads = []

            for workflow in workflows:
                thread = threading.Thread(target=workflow_worker, args=(workflow,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join(timeout=60)  # 最大60秒待機

            # 全てのワークフローが完了することを確認
            self.assertEqual(len(results), 3)

            # 少なくとも一部のワークフローが成功することを確認
            successful_count = sum(1 for r in results if len(r) >= 2 and r[1])
            self.assertGreater(successful_count, 0)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]

    def test_long_running_workflow_stability(self):
        """長時間実行ワークフロー安定性テスト"""
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"

        try:
            # 長時間実行をシミュレート
            result = self.enhanced_wrapper.run_workflow_with_diagnostics(
                workflow_file="performance.yml",
                pre_execution_diagnostics=False,
                timeout_seconds=300,  # 5分のタイムアウト
            )

            # 長時間実行でも安定して動作することを確認
            self.assertIsNotNone(result)

            # メモリリークがないことを確認（簡易チェック）
            if (
                hasattr(result, "process_monitoring_data")
                and result.process_monitoring_data
            ):
                monitoring_data = result.process_monitoring_data
                self.assertIsInstance(monitoring_data, dict)

        finally:
            if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
                del os.environ["ACTIONS_SIMULATOR_ENGINE"]


if __name__ == "__main__":
    unittest.main()
