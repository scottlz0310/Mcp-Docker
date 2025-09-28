#!/usr/bin/env python3
"""
GitHub Actions Simulator - サポートシステム統合テスト

このテストスイートは、サポートチャネルと診断ツールの統合を検証します。
"""

import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SupportIntegrationTest(unittest.TestCase):
    """サポートシステム統合テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.project_root = PROJECT_ROOT
        self.scripts_dir = self.project_root / "scripts"
        self.docs_dir = self.project_root / "docs"
        self.github_dir = self.project_root / ".github"

        # テスト用一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ファイルのクリーンアップ
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_support_scripts_exist(self):
        """サポートスクリプトの存在確認"""
        required_scripts = [
            "collect-support-info.sh",
            "diagnostic-helper.sh",
            "run-actions.sh",
        ]

        for script in required_scripts:
            script_path = self.scripts_dir / script
            self.assertTrue(
                script_path.exists(),
                f"必須サポートスクリプトが見つかりません: {script}",
            )
            self.assertTrue(
                os.access(script_path, os.X_OK),
                f"スクリプトに実行権限がありません: {script}",
            )

    def test_support_documentation_exists(self):
        """サポートドキュメントの存在確認"""
        required_docs = [
            "SUPPORT.md",
            "PROBLEM_REPORTING_GUIDE.md",
            "COMMUNITY_SUPPORT_GUIDE.md",
            "TROUBLESHOOTING.md",
        ]

        for doc in required_docs:
            doc_path = self.docs_dir / doc
            self.assertTrue(
                doc_path.exists(), f"必須サポートドキュメントが見つかりません: {doc}"
            )

            # ドキュメントが空でないことを確認
            content = doc_path.read_text(encoding="utf-8")
            self.assertGreater(
                len(content.strip()), 100, f"ドキュメントの内容が不十分です: {doc}"
            )

    def test_github_issue_templates_exist(self):
        """GitHub Issueテンプレートの存在確認"""
        template_dir = self.github_dir / "ISSUE_TEMPLATE"
        required_templates = [
            "bug_report.md",
            "feature_request.md",
            "question.md",
            "config.yml",
        ]

        self.assertTrue(
            template_dir.exists(),
            "GitHub Issue テンプレートディレクトリが見つかりません",
        )

        for template in required_templates:
            template_path = template_dir / template
            self.assertTrue(
                template_path.exists(),
                f"必須Issueテンプレートが見つかりません: {template}",
            )

    def test_collect_support_info_script(self):
        """サポート情報収集スクリプトのテスト"""
        script_path = self.scripts_dir / "collect-support-info.sh"

        # ヘルプオプションのテスト
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        self.assertEqual(result.returncode, 0, "ヘルプオプションが失敗しました")
        self.assertIn("使用方法", result.stdout, "ヘルプメッセージが不完全です")
        self.assertIn("--output", result.stdout, "オプション説明が不足しています")

        # 基本実行テスト（ドライラン）
        output_file = self.temp_dir / "test_support_info.txt"
        result = subprocess.run(
            [str(script_path), "--output", str(output_file), "--no-logs"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,  # タイムアウト設定
        )

        # スクリプトが正常終了することを確認
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")

        self.assertEqual(result.returncode, 0, "サポート情報収集が失敗しました")
        self.assertTrue(output_file.exists(), "出力ファイルが作成されませんでした")

        # 出力ファイルの内容確認
        content = output_file.read_text(encoding="utf-8")
        required_sections = ["システム情報", "バージョン情報", "収集完了"]

        for section in required_sections:
            self.assertIn(section, content, f"必須セクションが不足: {section}")

    def test_diagnostic_helper_script(self):
        """診断ヘルパースクリプトのテスト"""
        script_path = self.scripts_dir / "diagnostic-helper.sh"

        # ヘルプオプションのテスト
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        self.assertEqual(result.returncode, 0, "診断ヘルパーのヘルプが失敗しました")
        self.assertIn("診断タイプ", result.stdout, "診断タイプの説明が不足しています")

        # 依存関係診断のテスト
        result = subprocess.run(
            [str(script_path), "dependencies"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,
        )

        # 診断が実行されることを確認（結果は環境依存）
        self.assertIn(
            "依存関係を診断中", result.stdout, "依存関係診断が実行されませんでした"
        )

    def test_support_info_auto_troubleshoot(self):
        """自動トラブルシューティング機能のテスト"""
        script_path = self.scripts_dir / "collect-support-info.sh"
        output_file = self.temp_dir / "troubleshoot_info.txt"

        result = subprocess.run(
            [
                str(script_path),
                "--auto-troubleshoot",
                "--output",
                str(output_file),
                "--no-logs",
            ],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=45,
        )

        self.assertEqual(
            result.returncode, 0, "自動トラブルシューティングが失敗しました"
        )
        self.assertTrue(
            output_file.exists(),
            "トラブルシューティング結果ファイルが作成されませんでした",
        )

        content = output_file.read_text(encoding="utf-8")
        self.assertIn(
            "自動トラブルシューティング結果",
            content,
            "トラブルシューティング結果が含まれていません",
        )

    def test_issue_template_structure(self):
        """Issueテンプレートの構造確認"""
        template_dir = self.github_dir / "ISSUE_TEMPLATE"

        # バグ報告テンプレートの確認
        bug_template = template_dir / "bug_report.md"
        content = bug_template.read_text(encoding="utf-8")

        required_sections = [
            "問題の概要",
            "環境情報",
            "再現手順",
            "期待される動作",
            "実際の動作",
        ]

        for section in required_sections:
            self.assertIn(
                section,
                content,
                f"バグ報告テンプレートに必須セクションが不足: {section}",
            )

        # 機能要望テンプレートの確認
        feature_template = template_dir / "feature_request.md"
        content = feature_template.read_text(encoding="utf-8")

        required_sections = [
            "機能要望の概要",
            "動機・背景",
            "詳細な機能仕様",
            "受け入れ基準",
        ]

        for section in required_sections:
            self.assertIn(
                section,
                content,
                f"機能要望テンプレートに必須セクションが不足: {section}",
            )

    def test_documentation_cross_references(self):
        """ドキュメント間の相互参照確認"""
        # SUPPORT.mdから他のドキュメントへのリンク確認
        support_doc = self.docs_dir / "SUPPORT.md"
        content = support_doc.read_text(encoding="utf-8")

        expected_links = [
            "PROBLEM_REPORTING_GUIDE.md",
            "COMMUNITY_SUPPORT_GUIDE.md",
            "TROUBLESHOOTING.md",
        ]

        for link in expected_links:
            self.assertIn(link, content, f"SUPPORT.mdに必要なリンクが不足: {link}")

        # README.mdからサポートドキュメントへのリンク確認
        readme_path = self.project_root / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8")

        support_links = [
            "docs/SUPPORT.md",
            "docs/PROBLEM_REPORTING_GUIDE.md",
            "docs/COMMUNITY_SUPPORT_GUIDE.md",
        ]

        for link in support_links:
            self.assertIn(
                link, readme_content, f"README.mdに必要なサポートリンクが不足: {link}"
            )

    def test_diagnostic_script_options(self):
        """診断スクリプトのオプション機能テスト"""
        script_path = self.scripts_dir / "collect-support-info.sh"

        # 各オプションが認識されることを確認
        test_options = [
            ["--verbose"],
            ["--no-docker"],
            ["--no-logs"],
            ["--network"],
            ["--performance"],
        ]

        for options in test_options:
            output_file = (
                self.temp_dir / f"test_{'-'.join(options[0].split('--')[1:])}.txt"
            )
            cmd = [str(script_path)] + options + ["--output", str(output_file)]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root, timeout=30
            )

            # オプションが正しく処理されることを確認
            self.assertEqual(
                result.returncode,
                0,
                f"オプション {' '.join(options)} の処理が失敗しました: {result.stderr}",
            )

    def test_support_workflow_integration(self):
        """サポートワークフローの統合テスト"""
        # 1. 問題発生のシミュレーション
        # 2. 診断ツールの実行
        # 3. サポート情報の収集
        # 4. 問題報告の準備

        # 診断実行
        diagnostic_script = self.scripts_dir / "diagnostic-helper.sh"
        result = subprocess.run(
            [str(diagnostic_script), "dependencies", "--verbose"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,
        )

        # 診断が何らかの結果を返すことを確認
        self.assertIsNotNone(result.stdout, "診断結果が空です")

        # サポート情報収集
        support_script = self.scripts_dir / "collect-support-info.sh"
        output_file = self.temp_dir / "workflow_test.txt"

        result = subprocess.run(
            [str(support_script), "--output", str(output_file)],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=45,
        )

        self.assertEqual(result.returncode, 0, "サポートワークフローが失敗しました")
        self.assertTrue(
            output_file.exists(), "サポート情報ファイルが作成されませんでした"
        )

        # 収集された情報が問題報告に使用可能かチェック
        content = output_file.read_text(encoding="utf-8")
        essential_info = ["システム情報", "バージョン情報", "収集完了日時"]

        for info in essential_info:
            self.assertIn(info, content, f"問題報告に必要な情報が不足: {info}")

    def test_community_support_accessibility(self):
        """コミュニティサポートのアクセシビリティテスト"""
        # GitHub Issue テンプレートのアクセシビリティ
        config_file = self.github_dir / "ISSUE_TEMPLATE" / "config.yml"
        self.assertTrue(config_file.exists(), "Issue設定ファイルが見つかりません")

        # 設定ファイルの内容確認
        content = config_file.read_text(encoding="utf-8")
        self.assertIn("contact_links", content, "連絡先リンクが設定されていません")
        self.assertIn(
            "GitHub Discussions", content, "Discussionsリンクが設定されていません"
        )

        # ドキュメントのアクセシビリティ
        community_guide = self.docs_dir / "COMMUNITY_SUPPORT_GUIDE.md"
        content = community_guide.read_text(encoding="utf-8")

        accessibility_features = [
            "目的別チャネル選択",
            "効果的な質問の仕方",
            "コミュニティ貢献",
        ]

        for feature in accessibility_features:
            self.assertIn(feature, content, f"アクセシビリティ機能が不足: {feature}")


class SupportToolsPerformanceTest(unittest.TestCase):
    """サポートツールのパフォーマンステスト"""

    def setUp(self):
        self.project_root = PROJECT_ROOT
        self.scripts_dir = self.project_root / "scripts"
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_support_info_collection_performance(self):
        """サポート情報収集のパフォーマンステスト"""
        import time

        script_path = self.scripts_dir / "collect-support-info.sh"
        output_file = self.temp_dir / "perf_test.txt"

        start_time = time.time()

        result = subprocess.run(
            [str(script_path), "--output", str(output_file), "--no-logs"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=60,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        self.assertEqual(result.returncode, 0, "パフォーマンステストが失敗しました")
        self.assertLess(
            execution_time, 30, f"実行時間が長すぎます: {execution_time:.2f}秒"
        )

        # 出力ファイルサイズの確認
        if output_file.exists():
            file_size = output_file.stat().st_size
            self.assertGreater(file_size, 1000, "出力ファイルが小さすぎます")
            self.assertLess(
                file_size, 1024 * 1024, "出力ファイルが大きすぎます"
            )  # 1MB未満

    def test_diagnostic_helper_performance(self):
        """診断ヘルパーのパフォーマンステスト"""
        import time

        script_path = self.scripts_dir / "diagnostic-helper.sh"

        start_time = time.time()

        subprocess.run(
            [str(script_path), "dependencies"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # 診断は15秒以内に完了すべき
        self.assertLess(
            execution_time, 15, f"診断実行時間が長すぎます: {execution_time:.2f}秒"
        )


def run_support_integration_tests():
    """サポート統合テストの実行"""
    # テストスイートの作成
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # 基本統合テスト
    test_suite.addTests(loader.loadTestsFromTestCase(SupportIntegrationTest))

    # パフォーマンステスト
    test_suite.addTests(loader.loadTestsFromTestCase(SupportToolsPerformanceTest))

    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("GitHub Actions Simulator - サポートシステム統合テスト")
    print("=" * 60)

    success = run_support_integration_tests()

    if success:
        print("\n✅ 全てのサポート統合テストが成功しました！")
        sys.exit(0)
    else:
        print("\n❌ サポート統合テストに失敗しました")
        sys.exit(1)
