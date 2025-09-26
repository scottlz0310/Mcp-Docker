#!/usr/bin/env python3
"""
GitHub Actions Simulator - Unit Tests
=====================================

GitHub Actions Simulatorサービスの単体テストです。

テスト対象:
    - WorkflowParser: YAML解析機能
    - WorkflowSimulator: シミュレーション機能
    - ActionsLogger: ロギング機能
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# テスト対象のインポート
from services.actions.workflow_parser import WorkflowParser, WorkflowParseError
from services.actions.simulator import WorkflowSimulator, SimulationError
from services.actions.logger import ActionsLogger


class TestWorkflowParser:
    """WorkflowParser のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.parser = WorkflowParser()

    def test_parse_simple_workflow(self):
        """シンプルなワークフローの解析テスト"""
        workflow_content = """name: Test Workflow
"on": [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hello World"
"""

        # 一時ファイルを作成してテスト
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            workflow_data = self.parser.parse_file(temp_path)

            # アサーション
            assert workflow_data['name'] == 'Test Workflow'
            assert 'push' in workflow_data['on']
            assert 'test' in workflow_data['jobs']
            assert workflow_data['jobs']['test']['runs-on'] == 'ubuntu-latest'
            assert len(workflow_data['jobs']['test']['steps']) == 1
        finally:
            # クリーンアップ
            temp_path.unlink()

    def test_parse_complex_workflow(self):
        """複雑なワークフローの解析テスト"""
        workflow_content = """
name: Complex CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Lint code
        run: echo "Linting"

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v5
      - name: Run tests
        run: echo "Testing"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            workflow_data = self.parser.parse_file(temp_path)

            # アサーション
            assert workflow_data['name'] == 'Complex CI'
            assert len(workflow_data['jobs']) == 2
            assert 'lint' in workflow_data['jobs']
            assert 'test' in workflow_data['jobs']
            assert workflow_data['jobs']['test']['needs'] == 'lint'
        finally:
            temp_path.unlink()

    def test_parse_invalid_yaml(self):
        """無効なYAMLファイルの解析エラーテスト"""
        invalid_content = """name: Invalid
