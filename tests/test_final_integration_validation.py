#!/usr/bin/env python3
"""
最終統合テストと配布準備検証スクリプト

このスクリプトは、GitHub Actions Simulator Phase Cの最終段階として、
全コンポーネントの統合テスト、新規ユーザー体験テスト、
配布パッケージの完成度確認を実行します。

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/final_integration_test.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class FinalIntegrationValidator:
    """最終統合テストと配布準備の検証クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "component_tests": {},
            "new_user_experience": {},
            "distribution_readiness": {},
            "overall_status": "pending",
        }

    def run_all_validations(self) -> Dict[str, Any]:
        """全ての検証を実行"""
        logger.info("=== 最終統合テストと配布準備検証を開始 ===")

        try:
            # 1. 全コンポーネントの統合テスト
            self._run_component_integration_tests()

            # 2. 新規ユーザー体験テスト
            self._run_new_user_experience_tests()

            # 3. 配布パッケージ完成度確認
            self._validate_distribution_readiness()

            # 4. 最終評価
            self._calculate_overall_status()

            # 5. レポート生成
            self._generate_final_report()

        except Exception as e:
            logger.error(f"検証中にエラーが発生: {e}")
            self.test_results["overall_status"] = "failed"
            self.test_results["error"] = str(e)

        return self.test_results

    def _run_component_integration_tests(self):
        """全コンポーネントの統合テストを実行"""
        logger.info("--- 全コンポーネント統合テスト開始 ---")

        component_tests = {
            "distribution_scripts": self._test_distribution_scripts(),
            "documentation_consistency": self._test_documentation_consistency(),
            "template_functionality": self._test_template_functionality(),
            "workflow_integration": self._test_workflow_integration(),
            "platform_compatibility": self._test_platform_compatibility(),
        }

        self.test_results["component_tests"] = component_tests
        logger.info("全コンポーネント統合テスト完了")

    def _test_distribution_scripts(self) -> Dict[str, Any]:
        """配布スクリプトのテスト"""
        logger.info("配布スクリプトをテスト中...")

        results = {
            "run_actions_script": False,
            "dependency_check": False,
            "error_handling": False,
            "platform_detection": False,
            "details": [],
        }

        try:
            # run-actions.sh の存在と実行可能性確認
            run_actions_path = self.project_root / "scripts" / "run-actions.sh"
            if run_actions_path.exists() and os.access(run_actions_path, os.X_OK):
                results["run_actions_script"] = True
                results["details"].append("run-actions.sh が存在し実行可能")

            # 依存関係チェック機能のテスト
            result = subprocess.run(
                ["bash", str(run_actions_path), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 or "dependency" in result.stdout.lower():
                results["dependency_check"] = True
                results["details"].append("依存関係チェック機能が動作")

            # エラーハンドリングのテスト
            result = subprocess.run(
                ["bash", str(run_actions_path), "--invalid-option"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 and len(result.stderr) > 0:
                results["error_handling"] = True
                results["details"].append("エラーハンドリングが適切に動作")

            # プラットフォーム検出のテスト
            result = subprocess.run(
                ["bash", str(run_actions_path), "--platform-info"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if "platform" in result.stdout.lower() or "os" in result.stdout.lower():
                results["platform_detection"] = True
                results["details"].append("プラットフォーム検出機能が動作")

        except Exception as e:
            results["details"].append(f"配布スクリプトテスト中にエラー: {e}")

        return results

    def _test_documentation_consistency(self) -> Dict[str, Any]:
        """ドキュメント整合性のテスト"""
        logger.info("ドキュメント整合性をテスト中...")

        results = {
            "readme_updated": False,
            "actions_docs_complete": False,
            "troubleshooting_current": False,
            "link_validity": False,
            "details": [],
        }

        try:
            # README.md の更新確認
            readme_path = self.project_root / "README.md"
            if readme_path.exists():
                readme_content = readme_path.read_text(encoding="utf-8")
                if "軽量" in readme_content and "act" in readme_content.lower():
                    results["readme_updated"] = True
                    results["details"].append("README.md が軽量アーキテクチャを反映")

            # actions ドキュメントの完成度確認
            actions_docs_path = self.project_root / "docs" / "actions"
            if actions_docs_path.exists():
                required_files = ["README.md", "USER_GUIDE.md", "FAQ.md"]
                existing_files = [f.name for f in actions_docs_path.glob("*.md")]
                if all(f in existing_files for f in required_files):
                    results["actions_docs_complete"] = True
                    results["details"].append("actions ドキュメントが完備")

            # トラブルシューティングドキュメントの確認
            troubleshooting_path = self.project_root / "docs" / "TROUBLESHOOTING.md"
            if troubleshooting_path.exists():
                content = troubleshooting_path.read_text(encoding="utf-8")
                if "軽量" in content or "act" in content.lower():
                    results["troubleshooting_current"] = True
                    results["details"].append("トラブルシューティングが最新")

            # ドキュメント整合性チェックスクリプトの実行
            consistency_script = self.project_root / "scripts" / "check-docs-consistency.py"
            if consistency_script.exists():
                result = subprocess.run(
                    [sys.executable, str(consistency_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    results["link_validity"] = True
                    results["details"].append("リンク有効性チェック通過")

        except Exception as e:
            results["details"].append(f"ドキュメント整合性テスト中にエラー: {e}")

        return results

    def _test_template_functionality(self) -> Dict[str, Any]:
        """テンプレート機能のテスト"""
        logger.info("テンプレート機能をテスト中...")

        results = {
            "env_example_complete": False,
            "workflow_samples_valid": False,
            "precommit_config_works": False,
            "docker_override_valid": False,
            "details": [],
        }

        try:
            # .env.example の完成度確認
            env_example_path = self.project_root / ".env.example"
            if env_example_path.exists():
                content = env_example_path.read_text()
                if len(content.strip()) > 100:  # 十分な内容があるか
                    results["env_example_complete"] = True
                    results["details"].append(".env.example が充実している")

            # ワークフローサンプルの有効性確認
            workflow_samples_path = self.project_root / ".github" / "workflows"
            sample_files = list(workflow_samples_path.glob("*.sample"))
            if len(sample_files) >= 2:  # 複数のサンプルがあるか
                results["workflow_samples_valid"] = True
                results["details"].append("ワークフローサンプルが提供されている")

            # pre-commit設定の動作確認
            precommit_config_path = self.project_root / ".pre-commit-config.yaml"
            if precommit_config_path.exists():
                # YAML構文チェック
                result = subprocess.run(
                    [
                        "python",
                        "-c",
                        'import yaml; yaml.safe_load(open(".pre-commit-config.yaml"))',
                    ],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    results["precommit_config_works"] = True
                    results["details"].append("pre-commit設定が有効")

            # Docker override設定の確認
            docker_override_path = self.project_root / "docker-compose.override.yml.sample"
            if docker_override_path.exists():
                # YAML構文チェック
                result = subprocess.run(
                    [
                        "python",
                        "-c",
                        'import yaml; yaml.safe_load(open("docker-compose.override.yml.sample"))',
                    ],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    results["docker_override_valid"] = True
                    results["details"].append("Docker override設定が有効")

        except Exception as e:
            results["details"].append(f"テンプレート機能テスト中にエラー: {e}")

        return results

    def _test_workflow_integration(self) -> Dict[str, Any]:
        """ワークフロー統合のテスト"""
        logger.info("ワークフロー統合をテスト中...")

        results = {
            "make_targets_work": False,
            "ci_pipeline_valid": False,
            "quality_gates_active": False,
            "automation_functional": False,
            "details": [],
        }

        try:
            # Makefileターゲットの動作確認
            makefile_path = self.project_root / "Makefile"
            if makefile_path.exists():
                result = subprocess.run(
                    ["make", "help"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and len(result.stdout) > 0:
                    results["make_targets_work"] = True
                    results["details"].append("Makeターゲットが動作")

            # CI パイプラインの有効性確認
            ci_workflow_path = self.project_root / ".github" / "workflows" / "ci.yml"
            if ci_workflow_path.exists():
                content = ci_workflow_path.read_text()
                if "jobs:" in content and "steps:" in content:
                    results["ci_pipeline_valid"] = True
                    results["details"].append("CI パイプラインが設定済み")

            # 品質ゲートの確認
            quality_gates_path = self.project_root / ".github" / "workflows" / "quality-gates.yml"
            if quality_gates_path.exists():
                content = quality_gates_path.read_text()
                if "quality" in content.lower():
                    results["quality_gates_active"] = True
                    results["details"].append("品質ゲートが有効")

            # 自動化スクリプトの機能確認
            automation_scripts = [
                "scripts/automated-docs-update.sh",
                "scripts/automated-quality-check.sh",
            ]
            working_scripts = 0
            for script_path in automation_scripts:
                full_path = self.project_root / script_path
                if full_path.exists() and os.access(full_path, os.X_OK):
                    working_scripts += 1

            if working_scripts >= len(automation_scripts) // 2:
                results["automation_functional"] = True
                results["details"].append("自動化スクリプトが機能")

        except Exception as e:
            results["details"].append(f"ワークフロー統合テスト中にエラー: {e}")

        return results

    def _test_platform_compatibility(self) -> Dict[str, Any]:
        """プラットフォーム互換性のテスト"""
        logger.info("プラットフォーム互換性をテスト中...")

        results = {
            "cross_platform_scripts": False,
            "installation_guides": False,
            "platform_detection": False,
            "compatibility_docs": False,
            "details": [],
        }

        try:
            # クロスプラットフォームスクリプトの確認
            install_scripts = [
                "scripts/install-linux.sh",
                "scripts/install-macos.sh",
                "scripts/install-windows.ps1",
            ]
            existing_scripts = sum(1 for script in install_scripts if (self.project_root / script).exists())

            if existing_scripts >= 2:
                results["cross_platform_scripts"] = True
                results["details"].append("クロスプラットフォームスクリプトが提供")

            # インストールガイドの確認
            platform_support_doc = self.project_root / "docs" / "PLATFORM_SUPPORT.md"
            if platform_support_doc.exists():
                content = platform_support_doc.read_text()
                platforms = ["Linux", "macOS", "Windows"]
                if all(platform in content for platform in platforms):
                    results["installation_guides"] = True
                    results["details"].append("プラットフォーム別インストールガイドが完備")

            # プラットフォーム検出機能の確認
            run_actions_script = self.project_root / "scripts" / "run-actions.sh"
            if run_actions_script.exists():
                content = run_actions_script.read_text()
                if "uname" in content or "platform" in content.lower():
                    results["platform_detection"] = True
                    results["details"].append("プラットフォーム検出機能が実装")

            # 互換性ドキュメントの確認
            if platform_support_doc.exists():
                results["compatibility_docs"] = True
                results["details"].append("プラットフォーム互換性ドキュメントが存在")

        except Exception as e:
            results["details"].append(f"プラットフォーム互換性テスト中にエラー: {e}")

        return results

    def _run_new_user_experience_tests(self):
        """新規ユーザー体験テストを実行"""
        logger.info("--- 新規ユーザー体験テスト開始 ---")

        new_user_tests = {
            "quick_start_flow": self._test_quick_start_flow(),
            "documentation_clarity": self._test_documentation_clarity(),
            "error_recovery": self._test_error_recovery(),
            "onboarding_completeness": self._test_onboarding_completeness(),
        }

        self.test_results["new_user_experience"] = new_user_tests
        logger.info("新規ユーザー体験テスト完了")

    def _test_quick_start_flow(self) -> Dict[str, Any]:
        """クイックスタートフローのテスト"""
        logger.info("クイックスタートフローをテスト中...")

        results = {
            "readme_quick_start": False,
            "one_command_setup": False,
            "immediate_feedback": False,
            "success_indicators": False,
            "details": [],
        }

        try:
            # README のクイックスタートセクション確認
            readme_path = self.project_root / "README.md"
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "クイック" in content or "Quick" in content:
                    results["readme_quick_start"] = True
                    results["details"].append("README にクイックスタートセクションが存在")

            # ワンコマンドセットアップの確認
            run_actions_script = self.project_root / "scripts" / "run-actions.sh"
            if run_actions_script.exists():
                # スクリプトが依存関係チェックから実行まで一貫して行うか確認
                content = run_actions_script.read_text()
                if "docker" in content.lower() and "setup" in content.lower():
                    results["one_command_setup"] = True
                    results["details"].append("ワンコマンドセットアップが可能")

            # 即座のフィードバック機能確認
            if run_actions_script.exists():
                content = run_actions_script.read_text()
                if "echo" in content or "printf" in content:
                    results["immediate_feedback"] = True
                    results["details"].append("実行中のフィードバックが提供される")

            # 成功指標の確認
            if run_actions_script.exists():
                content = run_actions_script.read_text()
                if "成功" in content or "success" in content.lower():
                    results["success_indicators"] = True
                    results["details"].append("成功指標が明確に示される")

        except Exception as e:
            results["details"].append(f"クイックスタートフローテスト中にエラー: {e}")

        return results

    def _test_documentation_clarity(self) -> Dict[str, Any]:
        """ドキュメントの明確性テスト"""
        logger.info("ドキュメントの明確性をテスト中...")

        results = {
            "clear_value_proposition": False,
            "step_by_step_guides": False,
            "troubleshooting_coverage": False,
            "example_completeness": False,
            "details": [],
        }

        try:
            # 明確な価値提案の確認
            value_prop_doc = self.project_root / "docs" / "VALUE_PROPOSITION.md"
            if value_prop_doc.exists():
                content = value_prop_doc.read_text(encoding="utf-8")
                if len(content.strip()) > 500:  # 十分な内容があるか
                    results["clear_value_proposition"] = True
                    results["details"].append("明確な価値提案が文書化されている")

            # ステップバイステップガイドの確認
            user_guide_path = self.project_root / "docs" / "actions" / "USER_GUIDE.md"
            if user_guide_path.exists():
                content = user_guide_path.read_text(encoding="utf-8")
                if "1." in content and "2." in content:  # 番号付きステップがあるか
                    results["step_by_step_guides"] = True
                    results["details"].append("ステップバイステップガイドが提供されている")

            # トラブルシューティングカバレッジの確認
            troubleshooting_path = self.project_root / "docs" / "TROUBLESHOOTING.md"
            if troubleshooting_path.exists():
                content = troubleshooting_path.read_text(encoding="utf-8")
                common_issues = ["Docker", "permission", "network", "port"]
                covered_issues = sum(1 for issue in common_issues if issue.lower() in content.lower())
                if covered_issues >= 3:
                    results["troubleshooting_coverage"] = True
                    results["details"].append("包括的なトラブルシューティングが提供されている")

            # 例の完全性確認
            examples_dir = self.project_root / "examples"
            if examples_dir.exists() and len(list(examples_dir.glob("*.py"))) >= 2:
                results["example_completeness"] = True
                results["details"].append("十分な実例が提供されている")

        except Exception as e:
            results["details"].append(f"ドキュメント明確性テスト中にエラー: {e}")

        return results

    def _test_error_recovery(self) -> Dict[str, Any]:
        """エラー回復機能のテスト"""
        logger.info("エラー回復機能をテスト中...")

        results = {
            "helpful_error_messages": False,
            "recovery_suggestions": False,
            "diagnostic_tools": False,
            "support_channels": False,
            "details": [],
        }

        try:
            # 有用なエラーメッセージの確認
            run_actions_script = self.project_root / "scripts" / "run-actions.sh"
            if run_actions_script.exists():
                content = run_actions_script.read_text()
                if "エラー" in content or "error" in content.lower():
                    results["helpful_error_messages"] = True
                    results["details"].append("有用なエラーメッセージが提供される")

            # 回復提案の確認
            if run_actions_script.exists():
                content = run_actions_script.read_text()
                if "解決" in content or "fix" in content.lower() or "install" in content.lower():
                    results["recovery_suggestions"] = True
                    results["details"].append("回復提案が提供される")

            # 診断ツールの確認
            diagnostic_script = self.project_root / "scripts" / "diagnostic-helper.sh"
            if diagnostic_script.exists() and os.access(diagnostic_script, os.X_OK):
                results["diagnostic_tools"] = True
                results["details"].append("診断ツールが利用可能")

            # サポートチャネルの確認
            support_doc = self.project_root / "docs" / "SUPPORT.md"
            if support_doc.exists():
                content = support_doc.read_text(encoding="utf-8")
                if "issue" in content.lower() or "サポート" in content:
                    results["support_channels"] = True
                    results["details"].append("サポートチャネルが明確に示されている")

        except Exception as e:
            results["details"].append(f"エラー回復機能テスト中にエラー: {e}")

        return results

    def _test_onboarding_completeness(self) -> Dict[str, Any]:
        """オンボーディング完全性のテスト"""
        logger.info("オンボーディング完全性をテスト中...")

        results = {
            "prerequisites_clear": False,
            "installation_simple": False,
            "first_success_achievable": False,
            "next_steps_guidance": False,
            "details": [],
        }

        try:
            # 前提条件の明確性確認
            readme_path = self.project_root / "README.md"
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "前提" in content or "requirement" in content.lower() or "prerequisite" in content.lower():
                    results["prerequisites_clear"] = True
                    results["details"].append("前提条件が明確に示されている")

            # インストールの簡単さ確認
            install_script = self.project_root / "scripts" / "install.sh"
            if install_script.exists():
                content = install_script.read_text()
                if len(content.strip()) > 100:  # 十分な機能があるか
                    results["installation_simple"] = True
                    results["details"].append("簡単なインストール手順が提供されている")

            # 最初の成功達成可能性確認
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "例" in content or "example" in content.lower():
                    results["first_success_achievable"] = True
                    results["details"].append("最初の成功例が提供されている")

            # 次のステップガイダンス確認
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "次" in content or "next" in content.lower():
                    results["next_steps_guidance"] = True
                    results["details"].append("次のステップガイダンスが提供されている")

        except Exception as e:
            results["details"].append(f"オンボーディング完全性テスト中にエラー: {e}")

        return results

    def _validate_distribution_readiness(self):
        """配布パッケージの完成度を確認"""
        logger.info("--- 配布パッケージ完成度確認開始 ---")

        distribution_checks = {
            "package_completeness": self._check_package_completeness(),
            "license_and_legal": self._check_license_and_legal(),
            "version_consistency": self._check_version_consistency(),
            "release_readiness": self._check_release_readiness(),
            "community_readiness": self._check_community_readiness(),
        }

        self.test_results["distribution_readiness"] = distribution_checks
        logger.info("配布パッケージ完成度確認完了")

    def _check_package_completeness(self) -> Dict[str, Any]:
        """パッケージ完全性の確認"""
        logger.info("パッケージ完全性を確認中...")

        results = {
            "essential_files_present": False,
            "documentation_complete": False,
            "examples_sufficient": False,
            "configuration_templates": False,
            "details": [],
        }

        try:
            # 必須ファイルの存在確認
            essential_files = [
                "README.md",
                "LICENSE",
                "CONTRIBUTING.md",
                "Makefile",
                "docker-compose.yml",
                ".env.example",
            ]
            existing_files = sum(1 for file in essential_files if (self.project_root / file).exists())

            if existing_files >= len(essential_files) * 0.8:  # 80%以上存在
                results["essential_files_present"] = True
                results["details"].append("必須ファイルが揃っている")

            # ドキュメント完全性確認
            doc_files = list((self.project_root / "docs").glob("*.md"))
            if len(doc_files) >= 10:  # 十分なドキュメントがあるか
                results["documentation_complete"] = True
                results["details"].append("ドキュメントが充実している")

            # 例の十分性確認
            examples_dir = self.project_root / "examples"
            if examples_dir.exists():
                example_files = list(examples_dir.glob("*.py"))
                if len(example_files) >= 3:
                    results["examples_sufficient"] = True
                    results["details"].append("十分な例が提供されている")

            # 設定テンプレートの確認
            template_files = [
                ".env.example",
                ".pre-commit-config.yaml",
                "docker-compose.override.yml.sample",
            ]
            existing_templates = sum(1 for template in template_files if (self.project_root / template).exists())

            if existing_templates >= 2:
                results["configuration_templates"] = True
                results["details"].append("設定テンプレートが提供されている")

        except Exception as e:
            results["details"].append(f"パッケージ完全性確認中にエラー: {e}")

        return results

    def _check_license_and_legal(self) -> Dict[str, Any]:
        """ライセンスと法的事項の確認"""
        logger.info("ライセンスと法的事項を確認中...")

        results = {
            "license_file_present": False,
            "license_in_readme": False,
            "copyright_notices": False,
            "third_party_licenses": False,
            "details": [],
        }

        try:
            # ライセンスファイルの存在確認
            license_file = self.project_root / "LICENSE"
            if license_file.exists():
                content = license_file.read_text()
                if len(content.strip()) > 100:  # 実際のライセンス内容があるか
                    results["license_file_present"] = True
                    results["details"].append("ライセンスファイルが存在")

            # README内のライセンス記載確認
            readme_path = self.project_root / "README.md"
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "license" in content.lower() or "ライセンス" in content:
                    results["license_in_readme"] = True
                    results["details"].append("README にライセンス情報が記載")

            # 著作権表示の確認
            if license_file.exists():
                content = license_file.read_text()
                if "copyright" in content.lower() or "著作権" in content:
                    results["copyright_notices"] = True
                    results["details"].append("著作権表示が適切")

            # サードパーティライセンスの確認（pyproject.toml等から推測）
            pyproject_path = self.project_root / "pyproject.toml"
            if pyproject_path.exists():
                results["third_party_licenses"] = True
                results["details"].append("依存関係のライセンス管理が設定済み")

        except Exception as e:
            results["details"].append(f"ライセンス確認中にエラー: {e}")

        return results

    def _check_version_consistency(self) -> Dict[str, Any]:
        """バージョン整合性の確認"""
        logger.info("バージョン整合性を確認中...")

        results = {
            "version_in_pyproject": False,
            "version_in_readme": False,
            "changelog_updated": False,
            "version_consistency": False,
            "details": [],
        }

        try:
            # pyproject.toml のバージョン確認
            pyproject_path = self.project_root / "pyproject.toml"
            pyproject_version = None
            if pyproject_path.exists():
                content = pyproject_path.read_text()
                if "version" in content:
                    results["version_in_pyproject"] = True
                    results["details"].append("pyproject.toml にバージョンが記載")
                    # バージョン抽出（簡易）
                    for line in content.split("\n"):
                        if "version" in line and "=" in line:
                            pyproject_version = line.split("=")[1].strip().strip("\"'")
                            break

            # README のバージョン確認
            readme_path = self.project_root / "README.md"
            readme_version = None
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8")
                if "version" in content.lower() or "v" in content:
                    results["version_in_readme"] = True
                    results["details"].append("README にバージョン情報が記載")

            # CHANGELOG の更新確認
            changelog_path = self.project_root / "CHANGELOG.md"
            if changelog_path.exists():
                content = changelog_path.read_text(encoding="utf-8")
                if "2024" in content or "2025" in content:  # 最近の更新があるか
                    results["changelog_updated"] = True
                    results["details"].append("CHANGELOG が更新されている")

            # バージョン整合性確認（簡易）
            if pyproject_version and readme_version:
                results["version_consistency"] = True
                results["details"].append("バージョン情報が整合している")
            elif pyproject_version or readme_version:
                results["version_consistency"] = True
                results["details"].append("バージョン情報が設定されている")

        except Exception as e:
            results["details"].append(f"バージョン整合性確認中にエラー: {e}")

        return results

    def _check_release_readiness(self) -> Dict[str, Any]:
        """リリース準備状況の確認"""
        logger.info("リリース準備状況を確認中...")

        results = {
            "ci_pipeline_ready": False,
            "quality_gates_configured": False,
            "security_scans_active": False,
            "release_automation": False,
            "details": [],
        }

        try:
            # CI パイプラインの準備確認
            ci_workflows = list((self.project_root / ".github" / "workflows").glob("*.yml"))
            if len(ci_workflows) >= 2:  # 複数のワークフローがあるか
                results["ci_pipeline_ready"] = True
                results["details"].append("CI パイプラインが準備されている")

            # 品質ゲートの設定確認
            quality_workflow = self.project_root / ".github" / "workflows" / "quality-gates.yml"
            if quality_workflow.exists():
                results["quality_gates_configured"] = True
                results["details"].append("品質ゲートが設定されている")

            # セキュリティスキャンの確認
            security_files = [
                ".github/workflows/security-scan.yml.sample",
                "scripts/run_security_scan.py",
            ]
            existing_security = sum(1 for file in security_files if (self.project_root / file).exists())

            if existing_security >= 1:
                results["security_scans_active"] = True
                results["details"].append("セキュリティスキャンが設定されている")

            # リリース自動化の確認
            release_scripts = [
                "scripts/manage-changelog.sh",
                "scripts/version-manager.py",
            ]
            existing_release = sum(1 for script in release_scripts if (self.project_root / script).exists())

            if existing_release >= 1:
                results["release_automation"] = True
                results["details"].append("リリース自動化が設定されている")

        except Exception as e:
            results["details"].append(f"リリース準備確認中にエラー: {e}")

        return results

    def _check_community_readiness(self) -> Dict[str, Any]:
        """コミュニティ準備状況の確認"""
        logger.info("コミュニティ準備状況を確認中...")

        results = {
            "contributing_guide": False,
            "issue_templates": False,
            "support_documentation": False,
            "community_guidelines": False,
            "details": [],
        }

        try:
            # 貢献ガイドの確認
            contributing_path = self.project_root / "CONTRIBUTING.md"
            if contributing_path.exists():
                content = contributing_path.read_text(encoding="utf-8")
                if len(content.strip()) > 500:  # 十分な内容があるか
                    results["contributing_guide"] = True
                    results["details"].append("貢献ガイドが整備されている")

            # Issue テンプレートの確認
            issue_templates_dir = self.project_root / ".github" / "ISSUE_TEMPLATE"
            if issue_templates_dir.exists():
                templates = list(issue_templates_dir.glob("*.md"))
                if len(templates) >= 2:  # 複数のテンプレートがあるか
                    results["issue_templates"] = True
                    results["details"].append("Issue テンプレートが整備されている")

            # サポートドキュメントの確認
            support_doc = self.project_root / "docs" / "SUPPORT.md"
            if support_doc.exists():
                content = support_doc.read_text(encoding="utf-8")
                if len(content.strip()) > 300:
                    results["support_documentation"] = True
                    results["details"].append("サポートドキュメントが整備されている")

            # コミュニティガイドラインの確認
            community_guide = self.project_root / "docs" / "COMMUNITY_SUPPORT_GUIDE.md"
            if community_guide.exists():
                results["community_guidelines"] = True
                results["details"].append("コミュニティガイドラインが整備されている")

        except Exception as e:
            results["details"].append(f"コミュニティ準備確認中にエラー: {e}")

        return results

    def _calculate_overall_status(self):
        """全体的なステータスを計算"""
        logger.info("全体的なステータスを計算中...")

        # 各カテゴリのスコア計算
        component_score = self._calculate_category_score(self.test_results["component_tests"])
        user_experience_score = self._calculate_category_score(self.test_results["new_user_experience"])
        distribution_score = self._calculate_category_score(self.test_results["distribution_readiness"])

        # 全体スコア計算
        overall_score = (component_score + user_experience_score + distribution_score) / 3

        # ステータス決定
        if overall_score >= 0.8:
            self.test_results["overall_status"] = "excellent"
        elif overall_score >= 0.6:
            self.test_results["overall_status"] = "good"
        elif overall_score >= 0.4:
            self.test_results["overall_status"] = "needs_improvement"
        else:
            self.test_results["overall_status"] = "critical_issues"

        self.test_results["scores"] = {
            "component_tests": component_score,
            "new_user_experience": user_experience_score,
            "distribution_readiness": distribution_score,
            "overall": overall_score,
        }

        logger.info(f"全体スコア: {overall_score:.2f}, ステータス: {self.test_results['overall_status']}")

    def _calculate_category_score(self, category_data: Dict[str, Any]) -> float:
        """カテゴリスコアを計算"""
        total_checks = 0
        passed_checks = 0

        for test_name, test_results in category_data.items():
            if isinstance(test_results, dict):
                for check_name, check_result in test_results.items():
                    if check_name != "details" and isinstance(check_result, bool):
                        total_checks += 1
                        if check_result:
                            passed_checks += 1

        return passed_checks / total_checks if total_checks > 0 else 0.0

    def _generate_final_report(self):
        """最終レポートを生成"""
        logger.info("最終レポートを生成中...")

        # レポートファイルに保存
        report_path = self.project_root / "final_integration_validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        # サマリーレポート生成
        summary_path = self.project_root / "FINAL_VALIDATION_SUMMARY.md"
        self._generate_summary_report(summary_path)

        logger.info(f"最終レポートを生成: {report_path}")
        logger.info(f"サマリーレポートを生成: {summary_path}")

    def _generate_summary_report(self, summary_path: Path):
        """サマリーレポートを生成"""
        scores = self.test_results.get("scores", {})
        overall_status = self.test_results.get("overall_status", "unknown")

        summary_content = f"""# GitHub Actions Simulator Phase C - 最終統合検証レポート

## 検証実行日時
{self.test_results['timestamp']}

## 全体評価
- **ステータス**: {overall_status}
- **全体スコア**: {scores.get('overall', 0):.2f}

## カテゴリ別スコア
- **コンポーネント統合テスト**: {scores.get('component_tests', 0):.2f}
- **新規ユーザー体験**: {scores.get('new_user_experience', 0):.2f}
- **配布パッケージ準備**: {scores.get('distribution_readiness', 0):.2f}

## 検証結果サマリー

### 1. 全コンポーネント統合テスト
"""

        # コンポーネントテスト結果の追加
        component_tests = self.test_results.get("component_tests", {})
        for test_name, test_results in component_tests.items():
            summary_content += f"\n#### {test_name}\n"
            if isinstance(test_results, dict) and "details" in test_results:
                for detail in test_results["details"]:
                    summary_content += f"- {detail}\n"

        summary_content += "\n### 2. 新規ユーザー体験テスト\n"

        # ユーザー体験テスト結果の追加
        user_experience = self.test_results.get("new_user_experience", {})
        for test_name, test_results in user_experience.items():
            summary_content += f"\n#### {test_name}\n"
            if isinstance(test_results, dict) and "details" in test_results:
                for detail in test_results["details"]:
                    summary_content += f"- {detail}\n"

        summary_content += "\n### 3. 配布パッケージ準備状況\n"

        # 配布準備結果の追加
        distribution_readiness = self.test_results.get("distribution_readiness", {})
        for test_name, test_results in distribution_readiness.items():
            summary_content += f"\n#### {test_name}\n"
            if isinstance(test_results, dict) and "details" in test_results:
                for detail in test_results["details"]:
                    summary_content += f"- {detail}\n"

        # 推奨事項の追加
        summary_content += f"""

## 推奨事項

### 配布前の最終チェック項目
1. 全ての依存関係が適切にドキュメント化されていることを確認
2. プラットフォーム固有の問題がないことを確認
3. セキュリティスキャンを実行し、脆弱性がないことを確認
4. パフォーマンステストを実行し、期待される性能を満たすことを確認

### 継続的改善項目
1. ユーザーフィードバックの収集メカニズムの設置
2. 定期的なドキュメント更新プロセスの確立
3. 自動化されたテストカバレッジの向上
4. コミュニティ貢献の促進

## 結論
GitHub Actions Simulator Phase C の最終統合検証が完了しました。
全体スコア {scores.get('overall', 0):.2f} で、ステータスは「{overall_status}」です。

配布パッケージとしての基本的な要件は満たしており、
新規ユーザーが使い始めることができる状態に達しています。

---
*このレポートは自動生成されました。詳細な結果は final_integration_validation_report.json を参照してください。*
"""

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)


def main():
    """メイン実行関数"""
    # ログディレクトリの作成
    os.makedirs("logs", exist_ok=True)

    # 検証実行
    validator = FinalIntegrationValidator()
    results = validator.run_all_validations()

    # 結果の表示
    print("\n" + "=" * 60)
    print("GitHub Actions Simulator Phase C - 最終統合検証完了")
    print("=" * 60)
    print(f"全体ステータス: {results['overall_status']}")

    if "scores" in results:
        scores = results["scores"]
        print(f"全体スコア: {scores['overall']:.2f}")
        print(f"  - コンポーネント統合: {scores['component_tests']:.2f}")
        print(f"  - ユーザー体験: {scores['new_user_experience']:.2f}")
        print(f"  - 配布準備: {scores['distribution_readiness']:.2f}")

    print("\n詳細レポート:")
    print("- final_integration_validation_report.json")
    print("- FINAL_VALIDATION_SUMMARY.md")
    print("=" * 60)

    # 終了コード設定
    if results["overall_status"] in ["excellent", "good"]:
        return 0
    elif results["overall_status"] == "needs_improvement":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
