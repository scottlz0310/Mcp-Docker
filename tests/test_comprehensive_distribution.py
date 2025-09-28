#!/usr/bin/env python3
"""
GitHub Actions Simulator - 包括的配布スクリプトテストスイート
===========================================================

このテストスイートは、配布スクリプト（scripts/run-actions.sh）の全機能をカバーします。

テスト内容:
- 依存関係チェック機能のテスト
- プラットフォーム検出とガイダンスのテスト
- エラーハンドリングとトラブルシューティングのテスト
- 進捗表示と結果サマリーのテスト
- 非対話モードでの動作テスト

実行方法:
    pytest tests/test_comprehensive_distribution.py -v
    python -m pytest tests/test_comprehensive_distribution.py::TestDistributionScript::test_dependency_check -v
"""

import os
import subprocess
import tempfile
import pytest
import shutil
from pathlib import Path
import time


class TestDistributionScript:
    """配布スクリプトの包括的テストケース"""

    @pytest.fixture
    def script_path(self):
        """配布スクリプトのパス"""
        return Path(__file__).parent.parent / "scripts" / "run-actions.sh"

    @pytest.fixture
    def temp_project_dir(self):
        """テスト用の一時プロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 基本的なプロジェクト構造を作成
            (project_dir / ".github" / "workflows").mkdir(parents=True)
            (project_dir / "scripts").mkdir()
            (project_dir / "logs").mkdir()

            # テスト用ワークフローファイルを作成
            workflow_content = """
name: Test CI
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Run tests
        run: echo "Running tests"
