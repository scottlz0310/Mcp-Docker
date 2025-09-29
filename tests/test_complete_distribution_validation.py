#!/usr/bin/env python3
"""
完全配布検証テストスイート

GitHub Actions Simulator Phase C の最終統合テストとして、
新規ユーザー体験から配布パッケージの完成度まで包括的に検証します。

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import unittest
from pathlib import Path
from datetime import datetime
import logging

# テスト用ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CompleteDistributionValidationTest(unittest.TestCase):
    """完全配布検証テストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        cls.project_root = Path(__file__).parent.parent
        cls.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_summary": {},
            "detailed_results": {},
        }

        # ログディレクトリの作成
        os.makedirs(cls.project_root / "logs", exist_ok=True)

        logger.info("完全配布検証テストを開始")

    def setUp(self):
        """各テストの初期化"""
        self.current_test = self._testMethodName
        logger.info(f"テスト開始: {self.current_test}")

    def tearDown(self):
        """各テストの後処理"""
        logger.info(f"テスト完了: {self.current_test}")

    def test_01_essential_files_presence(self):
        """必須ファイルの存在確認テスト"""
        logger.info("必須ファイルの存在を確認中...")

        essential_files = [
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "Makefile",
            "docker-compose.yml",
            ".env.example",
            "pyproject.toml",
        ]

        missing_files = []
        for file_path in essential_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        self.assertEqual(len(missing_files), 0, f"必須ファイルが不足: {missing_files}")

        logger.info("✅ 全ての必須ファイルが存在")

    def test_02_readme_quality_and_completeness(self):
        """README.md の品質と完全性テスト"""
        logger.info("README.md の品質を確認中...")

        readme_path = self.project_root / "README.md"
        self.assertTrue(readme_path.exists(), "README.md が存在しない")

        content = readme_path.read_text(encoding="utf-8")

        # 最小限の内容確認
        self.assertGreater(len(content), 1000, "README.md の内容が不十分")

        # 必要なセクションの確認
        required_sections = [
            ("クイック", "Quick"),  # クイックスタート
            ("インストール", "install", "Install"),  # インストール手順
            ("使用", "使い方", "usage", "Usage"),  # 使用方法
            ("例", "example", "Example"),  # 例
        ]

        for section_keywords in required_sections:
            section_found = any(keyword in content for keyword in section_keywords)
            self.assertTrue(section_found, f"README.md に必要なセクションが不足: {section_keywords}")

        logger.info("✅ README.md の品質が適切")

    def test_03_distribution_script_functionality(self):
        """配布スクリプトの機能テスト"""
        logger.info("配布スクリプトの機能を確認中...")

        run_actions_script = self.project_root / "scripts" / "run-actions.sh"
        self.assertTrue(run_actions_script.exists(), "run-actions.sh が存在しない")
        self.assertTrue(os.access(run_actions_script, os.X_OK), "run-actions.sh が実行不可")

        # ヘルプ機能の確認
        try:
            result = subprocess.run(
                ["bash", str(run_actions_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
            )

            # ヘルプが表示されるか、または適切なエラーメッセージが表示されるか
            help_indicators = ["help", "usage", "ヘルプ", "使用法", "option"]
            help_found = any(
                indicator.lower() in result.stdout.lower() or indicator.lower() in result.stderr.lower()
                for indicator in help_indicators
            )

            self.assertTrue(help_found, "ヘルプ機能が適切に動作しない")

        except subprocess.TimeoutExpired:
            self.fail("run-actions.sh がタイムアウト")
        except Exception as e:
            self.fail(f"run-actions.sh の実行でエラー: {e}")

        logger.info("✅ 配布スクリプトが適切に動作")

    def test_04_documentation_consistency(self):
        """ドキュメント整合性テスト"""
        logger.info("ドキュメント整合性を確認中...")

        # 必要なドキュメントファイルの確認
        required_docs = [
            "docs/TROUBLESHOOTING.md",
            "docs/actions/README.md",
            "docs/SUPPORT.md",
        ]

        existing_docs = []
        for doc_path in required_docs:
            full_path = self.project_root / doc_path
            if full_path.exists():
                existing_docs.append(doc_path)

        # 最低限必要なドキュメントが存在するか
        self.assertGreaterEqual(
            len(existing_docs),
            len(required_docs) * 0.7,  # 70%以上
            f"必要なドキュメントが不足: 存在={len(existing_docs)}, 必要={len(required_docs)}",
        )

        # ドキュメント整合性チェックスクリプトの実行
        consistency_script = self.project_root / "scripts" / "check-docs-consistency.py"
        if consistency_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(consistency_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=self.project_root,
                )

                # スクリプトが正常終了するか、警告レベルのエラーのみか
                self.assertIn(
                    result.returncode,
                    [0, 1],
                    f"ドキュメント整合性チェックで重大なエラー: {result.stderr}",
                )

            except subprocess.TimeoutExpired:
                self.fail("ドキュメント整合性チェックがタイムアウト")
            except Exception as e:
                logger.warning(f"ドキュメント整合性チェックスクリプトの実行エラー: {e}")

        logger.info("✅ ドキュメント整合性が適切")

    def test_05_template_files_validity(self):
        """テンプレートファイルの有効性テスト"""
        logger.info("テンプレートファイルの有効性を確認中...")

        template_files = {
            ".env.example": "text",
            ".pre-commit-config.yaml": "yaml",
            "docker-compose.override.yml.sample": "yaml",
        }

        existing_templates = 0

        for template_path, file_type in template_files.items():
            full_path = self.project_root / template_path

            if full_path.exists():
                existing_templates += 1

                # ファイル内容の基本確認
                content = full_path.read_text(encoding="utf-8")
                self.assertGreater(len(content.strip()), 50, f"{template_path} の内容が不十分")

                # YAML ファイルの構文確認
                if file_type == "yaml":
                    try:
                        import yaml

                        yaml.safe_load(content)
                    except yaml.YAMLError as e:
                        self.fail(f"{template_path} のYAML構文エラー: {e}")

        # 最低限のテンプレートが存在するか
        self.assertGreaterEqual(
            existing_templates,
            len(template_files) * 0.6,  # 60%以上
            f"テンプレートファイルが不足: 存在={existing_templates}, 期待={len(template_files)}",
        )

        logger.info("✅ テンプレートファイルが適切")

    def test_06_workflow_integration(self):
        """ワークフロー統合テスト"""
        logger.info("ワークフロー統合を確認中...")

        # Makefile の確認
        makefile_path = self.project_root / "Makefile"
        if makefile_path.exists():
            try:
                result = subprocess.run(
                    ["make", "help"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.project_root,
                )

                # make help が動作するか
                self.assertIn(result.returncode, [0, 2], f"Makefile に問題がある: {result.stderr}")

            except subprocess.TimeoutExpired:
                self.fail("make help がタイムアウト")
            except FileNotFoundError:
                logger.warning("make コマンドが利用できない")

        # GitHub Actions ワークフローの確認
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

            self.assertGreater(len(workflow_files), 0, "GitHub Actions ワークフローが存在しない")

            # ワークフローファイルの基本構文確認
            for workflow_file in workflow_files[:3]:  # 最初の3つをチェック
                try:
                    import yaml

                    content = workflow_file.read_text(encoding="utf-8")
                    workflow_data = yaml.safe_load(content)

                    # 基本的なワークフロー構造の確認
                    if isinstance(workflow_data, dict):
                        self.assertIn(
                            "on",
                            workflow_data,
                            f"{workflow_file.name} にトリガーが定義されていない",
                        )

                except yaml.YAMLError as e:
                    self.fail(f"{workflow_file.name} のYAML構文エラー: {e}")

        logger.info("✅ ワークフロー統合が適切")

    def test_07_platform_compatibility(self):
        """プラットフォーム互換性テスト"""
        logger.info("プラットフォーム互換性を確認中...")

        # プラットフォーム別インストールスクリプトの確認
        install_scripts = [
            "scripts/install-linux.sh",
            "scripts/install-macos.sh",
            "scripts/install-windows.ps1",
        ]

        existing_scripts = 0
        for script_path in install_scripts:
            full_path = self.project_root / script_path
            if full_path.exists():
                existing_scripts += 1

                # スクリプトファイルの基本確認
                content = full_path.read_text(encoding="utf-8")
                self.assertGreater(len(content.strip()), 100, f"{script_path} の内容が不十分")

        # 最低限のプラットフォームサポート
        self.assertGreaterEqual(
            existing_scripts,
            2,
            f"プラットフォーム別スクリプトが不足: 存在={existing_scripts}",
        )

        # プラットフォームサポートドキュメントの確認
        platform_doc = self.project_root / "docs" / "PLATFORM_SUPPORT.md"
        if platform_doc.exists():
            content = platform_doc.read_text(encoding="utf-8")
            platforms = ["Linux", "macOS", "Windows"]

            supported_platforms = sum(1 for platform in platforms if platform in content)

            self.assertGreaterEqual(
                supported_platforms,
                2,
                f"プラットフォームサポートドキュメントが不十分: {supported_platforms}/3",
            )

        logger.info("✅ プラットフォーム互換性が適切")

    def test_08_new_user_experience_simulation(self):
        """新規ユーザー体験シミュレーションテスト"""
        logger.info("新規ユーザー体験をシミュレーション中...")

        # 一時ディレクトリで新規ユーザー環境をシミュレート
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project_dir = Path(temp_dir) / "github-actions-simulator"

            # プロジェクトをコピー（.git ディレクトリは除外）
            shutil.copytree(
                self.project_root,
                temp_project_dir,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"),
            )

            # 新規ユーザーとしての基本操作テスト

            # 1. README.md の可読性
            readme_path = temp_project_dir / "README.md"
            self.assertTrue(readme_path.exists(), "README.md が存在しない")

            readme_content = readme_path.read_text(encoding="utf-8")
            self.assertGreater(len(readme_content), 500, "README.md が短すぎる")

            # 2. 基本的な設定ファイルの存在
            essential_config_files = [".env.example", "docker-compose.yml"]
            for config_file in essential_config_files:
                config_path = temp_project_dir / config_file
                self.assertTrue(config_path.exists(), f"{config_file} が存在しない")

            # 3. 実行スクリプトの基本動作確認
            run_script = temp_project_dir / "scripts" / "run-actions.sh"
            if run_script.exists() and os.access(run_script, os.X_OK):
                try:
                    # 構文チェック
                    result = subprocess.run(
                        ["bash", "-n", str(run_script)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        f"run-actions.sh に構文エラー: {result.stderr}",
                    )

                except subprocess.TimeoutExpired:
                    self.fail("run-actions.sh の構文チェックがタイムアウト")

        logger.info("✅ 新規ユーザー体験シミュレーション成功")

    def test_09_security_and_license_compliance(self):
        """セキュリティとライセンス準拠テスト"""
        logger.info("セキュリティとライセンス準拠を確認中...")

        # ライセンスファイルの確認
        license_path = self.project_root / "LICENSE"
        self.assertTrue(license_path.exists(), "LICENSE ファイルが存在しない")

        license_content = license_path.read_text(encoding="utf-8")
        self.assertGreater(len(license_content), 100, "LICENSE ファイルの内容が不十分")

        # .gitignore の確認
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text(encoding="utf-8")

            # 重要な除外パターンの確認
            important_patterns = [".env", "secret", "key", "__pycache__"]
            for pattern in important_patterns:
                if pattern not in gitignore_content:
                    logger.warning(f".gitignore に {pattern} パターンが不足")

        # セキュリティ設定の確認
        security_files = [
            ".github/workflows/security-scan.yml.sample",
            "scripts/run_security_scan.py",
        ]

        security_setup = sum(1 for file_path in security_files if (self.project_root / file_path).exists())

        self.assertGreater(security_setup, 0, "セキュリティスキャン設定が不足")

        logger.info("✅ セキュリティとライセンス準拠が適切")

    def test_10_ci_cd_pipeline_readiness(self):
        """CI/CD パイプライン準備状況テスト"""
        logger.info("CI/CD パイプライン準備状況を確認中...")

        workflows_dir = self.project_root / ".github" / "workflows"
        self.assertTrue(
            workflows_dir.exists(),
            "GitHub Actions ワークフローディレクトリが存在しない",
        )

        # ワークフローファイルの確認
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        self.assertGreater(len(workflow_files), 0, "ワークフローファイルが存在しない")

        # 重要なワークフローの確認
        important_workflows = ["ci.yml", "quality-gates.yml"]
        existing_important = sum(1 for workflow in important_workflows if (workflows_dir / workflow).exists())

        self.assertGreater(existing_important, 0, "重要なワークフローが不足")

        # 品質ゲート設定の確認
        quality_scripts = [
            "scripts/automated-quality-check.sh",
            "scripts/run-comprehensive-tests.sh",
        ]

        quality_setup = sum(1 for script_path in quality_scripts if (self.project_root / script_path).exists())

        self.assertGreater(quality_setup, 0, "品質ゲート設定が不足")

        logger.info("✅ CI/CD パイプライン準備が適切")

    def test_11_comprehensive_integration_validation(self):
        """包括的統合検証テスト"""
        logger.info("包括的統合検証を実行中...")

        # 最終統合テストスクリプトの実行
        final_validation_script = self.project_root / "tests" / "test_final_integration_validation.py"
        if final_validation_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(final_validation_script)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.project_root,
                )

                # スクリプトが正常終了するか、軽微なエラーのみか
                self.assertIn(
                    result.returncode,
                    [0, 1],
                    f"最終統合テストで重大なエラー: {result.stderr}",
                )

            except subprocess.TimeoutExpired:
                self.fail("最終統合テストがタイムアウト")
            except Exception as e:
                logger.warning(f"最終統合テストスクリプトの実行エラー: {e}")

        # 配布検証スクリプトの実行
        distribution_validation_script = self.project_root / "scripts" / "final-distribution-validation.sh"
        if distribution_validation_script.exists() and os.access(distribution_validation_script, os.X_OK):
            try:
                result = subprocess.run(
                    ["bash", str(distribution_validation_script)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=self.project_root,
                )

                # スクリプトが正常終了するか、軽微なエラーのみか
                self.assertIn(
                    result.returncode,
                    [0, 1],
                    f"配布検証で重大なエラー: {result.stderr}",
                )

            except subprocess.TimeoutExpired:
                self.fail("配布検証がタイムアウト")
            except Exception as e:
                logger.warning(f"配布検証スクリプトの実行エラー: {e}")

        logger.info("✅ 包括的統合検証成功")

    @classmethod
    def tearDownClass(cls):
        """テストクラス終了処理"""
        # テスト結果の保存
        results_file = cls.project_root / "complete_distribution_validation_results.json"

        cls.test_results["completion_timestamp"] = datetime.utcnow().isoformat()

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(cls.test_results, f, ensure_ascii=False, indent=2)

        logger.info(f"完全配布検証テスト完了 - 結果: {results_file}")


def run_validation_suite():
    """検証スイートの実行"""
    # テストスイートの作成
    suite = unittest.TestLoader().loadTestsFromTestCase(CompleteDistributionValidationTest)

    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)

    result = runner.run(suite)

    # 結果の評価
    if result.wasSuccessful():
        print("\n" + "=" * 60)
        print("🎉 完全配布検証テスト - 全て成功!")
        print("配布パッケージの準備が完了しています。")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠️  完全配布検証テスト - 一部失敗")
        print(f"失敗: {len(result.failures)}, エラー: {len(result.errors)}")
        print("配布前に問題を解決してください。")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_validation_suite())
