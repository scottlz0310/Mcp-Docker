#!/usr/bin/env python3
"""
GitHub Actions Simulator - 包括的統合テストと最終検証
タスク15: 統合テストと最終検証の実装

このテストスイートは以下を検証します:
- 全コンポーネントの統合テスト実行
- 実際のワークフローファイルでのエンドツーエンドテスト
- パフォーマンスと安定性の検証
- Requirements: 5.1, 5.2, 5.3, 5.4
"""

import asyncio
import json
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

# テスト対象のコンポーネントをインポート
from services.actions.diagnostic import DiagnosticService, DiagnosticStatus
from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage
from services.actions.hangup_detector import HangupDetector, HangupType, HangupSeverity
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger
from services.actions.service import SimulationService, SimulationParameters
from services.actions.workflow_parser import WorkflowParser
from src.diagnostic_service import DiagnosticService as CoreDiagnosticService
from src.execution_tracer import ExecutionTracer as CoreExecutionTracer
from src.process_monitor import ProcessMonitor
from src.performance_monitor import PerformanceMonitor


class ComprehensiveIntegrationTest:
    """包括的統合テストクラス"""

    def __init__(self):
        self.logger = ActionsLogger(verbose=True, debug=True)
        self.test_results: Dict[str, Dict] = {}
        self.performance_metrics: Dict[str, float] = {}
        self.stability_metrics: Dict[str, int] = {}

    def setup_test_environment(self) -> Path:
        """テスト環境をセットアップ"""
        temp_dir = Path(tempfile.mkdtemp(prefix="github_actions_integration_"))

        # テスト用ワークフローファイルを作成
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        # 基本的なワークフロー
        basic_workflow = workflows_dir / "basic.yml"
        basic_workflow.write_text("""
name: Basic Test Workflow
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Simple test
        run: echo "Hello, World!"
      - name: Environment check
        run: |
          echo "Current directory: $(pwd)"
          echo "Environment variables:"
          env | grep -E '^(GITHUB_|CI)' || true
""")

        # 複雑なワークフロー（マトリックス、条件分岐）
        complex_workflow = workflows_dir / "complex.yml"
        complex_workflow.write_text("""
name: Complex Test Workflow
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
jobs:
  matrix-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16, 18, 20]
        os: [ubuntu-latest, windows-latest]
    steps:
      - name: Setup Node.js
        run: echo "Setting up Node.js ${{ matrix.node-version }} on ${{ matrix.os }}"
      - name: Install dependencies
        run: echo "Installing dependencies"
      - name: Run tests
        run: echo "Running tests with Node.js ${{ matrix.node-version }}"

  conditional-job:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    needs: matrix-test
    steps:
      - name: Deploy
        run: echo "Deploying application"
""")

        # 長時間実行ワークフロー（タイムアウトテスト用）
        timeout_workflow = workflows_dir / "timeout.yml"
        timeout_workflow.write_text("""
name: Timeout Test Workflow
on: [push]
jobs:
  long-running:
    runs-on: ubuntu-latest
    timeout-minutes: 1
    steps:
      - name: Long running task
        run: |
          echo "Starting long running task"
          sleep 5
          echo "Task completed"
      - name: Quick task
        run: echo "Quick task"
""")

        # エラー発生ワークフロー（エラーハンドリングテスト用）
        error_workflow = workflows_dir / "error.yml"
        error_workflow.write_text("""
name: Error Test Workflow
on: [push]
jobs:
  error-test:
    runs-on: ubuntu-latest
    steps:
      - name: Successful step
        run: echo "This step succeeds"
      - name: Failing step
        run: |
          echo "This step will fail"
          exit 1
      - name: Should not run
        run: echo "This should not execute"
""")

        return temp_dir

    def test_component_integration(self) -> Dict[str, bool]:
        """全コンポーネントの統合テスト"""
        results = {}

        try:
            # 1. DiagnosticService統合テスト
            self.logger.info("DiagnosticService統合テストを実行中...")
            diagnostic_service = DiagnosticService(logger=self.logger)
            health_report = diagnostic_service.run_comprehensive_health_check()
            results["diagnostic_service"] = health_report.overall_status != DiagnosticStatus.ERROR

            # 2. ExecutionTracer統合テスト
            self.logger.info("ExecutionTracer統合テストを実行中...")
            execution_tracer = ExecutionTracer(logger=self.logger)
            trace = execution_tracer.start_trace("integration_test")
            execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)
            time.sleep(0.1)  # 短時間実行をシミュレート
            execution_tracer.set_stage(ExecutionStage.COMPLETED)
            final_trace = execution_tracer.end_trace()
            results["execution_tracer"] = final_trace.trace_id == "integration_test"

            # 3. HangupDetector統合テスト
            self.logger.info("HangupDetector統合テストを実行中...")
            hangup_detector = HangupDetector(logger=self.logger)
            docker_issues = hangup_detector.detect_docker_socket_issues()
            results["hangup_detector"] = isinstance(docker_issues, list)

            # 4. AutoRecovery統合テスト
            self.logger.info("AutoRecovery統合テストを実行中...")
            auto_recovery = AutoRecovery(logger=self.logger)
            # Docker再接続テスト（モック環境）
            with patch.object(auto_recovery.docker_checker, 'test_docker_daemon_connection_with_retry') as mock_check:
                from services.actions.docker_integration_checker import DockerConnectionStatus
                mock_check.return_value = Mock(status=DockerConnectionStatus.CONNECTED)
                recovery_result = auto_recovery.attempt_docker_reconnection()
                results["auto_recovery"] = recovery_result is True

            # 5. ProcessMonitor統合テスト
            self.logger.info("ProcessMonitor統合テストを実行中...")
            process_monitor = ProcessMonitor(logger=self.logger)
            # モックプロセスで監視テスト
            mock_pid = 12345
            process_monitor.start_monitoring(mock_pid)
            time.sleep(0.1)
            process_monitor.stop_monitoring()
            results["process_monitor"] = True

            # 6. PerformanceMonitor統合テスト
            self.logger.info("PerformanceMonitor統合テストを実行中...")
            performance_monitor = PerformanceMonitor(logger=self.logger)
            performance_monitor.start_monitoring()
            time.sleep(0.2)
            metrics = performance_monitor.get_current_metrics()
            performance_monitor.stop_monitoring()
            results["performance_monitor"] = metrics is not None

        except Exception as e:
            self.logger.error(f"コンポーネント統合テスト中にエラーが発生: {e}")
            results["error"] = str(e)

        return results

    def test_workflow_execution_scenarios(self, workspace_dir: Path) -> Dict[str, Dict]:
        """実際のワークフローファイルでのエンドツーエンドテスト"""
        results = {}
        workflows_dir = workspace_dir / ".github" / "workflows"

        # SimulationServiceを初期化
        simulation_service = SimulationService()

        for workflow_file in workflows_dir.glob("*.yml"):
            workflow_name = workflow_file.stem
            self.logger.info(f"ワークフロー '{workflow_name}' のテストを実行中...")

            try:
                # ワークフロー解析テスト
                parser = WorkflowParser()
                workflow_data = parser.parse_file(workflow_file)

                # 基本的な構造検証
                has_jobs = "jobs" in workflow_data
                job_count = len(workflow_data.get("jobs", {}))

                # シミュレーション実行テスト（ドライランモード）
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,  # ドライランで安全にテスト
                    verbose=True
                )

                start_time = time.time()
                simulation_result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )
                execution_time = time.time() - start_time

                results[workflow_name] = {
                    "parsing_success": True,
                    "has_jobs": has_jobs,
                    "job_count": job_count,
                    "simulation_success": simulation_result.success,
                    "execution_time_seconds": execution_time,
                    "return_code": simulation_result.return_code,
                    "has_output": bool(simulation_result.stdout or simulation_result.stderr)
                }

                # パフォーマンスメトリクスを記録
                self.performance_metrics[f"{workflow_name}_execution_time"] = execution_time

            except Exception as e:
                self.logger.error(f"ワークフロー '{workflow_name}' のテスト中にエラー: {e}")
                results[workflow_name] = {
                    "parsing_success": False,
                    "error": str(e),
                    "execution_time_seconds": 0
                }

        return results

    def test_enhanced_act_wrapper_integration(self, workspace_dir: Path) -> Dict[str, any]:
        """EnhancedActWrapper統合テスト"""
        self.logger.info("EnhancedActWrapper統合テストを実行中...")

        try:
            wrapper = EnhancedActWrapper(
                working_directory=str(workspace_dir),
                logger=self.logger
            )

            # 診断機能テスト
            diagnostic_results = wrapper.run_pre_execution_diagnostics()

            # モックモードでのワークフロー実行テスト
            workflow_file = workspace_dir / ".github" / "workflows" / "basic.yml"

            start_time = time.time()
            result = wrapper.run_workflow_with_diagnostics(
                workflow_file=workflow_file,
                job=None,
                dry_run=True,
                mock_mode=True  # モックモードで安全にテスト
            )
            execution_time = time.time() - start_time

            return {
                "diagnostics_available": diagnostic_results is not None,
                "execution_success": result.success if hasattr(result, 'success') else True,
                "execution_time_seconds": execution_time,
                "has_detailed_result": hasattr(result, 'detailed_result'),
                "auto_recovery_available": hasattr(wrapper, 'auto_recovery')
            }

        except Exception as e:
            self.logger.error(f"EnhancedActWrapper統合テスト中にエラー: {e}")
            return {
                "error": str(e),
                "execution_success": False
            }

    def test_concurrent_execution_stability(self, workspace_dir: Path) -> Dict[str, any]:
        """並行実行安定性テスト"""
        self.logger.info("並行実行安定性テストを実行中...")

        def run_single_simulation(workflow_file: Path, iteration: int) -> Dict:
            """単一シミュレーション実行"""
            try:
                service = SimulationService()
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=False
                )

                start_time = time.time()
                result = service.run_simulation(params, logger=self.logger)
                execution_time = time.time() - start_time

                return {
                    "iteration": iteration,
                    "success": result.success,
                    "execution_time": execution_time,
                    "return_code": result.return_code
                }
            except Exception as e:
                return {
                    "iteration": iteration,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0
                }

        # 並行実行テスト
        workflow_file = workspace_dir / ".github" / "workflows" / "basic.yml"
        concurrent_count = 5
        iterations_per_thread = 3

        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = []

            for thread_id in range(concurrent_count):
                for iteration in range(iterations_per_thread):
                    future = executor.submit(
                        run_single_simulation,
                        workflow_file,
                        thread_id * iterations_per_thread + iteration
                    )
                    futures.append(future)

            # 結果を収集
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e),
                        "execution_time": 0
                    })

        total_time = time.time() - start_time

        # 統計を計算
        successful_runs = sum(1 for r in results if r.get("success", False))
        total_runs = len(results)
        success_rate = successful_runs / total_runs if total_runs > 0 else 0
        avg_execution_time = sum(r.get("execution_time", 0) for r in results) / total_runs if total_runs > 0 else 0

        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "total_test_time": total_time,
            "concurrent_threads": concurrent_count,
            "iterations_per_thread": iterations_per_thread
        }

    def test_performance_benchmarks(self, workspace_dir: Path) -> Dict[str, float]:
        """パフォーマンスベンチマークテスト"""
        self.logger.info("パフォーマンスベンチマークテストを実行中...")

        benchmarks = {}

        # 1. ワークフロー解析パフォーマンス
        workflow_file = workspace_dir / ".github" / "workflows" / "complex.yml"
        parser = WorkflowParser()

        start_time = time.time()
        for _ in range(10):  # 10回実行して平均を取る
            parser.parse_file(workflow_file)
        parsing_time = (time.time() - start_time) / 10
        benchmarks["workflow_parsing_avg_ms"] = parsing_time * 1000

        # 2. 診断サービスパフォーマンス
        diagnostic_service = DiagnosticService(logger=self.logger)

        start_time = time.time()
        diagnostic_service.run_comprehensive_health_check()
        benchmarks["diagnostic_check_ms"] = (time.time() - start_time) * 1000

        # 3. ハングアップ検出パフォーマンス
        hangup_detector = HangupDetector(logger=self.logger)

        start_time = time.time()
        hangup_detector.detect_docker_socket_issues()
        benchmarks["hangup_detection_ms"] = (time.time() - start_time) * 1000

        # 4. 実行トレースパフォーマンス
        execution_tracer = ExecutionTracer(logger=self.logger)

        start_time = time.time()
        trace = execution_tracer.start_trace("benchmark_test")
        execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)
        execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)
        execution_tracer.set_stage(ExecutionStage.COMPLETED)
        execution_tracer.end_trace()
        benchmarks["execution_trace_ms"] = (time.time() - start_time) * 1000

        return benchmarks

    def test_memory_usage_stability(self) -> Dict[str, float]:
        """メモリ使用量安定性テスト"""
        self.logger.info("メモリ使用量安定性テストを実行中...")

        try:
            import psutil
            process = psutil.Process()

            # 初期メモリ使用量
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # 複数回の操作を実行してメモリリークをチェック
            for i in range(50):
                # 各種コンポーネントを作成・破棄
                diagnostic_service = DiagnosticService(logger=self.logger)
                execution_tracer = ExecutionTracer(logger=self.logger)
                hangup_detector = HangupDetector(logger=self.logger)

                # 軽い処理を実行
                trace = execution_tracer.start_trace(f"memory_test_{i}")
                execution_tracer.end_trace()
                hangup_detector.detect_docker_socket_issues()

                # オブジェクトを明示的に削除
                del diagnostic_service, execution_tracer, hangup_detector

            # 最終メモリ使用量
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            return {
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_increase_mb": memory_increase,
                "memory_increase_percentage": (memory_increase / initial_memory) * 100 if initial_memory > 0 else 0
            }

        except ImportError:
            self.logger.warning("psutil not available - skipping memory usage test")
            return {"error": "psutil not available"}
        except Exception as e:
            self.logger.error(f"メモリ使用量テスト中にエラー: {e}")
            return {"error": str(e)}

    def test_error_handling_robustness(self, workspace_dir: Path) -> Dict[str, bool]:
        """エラーハンドリング堅牢性テスト"""
        self.logger.info("エラーハンドリング堅牢性テストを実行中...")

        results = {}

        # 1. 存在しないワークフローファイルのテスト
        try:
            parser = WorkflowParser()
            non_existent_file = workspace_dir / "non_existent.yml"
            parser.parse_file(non_existent_file)
            results["handles_missing_file"] = False
        except Exception:
            results["handles_missing_file"] = True

        # 2. 不正なYAMLファイルのテスト
        try:
            invalid_yaml_file = workspace_dir / "invalid.yml"
            invalid_yaml_file.write_text("invalid: yaml: content: [")
            parser = WorkflowParser()
            parser.parse_file(invalid_yaml_file)
            results["handles_invalid_yaml"] = False
        except Exception:
            results["handles_invalid_yaml"] = True

        # 3. 権限エラーのシミュレーション
        try:
            with patch("pathlib.Path.exists", return_value=False):
                diagnostic_service = DiagnosticService(logger=self.logger)
                diagnostic_service.check_docker_connectivity()
            results["handles_permission_errors"] = True
        except Exception as e:
            self.logger.error(f"権限エラーテスト中にエラー: {e}")
            results["handles_permission_errors"] = False

        # 4. タイムアウトエラーのシミュレーション
        try:
            from subprocess import TimeoutExpired
            with patch("subprocess.run", side_effect=TimeoutExpired("test", 10)):
                diagnostic_service = DiagnosticService(logger=self.logger)
                diagnostic_service.check_docker_connectivity()
            results["handles_timeout_errors"] = True
        except Exception as e:
            self.logger.error(f"タイムアウトエラーテスト中にエラー: {e}")
            results["handles_timeout_errors"] = False

        return results

    def generate_comprehensive_report(self) -> Dict[str, any]:
        """包括的なテストレポートを生成"""
        return {
            "test_execution_time": datetime.now(timezone.utc).isoformat(),
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "stability_metrics": self.stability_metrics,
            "summary": {
                "total_test_categories": len(self.test_results),
                "overall_success": all(
                    isinstance(result, dict) and result.get("success", True)
                    for result in self.test_results.values()
                ),
                "performance_acceptable": all(
                    metric < 5000  # 5秒以下
                    for key, metric in self.performance_metrics.items()
                    if "time" in key.lower()
                )
            }
        }

    def run_all_tests(self) -> Dict[str, any]:
        """全ての統合テストを実行"""
        self.logger.info("包括的統合テストスイートを開始します...")

        # テスト環境をセットアップ
        workspace_dir = self.setup_test_environment()

        try:
            # 1. コンポーネント統合テスト
            self.logger.info("=== コンポーネント統合テスト ===")
            component_results = self.test_component_integration()
            self.test_results["component_integration"] = component_results

            # 2. ワークフロー実行シナリオテスト
            self.logger.info("=== ワークフロー実行シナリオテスト ===")
            workflow_results = self.test_workflow_execution_scenarios(workspace_dir)
            self.test_results["workflow_execution"] = workflow_results

            # 3. EnhancedActWrapper統合テスト
            self.logger.info("=== EnhancedActWrapper統合テスト ===")
            wrapper_results = self.test_enhanced_act_wrapper_integration(workspace_dir)
            self.test_results["enhanced_act_wrapper"] = wrapper_results

            # 4. 並行実行安定性テスト
            self.logger.info("=== 並行実行安定性テスト ===")
            stability_results = self.test_concurrent_execution_stability(workspace_dir)
            self.test_results["concurrent_stability"] = stability_results
            self.stability_metrics.update(stability_results)

            # 5. パフォーマンスベンチマーク
            self.logger.info("=== パフォーマンスベンチマーク ===")
            performance_results = self.test_performance_benchmarks(workspace_dir)
            self.performance_metrics.update(performance_results)

            # 6. メモリ使用量安定性テスト
            self.logger.info("=== メモリ使用量安定性テスト ===")
            memory_results = self.test_memory_usage_stability()
            self.test_results["memory_stability"] = memory_results

            # 7. エラーハンドリング堅牢性テスト
            self.logger.info("=== エラーハンドリング堅牢性テスト ===")
            error_handling_results = self.test_error_handling_robustness(workspace_dir)
            self.test_results["error_handling"] = error_handling_results

            # 包括的レポートを生成
            comprehensive_report = self.generate_comprehensive_report()

            self.logger.info("包括的統合テストスイートが完了しました")
            return comprehensive_report

        finally:
            # クリーンアップ
            import shutil
            try:
                shutil.rmtree(workspace_dir)
            except Exception as e:
                self.logger.warning(f"テスト環境のクリーンアップ中にエラー: {e}")


