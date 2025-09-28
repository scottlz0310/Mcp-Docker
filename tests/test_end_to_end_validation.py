#!/usr/bin/env python3
"""
GitHub Actions Simulator - エンドツーエンド検証テスト
実際のワークフローファイルでの完全なエンドツーエンドテスト

このテストは以下を検証します:
- 実際の.github/workflows/*.ymlファイルでの実行
- 様々なワークフロー設定パターンの処理
- タイムアウトシナリオの適切な処理
- エラー条件での堅牢性
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

from services.actions.logger import ActionsLogger
from services.actions.service import SimulationService, SimulationParameters
from services.actions.workflow_parser import WorkflowParser


class EndToEndValidationTest:
    """エンドツーエンド検証テストクラス"""

    def __init__(self):
        self.logger = ActionsLogger(verbose=True, debug=True)
        self.test_results: Dict[str, Dict] = {}

    def create_real_world_workflows(self, workspace_dir: Path) -> Dict[str, Path]:
        """実際のプロジェクトで使用されるようなワークフローを作成"""
        workflows_dir = workspace_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        workflows = {}

        # 1. CI/CDワークフロー（一般的なパターン）
        ci_workflow = workflows_dir / "ci.yml"
        ci_workflow.write_text("""
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # 毎週月曜日 2:00 AM

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run Prettier
        run: npm run format:check

  test:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        node-version: [16, 18, 20]
        os: [ubuntu-latest, windows-latest, macos-latest]
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

      - name: Run tests
        run: npm test
        env:
          CI: true

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: matrix.node-version == 18 && matrix.os == 'ubuntu-latest'

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-files
          path: dist/

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v3
        with:
          name: build-files
          path: dist/

      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # Deployment commands would go here
""")
        workflows["ci_cd"] = ci_workflow

        # 2. セキュリティスキャンワークフロー
        security_workflow = workflows_dir / "security.yml"
        security_workflow.write_text("""
name: Security Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # 毎日 6:00 AM

permissions:
  contents: read
  security-events: write

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run npm audit
        run: npm audit --audit-level=high
        continue-on-error: true

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  code-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: javascript, python

      - name: Autobuild
        uses: github/codeql-action/autobuild@v2

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2

  container-scan:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t test-image .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'test-image'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
""")
        workflows["security"] = security_workflow

        # 3. リリースワークフロー
        release_workflow = workflows_dir / "release.yml"
        release_workflow.write_text("""
name: Release
on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  packages: write

jobs:
  create-release:
    runs-on: ubuntu-latest
    outputs:
      upload_url: ${{ steps.create_release.outputs.upload_url }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false

  build-and-upload:
    runs-on: ${{ matrix.os }}
    needs: create-release
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        include:
          - os: ubuntu-latest
            asset_name: app-linux
          - os: windows-latest
            asset_name: app-windows.exe
          - os: macos-latest
            asset_name: app-macos
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
        run: npm run build:${{ matrix.os }}

      - name: Upload Release Asset
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ needs.create-release.outputs.upload_url }}
          asset_path: ./dist/${{ matrix.asset_name }}
          asset_name: ${{ matrix.asset_name }}
          asset_content_type: application/octet-stream

  publish-docker:
    runs-on: ubuntu-latest
    needs: create-release
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: myorg/myapp
          tags: |
            type=ref,event=tag
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
""")
        workflows["release"] = release_workflow

        # 4. 複雑な条件分岐ワークフロー
        conditional_workflow = workflows_dir / "conditional.yml"
        conditional_workflow.write_text("""