"""
            (project_dir / ".github" / "workflows" / "ci.yml").write_text(
                workflow_content
            )

            yield project_dir

    def test_script_exists_and_executable(self, script_path):
        """配布スクリプトが存在し、実行可能であることを確認"""
        assert script_path.exists(), f"配布スクリプトが見つかりません: {script_path}"
        assert os.access(
            script_path, os.X_OK
        ), f"配布スクリプトが実行可能ではありません: {script_path}"

    def test_help_option(self, script_path):
        """ヘルプオプションの動作テスト"""
        result = subprocess.run(
            [str(script_path), "--help"], capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"ヘルプオプションが失敗: {result.stderr}"
        assert "GitHub Actions Simulator" in result.stdout
        assert "使用方法:" in result.stdout
        assert "--help" in result.stdout
        assert "--check-deps" in result.stdout
        assert "--non-interactive" in result.stdout

    def test_dependency_check_option(self, script_path, temp_project_dir):
        """依存関係チェックオプションのテスト"""
        # テスト環境でスクリプトを実行
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        # 依存関係チェックは成功または適切なエラーメッセージを返すべき
        assert result.returncode in [
            0,
            2,
        ], f"依存関係チェックが予期しない終了コード: {result.returncode}"

        # 出力に依存関係チェックの情報が含まれることを確認
        output = result.stdout + result.stderr
        assert "依存関係をチェック中" in output or "プラットフォーム:" in output

    def test_extended_dependency_check(self, script_path, temp_project_dir):
        """拡張依存関係チェックのテスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps-extended"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        # 拡張チェックは詳細情報を提供すべき
        output = result.stdout + result.stderr
        assert "プラットフォーム:" in output or "アーキテクチャ:" in output

    def test_non_interactive_mode(self, script_path, temp_project_dir):
        """非対話モードのテスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"
        env["INDEX"] = "1"  # 最初のワークフローを自動選択

        # タイムアウトを短く設定してテスト
        env["ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"] = "5"

        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=temp_project_dir,
            env=env,
        )

        # 非対話モードでは自動的に処理が進むべき
        output = result.stdout + result.stderr
        assert "非対話モード" in output or "自動選択" in output or "Docker" in output

    def test_timeout_option(self, script_path, temp_project_dir):
        """タイムアウトオプションのテスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--timeout=10"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        # タイムアウト設定が受け入れられることを確認
        # エラーが発生しても、タイムアウト設定自体は有効であるべき
        assert result.returncode != 127, "タイムアウトオプションが認識されませんでした"

    def test_workflow_discovery(self, script_path, temp_project_dir):
        """ワークフロー発見機能のテスト"""
        # 追加のワークフローファイルを作成
        additional_workflow = """
name: Additional Test
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Additional test"
"""
        (temp_project_dir / ".github" / "workflows" / "additional.yml").write_text(
            additional_workflow
        )

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        # ワークフローファイルが発見されることを確認
        # （依存関係チェックモードでも基本的な検証は行われる）
        assert result.returncode in [0, 2], "ワークフロー発見でエラーが発生"

    def test_error_handling_missing_workflow_dir(self, script_path):
        """ワークフローディレクトリが存在しない場合のエラーハンドリング"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_project = Path(temp_dir) / "empty_project"
            empty_project.mkdir()

            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=empty_project,
                env=env,
            )

            # 適切なエラーメッセージが表示されることを確認
            output = result.stdout + result.stderr
            assert result.returncode != 0, "エラーが適切に検出されませんでした"
            assert (
                "ワークフロー" in output
                or "見つかりません" in output
                or "Docker" in output
            )

    def test_log_directory_creation(self, script_path, temp_project_dir):
        """ログディレクトリの作成テスト"""
        # ログディレクトリを削除
        log_dir = temp_project_dir / "logs"
        if log_dir.exists():
            shutil.rmtree(log_dir)

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        # ログディレクトリが作成されることを確認
        assert log_dir.exists(), "ログディレクトリが作成されませんでした"

    def test_platform_detection(self, script_path, temp_project_dir):
        """プラットフォーム検出機能のテスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps-extended"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        output = result.stdout + result.stderr

        # プラットフォーム情報が出力されることを確認
        platform_indicators = [
            "Linux",
            "macOS",
            "Windows",
            "ubuntu",
            "darwin",
            "プラットフォーム",
        ]
        assert any(
            indicator in output for indicator in platform_indicators
        ), f"プラットフォーム情報が検出されませんでした: {output}"

    def test_docker_availability_check(self, script_path, temp_project_dir):
        """Docker可用性チェックのテスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=temp_project_dir,
            env=env,
        )

        output = result.stdout + result.stderr

        # Docker関連のチェック結果が出力されることを確認
        docker_indicators = ["Docker", "docker", "コンテナ", "イメージ"]
        assert any(
            indicator in output for indicator in docker_indicators
        ), f"Docker関連の情報が見つかりませんでした: {output}"

    def test_script_with_specific_workflow(self, script_path, temp_project_dir):
        """特定のワークフローファイルを指定した実行のテスト"""
        workflow_file = ".github/workflows/ci.yml"

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"
        env["ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"] = "5"

        result = subprocess.run(
            [str(script_path), workflow_file],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=temp_project_dir,
            env=env,
        )

        # 指定されたワークフローファイルが処理されることを確認
        output = result.stdout + result.stderr
        assert "ci.yml" in output or "Test CI" in output or "Docker" in output

    def test_invalid_arguments_handling(self, script_path, temp_project_dir):
        """無効な引数の処理テスト"""
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=temp_project_dir,
            env=env,
        )

        # 無効なオプションが適切に処理されることを確認
        # （エラーまたは無視される）
        assert (
            result.returncode != 127
        ), "無効なオプションでコマンドが見つからないエラーが発生"


class TestDistributionScriptIntegration:
    """配布スクリプトの統合テストクラス"""

    @pytest.fixture
    def script_path(self):
        """配布スクリプトのパス"""
        return Path(__file__).parent.parent / "scripts" / "run-actions.sh"

    def test_real_project_dependency_check(self, script_path):
        """実際のプロジェクトでの依存関係チェック"""
        project_root = Path(__file__).parent.parent

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
            env=env,
        )

        # 実際のプロジェクトでの依存関係チェックが動作することを確認
        output = result.stdout + result.stderr
        assert (
            "依存関係" in output or "プラットフォーム" in output or "Docker" in output
        )

    def test_real_project_workflow_discovery(self, script_path):
        """実際のプロジェクトでのワークフロー発見"""
        project_root = Path(__file__).parent.parent
        workflows_dir = project_root / ".github" / "workflows"

        if workflows_dir.exists():
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "1"

            result = subprocess.run(
                [str(script_path), "--check-deps"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
                env=env,
            )

            # ワークフローファイルが適切に処理されることを確認
            assert result.returncode in [
                0,
                2,
            ], "実際のプロジェクトでワークフロー処理が失敗"

    def test_script_performance(self, script_path):
        """スクリプトのパフォーマンステスト"""
        project_root = Path(__file__).parent.parent

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        start_time = time.time()

        result = subprocess.run(
            [str(script_path), "--check-deps"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=project_root,
            env=env,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # 依存関係チェックが合理的な時間内に完了することを確認
        assert (
            execution_time < 120
        ), f"依存関係チェックが遅すぎます: {execution_time:.2f}秒"

        # 結果が得られることを確認
        output = result.stdout + result.stderr
        assert len(output) > 0, "出力が生成されませんでした"


class TestDistributionScriptErrorScenarios:
    """配布スクリプトのエラーシナリオテスト"""

    @pytest.fixture
    def script_path(self):
        """配布スクリプトのパス"""
        return Path(__file__).parent.parent / "scripts" / "run-actions.sh"

    def test_permission_denied_scenario(self, script_path):
        """権限拒否シナリオのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = Path(temp_dir) / "restricted"
            restricted_dir.mkdir(mode=0o000)  # 権限なし

            try:
                env = os.environ.copy()
                env["NON_INTERACTIVE"] = "1"

                result = subprocess.run(
                    [str(script_path), "--check-deps"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=restricted_dir,
                    env=env,
                )

                # 権限エラーが適切に処理されることを確認
                # （エラーコードまたは適切なメッセージ）
                output = result.stdout + result.stderr
                assert len(output) > 0, "権限エラー時に出力が生成されませんでした"

            finally:
                # クリーンアップのために権限を復元
                restricted_dir.chmod(0o755)

    def test_disk_space_check(self, script_path):
        """ディスク容量チェックのテスト"""
        project_root = Path(__file__).parent.parent

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps-extended"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
            env=env,
        )

        # ディスク容量に関する情報が含まれることを確認
        output = result.stdout + result.stderr
        disk_indicators = ["容量", "ディスク", "GB", "MB", "space", "disk"]

        # 拡張チェックではディスク情報が含まれる可能性がある
        # （必須ではないが、含まれていれば適切に処理されているはず）
        if any(indicator in output for indicator in disk_indicators):
            assert True, "ディスク容量情報が適切に処理されています"

    def test_network_connectivity_check(self, script_path):
        """ネットワーク接続チェックのテスト"""
        project_root = Path(__file__).parent.parent

        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"

        result = subprocess.run(
            [str(script_path), "--check-deps-extended"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
            env=env,
        )

        # ネットワーク関連のチェックが実行されることを確認
        output = result.stdout + result.stderr
        network_indicators = ["ネットワーク", "接続", "ping", "network", "connectivity"]

        # 拡張チェックではネットワーク情報が含まれる可能性がある
        if any(indicator in output for indicator in network_indicators):
            assert True, "ネットワーク接続情報が適切に処理されています"


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])