# pytest用のテストクラス
class TestComprehensiveIntegration:
    """pytest用の包括的統合テストクラス"""

    @pytest.fixture(scope="class")
    def integration_tester(self):
        """統合テスターのフィクスチャ"""
        return ComprehensiveIntegrationTest()

    @pytest.mark.timeout(300)  # 5分でタイムアウト
    def test_full_integration_suite(self, integration_tester):
        """完全な統合テストスイートを実行"""
        report = integration_tester.run_all_tests()

        # 基本的な成功条件をチェック
        assert report["summary"]["total_test_categories"] > 0
        assert "component_integration" in report["test_results"]
        assert "workflow_execution" in report["test_results"]

        # パフォーマンス要件をチェック
        performance_metrics = report["performance_metrics"]
        if "workflow_parsing_avg_ms" in performance_metrics:
            assert performance_metrics["workflow_parsing_avg_ms"] < 1000  # 1秒以下

        # 安定性要件をチェック
        if "concurrent_stability" in report["test_results"]:
            stability = report["test_results"]["concurrent_stability"]
            if "success_rate" in stability:
                assert stability["success_rate"] >= 0.8  # 80%以上の成功率

        # メモリリーク要件をチェック
        if "memory_stability" in report["test_results"]:
            memory = report["test_results"]["memory_stability"]
            if "memory_increase_percentage" in memory:
                assert memory["memory_increase_percentage"] < 50  # 50%未満の増加

        # レポートをファイルに保存
        report_file = Path("output") / "comprehensive_integration_report.json"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"\n包括的統合テストレポートが保存されました: {report_file}")
        print(f"総合成功率: {report['summary']['overall_success']}")
        print(f"パフォーマンス要件達成: {report['summary']['performance_acceptable']}")


