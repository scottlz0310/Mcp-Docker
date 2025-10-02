#!/usr/bin/env python3
"""
GitHub Actions Simulator - エンドツーエンド新規ユーザー体験テストスイート
================================================================

このテストスイートは、新規ユーザーの完全な体験フローをテストします。

テスト内容:
- 新規ユーザーのオンボーディング体験
- ドキュメントからの実行フロー
- テンプレートを使用した初期セットアップ
- 一般的な使用パターンの動作確認
- エラー時のユーザーガイダンス

実行方法:
    pytest tests/test_end_to_end_user_experience.py -v
    python -m pytest tests/test_end_to_end_user_experience.py::TestNewUserExperience::test_complete_onboarding_flow -v
"""

import os
import shutil
import subprocess
import tempfile
import time
import pytest
from pathlib import Path


class TestNewUserExperience:
    """新規ユーザー体験テストクラス"""

    @pytest.fixture
    def clean_project_environment(self):
        """クリーンなプロジェクト環境を作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "github-actions-simulator"

            # 実際のプロジェクトをコピー
            source_dir = Path(__file__).parent.parent
            shutil.copytree(
                source_dir,
                project_dir,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    ".pytest_cache",
                    "node_modules",
                    ".venv",
                    "venv",
                    ".mypy_cache",
                    ".ruff_cache",
                    "logs",
                ),
            )

            yield project_dir

    @pytest.fixture
    def new_user_project(self):
        """新規ユーザーのプロジェクト環境を作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            user_project = Path(temp_dir) / "my_project"
            user_project.mkdir()

            # 基本的なプロジェクト構造を作成
            (user_project / ".github" / "workflows").mkdir(parents=True)
            (user_project / "src").mkdir()
            (user_project / "tests").mkdir()

            # サンプルワークフローを作成
            workflow_content = """
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest

      - name: Run tests
        run: pytest tests/
"""
            (user_project / ".github" / "workflows" / "ci.yml").write_text(workflow_content)

            # サンプルPythonファイル
            (user_project / "src" / "main.py").write_text('print("Hello, World!")')
            (user_project / "tests" / "test_main.py").write_text("def test_example():\n    assert True")

            yield user_project

    def test_complete_onboarding_flow(self, clean_project_environment):
        """完全なオンボーディングフローのテスト"""
        project_dir = clean_project_environment

        # Step 1: README.mdの確認
        readme_path = project_dir / "README.md"
        assert readme_path.exists(), "README.mdが存在しません"

        readme_content = readme_path.read_text(encoding="utf-8")

        # 新規ユーザー向けの情報が含まれていることを確認
        essential_info = [
            "GitHub Actions Simulator",
            "クイックスタート",
            "インストール",
            "使用方法",
        ]

        missing_info = []
        for info in essential_info:
            if info not in readme_content:
                missing_info.append(info)

        assert not missing_info, f"README.mdに必須情報が不足: {missing_info}"

        # Step 2: 依存関係チェックの実行
        run_script = project_dir / "scripts" / "run-actions.sh"
        assert run_script.exists(), "実行スクリプトが存在しません"

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(run_script), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_dir,
            env=env,
        )

        # 依存関係チェックが実行されることを確認
        output = result.stdout + result.stderr
        assert "依存関係" in output or "プラットフォーム" in output or "Docker" in output

        # Step 3: ヘルプ情報の確認
        help_result = subprocess.run(
            [str(run_script), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir,
        )

        assert help_result.returncode == 0, "ヘルプオプションが失敗しました"
        assert "使用方法" in help_result.stdout, "ヘルプに使用方法が含まれていません"

    def test_template_based_setup_flow(self, new_user_project, clean_project_environment):
        """テンプレートベースのセットアップフローのテスト"""
        simulator_dir = clean_project_environment
        user_project = new_user_project

        # Step 1: .env.exampleの確認と使用
        env_example = simulator_dir / ".env.example"
        assert env_example.exists(), ".env.exampleが存在しません"

        env_content = env_example.read_text(encoding="utf-8")

        # 必要な環境変数が含まれていることを確認
        required_vars = ["GITHUB_PERSONAL_ACCESS_TOKEN", "USER_ID", "GROUP_ID"]

        missing_vars = []
        for var in required_vars:
            if f"{var}=" not in env_content:
                missing_vars.append(var)

        assert not missing_vars, f".env.exampleに必要な変数が不足: {missing_vars}"

        # Step 2: ユーザープロジェクトに.envファイルを作成
        user_env = user_project / ".env"
        user_env.write_text(env_content.replace("your_github_token_here", "dummy_token_for_test"))

        # Step 3: pre-commitテンプレートの確認
        precommit_sample = simulator_dir / ".pre-commit-config.yaml.sample"
        if precommit_sample.exists():
            precommit_content = precommit_sample.read_text(encoding="utf-8")

            # 基本的なpre-commit設定が含まれていることを確認
            assert "repos:" in precommit_content, "pre-commit設定が無効です"

            # ユーザープロジェクトにコピー
            (user_project / ".pre-commit-config.yaml").write_text(precommit_content)

        # Step 4: GitHub Workflowテンプレートの確認
        workflow_samples = list((simulator_dir / ".github" / "workflows").glob("*.sample"))
        assert len(workflow_samples) > 0, "ワークフローサンプルが存在しません"

        for sample in workflow_samples:
            content = sample.read_text(encoding="utf-8")
            assert "name:" in content, f"無効なワークフローサンプル: {sample.name}"
            assert "on:" in content, f"無効なワークフローサンプル: {sample.name}"
            assert "jobs:" in content, f"無効なワークフローサンプル: {sample.name}"

    def test_first_time_execution_flow(self, new_user_project, clean_project_environment):
        """初回実行フローのテスト"""
        simulator_dir = clean_project_environment
        user_project = new_user_project

        # シミュレーターのrun-actions.shをユーザープロジェクトで実行
        run_script = simulator_dir / "scripts" / "run-actions.sh"

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"
        env["INDEX"] = "1"  # 最初のワークフローを自動選択
        env["ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"] = "10"  # 短いタイムアウト

        # ユーザープロジェクトでシミュレーターを実行
        result = subprocess.run(
            [str(run_script)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=user_project,
            env=env,
        )

        output = result.stdout + result.stderr

        # 実行が試行されることを確認（成功/失敗は問わない）
        execution_indicators = [
            "ワークフロー",
            "Docker",
            "実行",
            "ci.yml",
            "エラー",
            "タイムアウト",
        ]

        assert any(indicator in output for indicator in execution_indicators), f"実行が試行されませんでした: {output}"

    def test_error_guidance_for_new_users(self, clean_project_environment):
        """新規ユーザー向けエラーガイダンスのテスト"""
        project_dir = clean_project_environment
        run_script = project_dir / "scripts" / "run-actions.sh"

        # Step 1: 存在しないワークフローファイルを指定
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(run_script), "nonexistent-workflow.yml"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_dir,
            env=env,
        )

        output = result.stdout + result.stderr

        # エラーメッセージが有用であることを確認
        helpful_indicators = [
            "見つかりません",
            "確認",
            "ヘルプ",
            "ドキュメント",
            "トラブルシューティング",
        ]

        assert any(
            indicator in output for indicator in helpful_indicators
        ), f"有用なエラーメッセージが提供されませんでした: {output}"

        # Step 2: 無効なオプションのテスト
        invalid_option_result = subprocess.run(
            [str(run_script), "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir,
            env=env,
        )

        # 無効なオプションが適切に処理されることを確認
        assert invalid_option_result.returncode != 127, "無効なオプションでコマンドエラーが発生"

    def test_documentation_guided_workflow(self, clean_project_environment):
        """ドキュメントガイド付きワークフローのテスト"""
        project_dir = clean_project_environment

        # Step 1: トラブルシューティングドキュメントの確認
        troubleshooting_doc = project_dir / "docs" / "TROUBLESHOOTING.md"
        if troubleshooting_doc.exists():
            content = troubleshooting_doc.read_text(encoding="utf-8")

            # 新規ユーザー向けの情報が含まれていることを確認
            user_friendly_sections = [
                "インストール",
                "依存関係",
                "Docker",
                "エラー",
                "解決方法",
            ]

            found_sections = []
            for section in user_friendly_sections:
                if section in content:
                    found_sections.append(section)

            assert (
                len(found_sections) >= 3
            ), f"トラブルシューティングドキュメントに十分な情報がありません。見つかったセクション: {found_sections}"

        # Step 2: actionsディレクトリのドキュメント確認
        actions_readme = project_dir / "docs" / "actions" / "README.md"
        if actions_readme.exists():
            content = actions_readme.read_text(encoding="utf-8")

            # 使用方法の説明が含まれていることを確認
            usage_indicators = ["使用方法", "実行", "例", "コマンド"]

            assert any(
                indicator in content for indicator in usage_indicators
            ), "actionsドキュメントに使用方法が含まれていません"

        # Step 3: プラットフォームサポートドキュメントの確認
        platform_doc = project_dir / "docs" / "PLATFORM_SUPPORT.md"
        if platform_doc.exists():
            content = platform_doc.read_text(encoding="utf-8")

            # 主要プラットフォームの情報が含まれていることを確認
            platforms = ["Linux", "macOS", "Windows", "Ubuntu", "Docker"]

            found_platforms = []
            for platform in platforms:
                if platform in content:
                    found_platforms.append(platform)

            assert (
                len(found_platforms) >= 3
            ), f"プラットフォームサポートドキュメントに十分な情報がありません。見つかったプラットフォーム: {found_platforms}"

    def test_makefile_integration_for_users(self, clean_project_environment):
        """ユーザー向けMakefile統合のテスト"""
        project_dir = clean_project_environment
        makefile_path = project_dir / "Makefile"

        if not makefile_path.exists():
            pytest.skip("Makefileが存在しません")

        # 重要なターゲットが存在することを確認
        makefile_content = makefile_path.read_text(encoding="utf-8")

        important_targets = ["setup", "actions", "clean", "help"]

        missing_targets = []
        for target in important_targets:
            if f"{target}:" not in makefile_content:
                missing_targets.append(target)

        # 一部のターゲットが存在すれば良い（全てが必須ではない）
        if len(missing_targets) == len(important_targets):
            pytest.skip("重要なMakeターゲットが見つかりません")

        # makeコマンドの実行テスト（利用可能な場合）
        if shutil.which("make"):
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            # make helpの実行テスト
            if "help:" in makefile_content:
                help_result = subprocess.run(
                    ["make", "help"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_dir,
                    env=env,
                )

                if help_result.returncode == 0:
                    assert len(help_result.stdout) > 0, "make helpが出力を生成しませんでした"


class TestUserExperienceEdgeCases:
    """ユーザー体験エッジケーステストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    def test_empty_project_handling(self, project_root):
        """空のプロジェクトでの処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_project = Path(temp_dir) / "empty_project"
            empty_project.mkdir()

            run_script = project_root / "scripts" / "run-actions.sh"

            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            result = subprocess.run(
                [str(run_script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=empty_project,
                env=env,
            )

            output = result.stdout + result.stderr

            # 適切なエラーメッセージまたはガイダンスが提供されることを確認
            guidance_indicators = [
                "ワークフロー",
                "見つかりません",
                "作成",
                "GitHub Actions",
                ".github/workflows",
            ]

            assert any(
                indicator in output for indicator in guidance_indicators
            ), f"空のプロジェクトに対する適切なガイダンスが提供されませんでした: {output}"

    def test_permission_issues_handling(self, project_root):
        """権限問題の処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_project = Path(temp_dir) / "restricted_project"
            restricted_project.mkdir()

            # 読み取り専用ディレクトリを作成
            readonly_dir = restricted_project / "readonly"
            readonly_dir.mkdir(mode=0o444)

            try:
                run_script = project_root / "scripts" / "run-actions.sh"

                env = os.environ.copy()
                env["NON_INTERACTIVE"] = "1"

                result = subprocess.run(
                    [str(run_script), "--check-deps"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=restricted_project,
                    env=env,
                )

                # 権限問題が適切に処理されることを確認
                output = result.stdout + result.stderr
                assert len(output) > 0, "権限制限下でも何らかの出力が生成されるべきです"

            finally:
                # クリーンアップのために権限を復元
                readonly_dir.chmod(0o755)

    def test_network_connectivity_issues(self, project_root):
        """ネットワーク接続問題のテスト"""
        run_script = project_root / "scripts" / "run-actions.sh"

        # ネットワーク接続をシミュレートするため、プロキシ設定を使用
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"
        env["HTTP_PROXY"] = "http://invalid-proxy:8080"
        env["HTTPS_PROXY"] = "http://invalid-proxy:8080"

        result = subprocess.run(
            [str(run_script), "--check-deps-extended"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
            env=env,
        )

        # ネットワーク問題が検出または適切に処理されることを確認
        output = result.stdout + result.stderr

        # ネットワーク関連の情報またはエラーハンドリングが含まれることを確認
        network_indicators = [
            "ネットワーク",
            "接続",
            "プロキシ",
            "タイムアウト",
            "network",
            "connectivity",
        ]

        # ネットワーク問題が言及されるか、正常に処理されることを確認
        has_network_mention = any(indicator in output for indicator in network_indicators)
        has_normal_output = "依存関係" in output or "プラットフォーム" in output

        assert has_network_mention or has_normal_output, f"ネットワーク問題が適切に処理されませんでした: {output}"

    def test_large_project_handling(self, project_root):
        """大規模プロジェクトでの処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            large_project = Path(temp_dir) / "large_project"
            large_project.mkdir()

            # 多数のワークフローファイルを作成
            workflows_dir = large_project / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            for i in range(20):  # 20個のワークフローファイル
                workflow_content = f"""
name: Test Workflow {i}
on: [push]
jobs:
  test{i}:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Test {i}"
"""
                (workflows_dir / f"test{i}.yml").write_text(workflow_content)

            run_script = project_root / "scripts" / "run-actions.sh"

            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"
            env["INDEX"] = "1"  # 最初のワークフローを選択

            start_time = time.time()

            result = subprocess.run(
                [str(run_script), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=large_project,
                env=env,
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # 大規模プロジェクトでも合理的な時間で処理されることを確認
            assert execution_time < 120, f"大規模プロジェクトの処理が遅すぎます: {execution_time:.2f}秒"

            # 適切に処理されることを確認
            output = result.stdout + result.stderr
            assert len(output) > 0, "大規模プロジェクトで出力が生成されませんでした"


class TestUserExperienceAccessibility:
    """ユーザー体験アクセシビリティテストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    def test_colorblind_friendly_output(self, project_root):
        """色覚障害者に配慮した出力のテスト"""
        run_script = project_root / "scripts" / "run-actions.sh"

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

        output = result.stdout + result.stderr

        # 絵文字やアイコンが情報伝達に使用されていることを確認
        # （色だけに依存しない情報伝達）
        visual_indicators = ["✅", "❌", "⚠️", "🔍", "📋", "🚀", "💡"]

        has_visual_indicators = any(indicator in output for indicator in visual_indicators)

        # テキストベースの状態表示も確認
        text_indicators = ["成功", "エラー", "警告", "情報", "OK", "FAIL", "WARNING"]
        has_text_indicators = any(indicator in output for indicator in text_indicators)

        # どちらかの方法で状態が表現されていることを確認
        assert has_visual_indicators or has_text_indicators, "アクセシブルな状態表示が不足しています"

    def test_screen_reader_friendly_output(self, project_root):
        """スクリーンリーダー対応出力のテスト"""
        run_script = project_root / "scripts" / "run-actions.sh"

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(run_script), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
            env=env,
        )

        output = result.stdout + result.stderr

        # 構造化された出力が提供されていることを確認
        structure_indicators = [
            "===",  # セクション区切り
            "---",  # サブセクション区切り
            "1.",  # 番号付きリスト
            "•",  # 箇条書き
            ":",  # ラベル付き情報
        ]

        has_structure = any(indicator in output for indicator in structure_indicators)

        # 明確なラベルが使用されていることを確認
        label_indicators = ["ステップ", "結果", "状態", "エラー", "警告", "情報"]

        has_labels = any(indicator in output for indicator in label_indicators)

        assert has_structure or has_labels, "スクリーンリーダー対応の構造化出力が不足しています"


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])
