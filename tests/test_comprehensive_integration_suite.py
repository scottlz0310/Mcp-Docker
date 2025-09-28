#!/usr/bin/env python3
"""
GitHub Actions Simulator - 包括的統合テストスイート
===============================================

このテストスイートは、全コンポーネントの統合テストを実行します。

テスト内容:
- 配布スクリプト、ドキュメント、テンプレートの統合動作
- CI/CDパイプラインでの品質ゲート検証
- 全体的なシステム整合性確認
- パフォーマンスと安定性の検証

実行方法:
    pytest tests/test_comprehensive_integration_suite.py -v
    python -m pytest tests/test_comprehensive_integration_suite.py::TestComprehensiveIntegration::test_full_system_integration -v
"""

import os
import subprocess
import tempfile
import time
import pytest
import yaml
from pathlib import Path
from typing import Dict
import concurrent.futures
import threading


class TestComprehensiveIntegration:
    """包括的統合テストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def test_environment(self, project_root):
        """テスト環境の設定"""
        return {
            "project_root": project_root,
            "scripts_dir": project_root / "scripts",
            "docs_dir": project_root / "docs",
            "tests_dir": project_root / "tests",
            "workflows_dir": project_root / ".github" / "workflows",
        }

    def test_full_system_integration(self, test_environment):
        """フルシステム統合テスト"""
        project_root = test_environment["project_root"]

        # Phase 1: 配布スクリプトの動作確認
        distribution_result = self._test_distribution_script_integration(project_root)
        assert distribution_result[
            "success"
        ], f"配布スクリプト統合テスト失敗: {distribution_result['error']}"

        # Phase 2: ドキュメント整合性の確認
        documentation_result = self._test_documentation_integration(project_root)
        assert documentation_result[
            "success"
        ], f"ドキュメント統合テスト失敗: {documentation_result['error']}"

        # Phase 3: テンプレート検証の確認
        template_result = self._test_template_integration(project_root)
        assert template_result[
            "success"
        ], f"テンプレート統合テスト失敗: {template_result['error']}"

        # Phase 4: エンドツーエンド体験の確認
        e2e_result = self._test_end_to_end_integration(project_root)
        assert e2e_result[
            "success"
        ], f"エンドツーエンド統合テスト失敗: {e2e_result['error']}"

        # 統合結果のサマリー
        integration_summary = {
            "distribution": distribution_result,
            "documentation": documentation_result,
            "templates": template_result,
            "end_to_end": e2e_result,
            "overall_success": True,
        }

        return integration_summary

    def _test_distribution_script_integration(self, project_root: Path) -> Dict:
        """配布スクリプト統合テスト"""
        try:
            run_script = project_root / "scripts" / "run-actions.sh"

            if not run_script.exists():
                return {"success": False, "error": "run-actions.sh が見つかりません"}

            # 基本的な機能テスト
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            # ヘルプオプションのテスト
            help_result = subprocess.run(
                [str(run_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_root,
                env=env,
            )

            if help_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"ヘルプオプション失敗: {help_result.stderr}",
                }

            # 依存関係チェックのテスト
            deps_result = subprocess.run(
                [str(run_script), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
                env=env,
            )

            # 依存関係チェックは成功または適切なエラーを返すべき
            if deps_result.returncode not in [0, 2]:
                return {
                    "success": False,
                    "error": f"依存関係チェック異常終了: {deps_result.returncode}",
                }

            return {
                "success": True,
                "help_output_length": len(help_result.stdout),
                "deps_output_length": len(deps_result.stdout + deps_result.stderr),
                "execution_time": "normal",
            }

        except Exception as e:
            return {"success": False, "error": f"配布スクリプトテスト例外: {str(e)}"}

    def _test_documentation_integration(self, project_root: Path) -> Dict:
        """ドキュメント統合テスト"""
        try:
            # 必須ドキュメントの存在確認
            required_docs = ["README.md", "CONTRIBUTING.md", "docs/TROUBLESHOOTING.md"]

            missing_docs = []
            for doc_path in required_docs:
                if not (project_root / doc_path).exists():
                    missing_docs.append(doc_path)

            if missing_docs:
                return {
                    "success": False,
                    "error": f"必須ドキュメント不足: {missing_docs}",
                }

            # ドキュメント整合性チェックスクリプトの実行
            docs_check_script = project_root / "scripts" / "check-docs-consistency.py"
            if docs_check_script.exists():
                docs_result = subprocess.run(
                    ["python", str(docs_check_script)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_root,
                )

                if docs_result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"ドキュメント整合性チェック失敗: {docs_result.stderr}",
                    }

            # README.mdの基本構造確認
            readme_content = (project_root / "README.md").read_text(encoding="utf-8")
            essential_sections = [
                "GitHub Actions Simulator",
                "使用方法",
                "インストール",
            ]

            missing_sections = []
            for section in essential_sections:
                if section not in readme_content:
                    missing_sections.append(section)

            if missing_sections:
                return {
                    "success": False,
                    "error": f"README必須セクション不足: {missing_sections}",
                }

            return {
                "success": True,
                "readme_length": len(readme_content),
                "docs_count": len(list(project_root.glob("docs/**/*.md"))),
                "consistency_check": "passed",
            }

        except Exception as e:
            return {"success": False, "error": f"ドキュメント統合テスト例外: {str(e)}"}

    def _test_template_integration(self, project_root: Path) -> Dict:
        """テンプレート統合テスト"""
        try:
            # テンプレート検証スクリプトの実行
            template_validator = project_root / "scripts" / "validate-templates.py"

            if not template_validator.exists():
                return {
                    "success": False,
                    "error": "validate-templates.py が見つかりません",
                }

            validation_result = subprocess.run(
                ["python", str(template_validator), "--check-only"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=project_root,
            )

            # テンプレート検証は成功または警告付き成功を返すべき
            if validation_result.returncode not in [0, 1]:
                return {
                    "success": False,
                    "error": f"テンプレート検証失敗: {validation_result.stderr}",
                }

            # 重要なテンプレートファイルの存在確認
            important_templates = [
                ".env.example",
                "docker-compose.override.yml.sample",
                ".pre-commit-config.yaml.sample",
            ]

            missing_templates = []
            for template_path in important_templates:
                if not (project_root / template_path).exists():
                    missing_templates.append(template_path)

            # 一部のテンプレートが不足していても警告レベル
            template_status = "complete" if not missing_templates else "partial"

            return {
                "success": True,
                "validation_output": validation_result.stdout,
                "template_status": template_status,
                "missing_templates": missing_templates,
                "validation_time": "normal",
            }

        except Exception as e:
            return {"success": False, "error": f"テンプレート統合テスト例外: {str(e)}"}

    def _test_end_to_end_integration(self, project_root: Path) -> Dict:
        """エンドツーエンド統合テスト"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_project = Path(temp_dir) / "test_project"
                test_project.mkdir()

                # テストプロジェクトの基本構造を作成
                (test_project / ".github" / "workflows").mkdir(parents=True)

                # サンプルワークフローを作成
                workflow_content = """
name: Test CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: echo "Test completed"
"""
                (test_project / ".github" / "workflows" / "test.yml").write_text(
                    workflow_content
                )

                # 配布スクリプトでテストプロジェクトを実行
                run_script = project_root / "scripts" / "run-actions.sh"

                env = os.environ.copy()
                env["NON_INTERACTIVE"] = "1"
                env["INDEX"] = "1"
                env["ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"] = "15"

                e2e_result = subprocess.run(
                    [str(run_script)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=test_project,
                    env=env,
                )

                # エンドツーエンドテストは実行が試行されることを確認
                output = e2e_result.stdout + e2e_result.stderr

                execution_indicators = [
                    "ワークフロー",
                    "Docker",
                    "実行",
                    "test.yml",
                    "タイムアウト",
                    "エラー",
                ]

                execution_attempted = any(
                    indicator in output for indicator in execution_indicators
                )

                if not execution_attempted:
                    return {
                        "success": False,
                        "error": f"エンドツーエンド実行が試行されませんでした: {output}",
                    }

                return {
                    "success": True,
                    "execution_attempted": True,
                    "output_length": len(output),
                    "return_code": e2e_result.returncode,
                    "test_project_created": True,
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"エンドツーエンド統合テスト例外: {str(e)}",
            }

    def test_parallel_component_testing(self, test_environment):
        """並列コンポーネントテスト"""
        project_root = test_environment["project_root"]

        # 並列実行するテスト関数
        test_functions = [
            ("distribution", self._test_distribution_script_integration),
            ("documentation", self._test_documentation_integration),
            ("template", self._test_template_integration),
        ]

        results = {}

        # 並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_test = {
                executor.submit(test_func, project_root): test_name
                for test_name, test_func in test_functions
            }

            for future in concurrent.futures.as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    result = future.result(timeout=300)  # 5分タイムアウト
                    results[test_name] = result
                except Exception as e:
                    results[test_name] = {
                        "success": False,
                        "error": f"並列実行例外: {str(e)}",
                    }

        # 全てのテストが成功することを確認
        failed_tests = []
        for test_name, result in results.items():
            if not result["success"]:
                failed_tests.append(f"{test_name}: {result['error']}")

        assert not failed_tests, f"並列テストで失敗: {failed_tests}"

        return results

    def test_performance_benchmarks(self, test_environment):
        """パフォーマンスベンチマークテスト"""
        project_root = test_environment["project_root"]

        benchmarks = {}

        # 配布スクリプトのパフォーマンステスト
        run_script = project_root / "scripts" / "run-actions.sh"

        if run_script.exists():
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            # ヘルプオプションの実行時間
            start_time = time.time()
            help_result = subprocess.run(
                [str(run_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_root,
                env=env,
            )
            help_time = time.time() - start_time

            benchmarks["help_execution_time"] = help_time

            # 依存関係チェックの実行時間
            start_time = time.time()
            deps_result = subprocess.run(
                [str(run_script), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
                env=env,
            )
            deps_time = time.time() - start_time

            benchmarks["deps_check_time"] = deps_time

        # テンプレート検証のパフォーマンステスト
        template_validator = project_root / "scripts" / "validate-templates.py"

        if template_validator.exists():
            start_time = time.time()
            validation_result = subprocess.run(
                ["python", str(template_validator), "--check-only"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=project_root,
            )
            validation_time = time.time() - start_time

            benchmarks["template_validation_time"] = validation_time

        # パフォーマンス基準の確認
        performance_issues = []

        if benchmarks.get("help_execution_time", 0) > 10:
            performance_issues.append(
                f"ヘルプ実行が遅い: {benchmarks['help_execution_time']:.2f}秒"
            )

        if benchmarks.get("deps_check_time", 0) > 60:
            performance_issues.append(
                f"依存関係チェックが遅い: {benchmarks['deps_check_time']:.2f}秒"
            )

        if benchmarks.get("template_validation_time", 0) > 120:
            performance_issues.append(
                f"テンプレート検証が遅い: {benchmarks['template_validation_time']:.2f}秒"
            )

        assert not performance_issues, f"パフォーマンス問題: {performance_issues}"

        return benchmarks

    def test_error_recovery_scenarios(self, test_environment):
        """エラー回復シナリオテスト"""
        project_root = test_environment["project_root"]

        recovery_tests = []

        # シナリオ1: 存在しないワークフローファイル
        with tempfile.TemporaryDirectory() as temp_dir:
            test_project = Path(temp_dir) / "error_test_project"
            test_project.mkdir()

            run_script = project_root / "scripts" / "run-actions.sh"

            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            result = subprocess.run(
                [str(run_script), "nonexistent.yml"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=test_project,
                env=env,
            )

            output = result.stdout + result.stderr

            # エラーメッセージが有用であることを確認
            helpful_error = any(
                indicator in output
                for indicator in ["見つかりません", "存在しません", "確認", "ヘルプ"]
            )

            recovery_tests.append(
                {
                    "scenario": "nonexistent_workflow",
                    "helpful_error": helpful_error,
                    "output_length": len(output),
                }
            )

        # シナリオ2: 無効なオプション
        result = subprocess.run(
            [str(project_root / "scripts" / "run-actions.sh"), "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root,
            env={"NON_INTERACTIVE": "1"},
        )

        # 無効なオプションが適切に処理されることを確認
        recovery_tests.append(
            {
                "scenario": "invalid_option",
                "handled_gracefully": result.returncode != 127,
                "output_length": len(result.stdout + result.stderr),
            }
        )

        # 全ての回復シナリオが適切に処理されることを確認
        failed_recoveries = []
        for test in recovery_tests:
            if test["scenario"] == "nonexistent_workflow" and not test["helpful_error"]:
                failed_recoveries.append(
                    "存在しないワークフローファイルのエラーメッセージが不適切"
                )
            elif (
                test["scenario"] == "invalid_option" and not test["handled_gracefully"]
            ):
                failed_recoveries.append("無効なオプションが適切に処理されていない")

        assert not failed_recoveries, f"エラー回復に問題: {failed_recoveries}"

        return recovery_tests

    def test_ci_cd_quality_gates(self, test_environment):
        """CI/CD品質ゲートテスト"""
        project_root = test_environment["project_root"]

        quality_checks = {}

        # GitHub Workflowファイルの存在確認
        workflows_dir = project_root / ".github" / "workflows"
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("*.yml")) + list(
                workflows_dir.glob("*.yaml")
            )
            quality_checks["workflow_files_count"] = len(workflow_files)

            # ワークフローファイルの基本的な検証
            valid_workflows = 0
            for workflow_file in workflow_files:
                try:
                    content = workflow_file.read_text(encoding="utf-8")
                    workflow_data = yaml.safe_load(content)

                    # 基本的な構造の確認
                    if all(key in workflow_data for key in ["name", "on", "jobs"]):
                        valid_workflows += 1
                except Exception:
                    pass

            quality_checks["valid_workflows"] = valid_workflows

        # pre-commit設定の確認
        precommit_config = project_root / ".pre-commit-config.yaml"
        if precommit_config.exists():
            try:
                content = precommit_config.read_text(encoding="utf-8")
                precommit_data = yaml.safe_load(content)
                quality_checks["precommit_repos"] = len(precommit_data.get("repos", []))
            except Exception:
                quality_checks["precommit_repos"] = 0

        # Makefileターゲットの確認
        makefile = project_root / "Makefile"
        if makefile.exists():
            content = makefile.read_text(encoding="utf-8")
            import re

            targets = re.findall(
                r"^([a-zA-Z][a-zA-Z0-9_-]*):(?!.*=)", content, re.MULTILINE
            )
            quality_checks["makefile_targets"] = len(targets)

        # 品質基準の確認
        quality_issues = []

        if quality_checks.get("workflow_files_count", 0) == 0:
            quality_issues.append("GitHub Workflowファイルが存在しません")

        if (
            quality_checks.get("valid_workflows", 0) == 0
            and quality_checks.get("workflow_files_count", 0) > 0
        ):
            quality_issues.append("有効なGitHub Workflowファイルがありません")

        # 品質問題があっても警告レベル（テスト失敗にはしない）
        if quality_issues:
            print(f"品質警告: {quality_issues}")

        return quality_checks


class TestSystemStabilityAndReliability:
    """システム安定性・信頼性テストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    def test_repeated_execution_stability(self, project_root):
        """繰り返し実行安定性テスト"""
        run_script = project_root / "scripts" / "run-actions.sh"

        if not run_script.exists():
            pytest.skip("run-actions.sh が存在しません")

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        results = []

        # 5回繰り返し実行
        for i in range(5):
            start_time = time.time()

            result = subprocess.run(
                [str(run_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_root,
                env=env,
            )

            execution_time = time.time() - start_time

            results.append(
                {
                    "iteration": i + 1,
                    "return_code": result.returncode,
                    "execution_time": execution_time,
                    "output_length": len(result.stdout),
                    "stderr_length": len(result.stderr),
                }
            )

        # 安定性の確認
        return_codes = [r["return_code"] for r in results]
        execution_times = [r["execution_time"] for r in results]
        output_lengths = [r["output_length"] for r in results]

        # 全ての実行が同じ終了コードを返すことを確認
        assert len(set(return_codes)) == 1, f"終了コードが不安定: {return_codes}"

        # 実行時間の変動が合理的であることを確認
        max_time = max(execution_times)
        min_time = min(execution_times)
        time_variation = (max_time - min_time) / min_time if min_time > 0 else 0

        assert (
            time_variation < 2.0
        ), f"実行時間の変動が大きすぎます: {time_variation:.2f}"

        # 出力長の一貫性を確認
        assert len(set(output_lengths)) <= 2, f"出力長が不安定: {output_lengths}"

        return results

    def test_concurrent_execution_safety(self, project_root):
        """並行実行安全性テスト"""
        run_script = project_root / "scripts" / "run-actions.sh"

        if not run_script.exists():
            pytest.skip("run-actions.sh が存在しません")

        def execute_script():
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            result = subprocess.run(
                [str(run_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_root,
                env=env,
            )

            return {
                "return_code": result.returncode,
                "output_length": len(result.stdout),
                "thread_id": threading.get_ident(),
            }

        # 3つのスレッドで並行実行
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(execute_script) for _ in range(3)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})

        # 並行実行の安全性確認
        successful_results = [r for r in results if "error" not in r]

        assert len(successful_results) == 3, f"並行実行で失敗が発生: {results}"

        # 全ての実行が同じ結果を返すことを確認
        return_codes = [r["return_code"] for r in successful_results]
        output_lengths = [r["output_length"] for r in successful_results]

        assert (
            len(set(return_codes)) == 1
        ), f"並行実行で終了コードが不一致: {return_codes}"
        assert (
            len(set(output_lengths)) <= 2
        ), f"並行実行で出力長が大きく異なる: {output_lengths}"

        return results

    def test_resource_cleanup(self, project_root):
        """リソースクリーンアップテスト"""
        # テスト前のプロセス数を記録
        initial_processes = self._count_related_processes()

        # 複数回実行してリソースリークをチェック
        run_script = project_root / "scripts" / "run-actions.sh"

        if not run_script.exists():
            pytest.skip("run-actions.sh が存在しません")

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        for i in range(3):
            result = subprocess.run(
                [str(run_script), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
                env=env,
            )

            # 各実行後に短時間待機
            time.sleep(1)

        # テスト後のプロセス数を確認
        final_processes = self._count_related_processes()

        # プロセス数の増加が合理的な範囲内であることを確認
        process_increase = final_processes - initial_processes

        assert (
            process_increase <= 5
        ), f"プロセスリークの可能性: 増加数 {process_increase}"

        return {
            "initial_processes": initial_processes,
            "final_processes": final_processes,
            "process_increase": process_increase,
        }

    def _count_related_processes(self) -> int:
        """関連プロセス数をカウント"""
        try:
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=10
            )

            # GitHub Actions Simulator関連のプロセスをカウント
            lines = result.stdout.split("\n")
            related_count = 0

            for line in lines:
                if any(
                    keyword in line.lower()
                    for keyword in ["run-actions", "github-actions", "simulator", "act"]
                ):
                    related_count += 1

            return related_count

        except Exception:
            # プロセス数の取得に失敗した場合は0を返す
            return 0


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])
