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
from unittest.mock import patch

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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
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
    def test_logger_methods(self, mock_logging):
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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
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