"on": [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
    invalid_indent_here
    another_problem: ]
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises((WorkflowParseError, yaml.YAMLError)):
                self.parser.parse_file(temp_path)
        finally:
            # クリーンアップ
            temp_path.unlink()

    def test_parse_missing_required_fields(self):
        """必須フィールド不足の解析エラーテスト"""
        incomplete_content = """
name: Incomplete
# 'on' フィールドが欠如
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(incomplete_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(WorkflowParseError):
                self.parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self):
        """存在しないファイルの解析エラーテスト"""
        nonexistent_path = Path("/tmp/nonexistent_workflow.yml")

        with pytest.raises(WorkflowParseError):
            self.parser.parse_file(nonexistent_path)


class TestWorkflowSimulator:
    """WorkflowSimulator のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.simulator = WorkflowSimulator()

    def test_simulator_initialization(self):
        """シミュレーターの初期化テスト"""
        assert self.simulator.env_vars is not None
        assert 'GITHUB_WORKSPACE' in self.simulator.env_vars
        assert 'GITHUB_REPOSITORY' in self.simulator.env_vars

    def test_dry_run_simple_workflow(self):
        """シンプルワークフローのドライランテスト"""
        workflow_data = {
            'name': 'Test Workflow',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'run': 'echo "Hello World"'}
                    ]
                }
            }
        }

        result = self.simulator.dry_run(workflow_data)
        assert result == 0

    def test_dry_run_specific_job(self):
        """特定ジョブのドライランテスト"""
        workflow_data = {
            'name': 'Multi Job Workflow',
            'jobs': {
                'job1': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo "Job 1"'}]
                },
                'job2': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo "Job 2"'}]
                }
            }
        }

        result = self.simulator.dry_run(workflow_data, job_name='job1')
        assert result == 0

    def test_dry_run_nonexistent_job(self):
        """存在しないジョブのドライランエラーテスト"""
        workflow_data = {
            'name': 'Test Workflow',
            'jobs': {
                'existing_job': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo "test"'}]
                }
            }
        }

        result = self.simulator.dry_run(workflow_data, job_name='nonexistent_job')
        assert result == 1

    def test_run_respects_needs_order(self):
        """needs 依存関係に基づきジョブが正しい順序で実行される"""
        workflow_data = {
            'name': 'Needs Workflow',
            'jobs': {
                'lint': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo lint'}],
                },
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'needs': 'lint',
                    'steps': [{'run': 'echo test'}],
                },
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'needs': ['test'],
                    'steps': [{'run': 'echo deploy'}],
                },
            },
        }

        execution_order = []

        def fake_run(
            job_id: str,
            job_data: Dict[str, Any],
            *_args: Any,
        ) -> int:
            execution_order.append(job_id)
            return 0

        with patch.object(self.simulator, '_run_job', side_effect=fake_run):
            result = self.simulator.run(workflow_data)

        assert result == 0
        assert set(execution_order) == {'lint', 'test', 'deploy'}
        assert execution_order.index('lint') < execution_order.index('test')
        assert execution_order.index('test') < execution_order.index('deploy')

    def test_run_skips_failed_dependencies(self):
        """依存ジョブが失敗した場合に後続ジョブがスキップされる"""
        workflow_data = {
            'name': 'Failure Workflow',
            'jobs': {
                'lint': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo lint'}],
                },
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'needs': 'lint',
                    'steps': [{'run': 'echo test'}],
                },
                'docs': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo docs'}],
                },
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'needs': ['test'],
                    'steps': [{'run': 'echo deploy'}],
                },
            },
        }

        execution_order = []

        def fake_run(
            job_id: str,
            job_data: Dict[str, Any],
            *_args: Any,
        ) -> int:
            execution_order.append(job_id)
            return 1 if job_id == 'lint' else 0

        with patch.object(self.simulator, '_run_job', side_effect=fake_run):
            result = self.simulator.run(workflow_data)

        assert result == 1
        assert set(execution_order) == {'lint', 'docs'}
        assert 'test' not in execution_order
        assert 'deploy' not in execution_order

    def test_job_if_helpers(self):
        """`if:` 条件で startsWith / contains ヘルパーが利用できる"""
        workflow_data = {
            'name': 'Conditional Jobs',
            'jobs': {
                'should_run': {
                    'if': "startsWith(github.ref, 'refs/heads/')",
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo run'}],
                },
                'should_skip': {
                    'if': "contains(env.TARGET, 'ubuntu')",
                    'runs-on': 'ubuntu-latest',
                    'env': {'TARGET': 'windows-latest'},
                    'steps': [{'run': 'echo skip'}],
                },
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            return_value=0,
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        commands = [call.args[0] for call in mock_exec.call_args_list]
        assert commands.count('echo run') == 1
        assert 'echo skip' not in commands

    def test_step_if_uses_string_functions(self):
        """ステップ条件で contains / endsWith ヘルパーが評価される"""
        workflow_data = {
            'name': 'Step Conditions',
            'jobs': {
                'verify': {
                    'runs-on': 'ubuntu-latest',
                    'env': {'TARGET': 'ubuntu-latest', 'VERSION': '1.0'},
                    'steps': [
                        {'run': 'echo first'},
                        {
                            'name': 'Only on Ubuntu',
                            'if': "contains(env.TARGET, 'ubuntu')",
                            'run': 'echo ubuntu',
                        },
                        {
                            'name': 'Version Gate',
                            'if': "endsWith(env.VERSION, '.0')",
                            'run': 'echo version',
                        },
                    ],
                },
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            return_value=0,
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        commands = [call.args[0] for call in mock_exec.call_args_list]
        assert commands.count('echo ubuntu') == 1
        assert commands.count('echo version') == 1

    def test_run_missing_dependency(self):
        """存在しない依存ジョブが指定された場合にエラーを返す"""
        workflow_data = {
            'name': 'Missing Dependency Workflow',
            'jobs': {
                'lint': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo lint'}],
                },
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'needs': 'build',
                    'steps': [{'run': 'echo test'}],
                },
            },
        }

        result = self.simulator.run(workflow_data)

        assert result == 1

    def test_run_detects_dependency_cycles(self):
        """循環依存がある場合にエラーを返す"""
        workflow_data = {
            'name': 'Cyclic Workflow',
            'jobs': {
                'job1': {
                    'runs-on': 'ubuntu-latest',
                    'needs': 'job2',
                    'steps': [{'run': 'echo job1'}],
                },
                'job2': {
                    'runs-on': 'ubuntu-latest',
                    'needs': 'job1',
                    'steps': [{'run': 'echo job2'}],
                },
            },
        }

        result = self.simulator.run(workflow_data)

        assert result == 1

    def test_step_condition_skip(self):
        """if 条件によりステップがスキップされる"""
        workflow_data = {
            'name': 'Conditional Workflow',
            'jobs': {
                'conditional': {
                    'runs-on': 'ubuntu-latest',
                    'env': {'RUN_FIRST': 'false'},
                    'steps': [
                        {
                            'name': 'First step',
                            'run': 'echo first',
                            'if': "${{ env.RUN_FIRST == 'true' }}",
                        },
                        {
                            'name': 'Second step',
                            'run': 'echo second',
                        },
                    ],
                }
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            return_value=0,
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        assert mock_exec.call_count == 1
        executed_command = mock_exec.call_args[0][0]
        assert executed_command == 'echo second'

    def test_job_condition_skip(self):
        """ジョブ if 条件が満たされない場合にジョブがスキップされる"""
        workflow_data = {
            'name': 'Job Conditional Workflow',
            'jobs': {
                'job': {
                    'runs-on': 'ubuntu-latest',
                    'if': "${{ contains(github.ref, 'feature/') }}",
                    'steps': [
                        {'run': 'echo should not run'},
                    ],
                }
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            return_value=0,
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        mock_exec.assert_not_called()

    def test_continue_on_error_allows_job_to_succeed(self, tmp_path):
        """continue-on-error が true の場合にジョブ全体は成功するが failure() は真になる"""
        self.simulator.workspace_path = tmp_path
        self.simulator.env_vars['GITHUB_WORKSPACE'] = str(tmp_path)

        continue_expr = "${{ env.ALLOW_FAILURE == '1' }}"

        workflow_data = {
            'name': 'Continue On Error Workflow',
            'jobs': {
                'conditional': {
                    'runs-on': 'ubuntu-latest',
                    'env': {'ALLOW_FAILURE': '1'},
                    'steps': [
                        {
                            'id': 'allow_fail',
                            'name': 'Allow failure',
                            'run': 'echo fail',
                            'continue-on-error': continue_expr,
                        },
                        {
                            'name': 'Execute on failure',
                            'if': 'failure()',
                            'run': 'echo fallback',
                        },
                        {
                            'name': 'Success gated step',
                            'if': 'success()',
                            'run': 'echo success',
                        },
                    ],
                },
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            side_effect=[1, 0],
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        executed = [call.args[0] for call in mock_exec.call_args_list]
        assert executed == ['echo fail', 'echo fallback']

    def test_extended_expression_helpers(self, tmp_path):
        """format/join/fromJSON/toJSON/hashFiles ヘルパーを評価できる"""
        self.simulator.workspace_path = tmp_path
        self.simulator.env_vars['GITHUB_WORKSPACE'] = str(tmp_path)

        sample_file = tmp_path / 'sample.txt'
        sample_file.write_text('hello world', encoding='utf-8')

        format_join_expr = (
            "${{ format('Hello {0}', 'World') == 'Hello World' "
            "and join(fromJSON('[\"a\",\"b\"]'), ',') == 'a,b' }}"
        )
        hash_expr = "${{ hashFiles('*.txt') != '' }}"
        to_json_expr = "${{ contains(toJSON(github), 'local/test') }}"

        workflow_data = {
            'name': 'Expression Helpers Workflow',
            'jobs': {
                'helpers': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'run': 'echo base'},
                        {
                            'name': 'Format and join',
                            'if': format_join_expr,
                            'run': 'echo format',
                        },
                        {
                            'name': 'Hash files',
                            'if': hash_expr,
                            'run': 'echo hashed',
                        },
                        {
                            'name': 'To JSON',
                            'if': to_json_expr,
                            'run': 'echo json',
                        },
                    ],
                },
            },
        }

        with patch.object(
            self.simulator,
            '_execute_command',
            return_value=0,
        ) as mock_exec:
            result = self.simulator.run(workflow_data)

        assert result == 0
        commands = [call.args[0] for call in mock_exec.call_args_list]
        assert commands == [
            'echo base',
            'echo format',
            'echo hashed',
            'echo json',
        ]

    def test_load_env_file(self):
        """環境変数ファイル読み込みテスト"""
        env_content = """
# Test environment variables
TEST_VAR1=value1
TEST_VAR2=value2
# Comment line
EMPTY_LINE_BELOW=

TEST_VAR3=value3
"""

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.env',
            delete=False,
        ) as f:
            f.write(env_content)
            temp_path = Path(f.name)

        try:
            self.simulator.load_env_file(temp_path)

            # アサーション
            assert self.simulator.env_vars['TEST_VAR1'] == 'value1'
            assert self.simulator.env_vars['TEST_VAR2'] == 'value2'
            assert self.simulator.env_vars['TEST_VAR3'] == 'value3'
        finally:
            temp_path.unlink()

    def test_load_nonexistent_env_file(self):
        """存在しない環境変数ファイルの読み込みエラーテスト"""
        nonexistent_path = Path("/tmp/nonexistent.env")

        with pytest.raises(SimulationError):
            self.simulator.load_env_file(nonexistent_path)


class TestActionsLogger:
    """ActionsLogger のテストクラス"""

    def test_logger_initialization(self):
        """ロガーの初期化テスト"""
        logger = ActionsLogger()
        assert logger is not None

        verbose_logger = ActionsLogger(verbose=True)
        assert verbose_logger is not None

    @patch('services.actions.logger.logging')
    def test_logger_methods(self, mock_logging: MagicMock):
        """ロガーメソッドのテスト"""
        logger = ActionsLogger()

        # ログメソッドの呼び出しテスト
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # loggingモジュールが適切に呼び出されることを確認
        assert mock_logging.getLogger.called


class TestIntegration:
    """統合テストクラス"""

    def test_full_workflow_parse_and_simulate(self):
        """ワークフロー解析からシミュレーション実行までの統合テスト"""
        workflow_content = """
name: Integration Test Workflow
on: [push]
jobs:
  integration_test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Run integration test
        run: echo "Integration test passed"
"""

        # ワークフロー解析
        parser = WorkflowParser()
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False,
        ) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            workflow_data = parser.parse_file(temp_path)

            # シミュレーション実行
            simulator = WorkflowSimulator()
            result = simulator.dry_run(workflow_data)

            # アサーション
            assert result == 0
            assert workflow_data['name'] == 'Integration Test Workflow'
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    # テスト実行用のエントリーポイント
    pytest.main([__file__, "-v"])
