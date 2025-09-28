#!/usr/bin/env python3
"""
GitHub Actions Simulator - テンプレート検証システムのテストスイート
================================================================

このテストスイートは、テンプレート検証システムの動作を確認します。

テスト内容:
- 構文チェック機能のテスト
- 機能テスト機能のテスト
- セキュリティチェック機能のテスト
- 統合テスト
- エラーハンドリングのテスト

実行方法:
    pytest tests/test_template_validation.py -v
    python -m pytest tests/test_template_validation.py::TestTemplateValidator::test_validate_env_template -v
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module with the correct name
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_templates",
    Path(__file__).parent.parent / "scripts" / "validate-templates.py",
)
validate_templates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_templates)

TemplateValidator = validate_templates.TemplateValidator
ValidationResult = validate_templates.ValidationResult
ValidationSummary = validate_templates.ValidationSummary


class TestTemplateValidator:
    """TemplateValidatorクラスのテストケース"""

    @pytest.fixture
    def validator(self):
        """テスト用のバリデーターインスタンス"""
        return TemplateValidator(verbose=False)

    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_validator_initialization(self, validator):
        """バリデーターの初期化テスト"""
        assert validator is not None
        assert validator.verbose is False
        assert validator.logger is not None
        assert isinstance(validator.template_patterns, dict)

    def test_determine_template_type(self, validator):
        """テンプレートタイプ判定のテスト"""
        test_cases = [
            (".env.example", "env"),
            ("docker-compose.override.yml.sample", "docker_compose"),
            (".pre-commit-config.yaml.sample", "precommit"),
            (".github/workflows/ci.yml.sample", "github_workflows"),
            ("script.sh", "shell"),
            ("config.yml.sample", "yaml"),
            ("data.json.sample", "json"),
            ("unknown.txt", "unknown"),
        ]

        for file_name, expected_type in test_cases:
            file_path = Path(file_name)
            result = validator._determine_template_type(file_path)
            assert (
                result == expected_type
            ), f"Failed for {file_name}: expected {expected_type}, got {result}"

    def test_validate_yaml_syntax_valid(self, validator):
        """有効なYAML構文のテスト"""
        result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        valid_yaml = """
name: Test Workflow
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
"""

        validator._validate_yaml_syntax(valid_yaml, result)
        assert result.syntax_valid is True
        assert len(result.syntax_errors) == 0

    def test_validate_yaml_syntax_invalid(self, validator):
        """無効なYAML構文のテスト"""
        result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        invalid_yaml = """