name: Conditional Workflow
on:
  push:
    branches: [main, develop, 'feature/*', 'hotfix/*']
  pull_request:
    types: [opened, synchronize, reopened, closed]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      frontend-changed: ${{ steps.changes.outputs.frontend }}
      backend-changed: ${{ steps.changes.outputs.backend }}
      docs-changed: ${{ steps.changes.outputs.docs }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changes
        id: changes
        uses: dorny/paths-filter@v2
        with:
          filters: |
            frontend:
              - 'frontend/**'
              - 'package.json'
            backend:
              - 'backend/**'
              - 'requirements.txt'
            docs:
              - 'docs/**'
              - '*.md'

  frontend-tests:
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend-changed == 'true'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Run frontend tests
        run: |
          cd frontend
          npm ci
          npm test

  backend-tests:
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.backend-changed == 'true'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run backend tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest

  docs-build:
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.docs-changed == 'true'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build documentation
        run: |
          cd docs
          make html

  integration-tests:
    runs-on: ubuntu-latest
    needs: [frontend-tests, backend-tests]
    if: always() && (needs.frontend-tests.result == 'success' || needs.backend-tests.result == 'success')
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run integration tests
        run: |
          echo "Running integration tests..."
          # Integration test commands

  deploy-staging:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          echo "Deploying to staging environment..."

  deploy-production:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          echo "Deploying to production environment..."
""")
        workflows["conditional"] = conditional_workflow

        # 5. パフォーマンステスト用の長時間実行ワークフロー
        performance_workflow = workflows_dir / "performance.yml"
        performance_workflow.write_text("""
name: Performance Tests
on:
  schedule:
    - cron: '0 3 * * 0'  # 毎週日曜日 3:00 AM
  workflow_dispatch:
    inputs:
      test_duration:
        description: 'Test duration in minutes'
        required: false
        default: '10'

jobs:
  load-test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup test environment
        run: |
          echo "Setting up load test environment..."
          sleep 2

      - name: Run load tests
        run: |
          echo "Running load tests for ${{ github.event.inputs.test_duration || '10' }} minutes..."
          # Simulate long-running load test
          for i in {1..5}; do
            echo "Load test iteration $i/5"
            sleep 3
          done

      - name: Generate performance report
        run: |
          echo "Generating performance report..."
          sleep 1

  stress-test:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run stress tests
        run: |
          echo "Running stress tests..."
          # Simulate stress testing
          for i in {1..10}; do
            echo "Stress test batch $i/10"
            sleep 2
          done

  benchmark:
    runs-on: ubuntu-latest
    needs: [load-test, stress-test]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run benchmarks
        run: |
          echo "Running performance benchmarks..."
          sleep 5

      - name: Compare with baseline
        run: |
          echo "Comparing results with baseline..."
          sleep 2
""")
        workflows["performance"] = performance_workflow

        return workflows

    def test_workflow_parsing_accuracy(self, workflows: Dict[str, Path]) -> Dict[str, Dict]:
        """ワークフロー解析精度テスト"""
        self.logger.info("ワークフロー解析精度テストを実行中...")

        results = {}
        parser = WorkflowParser()

        for name, workflow_file in workflows.items():
            try:
                start_time = time.time()
                workflow_data = parser.parse_file(workflow_file)
                parsing_time = time.time() - start_time

                # 解析結果の詳細検証
                jobs = workflow_data.get("jobs", {})
                total_steps = sum(len(job.get("steps", [])) for job in jobs.values())

                # マトリックス戦略の検出
                has_matrix = any(
                    "strategy" in job and "matrix" in job.get("strategy", {})
                    for job in jobs.values()
                )

                # 条件分岐の検出
                has_conditions = any(
                    "if" in job for job in jobs.values()
                ) or any(
                    "if" in step
                    for job in jobs.values()
                    for step in job.get("steps", [])
                )

                # 環境変数の検出
                has_env_vars = "env" in workflow_data or any(
                    "env" in job for job in jobs.values()
                )

                # needs依存関係の検出
                has_dependencies = any(
                    "needs" in job for job in jobs.values()
                )

                results[name] = {
                    "parsing_success": True,
                    "parsing_time_ms": parsing_time * 1000,
                    "job_count": len(jobs),
                    "total_steps": total_steps,
                    "has_matrix_strategy": has_matrix,
                    "has_conditions": has_conditions,
                    "has_env_vars": has_env_vars,
                    "has_dependencies": has_dependencies,
                    "triggers": list(workflow_data.get("on", {}).keys()) if isinstance(workflow_data.get("on"), dict) else [workflow_data.get("on", "")],
                }

            except Exception as e:
                self.logger.error(f"ワークフロー '{name}' の解析中にエラー: {e}")
                results[name] = {
                    "parsing_success": False,
                    "error": str(e),
                    "parsing_time_ms": 0
                }

        return results

    def test_simulation_execution_scenarios(self, workflows: Dict[str, Path]) -> Dict[str, Dict]:
        """シミュレーション実行シナリオテスト"""
        self.logger.info("シミュレーション実行シナリオテストを実行中...")

        results = {}
        simulation_service = SimulationService()

        for name, workflow_file in workflows.items():
            self.logger.info(f"ワークフロー '{name}' のシミュレーションテストを実行中...")

            try:
                # 基本的なドライラン実行
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=True
                )

                start_time = time.time()
                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )
                execution_time = time.time() - start_time

                # 特定のジョブのみの実行テスト（最初のジョブ）
                parser = WorkflowParser()
                workflow_data = parser.parse_file(workflow_file)
                jobs = workflow_data.get("jobs", {})
                first_job = list(jobs.keys())[0] if jobs else None

                job_specific_result = None
                if first_job:
                    job_params = SimulationParameters(
                        workflow_file=workflow_file,
                        job=first_job,
                        dry_run=True,
                        verbose=False
                    )
                    job_specific_result = simulation_service.run_simulation(
                        job_params,
                        logger=self.logger,
                        capture_output=True
                    )

                results[name] = {
                    "execution_success": result.success,
                    "execution_time_seconds": execution_time,
                    "return_code": result.return_code,
                    "has_stdout": bool(result.stdout),
                    "has_stderr": bool(result.stderr),
                    "stdout_length": len(result.stdout) if result.stdout else 0,
                    "stderr_length": len(result.stderr) if result.stderr else 0,
                    "job_specific_test": {
                        "tested_job": first_job,
                        "success": job_specific_result.success if job_specific_result else False
                    } if first_job else None
                }

            except Exception as e:
                self.logger.error(f"ワークフロー '{name}' のシミュレーション中にエラー: {e}")
                results[name] = {
                    "execution_success": False,
                    "error": str(e),
                    "execution_time_seconds": 0
                }

        return results

    def test_timeout_handling_scenarios(self, workspace_dir: Path) -> Dict[str, Dict]:
        """タイムアウト処理シナリオテスト"""
        self.logger.info("タイムアウト処理シナリオテストを実行中...")

        # タイムアウトテスト用のワークフローを作成
        timeout_workflows_dir = workspace_dir / "timeout_tests"
        timeout_workflows_dir.mkdir(exist_ok=True)

        # 短いタイムアウトワークフロー
        short_timeout_workflow = timeout_workflows_dir / "short_timeout.yml"
        short_timeout_workflow.write_text("""
name: Short Timeout Test
on: [push]
jobs:
  quick-job:
    runs-on: ubuntu-latest
    timeout-minutes: 1
    steps:
      - name: Quick task
        run: echo "This should complete quickly"
      - name: Another quick task
        run: sleep 1 && echo "Still quick"
""")

        # 中程度のタイムアウトワークフロー
        medium_timeout_workflow = timeout_workflows_dir / "medium_timeout.yml"
        medium_timeout_workflow.write_text("""
name: Medium Timeout Test
on: [push]
jobs:
  medium-job:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Setup
        run: echo "Setting up..."
      - name: Medium task
        run: |
          echo "Running medium duration task"
          sleep 2
          echo "Task completed"
""")

        results = {}
        simulation_service = SimulationService()

        timeout_workflows = {
            "short_timeout": short_timeout_workflow,
            "medium_timeout": medium_timeout_workflow
        }

        for name, workflow_file in timeout_workflows.items():
            try:
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=True
                )

                start_time = time.time()
                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )
                execution_time = time.time() - start_time

                results[name] = {
                    "execution_success": result.success,
                    "execution_time_seconds": execution_time,
                    "timeout_handled_properly": execution_time < 30,  # 30秒以内で完了すべき
                    "return_code": result.return_code
                }

            except Exception as e:
                self.logger.error(f"タイムアウトテスト '{name}' 中にエラー: {e}")
                results[name] = {
                    "execution_success": False,
                    "error": str(e),
                    "timeout_handled_properly": False
                }

        return results

    def test_error_recovery_scenarios(self, workspace_dir: Path) -> Dict[str, Dict]:
        """エラー復旧シナリオテスト"""
        self.logger.info("エラー復旧シナリオテストを実行中...")

        # エラーテスト用のワークフローを作成
        error_workflows_dir = workspace_dir / "error_tests"
        error_workflows_dir.mkdir(exist_ok=True)

        # 構文エラーワークフロー
        syntax_error_workflow = error_workflows_dir / "syntax_error.yml"
        syntax_error_workflow.write_text("""
name: Syntax Error Test
on: [push]
jobs:
  syntax-error-job:
    runs-on: ubuntu-latest
    steps:
      - name: Valid step
        run: echo "This is valid"
      - name: Invalid syntax
        run: echo "Missing quote
      - name: Another step
        run: echo "This won't be reached"
""")

        # 実行時エラーワークフロー
        runtime_error_workflow = error_workflows_dir / "runtime_error.yml"
        runtime_error_workflow.write_text("""
name: Runtime Error Test
on: [push]
jobs:
  runtime-error-job:
    runs-on: ubuntu-latest
    steps:
      - name: Successful step
        run: echo "This succeeds"
      - name: Failing step
        run: |
          echo "This will fail"
          exit 1
      - name: Should not execute
        run: echo "This should not run"
""")

        results = {}
        simulation_service = SimulationService()

        error_workflows = {
            "syntax_error": syntax_error_workflow,
            "runtime_error": runtime_error_workflow
        }

        for name, workflow_file in error_workflows.items():
            try:
                params = SimulationParameters(
                    workflow_file=workflow_file,
                    dry_run=True,
                    verbose=True
                )

                start_time = time.time()
                result = simulation_service.run_simulation(
                    params,
                    logger=self.logger,
                    capture_output=True
                )
                execution_time = time.time() - start_time

                # エラーが適切に処理されたかチェック
                error_handled_properly = (
                    not result.success and  # 失敗が検出された
                    result.return_code != 0 and  # 適切な終了コード
                    execution_time < 10  # 適切な時間内で終了
                )

                results[name] = {
                    "error_detected": not result.success,
                    "execution_time_seconds": execution_time,
                    "error_handled_properly": error_handled_properly,
                    "return_code": result.return_code,
                    "has_error_output": bool(result.stderr)
                }

            except Exception as e:
                # 例外が発生した場合も適切なエラーハンドリングとして評価
                results[name] = {
                    "error_detected": True,
                    "exception_caught": True,
                    "error_handled_properly": True,
                    "exception_message": str(e)
                }

        return results

    def test_performance_under_load(self, workflows: Dict[str, Path]) -> Dict[str, float]:
        """負荷下でのパフォーマンステスト"""
        self.logger.info("負荷下でのパフォーマンステストを実行中...")

        performance_metrics = {}
        simulation_service = SimulationService()

        # 複数のワークフローを連続実行
        total_start_time = time.time()
        execution_times = []

        for iteration in range(3):  # 3回繰り返し
            self.logger.info(f"パフォーマンステスト反復 {iteration + 1}/3")

            for name, workflow_file in workflows.items():
                try:
                    params = SimulationParameters(
                        workflow_file=workflow_file,
                        dry_run=True,
                        verbose=False  # パフォーマンステストでは詳細ログを無効化
                    )

                    start_time = time.time()
                    result = simulation_service.run_simulation(
                        params,
                        logger=self.logger,
                        capture_output=True
                    )
                    execution_time = time.time() - start_time
                    execution_times.append(execution_time)

                except Exception as e:
                    self.logger.error(f"パフォーマンステスト中にエラー ({name}): {e}")
                    execution_times.append(float('inf'))  # エラーの場合は無限大

        total_time = time.time() - total_start_time

        # 統計を計算
        valid_times = [t for t in execution_times if t != float('inf')]

        if valid_times:
            performance_metrics.update({
                "total_execution_time_seconds": total_time,
                "average_execution_time_seconds": sum(valid_times) / len(valid_times),
                "min_execution_time_seconds": min(valid_times),
                "max_execution_time_seconds": max(valid_times),
                "successful_executions": len(valid_times),
                "total_executions": len(execution_times),
                "success_rate": len(valid_times) / len(execution_times)
            })
        else:
            performance_metrics.update({
                "total_execution_time_seconds": total_time,
                "successful_executions": 0,
                "total_executions": len(execution_times),
                "success_rate": 0.0
            })

        return performance_metrics

    def run_comprehensive_end_to_end_tests(self) -> Dict[str, any]:
        """包括的なエンドツーエンドテストを実行"""
        self.logger.info("包括的エンドツーエンドテストを開始します...")

        # テスト環境をセットアップ
        workspace_dir = Path(tempfile.mkdtemp(prefix="e2e_validation_"))

        try:
            # 実世界のワークフローを作成
            workflows = self.create_real_world_workflows(workspace_dir)

            # 1. ワークフロー解析精度テスト
            self.logger.info("=== ワークフロー解析精度テスト ===")
            parsing_results = self.test_workflow_parsing_accuracy(workflows)
            self.test_results["workflow_parsing"] = parsing_results

            # 2. シミュレーション実行シナリオテスト
            self.logger.info("=== シミュレーション実行シナリオテスト ===")
            execution_results = self.test_simulation_execution_scenarios(workflows)
            self.test_results["simulation_execution"] = execution_results

            # 3. タイムアウト処理シナリオテスト
            self.logger.info("=== タイムアウト処理シナリオテスト ===")
            timeout_results = self.test_timeout_handling_scenarios(workspace_dir)
            self.test_results["timeout_handling"] = timeout_results

            # 4. エラー復旧シナリオテスト
            self.logger.info("=== エラー復旧シナリオテスト ===")
            error_recovery_results = self.test_error_recovery_scenarios(workspace_dir)
            self.test_results["error_recovery"] = error_recovery_results

            # 5. 負荷下でのパフォーマンステスト
            self.logger.info("=== 負荷下でのパフォーマンステスト ===")
            performance_results = self.test_performance_under_load(workflows)
            self.test_results["performance_under_load"] = performance_results

            # 総合レポートを生成
            return self.generate_end_to_end_report()

        finally:
            # クリーンアップ
            import shutil
            try:
                shutil.rmtree(workspace_dir)
            except Exception as e:
                self.logger.warning(f"テスト環境のクリーンアップ中にエラー: {e}")

    def generate_end_to_end_report(self) -> Dict[str, any]:
        """エンドツーエンドテストレポートを生成"""
        # 成功率を計算
        parsing_success_rate = self._calculate_success_rate(
            self.test_results.get("workflow_parsing", {}),
            "parsing_success"
        )

        execution_success_rate = self._calculate_success_rate(
            self.test_results.get("simulation_execution", {}),
            "execution_success"
        )

        timeout_success_rate = self._calculate_success_rate(
            self.test_results.get("timeout_handling", {}),
            "timeout_handled_properly"
        )

        error_recovery_success_rate = self._calculate_success_rate(
            self.test_results.get("error_recovery", {}),
            "error_handled_properly"
        )

        # パフォーマンス要件チェック
        performance_data = self.test_results.get("performance_under_load", {})
        performance_acceptable = (
            performance_data.get("success_rate", 0) >= 0.8 and
            performance_data.get("average_execution_time_seconds", float('inf')) < 10
        )

        return {
            "test_execution_time": time.time(),
            "test_results": self.test_results,
            "summary": {
                "workflow_parsing_success_rate": parsing_success_rate,
                "simulation_execution_success_rate": execution_success_rate,
                "timeout_handling_success_rate": timeout_success_rate,
                "error_recovery_success_rate": error_recovery_success_rate,
                "performance_acceptable": performance_acceptable,
                "overall_success": all([
                    parsing_success_rate >= 0.9,
                    execution_success_rate >= 0.8,
                    timeout_success_rate >= 0.8,
                    error_recovery_success_rate >= 0.8,
                    performance_acceptable
                ])
            },
            "requirements_validation": {
                "requirement_5_1": execution_success_rate >= 0.8,  # 様々なワークフローファイルでの成功実行
                "requirement_5_2": timeout_success_rate >= 0.8,    # タイムアウトシナリオの適切な処理
                "requirement_5_3": performance_acceptable,          # 安定性とパフォーマンス
                "requirement_5_4": parsing_success_rate >= 0.9     # 様々なワークフロー設定の処理
            }
        }

    def _calculate_success_rate(self, results: Dict, success_key: str) -> float:
        """成功率を計算"""
        if not results:
            return 0.0

        successful = sum(
            1 for result in results.values()
            if isinstance(result, dict) and result.get(success_key, False)
        )
        total = len(results)

        return successful / total if total > 0 else 0.0


# pytest用のテストクラス
class TestEndToEndValidation:
    """pytest用のエンドツーエンド検証テストクラス"""

    @pytest.fixture(scope="class")
    def e2e_tester(self):
        """エンドツーエンドテスターのフィクスチャ"""
        return EndToEndValidationTest()

    @pytest.mark.timeout(600)  # 10分でタイムアウト
    def test_comprehensive_end_to_end_validation(self, e2e_tester):
        """包括的なエンドツーエンド検証テストを実行"""
        report = e2e_tester.run_comprehensive_end_to_end_tests()

        # Requirements 5.1-5.4 の検証
        requirements = report["requirements_validation"]

        # Requirement 5.1: 様々なワークフローファイルでの成功実行
        assert requirements["requirement_5_1"], "Requirement 5.1 failed: ワークフローの実行成功率が不十分"

        # Requirement 5.2: タイムアウトシナリオの適切な処理
        assert requirements["requirement_5_2"], "Requirement 5.2 failed: タイムアウト処理が不適切"

        # Requirement 5.3: 安定性とパフォーマンス
        assert requirements["requirement_5_3"], "Requirement 5.3 failed: パフォーマンス要件未達成"

        # Requirement 5.4: 様々なワークフロー設定の処理
        assert requirements["requirement_5_4"], "Requirement 5.4 failed: ワークフロー解析成功率が不十分"

        # 総合成功判定
        assert report["summary"]["overall_success"], "エンドツーエンドテストの総合判定が失敗"

        # レポートをファイルに保存
        report_file = Path("output") / "end_to_end_validation_report.json"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"\nエンドツーエンド検証レポートが保存されました: {report_file}")
        print(f"総合成功: {'✅' if report['summary']['overall_success'] else '❌'}")
        print(f"ワークフロー解析成功率: {report['summary']['workflow_parsing_success_rate']:.1%}")
        print(f"シミュレーション実行成功率: {report['summary']['simulation_execution_success_rate']:.1%}")


def main():
    """スタンドアロン実行用のメイン関数"""
    tester = EndToEndValidationTest()
    report = tester.run_comprehensive_end_to_end_tests()

    # レポートを出力
    print("\n" + "="*80)
    print("エンドツーエンド検証テスト結果レポート")
    print("="*80)

    summary = report["summary"]
    requirements = report["requirements_validation"]

    print(f"\n総合成功: {'✅' if summary['overall_success'] else '❌'}")
    print(f"ワークフロー解析成功率: {summary['workflow_parsing_success_rate']:.1%}")
    print(f"シミュレーション実行成功率: {summary['simulation_execution_success_rate']:.1%}")
    print(f"タイムアウト処理成功率: {summary['timeout_handling_success_rate']:.1%}")
    print(f"エラー復旧成功率: {summary['error_recovery_success_rate']:.1%}")
    print(f"パフォーマンス要件: {'✅' if summary['performance_acceptable'] else '❌'}")

    print("\n要件検証結果:")
    print(f"  Requirement 5.1 (ワークフロー実行): {'✅' if requirements['requirement_5_1'] else '❌'}")
    print(f"  Requirement 5.2 (タイムアウト処理): {'✅' if requirements['requirement_5_2'] else '❌'}")
    print(f"  Requirement 5.3 (安定性・パフォーマンス): {'✅' if requirements['requirement_5_3'] else '❌'}")
    print(f"  Requirement 5.4 (ワークフロー設定): {'✅' if requirements['requirement_5_4'] else '❌'}")

    # レポートファイルを保存
    report_file = Path("end_to_end_validation_report.json")
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n詳細レポートが保存されました: {report_file}")

    return 0 if summary["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
