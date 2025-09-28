#!/usr/bin/env python3
"""
GitHub Actions Simulator - パフォーマンスと安定性検証テスト
タスク15の一部: パフォーマンスと安定性の検証を完了

このテストは以下を検証します:
- 長時間実行での安定性
- メモリリークの検出
- 並行処理での安定性
- リソース使用量の監視
- パフォーマンス回帰の検出
"""

import gc
import json
import os
import psutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

from services.actions.logger import ActionsLogger
from services.actions.service import SimulationService, SimulationParameters
from services.actions.diagnostic import DiagnosticService
from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.execution_tracer import ExecutionTracer
from services.actions.hangup_detector import HangupDetector
from services.actions.auto_recovery import AutoRecovery
from src.process_monitor import ProcessMonitor
from src.performance_monitor import PerformanceMonitor


class PerformanceStabilityValidator:
    """パフォーマンスと安定性検証クラス"""

    def __init__(self):
        self.logger = ActionsLogger(verbose=False, debug=False)  # パフォーマンステストでは詳細ログを抑制
        self.process = psutil.Process()
        self.baseline_metrics = {}
        self.test_results = {}
        self.performance_history = []

    def setup_test_workspace(self) -> Path:
        """テスト用ワークスペースをセットアップ"""
        import tempfile
        workspace = Path(tempfile.mkdtemp(prefix="perf_stability_test_"))

        # テスト用ワークフローを作成
        workflows_dir = workspace / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        # 軽量ワークフロー（高速実行用）
        light_workflow = workflows_dir / "light.yml"
        light_workflow.write_text("""
name: Light Workflow
on: [push]
jobs:
  quick-test:
    runs-on: ubuntu-latest
    steps:
      - name: Quick echo
        run: echo "Hello World"
      - name: Simple calculation
        run: echo $((2 + 2))
""")

        # 中程度ワークフロー（通常の処理負荷）
        medium_workflow = workflows_dir / "medium.yml"
        medium_workflow.write_text("""
name: Medium Workflow
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup environment
        run: |
          echo "Setting up environment..."
          sleep 1
      - name: Build
        run: |
          echo "Building application..."
          for i in {1..5}; do
            echo "Build step $i"
            sleep 0.2
          done
      - name: Test
        run: |
          echo "Running tests..."
          sleep 0.5
""")

        # 複雑ワークフロー（高負荷処理）
        complex_workflow = workflows_dir / "complex.yml"
        complex_workflow.write_text("""
name: Complex Workflow
on:
  push:
    branches: [main, develop]
  pull_request:
    types: [opened, synchronize]
jobs:
  matrix-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        version: [16, 18, 20]
        os: [ubuntu-latest, windows-latest]
    steps:
      - name: Setup ${{ matrix.version }} on ${{ matrix.os }}
        run: echo "Setting up version ${{ matrix.version }} on ${{ matrix.os }}"
      - name: Install dependencies
        run: |
          echo "Installing dependencies for ${{ matrix.version }}"
          sleep 0.3
      - name: Run tests
        run: |
          echo "Running tests with version ${{ matrix.version }}"
          sleep 0.5

  integration:
    runs-on: ubuntu-latest
    needs: matrix-test
    if: github.event_name == 'push'
    steps:
      - name: Integration tests
        run: |
          echo "Running integration tests..."
          sleep 1
      - name: Deploy
        run: |
          echo "Deploying application..."
          sleep 0.8
""")

        return workspace

    def capture_baseline_metrics(self) -> Dict[str, float]:
        """ベースラインメトリクスを取得"""
        self.logger.info("ベースラインメトリクスを取得中...")

        # ガベージコレクションを実行してクリーンな状態にする
        gc.collect()
        time.sleep(1)

        memory_info = self.process.memory_info()

        baseline = {
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent(interval=1),
            "num_threads": self.process.num_threads(),
            "num_fds": self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
            "timestamp": time.time()
        }

        self.baseline_metrics = baseline
        return baseline

    def capture_current_metrics(self) -> Dict[str, float]:
        """現在のメトリクスを取得"""
        memory_info = self.process.memory_info()

        return {
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent(),
            "num_threads": self.process.num_threads(),
            "num_fds": self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
            "timestamp": time.time()
        }

    def test_memory_leak_detection(self, workspace: Path) -> Dict[str, any]:
        """メモリリーク検出テスト"""
        self.logger.info("メモリリーク検出テストを実行中...")

        workflow_file = workspace / ".github" / "workflows" / "light.yml"
        simulation_service = SimulationService()

        # 初期メモリ使用量を記録
        initial_metrics = self.capture_current_metrics()
        memory_samples = [initial_metrics["memory_rss_mb"]]

        # 100回の実行でメモリリークをチェック
        iterations = 100
        for i in range(iterations):
            try:
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=False
                )

                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )

                # 10回ごとにメモリ使用量をサンプリング
                if i % 10 == 0:
                    current_metrics = self.capture_current_metrics()
                    memory_samples.append(current_metrics["memory_rss_mb"])

                    # 強制的にガベージコレクション
                    if i % 50 == 0:
                        gc.collect()

            except Exception as e:
                self.logger.error(f"メモリリークテスト反復 {i} でエラー: {e}")

        # 最終メモリ使用量を記録
        final_metrics = self.capture_current_metrics()
        memory_samples.append(final_metrics["memory_rss_mb"])

        # メモリリーク分析
        memory_increase = final_metrics["memory_rss_mb"] - initial_metrics["memory_rss_mb"]
        memory_increase_percent = (memory_increase / initial_metrics["memory_rss_mb"]) * 100

        # メモリ使用量の傾向を分析
        memory_trend = self._analyze_memory_trend(memory_samples)

        return {
            "iterations": iterations,
            "initial_memory_mb": initial_metrics["memory_rss_mb"],
            "final_memory_mb": final_metrics["memory_rss_mb"],
            "memory_increase_mb": memory_increase,
            "memory_increase_percent": memory_increase_percent,
            "memory_samples": memory_samples,
            "memory_trend": memory_trend,
            "leak_detected": memory_increase_percent > 20,  # 20%以上の増加をリークとみなす
            "acceptable_memory_usage": memory_increase_percent < 10  # 10%未満を許容範囲とする
        }

    def test_concurrent_execution_stability(self, workspace: Path) -> Dict[str, any]:
        """並行実行安定性テスト"""
        self.logger.info("並行実行安定性テストを実行中...")

        workflow_files = [
            workspace / ".github" / "workflows" / "light.yml",
            workspace / ".github" / "workflows" / "medium.yml",
            workspace / ".github" / "workflows" / "complex.yml"
        ]

        def run_simulation_worker(workflow_file: Path, worker_id: int, iterations: int) -> Dict:
            """ワーカー関数：指定された回数だけシミュレーションを実行"""
            worker_results = {
                "worker_id": worker_id,
                "successful_runs": 0,
                "failed_runs": 0,
                "total_execution_time": 0,
                "errors": []
            }

            simulation_service = SimulationService()

            for i in range(iterations):
                try:
                    params = SimulationParameters(
                        workflow_file=workflow_file,
                        dry_run=True,
                        verbose=False
                    )

                    start_time = time.time()
                    result = simulation_service.run_simulation(
                        params,
                        logger=self.logger,
                        capture_output=True
                    )
                    execution_time = time.time() - start_time

                    worker_results["total_execution_time"] += execution_time

                    if result.success:
                        worker_results["successful_runs"] += 1
                    else:
                        worker_results["failed_runs"] += 1

                except Exception as e:
                    worker_results["failed_runs"] += 1
                    worker_results["errors"].append(str(e))

            return worker_results

        # 並行実行テスト設定
        num_workers = 8
        iterations_per_worker = 10

        initial_metrics = self.capture_current_metrics()
        start_time = time.time()

        # ThreadPoolExecutorで並行実行
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []

            for worker_id in range(num_workers):
                workflow_file = workflow_files[worker_id % len(workflow_files)]
                future = executor.submit(
                    run_simulation_worker,
                    workflow_file,
                    worker_id,
                    iterations_per_worker
                )
                futures.append(future)

            # 結果を収集
            worker_results = []
            for future in as_completed(futures, timeout=300):  # 5分でタイムアウト
                try:
                    result = future.result()
                    worker_results.append(result)
                except Exception as e:
                    self.logger.error(f"ワーカー実行中にエラー: {e}")
                    worker_results.append({
                        "worker_id": -1,
                        "successful_runs": 0,
                        "failed_runs": iterations_per_worker,
                        "total_execution_time": 0,
                        "errors": [str(e)]
                    })

        total_time = time.time() - start_time
        final_metrics = self.capture_current_metrics()

        # 統計を計算
        total_successful = sum(r["successful_runs"] for r in worker_results)
        total_failed = sum(r["failed_runs"] for r in worker_results)
        total_runs = total_successful + total_failed
        success_rate = total_successful / total_runs if total_runs > 0 else 0

        total_execution_time = sum(r["total_execution_time"] for r in worker_results)
        average_execution_time = total_execution_time / total_runs if total_runs > 0 else 0

        return {
            "num_workers": num_workers,
            "iterations_per_worker": iterations_per_worker,
            "total_runs": total_runs,
            "successful_runs": total_successful,
            "failed_runs": total_failed,
            "success_rate": success_rate,
            "total_test_time_seconds": total_time,
            "average_execution_time_seconds": average_execution_time,
            "throughput_runs_per_second": total_runs / total_time if total_time > 0 else 0,
            "memory_increase_mb": final_metrics["memory_rss_mb"] - initial_metrics["memory_rss_mb"],
            "thread_count_increase": final_metrics["num_threads"] - initial_metrics["num_threads"],
            "worker_results": worker_results,
            "stability_acceptable": success_rate >= 0.95 and total_time < 120  # 95%成功率、2分以内
        }

    def test_long_running_stability(self, workspace: Path) -> Dict[str, any]:
        """長時間実行安定性テスト"""
        self.logger.info("長時間実行安定性テストを実行中...")

        workflow_file = workspace / ".github" / "workflows" / "medium.yml"
        simulation_service = SimulationService()

        # テスト設定
        test_duration_minutes = 5  # 5分間の連続実行
        sampling_interval_seconds = 30  # 30秒ごとにメトリクスをサンプリング

        start_time = time.time()
        end_time = start_time + (test_duration_minutes * 60)

        metrics_history = []
        execution_count = 0
        error_count = 0
        errors = []

        initial_metrics = self.capture_current_metrics()

        while time.time() < end_time:
            try:
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=False
                )

                execution_start = time.time()
                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )
                execution_time = time.time() - execution_start

                execution_count += 1

                if not result.success:
                    error_count += 1
                    errors.append(f"Execution {execution_count}: {result.stderr}")

                # 定期的にメトリクスをサンプリング
                if execution_count % 10 == 0:
                    current_metrics = self.capture_current_metrics()
                    current_metrics["execution_count"] = execution_count
                    current_metrics["error_count"] = error_count
                    current_metrics["execution_time"] = execution_time
                    metrics_history.append(current_metrics)

                # CPU使用率が高すぎる場合は少し待機
                if execution_count % 50 == 0:
                    time.sleep(0.1)

            except Exception as e:
                error_count += 1
                errors.append(f"Exception at execution {execution_count}: {str(e)}")
                self.logger.error(f"長時間実行テスト中にエラー: {e}")

        total_time = time.time() - start_time
        final_metrics = self.capture_current_metrics()

        # 安定性分析
        success_rate = (execution_count - error_count) / execution_count if execution_count > 0 else 0
        throughput = execution_count / total_time if total_time > 0 else 0

        # メモリ使用量の安定性分析
        memory_stability = self._analyze_memory_stability(metrics_history)

        return {
            "test_duration_minutes": test_duration_minutes,
            "actual_duration_seconds": total_time,
            "total_executions": execution_count,
            "successful_executions": execution_count - error_count,
            "error_count": error_count,
            "success_rate": success_rate,
            "throughput_executions_per_second": throughput,
            "initial_memory_mb": initial_metrics["memory_rss_mb"],
            "final_memory_mb": final_metrics["memory_rss_mb"],
            "memory_increase_mb": final_metrics["memory_rss_mb"] - initial_metrics["memory_rss_mb"],
            "memory_stability": memory_stability,
            "metrics_history": metrics_history,
            "errors": errors[:10],  # 最初の10個のエラーのみ保存
            "stability_acceptable": success_rate >= 0.98 and memory_stability["is_stable"]
        }

    def test_component_performance_benchmarks(self) -> Dict[str, Dict]:
        """コンポーネントパフォーマンスベンチマーク"""
        self.logger.info("コンポーネントパフォーマンスベンチマークを実行中...")

        benchmarks = {}

        # 1. DiagnosticService ベンチマーク
        diagnostic_service = DiagnosticService(logger=self.logger)

        start_time = time.time()
        for _ in range(10):
            diagnostic_service.run_comprehensive_health_check()
        diagnostic_time = (time.time() - start_time) / 10

        benchmarks["diagnostic_service"] = {
            "average_execution_time_ms": diagnostic_time * 1000,
            "acceptable_performance": diagnostic_time < 2.0  # 2秒以内
        }

        # 2. ExecutionTracer ベンチマーク
        execution_tracer = ExecutionTracer(logger=self.logger)

        start_time = time.time()
        for i in range(100):
            trace = execution_tracer.start_trace(f"benchmark_{i}")
            execution_tracer.set_stage("SUBPROCESS_CREATION")
            execution_tracer.set_stage("PROCESS_MONITORING")
            execution_tracer.set_stage("COMPLETED")
            execution_tracer.end_trace()
        tracer_time = (time.time() - start_time) / 100

        benchmarks["execution_tracer"] = {
            "average_execution_time_ms": tracer_time * 1000,
            "acceptable_performance": tracer_time < 0.1  # 100ms以内
        }

        # 3. HangupDetector ベンチマーク
        hangup_detector = HangupDetector(logger=self.logger)

        start_time = time.time()
        for _ in range(20):
            hangup_detector.detect_docker_socket_issues()
        detector_time = (time.time() - start_time) / 20

        benchmarks["hangup_detector"] = {
            "average_execution_time_ms": detector_time * 1000,
            "acceptable_performance": detector_time < 1.0  # 1秒以内
        }

        # 4. ProcessMonitor ベンチマーク
        process_monitor = ProcessMonitor(logger=self.logger)

        start_time = time.time()
        for i in range(50):
            mock_pid = 1000 + i
            process_monitor.start_monitoring(mock_pid)
            time.sleep(0.01)  # 短時間監視
            process_monitor.stop_monitoring()
        monitor_time = (time.time() - start_time) / 50

        benchmarks["process_monitor"] = {
            "average_execution_time_ms": monitor_time * 1000,
            "acceptable_performance": monitor_time < 0.5  # 500ms以内
        }

        return benchmarks

    def test_resource_usage_limits(self, workspace: Path) -> Dict[str, any]:
        """リソース使用量制限テスト"""
        self.logger.info("リソース使用量制限テストを実行中...")

        workflow_file = workspace / ".github" / "workflows" / "complex.yml"
        simulation_service = SimulationService()

        # リソース使用量を監視しながら実行
        max_memory_mb = 0
        max_cpu_percent = 0
        max_threads = 0
        max_fds = 0

        resource_samples = []

        # 50回実行してリソース使用量をモニタリング
        for i in range(50):
            try:
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=False
                )

                # 実行前のリソース状況
                pre_metrics = self.capture_current_metrics()

                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )

                # 実行後のリソース状況
                post_metrics = self.capture_current_metrics()

                # 最大値を更新
                max_memory_mb = max(max_memory_mb, post_metrics["memory_rss_mb"])
                max_cpu_percent = max(max_cpu_percent, post_metrics["cpu_percent"])
                max_threads = max(max_threads, post_metrics["num_threads"])
                max_fds = max(max_fds, post_metrics["num_fds"])

                # サンプルを記録
                resource_samples.append({
                    "iteration": i,
                    "memory_mb": post_metrics["memory_rss_mb"],
                    "cpu_percent": post_metrics["cpu_percent"],
                    "threads": post_metrics["num_threads"],
                    "fds": post_metrics["num_fds"]
                })

                # 10回ごとにガベージコレクション
                if i % 10 == 0:
                    gc.collect()

            except Exception as e:
                self.logger.error(f"リソース使用量テスト反復 {i} でエラー: {e}")

        # リソース使用量の分析
        avg_memory = sum(s["memory_mb"] for s in resource_samples) / len(resource_samples)
        avg_cpu = sum(s["cpu_percent"] for s in resource_samples) / len(resource_samples)
        avg_threads = sum(s["threads"] for s in resource_samples) / len(resource_samples)
        avg_fds = sum(s["fds"] for s in resource_samples) / len(resource_samples)

        return {
            "max_memory_mb": max_memory_mb,
            "max_cpu_percent": max_cpu_percent,
            "max_threads": max_threads,
            "max_fds": max_fds,
            "avg_memory_mb": avg_memory,
            "avg_cpu_percent": avg_cpu,
            "avg_threads": avg_threads,
            "avg_fds": avg_fds,
            "resource_samples": resource_samples[-10:],  # 最後の10サンプルのみ保存
            "memory_within_limits": max_memory_mb < 500,  # 500MB以内
            "cpu_within_limits": max_cpu_percent < 80,    # 80%以内
            "threads_within_limits": max_threads < 50,    # 50スレッド以内
            "fds_within_limits": max_fds < 100           # 100ファイルディスクリプタ以内
        }

    def _analyze_memory_trend(self, memory_samples: List[float]) -> Dict[str, any]:
        """メモリ使用量の傾向を分析"""
        if len(memory_samples) < 3:
            return {"trend": "insufficient_data"}

        # 線形回帰で傾向を分析
        n = len(memory_samples)
        x_sum = sum(range(n))
        y_sum = sum(memory_samples)
        xy_sum = sum(i * memory_samples[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        return {
            "trend": "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable",
            "slope_mb_per_sample": slope,
            "initial_memory": memory_samples[0],
            "final_memory": memory_samples[-1],
            "max_memory": max(memory_samples),
            "min_memory": min(memory_samples)
        }

    def _analyze_memory_stability(self, metrics_history: List[Dict]) -> Dict[str, any]:
        """メモリ使用量の安定性を分析"""
        if len(metrics_history) < 3:
            return {"is_stable": True, "reason": "insufficient_data"}

        memory_values = [m["memory_rss_mb"] for m in metrics_history]

        # 標準偏差を計算
        mean_memory = sum(memory_values) / len(memory_values)
        variance = sum((x - mean_memory) ** 2 for x in memory_values) / len(memory_values)
        std_dev = variance ** 0.5

        # 変動係数を計算（標準偏差/平均）
        coefficient_of_variation = std_dev / mean_memory if mean_memory > 0 else 0

        # 安定性の判定（変動係数が10%以下を安定とみなす）
        is_stable = coefficient_of_variation < 0.1

        return {
            "is_stable": is_stable,
            "mean_memory_mb": mean_memory,
            "std_dev_mb": std_dev,
            "coefficient_of_variation": coefficient_of_variation,
            "max_memory_mb": max(memory_values),
            "min_memory_mb": min(memory_values)
        }

    def run_comprehensive_performance_stability_tests(self) -> Dict[str, any]:
        """包括的なパフォーマンス・安定性テストを実行"""
        self.logger.info("包括的パフォーマンス・安定性テストを開始します...")

        # テスト環境をセットアップ
        workspace = self.setup_test_workspace()

        try:
            # ベースラインメトリクスを取得
            baseline = self.capture_baseline_metrics()

            # 1. メモリリーク検出テスト
            self.logger.info("=== メモリリーク検出テスト ===")
            memory_leak_results = self.test_memory_leak_detection(workspace)
            self.test_results["memory_leak_detection"] = memory_leak_results

            # 2. 並行実行安定性テスト
            self.logger.info("=== 並行実行安定性テスト ===")
            concurrent_results = self.test_concurrent_execution_stability(workspace)
            self.test_results["concurrent_execution_stability"] = concurrent_results

            # 3. 長時間実行安定性テスト
            self.logger.info("=== 長時間実行安定性テスト ===")
            long_running_results = self.test_long_running_stability(workspace)
            self.test_results["long_running_stability"] = long_running_results

            # 4. コンポーネントパフォーマンスベンチマーク
            self.logger.info("=== コンポーネントパフォーマンスベンチマーク ===")
            benchmark_results = self.test_component_performance_benchmarks()
            self.test_results["component_benchmarks"] = benchmark_results

            # 5. リソース使用量制限テスト
            self.logger.info("=== リソース使用量制限テスト ===")
            resource_results = self.test_resource_usage_limits(workspace)
            self.test_results["resource_usage_limits"] = resource_results

            # 最終メトリクスを取得
            final_metrics = self.capture_current_metrics()

            # 総合レポートを生成
            return self.generate_performance_stability_report(baseline, final_metrics)

        finally:
            # クリーンアップ
            import shutil
            try:
                shutil.rmtree(workspace)
            except Exception as e:
                self.logger.warning(f"テスト環境のクリーンアップ中にエラー: {e}")

    def generate_performance_stability_report(self, baseline: Dict, final_metrics: Dict) -> Dict[str, any]:
        """パフォーマンス・安定性レポートを生成"""

        # 各テストの成功判定
        memory_leak_ok = self.test_results.get("memory_leak_detection", {}).get("acceptable_memory_usage", False)
        concurrent_ok = self.test_results.get("concurrent_execution_stability", {}).get("stability_acceptable", False)
        long_running_ok = self.test_results.get("long_running_stability", {}).get("stability_acceptable", False)

        # コンポーネントベンチマークの成功判定
        benchmark_results = self.test_results.get("component_benchmarks", {})
        benchmark_ok = all(
            component.get("acceptable_performance", False)
            for component in benchmark_results.values()
        )

        # リソース使用量の成功判定
        resource_results = self.test_results.get("resource_usage_limits", {})
        resource_ok = all([
            resource_results.get("memory_within_limits", False),
            resource_results.get("cpu_within_limits", False),
            resource_results.get("threads_within_limits", False),
            resource_results.get("fds_within_limits", False)
        ])

        # 総合成功判定
        overall_success = all([memory_leak_ok, concurrent_ok, long_running_ok, benchmark_ok, resource_ok])

        return {
            "test_execution_time": datetime.now(timezone.utc).isoformat(),
            "baseline_metrics": baseline,
            "final_metrics": final_metrics,
            "test_results": self.test_results,
            "summary": {
                "memory_leak_detection_passed": memory_leak_ok,
                "concurrent_execution_stability_passed": concurrent_ok,
                "long_running_stability_passed": long_running_ok,
                "component_benchmarks_passed": benchmark_ok,
                "resource_usage_limits_passed": resource_ok,
                "overall_success": overall_success
            },
            "performance_metrics": {
                "total_memory_increase_mb": final_metrics["memory_rss_mb"] - baseline["memory_rss_mb"],
                "total_memory_increase_percent": ((final_metrics["memory_rss_mb"] - baseline["memory_rss_mb"]) / baseline["memory_rss_mb"]) * 100,
                "thread_count_change": final_metrics["num_threads"] - baseline["num_threads"],
                "fd_count_change": final_metrics["num_fds"] - baseline["num_fds"]
            },
            "requirements_validation": {
                "requirement_5_3_stability": concurrent_ok and long_running_ok,
                "requirement_5_3_performance": benchmark_ok and resource_ok,
                "requirement_5_3_memory_management": memory_leak_ok
            }
        }


# pytest用のテストクラス
class TestPerformanceStabilityValidation:
    """pytest用のパフォーマンス・安定性検証テストクラス"""

    @pytest.fixture(scope="class")
    def perf_validator(self):
        """パフォーマンス検証器のフィクスチャ"""
        return PerformanceStabilityValidator()

    @pytest.mark.timeout(900)  # 15分でタイムアウト
    def test_comprehensive_performance_stability(self, perf_validator):
        """包括的なパフォーマンス・安定性テストを実行"""
        report = perf_validator.run_comprehensive_performance_stability_tests()

        # Requirement 5.3 の検証
        requirements = report["requirements_validation"]

        # 安定性要件の検証
        assert requirements["requirement_5_3_stability"], "Requirement 5.3 failed: 安定性要件未達成"

        # パフォーマンス要件の検証
        assert requirements["requirement_5_3_performance"], "Requirement 5.3 failed: パフォーマンス要件未達成"

        # メモリ管理要件の検証
        assert requirements["requirement_5_3_memory_management"], "Requirement 5.3 failed: メモリ管理要件未達成"

        # 総合成功判定
        assert report["summary"]["overall_success"], "パフォーマンス・安定性テストの総合判定が失敗"

        # 個別テスト結果の検証
        summary = report["summary"]
        assert summary["memory_leak_detection_passed"], "メモリリーク検出テストが失敗"
        assert summary["concurrent_execution_stability_passed"], "並行実行安定性テストが失敗"
        assert summary["long_running_stability_passed"], "長時間実行安定性テストが失敗"
        assert summary["component_benchmarks_passed"], "コンポーネントベンチマークテストが失敗"
        assert summary["resource_usage_limits_passed"], "リソース使用量制限テストが失敗"

        # パフォーマンスメトリクスの検証
        perf_metrics = report["performance_metrics"]
        assert perf_metrics["total_memory_increase_percent"] < 50, "メモリ使用量の増加が許容範囲を超過"

        # レポートをファイルに保存
        report_file = Path("output") / "performance_stability_report.json"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"\nパフォーマンス・安定性レポートが保存されました: {report_file}")
        print(f"総合成功: {'✅' if report['summary']['overall_success'] else '❌'}")
        print(f"メモリ使用量増加: {perf_metrics['total_memory_increase_percent']:.1f}%")


def main():
    """スタンドアロン実行用のメイン関数"""
    validator = PerformanceStabilityValidator()
    report = validator.run_comprehensive_performance_stability_tests()

    # レポートを出力
    print("\n" + "="*80)
    print("パフォーマンス・安定性検証テスト結果レポート")
    print("="*80)

    summary = report["summary"]
    perf_metrics = report["performance_metrics"]

    print(f"\n総合成功: {'✅' if summary['overall_success'] else '❌'}")
    print(f"メモリリーク検出: {'✅' if summary['memory_leak_detection_passed'] else '❌'}")
    print(f"並行実行安定性: {'✅' if summary['concurrent_execution_stability_passed'] else '❌'}")
    print(f"長時間実行安定性: {'✅' if summary['long_running_stability_passed'] else '❌'}")
    print(f"コンポーネントベンチマーク: {'✅' if summary['component_benchmarks_passed'] else '❌'}")
    print(f"リソース使用量制限: {'✅' if summary['resource_usage_limits_passed'] else '❌'}")

    print(f"\nパフォーマンスメトリクス:")
    print(f"  メモリ使用量増加: {perf_metrics['total_memory_increase_percent']:.1f}%")
    print(f"  スレッド数変化: {perf_metrics['thread_count_change']}")
    print(f"  ファイルディスクリプタ変化: {perf_metrics['fd_count_change']}")

    # レポートファイルを保存
    report_file = Path("performance_stability_report.json")
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n詳細レポートが保存されました: {report_file}")

    return 0 if summary["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