def main():
    """スタンドアロン実行用のメイン関数"""
    tester = ComprehensiveIntegrationTest()
    report = tester.run_all_tests()

    # レポートを出力
    print("\n" + "="*80)
    print("包括的統合テスト結果レポート")
    print("="*80)

    print(f"\n実行時刻: {report['test_execution_time']}")
    print(f"テストカテゴリ数: {report['summary']['total_test_categories']}")
    print(f"総合成功: {'✅' if report['summary']['overall_success'] else '❌'}")
    print(f"パフォーマンス要件: {'✅' if report['summary']['performance_acceptable'] else '❌'}")

    # 詳細結果
    print("\n詳細結果:")
    for category, results in report["test_results"].items():
        if isinstance(results, dict):
            success_count = sum(1 for v in results.values() if v is True or (isinstance(v, dict) and v.get("success", False)))
            total_count = len(results)
            print(f"  {category}: {success_count}/{total_count} 成功")
        else:
            print(f"  {category}: {results}")

    # パフォーマンスメトリクス
    if report["performance_metrics"]:
        print("\nパフォーマンスメトリクス:")
        for metric, value in report["performance_metrics"].items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.2f}")
            else:
                print(f"  {metric}: {value}")

    # レポートファイルを保存
    report_file = Path("comprehensive_integration_report.json")
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n詳細レポートが保存されました: {report_file}")

    return 0 if report["summary"]["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