name: Test Workflow
on:
  push:
    branches: [main
jobs:  # 閉じ括弧が不足
  test:
    runs-on: ubuntu-latest
"""

        validator._validate_yaml_syntax(invalid_yaml, result)
        assert result.syntax_valid is False
        assert len(result.syntax_errors) > 0
        assert "YAML構文エラー" in result.syntax_errors[0]

    def test_validate_json_syntax_valid(self, validator):
        """有効なJSON構文のテスト"""
        result = ValidationResult(
            file_path="test.json",
            template_type="json",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        valid_json = '{"name": "test", "version": "1.0.0"}'

        validator._validate_json_syntax(valid_json, result)
        assert result.syntax_valid is True
        assert len(result.syntax_errors) == 0

    def test_validate_json_syntax_invalid(self, validator):
        """無効なJSON構文のテスト"""
        result = ValidationResult(
            file_path="test.json",
            template_type="json",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        invalid_json = '{"name": "test", "version": 1.0.0,}'  # 末尾のカンマが不正

        validator._validate_json_syntax(invalid_json, result)
        assert result.syntax_valid is False
        assert len(result.syntax_errors) > 0
        assert "JSON構文エラー" in result.syntax_errors[0]

    def test_validate_env_syntax_valid(self, validator):
        """有効な環境変数ファイル構文のテスト"""
        result = ValidationResult(
            file_path=".env.example",
            template_type="env",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        valid_env = """
# GitHub Actions Simulator 環境変数
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
USER_ID=1000
GROUP_ID=1000
LOG_LEVEL=info
"""

        validator._validate_env_syntax(valid_env, result)
        assert result.syntax_valid is True
        assert len(result.syntax_errors) == 0

    def test_validate_env_syntax_invalid(self, validator):
        """無効な環境変数ファイル構文のテスト"""
        result = ValidationResult(
            file_path=".env.example",
            template_type="env",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        invalid_env = """
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
INVALID_LINE_WITHOUT_EQUALS
USER_ID=1000
"""

        validator._validate_env_syntax(invalid_env, result)
        assert result.syntax_valid is False
        assert len(result.syntax_errors) > 0
        assert "環境変数の形式が正しくありません" in result.syntax_errors[0]

    def test_validate_security_secrets_detection(self, validator):
        """セキュリティチェック - 秘密情報検出のテスト"""
        result = ValidationResult(
            file_path="test.env",
            template_type="env",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        # 実際の秘密情報を含むコンテンツ
        content_with_secrets = """
PASSWORD=realpassword123
TOKEN=ghp_1234567890abcdef1234567890abcdef12345678
API_KEY=sk-1234567890abcdef1234567890abcdef
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content_with_secrets)
            temp_file = Path(f.name)

        try:
            validator._validate_security(temp_file, "env", result)
            assert len(result.security_issues) > 0
            # 実際のトークンやパスワードが検出されることを確認
            security_text = " ".join(result.security_issues).lower()
            assert any(
                keyword in security_text
                for keyword in ["パスワード", "トークン", "api"]
            )
        finally:
            temp_file.unlink()

    def test_validate_security_safe_placeholders(self, validator):
        """セキュリティチェック - 安全なプレースホルダーのテスト"""
        result = ValidationResult(
            file_path="test.env",
            template_type="env",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        # プレースホルダーを含む安全なコンテンツ
        content_with_placeholders = """
PASSWORD=your_password_here
TOKEN=your_github_token_here
API_KEY=example_api_key
SECRET=dummy_secret_value
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content_with_placeholders)
            temp_file = Path(f.name)

        try:
            validator._validate_security(temp_file, "env", result)
            # プレースホルダーは安全として扱われるべき
            assert len(result.security_issues) == 0
        finally:
            temp_file.unlink()

    def test_validate_template_complete(self, validator, temp_dir):
        """完全なテンプレート検証のテスト"""
        # テスト用の有効なYAMLテンプレートを作成
        yaml_content = """
name: Test Workflow
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v5
"""

        yaml_file = temp_dir / "test-workflow.yml.sample"
        yaml_file.write_text(yaml_content)

        result = validator.validate_template(yaml_file, "github_workflows")

        assert result.file_path == str(yaml_file)
        assert result.template_type == "github_workflows"
        assert result.syntax_valid is True
        assert len(result.syntax_errors) == 0
        assert result.execution_time > 0

    def test_find_template_files(self, validator):
        """テンプレートファイル検索のテスト"""
        with (
            patch("pathlib.Path.cwd") as mock_cwd,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.glob") as mock_glob,
        ):
            # モックの設定
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = True
            mock_glob.return_value = []

            template_files = validator.find_template_files()

            # 基本的な構造が返されることを確認
            assert isinstance(template_files, dict)

    @patch("subprocess.run")
    def test_validate_shell_syntax_with_shellcheck(self, mock_run, validator, temp_dir):
        """ShellCheck使用時のShell構文チェックのテスト"""
        # ShellCheckが利用可能な場合のモック
        with patch("shutil.which", return_value="/usr/bin/shellcheck"):
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")

            result = ValidationResult(
                file_path="test.sh",
                template_type="shell",
                syntax_valid=True,
                syntax_errors=[],
                functionality_valid=True,
                functionality_errors=[],
                security_issues=[],
                warnings=[],
                execution_time=0.0,
            )

            shell_file = temp_dir / "test.sh"
            shell_file.write_text("#!/bin/bash\necho 'Hello World'")

            validator._validate_shell_syntax(shell_file, result)

            assert result.syntax_valid is True
            assert len(result.syntax_errors) == 0
            mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_validate_shell_syntax_with_errors(self, mock_run, validator, temp_dir):
        """ShellCheckでエラーが検出される場合のテスト"""
        with patch("shutil.which", return_value="/usr/bin/shellcheck"):
            # ShellCheckがエラーを返すモック
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout='[{"line": 2, "level": "error", "message": "Syntax error"}]',
                stderr="",
            )

            result = ValidationResult(
                file_path="test.sh",
                template_type="shell",
                syntax_valid=True,
                syntax_errors=[],
                functionality_valid=True,
                functionality_errors=[],
                security_issues=[],
                warnings=[],
                execution_time=0.0,
            )

            shell_file = temp_dir / "test.sh"
            shell_file.write_text("#!/bin/bash\necho 'Hello World")  # クォート不足

            validator._validate_shell_syntax(shell_file, result)

            assert result.syntax_valid is False
            assert len(result.syntax_errors) > 0
            assert "ShellCheck エラー" in result.syntax_errors[0]

    def test_validate_all_templates_integration(self, validator):
        """統合テスト - 全テンプレート検証"""
        with (
            patch.object(validator, "find_template_files") as mock_find,
            patch.object(validator, "validate_template") as mock_validate,
        ):
            # モックの設定
            mock_find.return_value = {
                "yaml": [Path("test1.yml.sample")],
                "env": [Path(".env.example")],
            }

            mock_validate.side_effect = [
                ValidationResult(
                    file_path="test1.yml.sample",
                    template_type="yaml",
                    syntax_valid=True,
                    syntax_errors=[],
                    functionality_valid=True,
                    functionality_errors=[],
                    security_issues=[],
                    warnings=[],
                    execution_time=0.1,
                ),
                ValidationResult(
                    file_path=".env.example",
                    template_type="env",
                    syntax_valid=True,
                    syntax_errors=[],
                    functionality_valid=True,
                    functionality_errors=[],
                    security_issues=[],
                    warnings=["Minor warning"],
                    execution_time=0.05,
                ),
            ]

            summary = validator.validate_all_templates()

            assert isinstance(summary, ValidationSummary)
            assert summary.total_templates == 2
            assert summary.valid_templates == 2
            assert summary.invalid_templates == 0
            assert summary.templates_with_warnings == 1
            assert summary.success_rate() == 100.0

    def test_generate_report_text_format(self, validator):
        """テキスト形式レポート生成のテスト"""
        summary = ValidationSummary(
            total_templates=2,
            valid_templates=1,
            invalid_templates=1,
            templates_with_warnings=1,
            execution_time=1.5,
            results=[
                ValidationResult(
                    file_path="valid.yml",
                    template_type="yaml",
                    syntax_valid=True,
                    syntax_errors=[],
                    functionality_valid=True,
                    functionality_errors=[],
                    security_issues=[],
                    warnings=["Minor warning"],
                    execution_time=0.5,
                ),
                ValidationResult(
                    file_path="invalid.yml",
                    template_type="yaml",
                    syntax_valid=False,
                    syntax_errors=["Syntax error"],
                    functionality_valid=False,
                    functionality_errors=["Function error"],
                    security_issues=["Security issue"],
                    warnings=[],
                    execution_time=1.0,
                ),
            ],
        )

        report = validator.generate_report(summary, "text")

        assert "テンプレート検証レポート" in report
        assert "成功率: 50.0%" in report
        assert "総テンプレート数: 2" in report
        assert "有効なテンプレート: 1" in report
        assert "無効なテンプレート: 1" in report
        assert "valid.yml" in report
        assert "invalid.yml" in report
        assert "構文エラー:" in report
        assert "機能エラー:" in report
        assert "セキュリティ問題:" in report

    def test_generate_report_json_format(self, validator):
        """JSON形式レポート生成のテスト"""
        summary = ValidationSummary(
            total_templates=1,
            valid_templates=1,
            invalid_templates=0,
            templates_with_warnings=0,
            execution_time=0.5,
            results=[
                ValidationResult(
                    file_path="test.yml",
                    template_type="yaml",
                    syntax_valid=True,
                    syntax_errors=[],
                    functionality_valid=True,
                    functionality_errors=[],
                    security_issues=[],
                    warnings=[],
                    execution_time=0.5,
                )
            ],
        )

        report = validator.generate_report(summary, "json")

        # JSONとしてパース可能であることを確認
        parsed_report = json.loads(report)
        assert parsed_report["total_templates"] == 1
        assert parsed_report["valid_templates"] == 1
        assert parsed_report["invalid_templates"] == 0
        assert len(parsed_report["results"]) == 1
        assert parsed_report["results"][0]["file_path"] == "test.yml"

    def test_validation_result_is_valid(self):
        """ValidationResult.is_valid()メソッドのテスト"""
        # 有効なケース
        valid_result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.1,
        )
        assert valid_result.is_valid() is True

        # 構文エラーがあるケース
        syntax_error_result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=False,
            syntax_errors=["Syntax error"],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.1,
        )
        assert syntax_error_result.is_valid() is False

        # 機能エラーがあるケース
        function_error_result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=False,
            functionality_errors=["Function error"],
            security_issues=[],
            warnings=[],
            execution_time=0.1,
        )
        assert function_error_result.is_valid() is False

        # セキュリティ問題があるケース
        security_issue_result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=["Security issue"],
            warnings=[],
            execution_time=0.1,
        )
        assert security_issue_result.is_valid() is False

        # 警告のみのケース（有効とみなされる）
        warning_only_result = ValidationResult(
            file_path="test.yml",
            template_type="yaml",
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=["Warning"],
            execution_time=0.1,
        )
        assert warning_only_result.is_valid() is True

    def test_validation_summary_success_rate(self):
        """ValidationSummary.success_rate()メソッドのテスト"""
        # 100%成功のケース
        summary_100 = ValidationSummary(
            total_templates=5,
            valid_templates=5,
            invalid_templates=0,
            templates_with_warnings=2,
            execution_time=1.0,
            results=[],
        )
        assert summary_100.success_rate() == 100.0

        # 50%成功のケース
        summary_50 = ValidationSummary(
            total_templates=4,
            valid_templates=2,
            invalid_templates=2,
            templates_with_warnings=1,
            execution_time=1.0,
            results=[],
        )
        assert summary_50.success_rate() == 50.0

        # 0%成功のケース
        summary_0 = ValidationSummary(
            total_templates=3,
            valid_templates=0,
            invalid_templates=3,
            templates_with_warnings=0,
            execution_time=1.0,
            results=[],
        )
        assert summary_0.success_rate() == 0.0

        # テンプレートが0個のケース
        summary_empty = ValidationSummary(
            total_templates=0,
            valid_templates=0,
            invalid_templates=0,
            templates_with_warnings=0,
            execution_time=0.0,
            results=[],
        )
        assert summary_empty.success_rate() == 100.0


class TestTemplateValidationIntegration:
    """統合テストクラス"""

    def test_real_env_example_validation(self):
        """実際の.env.exampleファイルの検証テスト"""
        validator = TemplateValidator(verbose=False)
        env_example_path = Path(".env.example")

        if env_example_path.exists():
            result = validator.validate_template(env_example_path, "env")

            # 基本的な検証が通ることを確認
            assert result.file_path == str(env_example_path)
            assert result.template_type == "env"
            # 構文エラーがないことを確認（警告はあっても良い）
            assert result.syntax_valid is True
            # セキュリティ問題がないことを確認（プレースホルダーのため）
            assert len(result.security_issues) == 0

    def test_real_docker_compose_sample_validation(self):
        """実際のdocker-compose.override.yml.sampleファイルの検証テスト"""
        validator = TemplateValidator(verbose=False)
        docker_compose_path = Path("docker-compose.override.yml.sample")

        if docker_compose_path.exists():
            result = validator.validate_template(docker_compose_path, "docker_compose")

            # 基本的な検証が通ることを確認
            assert result.file_path == str(docker_compose_path)
            assert result.template_type == "docker_compose"
            # 構文エラーがないことを確認
            assert result.syntax_valid is True

    def test_real_precommit_sample_validation(self):
        """実際の.pre-commit-config.yaml.sampleファイルの検証テスト"""
        validator = TemplateValidator(verbose=False)
        precommit_path = Path(".pre-commit-config.yaml.sample")

        if precommit_path.exists():
            result = validator.validate_template(precommit_path, "precommit")

            # 基本的な検証が通ることを確認
            assert result.file_path == str(precommit_path)
            assert result.template_type == "precommit"
            # 構文エラーがないことを確認
            assert result.syntax_valid is True

    def test_real_github_workflow_samples_validation(self):
        """実際のGitHub Workflowサンプルファイルの検証テスト"""
        validator = TemplateValidator(verbose=False)
        workflow_dir = Path(".github/workflows")

        if workflow_dir.exists():
            sample_files = list(workflow_dir.glob("*.yml.sample"))

            for sample_file in sample_files:
                result = validator.validate_template(sample_file, "github_workflows")

                # 基本的な検証が通ることを確認
                assert result.file_path == str(sample_file)
                assert result.template_type == "github_workflows"
                # 構文エラーがないことを確認
                assert (
                    result.syntax_valid is True
                ), f"Syntax error in {sample_file}: {result.syntax_errors}"


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])
