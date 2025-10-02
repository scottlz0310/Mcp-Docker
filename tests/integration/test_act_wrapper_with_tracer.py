"""
GitHub Actions Simulator - ActWrapper with ExecutionTracer integration test
ActWrapperとExecutionTracerの統合テスト
"""

import os
import tempfile
import yaml
from pathlib import Path


from services.actions.enhanced_act_wrapper import EnhancedActWrapper as ActWrapper
from services.actions.execution_tracer import ExecutionTracer
from services.actions.logger import ActionsLogger


class TestActWrapperWithTracer:
    """ActWrapperとExecutionTracerの統合テストクラス"""

    def setup_method(self):
        """テストメソッドの前処理"""
        # モックモードを有効にして実際のactバイナリを使わない
        os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"
        os.environ["ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS"] = "0.1"

    def teardown_method(self):
        """テストメソッドの後処理"""
        # 環境変数をクリア
        os.environ.pop("ACTIONS_SIMULATOR_ENGINE", None)
        os.environ.pop("ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS", None)

    def test_mock_workflow_execution_with_tracing(self):
        """モックワークフロー実行でのトレース機能をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # テスト用のワークフローファイルを作成
            workflow_content = {
                "name": "Test Workflow",
                "on": ["push"],
                "jobs": {
                    "test": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"name": "Checkout", "uses": "actions/checkout@v2"},
                            {"name": "Run tests", "run": 'echo "Running tests"'},
                        ],
                    }
                },
            }

            workflow_file = temp_path / "test-workflow.yml"
            with open(workflow_file, "w", encoding="utf-8") as f:
                yaml.dump(workflow_content, f)

            # ActWrapperとExecutionTracerを初期化
            logger = ActionsLogger(verbose=True)
            tracer = ExecutionTracer(logger=logger, heartbeat_interval=1.0)

            wrapper = ActWrapper(working_directory=str(temp_path), logger=logger, execution_tracer=tracer)

            # ワークフローを実行
            result = wrapper.run_workflow(
                workflow_file="test-workflow.yml",
                job="test",
                dry_run=False,
                verbose=True,
            )

            # 実行結果を検証
            assert result["success"] is True
            assert result["returncode"] == 0
            assert "Test Workflow" in result["stdout"]

            # トレース情報を検証
            current_trace = tracer.get_current_trace()
            assert current_trace is None  # トレースは終了している

    def test_execution_stages_progression(self):
        """実行段階の進行をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 簡単なワークフローファイルを作成
            workflow_content = {
                "name": "Simple Workflow",
                "on": ["push"],
                "jobs": {
                    "simple": {
                        "runs-on": "ubuntu-latest",
                        "steps": [{"name": "Echo", "run": "echo hello"}],
                    }
                },
            }

            workflow_file = temp_path / "simple-workflow.yml"
            with open(workflow_file, "w", encoding="utf-8") as f:
                yaml.dump(workflow_content, f)

            logger = ActionsLogger(verbose=False)
            tracer = ExecutionTracer(logger=logger)

            wrapper = ActWrapper(working_directory=str(temp_path), logger=logger, execution_tracer=tracer)

            # ワークフローを実行
            result = wrapper.run_workflow(workflow_file="simple-workflow.yml")

            # 実行が成功したことを確認
            assert result["success"] is True

    def test_tracer_with_different_configurations(self):
        """異なる設定でのトレーサーをテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # ワークフローファイルを作成
            workflow_content = {
                "name": "Config Test Workflow",
                "on": ["push"],
                "jobs": {
                    "config_test": {
                        "runs-on": "ubuntu-latest",
                        "steps": [{"name": "Test", "run": "echo config test"}],
                    }
                },
            }

            workflow_file = temp_path / "config-test-workflow.yml"
            with open(workflow_file, "w", encoding="utf-8") as f:
                yaml.dump(workflow_content, f)

            logger = ActionsLogger(verbose=False)

            # カスタム設定でExecutionTracerを作成
            tracer = ExecutionTracer(
                logger=logger,
                heartbeat_interval=0.5,
                resource_monitoring_interval=0.2,
                enable_detailed_logging=True,
            )

            wrapper = ActWrapper(
                working_directory=str(temp_path),
                logger=logger,
                execution_tracer=tracer,
                config={
                    "timeouts": {"act_seconds": 30},
                    "environment": {"TEST_VAR": "test_value"},
                },
            )

            # ワークフローを実行
            result = wrapper.run_workflow(
                workflow_file="config-test-workflow.yml",
                env_vars={"CUSTOM_VAR": "custom_value"},
            )

            # 実行が成功したことを確認
            assert result["success"] is True
            assert "Config Test Workflow" in result["stdout"]

    def test_error_handling_with_tracer(self):
        """エラーハンドリングでのトレーサーをテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            logger = ActionsLogger(verbose=False)
            tracer = ExecutionTracer(logger=logger)

            wrapper = ActWrapper(working_directory=str(temp_path), logger=logger, execution_tracer=tracer)

            # 存在しないワークフローファイルで実行
            result = wrapper.run_workflow(workflow_file="nonexistent-workflow.yml")

            # エラーが適切に処理されることを確認
            assert result["success"] is False
            assert result["returncode"] == 1
            assert "ワークフローファイルが見つかりません" in result["stderr"]

    def test_heartbeat_logging_during_execution(self):
        """実行中のハートビートログをテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # ワークフローファイルを作成
            workflow_content = {
                "name": "Heartbeat Test Workflow",
                "on": ["push"],
                "jobs": {
                    "heartbeat_test": {
                        "runs-on": "ubuntu-latest",
                        "steps": [{"name": "Test", "run": "echo heartbeat test"}],
                    }
                },
            }

            workflow_file = temp_path / "heartbeat-test-workflow.yml"
            with open(workflow_file, "w", encoding="utf-8") as f:
                yaml.dump(workflow_content, f)

            logger = ActionsLogger(verbose=True)

            # 短いハートビート間隔でトレーサーを作成
            tracer = ExecutionTracer(
                logger=logger,
                heartbeat_interval=0.1,  # 0.1秒間隔
                resource_monitoring_interval=0.05,
            )

            wrapper = ActWrapper(working_directory=str(temp_path), logger=logger, execution_tracer=tracer)

            # ワークフローを実行
            result = wrapper.run_workflow(workflow_file="heartbeat-test-workflow.yml")

            # 実行が成功したことを確認
            assert result["success"] is True

    def test_multiple_workflow_executions(self):
        """複数のワークフロー実行をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            logger = ActionsLogger(verbose=False)
            tracer = ExecutionTracer(logger=logger)

            wrapper = ActWrapper(working_directory=str(temp_path), logger=logger, execution_tracer=tracer)

            # 複数のワークフローファイルを作成
            for i in range(3):
                workflow_content = {
                    "name": f"Test Workflow {i + 1}",
                    "on": ["push"],
                    "jobs": {
                        f"test_{i + 1}": {
                            "runs-on": "ubuntu-latest",
                            "steps": [{"name": f"Step {i + 1}", "run": f'echo "Test {i + 1}"'}],
                        }
                    },
                }

                workflow_file = temp_path / f"test-workflow-{i + 1}.yml"
                with open(workflow_file, "w", encoding="utf-8") as f:
                    yaml.dump(workflow_content, f)

                # ワークフローを実行
                result = wrapper.run_workflow(workflow_file=f"test-workflow-{i + 1}.yml")

                # 各実行が成功することを確認
                assert result["success"] is True
                assert f"Test Workflow {i + 1}" in result["stdout"]
