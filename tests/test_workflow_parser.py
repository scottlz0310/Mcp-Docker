"""
GitHub Actions Simulator - WorkflowParser テスト
ワークフロー解析機能のテストケース
"""

import tempfile
import yaml
from pathlib import Path

import pytest

from services.actions.workflow_parser import WorkflowParser, WorkflowParseError


class TestWorkflowParser:
    """WorkflowParserのテストクラス"""

    @pytest.fixture
    def parser(self):
        """WorkflowParserインスタンスを作成"""
        return WorkflowParser()

    @pytest.fixture
    def valid_workflow_data(self):
        """有効なワークフローデータ"""
        return {
            "name": "Test Workflow",
            "on": ["push", "pull_request"],
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"name": "Checkout", "uses": "actions/checkout@v3"},
                        {"name": "Test", "run": "echo 'Hello World'"},
                    ],
                }
            },
        }

    @pytest.fixture
    def temp_workflow_file(self, valid_workflow_data):
        """一時的なワークフローファイルを作成"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(valid_workflow_data, f)
            yield Path(f.name)
        Path(f.name).unlink()

    def test_init(self, parser):
        """初期化テスト"""
        assert parser.required_fields == ["name", "on", "jobs"]
        assert "push" in parser.supported_events
        assert "pull_request" in parser.supported_events
        assert "schedule" in parser.supported_events
        assert "workflow_dispatch" in parser.supported_events

    def test_parse_file_success(self, parser, temp_workflow_file):
        """ファイル解析成功テスト"""
        result = parser.parse_file(temp_workflow_file)

        assert result["name"] == "Test Workflow"
        assert "push" in result["on"]
        assert "pull_request" in result["on"]
        assert "test" in result["jobs"]
        assert result["jobs"]["test"]["runs-on"] == "ubuntu-latest"

    def test_parse_file_not_found(self, parser):
        """ファイルが見つからない場合のテスト"""
        non_existent_file = Path("/non/existent/workflow.yml")

        with pytest.raises(WorkflowParseError) as exc_info:
            parser.parse_file(non_existent_file)

        assert "ファイルが見つかりません" in str(exc_info.value)

    def test_parse_file_invalid_yaml(self, parser):
        """無効なYAMLファイルのテスト"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = Path(f.name)

        try:
            with pytest.raises(WorkflowParseError) as exc_info:
                parser.parse_file(invalid_file)

            assert "YAML解析エラー" in str(exc_info.value)
        finally:
            invalid_file.unlink()

    def test_parse_file_missing_required_fields(self, parser):
        """必須フィールドが不足している場合のテスト"""
        incomplete_data = {"name": "Test Workflow"}  # "on"と"jobs"が不足

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(incomplete_data, f)
            incomplete_file = Path(f.name)

        try:
            with pytest.raises(WorkflowParseError) as exc_info:
                parser.parse_file(incomplete_file)

            assert "必須フィールド" in str(exc_info.value)
        finally:
            incomplete_file.unlink()

    def test_validate_basic_structure_success(self, parser, valid_workflow_data):
        """基本構造検証成功テスト"""
        # 検証が成功する場合は例外が発生しない
        parser._validate_basic_structure(valid_workflow_data)

    def test_validate_basic_structure_missing_name(self, parser):
        """名前フィールドが不足している場合のテスト"""
        invalid_data = {
            "on": ["push"],
            "jobs": {
                "test": {"runs-on": "ubuntu-latest", "steps": [{"run": "echo test"}]}
            },
        }

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_basic_structure(invalid_data)

        assert "name" in str(exc_info.value)

    def test_validate_basic_structure_missing_on(self, parser):
        """onフィールドが不足している場合のテスト"""
        invalid_data = {
            "name": "Test",
            "jobs": {
                "test": {"runs-on": "ubuntu-latest", "steps": [{"run": "echo test"}]}
            },
        }

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_basic_structure(invalid_data)

        assert "on" in str(exc_info.value)

    def test_validate_basic_structure_missing_jobs(self, parser):
        """jobsフィールドが不足している場合のテスト"""
        invalid_data = {"name": "Test", "on": ["push"]}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_basic_structure(invalid_data)

        assert "jobs" in str(exc_info.value)

    def test_validate_basic_structure_empty_jobs(self, parser):
        """jobsが空の場合のテスト"""
        invalid_data = {"name": "Test", "on": ["push"], "jobs": {}}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_basic_structure(invalid_data)

        assert "ジョブが必要です" in str(exc_info.value)

    def test_strict_validate_unsupported_event(self, parser):
        """サポートされていないイベントの場合のテスト"""
        invalid_data = {
            "name": "Test",
            "on": ["unsupported_event"],
            "jobs": {
                "test": {"runs-on": "ubuntu-latest", "steps": [{"run": "echo test"}]}
            },
        }

        with pytest.raises(WorkflowParseError) as exc_info:
            parser.strict_validate(invalid_data)

        assert "サポートされていないイベント" in str(exc_info.value)

    def test_normalize_needs_string(self, parser):
        """needs正規化（文字列）テスト"""
        result = parser._normalize_needs("build")
        assert result == ["build"]

    def test_normalize_needs_list(self, parser):
        """needs正規化（リスト）テスト"""
        result = parser._normalize_needs(["build", "test"])
        assert result == ["build", "test"]

    def test_normalize_needs_empty(self, parser):
        """needs正規化（空）テスト"""
        assert parser._normalize_needs(None) == []
        assert parser._normalize_needs([]) == []
        assert parser._normalize_needs("") == []

    def test_validate_job_success(self, parser):
        """ジョブ検証成功テスト"""
        valid_job = {
            "runs-on": "ubuntu-latest",
            "steps": [{"name": "Test", "run": "echo test"}],
        }

        # 例外が発生しないことを確認
        parser._validate_job("test_job", valid_job)

    def test_validate_job_missing_runs_on(self, parser):
        """runs-onが不足している場合のテスト"""
        invalid_job = {"steps": [{"name": "Test", "run": "echo test"}]}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_job("test_job", invalid_job)

        assert "runs-on" in str(exc_info.value)

    def test_validate_job_missing_steps(self, parser):
        """stepsが不足している場合のテスト"""
        invalid_job = {"runs-on": "ubuntu-latest"}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_job("test_job", invalid_job)

        assert "ステップがありません" in str(exc_info.value)

    def test_validate_job_empty_steps(self, parser):
        """stepsが空の場合のテスト"""
        invalid_job = {"runs-on": "ubuntu-latest", "steps": []}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_job("test_job", invalid_job)

        assert "ステップがありません" in str(exc_info.value)

    def test_validate_step_run_step(self, parser):
        """runステップ検証テスト"""
        valid_step = {"name": "Test", "run": "echo test"}

        # 例外が発生しないことを確認
        parser._validate_step("test_job", 0, valid_step)

    def test_validate_step_uses_step(self, parser):
        """usesステップ検証テスト"""
        valid_step = {"name": "Checkout", "uses": "actions/checkout@v3"}

        # 例外が発生しないことを確認
        parser._validate_step("test_job", 0, valid_step)

    def test_validate_step_missing_action(self, parser):
        """アクションが不足している場合のテスト"""
        invalid_step = {"name": "Invalid Step"}

        with pytest.raises(WorkflowParseError) as exc_info:
            parser._validate_step("test_job", 0, invalid_step)

        assert "run" in str(exc_info.value) and "uses" in str(exc_info.value)

    def test_get_jobs_summary(self, parser, valid_workflow_data):
        """ジョブサマリー取得テスト"""
        summary = parser.get_jobs_summary(valid_workflow_data)

        assert len(summary) == 1
        assert summary[0]["id"] == "test"
        assert summary[0]["runs_on"] == "ubuntu-latest"
        assert summary[0]["steps_count"] == 2

    def test_matrix_expansion(self, parser):
        """マトリックス展開テスト"""
        matrix_workflow = {
            "name": "Matrix Workflow",
            "on": ["push"],
            "jobs": {
                "build": {
                    "runs-on": "ubuntu-latest",
                    "strategy": {"matrix": {"node-version": ["16", "18", "20"]}},
                    "steps": [{"name": "Test", "run": "echo test"}],
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(matrix_workflow, f)
            matrix_file = Path(f.name)

        try:
            result = parser.parse_file(matrix_file)

            # マトリックスが展開されることを確認
            jobs = result["jobs"]
            assert len(jobs) == 3  # 3つのnode-versionに展開される

            # 展開されたジョブ名を確認
            job_ids = list(jobs.keys())
            assert any("node-version-16" in job_id for job_id in job_ids)
            assert any("node-version-18" in job_id for job_id in job_ids)
            assert any("node-version-20" in job_id for job_id in job_ids)

        finally:
            matrix_file.unlink()

    def test_sanitize_identifier(self, parser):
        """識別子サニタイズテスト"""
        assert parser._sanitize_identifier("node-18") == "node-18"
        assert parser._sanitize_identifier("node.18") == "node-18"
        assert parser._sanitize_identifier("node@18") == "node-18"
        assert parser._sanitize_identifier("18.x") == "18-x"

    def test_stringify_matrix_value(self, parser):
        """マトリックス値文字列化テスト"""
        assert parser._stringify_matrix_value("18") == "'18'"
        assert parser._stringify_matrix_value(18) == "18"
        assert parser._stringify_matrix_value(True) == "True"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
