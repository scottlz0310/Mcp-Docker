#!/usr/bin/env python3
"""
GitHub Actions Simulator - テンプレート動作検証システム
=======================================================

このスクリプトは全テンプレートファイルの構文チェックと動作確認を行います。

機能:
- 構文チェック (YAML, JSON, Shell, Docker)
- テンプレート変数の検証
- 実際の動作確認テスト
- CI/CD パイプラインでの自動検証

使用方法:
    python scripts/validate-templates.py [options]

オプション:
    --check-only    構文チェックのみ実行
    --test-only     動作テストのみ実行
    --verbose       詳細ログを出力
    --format json   結果をJSON形式で出力
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List
import shutil
import re
from datetime import datetime


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""

    file_path: str
    template_type: str
    syntax_valid: bool
    syntax_errors: List[str]
    functionality_valid: bool
    functionality_errors: List[str]
    security_issues: List[str]
    warnings: List[str]
    execution_time: float

    def is_valid(self) -> bool:
        """テンプレートが有効かどうかを判定"""
        return self.syntax_valid and self.functionality_valid and not self.security_issues


@dataclass
class ValidationSummary:
    """検証サマリーを格納するデータクラス"""

    total_templates: int
    valid_templates: int
    invalid_templates: int
    templates_with_warnings: int
    execution_time: float
    results: List[ValidationResult]

    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_templates == 0:
            return 100.0
        return (self.valid_templates / self.total_templates) * 100.0


class TemplateValidator:
    """テンプレート検証システムのメインクラス"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = self._setup_logger()
        self.template_patterns = {
            "env": [".env.example", ".env.template"],
            "docker_compose": [
                "docker-compose.*.yml.sample",
                "docker-compose.override.yml.sample",
            ],
            "precommit": [".pre-commit-config.yaml.sample"],
            "github_workflows": [
                ".github/workflows/*.yml.sample",
                ".github/workflows/*.yaml.sample",
            ],
            "shell": ["scripts/*.sh.sample", "*.sh.template"],
            "makefile": ["Makefile.sample", "Makefile.template"],
            "yaml": ["*.yml.sample", "*.yaml.sample"],
            "json": ["*.json.sample", "*.json.template"],
        }

    def _setup_logger(self) -> logging.Logger:
        """ロガーのセットアップ"""
        logger = logging.getLogger("template_validator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def find_template_files(self) -> Dict[str, List[Path]]:
        """テンプレートファイルを検索"""
        self.logger.info("🔍 テンプレートファイルを検索中...")

        template_files = {}
        project_root = Path.cwd()

        # 既知のテンプレートファイルを直接チェック
        known_templates = [
            ".env.example",
            "docker-compose.override.yml.sample",
            ".pre-commit-config.yaml.sample",
            ".github/workflows/local-ci.yml.sample",
            ".github/workflows/basic-test.yml.sample",
            ".github/workflows/security-scan.yml.sample",
            ".github/workflows/docs-check.yml.sample",
        ]

        for template_path in known_templates:
            file_path = project_root / template_path
            if file_path.exists():
                template_type = self._determine_template_type(file_path)
                if template_type not in template_files:
                    template_files[template_type] = []
                template_files[template_type].append(file_path)

        # パターンマッチングで追加のテンプレートを検索
        for template_type, patterns in self.template_patterns.items():
            for pattern in patterns:
                for file_path in project_root.glob(pattern):
                    if file_path.is_file():
                        if template_type not in template_files:
                            template_files[template_type] = []
                        if file_path not in template_files[template_type]:
                            template_files[template_type].append(file_path)

        total_files = sum(len(files) for files in template_files.values())
        self.logger.info(f"📋 {total_files} 個のテンプレートファイルを発見")

        for template_type, files in template_files.items():
            self.logger.debug(f"  {template_type}: {len(files)} ファイル")
            for file_path in files:
                self.logger.debug(f"    - {file_path}")

        return template_files

    def _determine_template_type(self, file_path: Path) -> str:
        """ファイルパスからテンプレートタイプを判定"""
        file_name = file_path.name.lower()
        file_suffix = file_path.suffix.lower()

        # .sample や .template ファイルの場合、その前の拡張子を確認
        if file_suffix in [".sample", ".template", ".example"]:
            # .yml.sample のような場合、.yml を取得
            stem_parts = file_path.stem.split(".")
            if len(stem_parts) > 1:
                actual_suffix = "." + stem_parts[-1].lower()
            else:
                actual_suffix = file_suffix
        else:
            actual_suffix = file_suffix

        if file_name.startswith(".env"):
            return "env"
        elif "docker-compose" in file_name:
            return "docker_compose"
        elif "pre-commit" in file_name:
            return "precommit"
        elif ".github/workflows" in str(file_path):
            return "github_workflows"
        elif actual_suffix in [".sh"]:
            return "shell"
        elif file_name.startswith("makefile"):
            return "makefile"
        elif actual_suffix in [".yml", ".yaml"]:
            return "yaml"
        elif actual_suffix in [".json"]:
            return "json"
        else:
            return "unknown"

    def validate_template(self, file_path: Path, template_type: str) -> ValidationResult:
        """個別テンプレートファイルの検証"""
        start_time = datetime.now()
        self.logger.info(f"🔍 検証中: {file_path}")

        result = ValidationResult(
            file_path=str(file_path),
            template_type=template_type,
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        try:
            # 構文チェック
            self._validate_syntax(file_path, template_type, result)

            # 機能チェック
            self._validate_functionality(file_path, template_type, result)

            # セキュリティチェック
            self._validate_security(file_path, template_type, result)

        except Exception as e:
            self.logger.error(f"❌ 検証エラー: {file_path} - {e}")
            result.syntax_valid = False
            result.syntax_errors.append(f"検証エラー: {str(e)}")

        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()

        if result.is_valid():
            self.logger.info(f"✅ 検証成功: {file_path}")
        else:
            self.logger.warning(f"⚠️ 検証失敗: {file_path}")

        return result

    def _validate_syntax(self, file_path: Path, template_type: str, result: ValidationResult):
        """構文チェック"""
        self.logger.debug(f"🔍 構文チェック: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            result.syntax_valid = False
            result.syntax_errors.append("ファイルエンコーディングエラー（UTF-8で読み取れません）")
            return

        if template_type == "yaml" or template_type in [
            "docker_compose",
            "precommit",
            "github_workflows",
        ]:
            self._validate_yaml_syntax(content, result)
        elif template_type == "json":
            self._validate_json_syntax(content, result)
        elif template_type == "shell":
            self._validate_shell_syntax(file_path, result)
        elif template_type == "env":
            self._validate_env_syntax(content, result)

        # 共通チェック
        self._validate_common_syntax(content, result)

    def _validate_yaml_syntax(self, content: str, result: ValidationResult):
        """YAML構文チェック"""
        try:
            # コメントアウトされたサンプル行を一時的に除外
            lines = content.split("\n")
            filtered_lines = []

            for line in lines:
                # サンプル用のコメントアウト行をスキップ
                if line.strip().startswith("# ") and ("例:" in line or "sample:" in line.lower()):
                    continue
                filtered_lines.append(line)

            filtered_content = "\n".join(filtered_lines)
            yaml.safe_load(filtered_content)

        except yaml.YAMLError as e:
            result.syntax_valid = False
            result.syntax_errors.append(f"YAML構文エラー: {str(e)}")

    def _validate_json_syntax(self, content: str, result: ValidationResult):
        """JSON構文チェック"""
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            result.syntax_valid = False
            result.syntax_errors.append(f"JSON構文エラー: {str(e)}")

    def _validate_shell_syntax(self, file_path: Path, result: ValidationResult):
        """Shell構文チェック"""
        try:
            # shellcheckが利用可能な場合は使用
            if shutil.which("shellcheck"):
                cmd_result = subprocess.run(
                    ["shellcheck", "-f", "json", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if cmd_result.returncode != 0:
                    try:
                        shellcheck_output = json.loads(cmd_result.stdout)
                        for issue in shellcheck_output:
                            if issue.get("level") == "error":
                                result.syntax_valid = False
                                result.syntax_errors.append(
                                    f"ShellCheck エラー (行 {issue.get('line', '?')}): {issue.get('message', '不明なエラー')}"
                                )
                            elif issue.get("level") == "warning":
                                result.warnings.append(
                                    f"ShellCheck 警告 (行 {issue.get('line', '?')}): {issue.get('message', '不明な警告')}"
                                )
                    except json.JSONDecodeError:
                        result.warnings.append("ShellCheck出力の解析に失敗しました")
            else:
                # 基本的な構文チェック
                cmd_result = subprocess.run(
                    ["bash", "-n", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if cmd_result.returncode != 0:
                    result.syntax_valid = False
                    result.syntax_errors.append(f"Bash構文エラー: {cmd_result.stderr}")

        except subprocess.TimeoutExpired:
            result.warnings.append("Shell構文チェックがタイムアウトしました")
        except Exception as e:
            result.warnings.append(f"Shell構文チェックエラー: {str(e)}")

    def _validate_env_syntax(self, content: str, result: ValidationResult):
        """環境変数ファイル構文チェック"""
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # 空行やコメント行はスキップ
            if not line or line.startswith("#"):
                continue

            # 環境変数の形式チェック
            if "=" not in line:
                result.syntax_errors.append(f"行 {line_num}: 環境変数の形式が正しくありません: {line}")
                result.syntax_valid = False
                continue

            var_name, var_value = line.split("=", 1)

            # 変数名の検証
            if not re.match(r"^[A-Z][A-Z0-9_]*$", var_name):
                result.warnings.append(f"行 {line_num}: 変数名が推奨形式ではありません: {var_name}")

            # 値の検証
            if var_value and not var_value.startswith('"') and " " in var_value:
                result.warnings.append(f"行 {line_num}: スペースを含む値はクォートすることを推奨: {var_name}")

    def _validate_common_syntax(self, content: str, result: ValidationResult):
        """共通構文チェック"""
        # 文字エンコーディングチェック
        try:
            content.encode("utf-8")
        except UnicodeEncodeError:
            result.syntax_errors.append("UTF-8エンコーディングエラー")
            result.syntax_valid = False

        # 行末の空白チェック
        lines_with_trailing_whitespace = []
        for line_num, line in enumerate(content.split("\n"), 1):
            if line.rstrip() != line:
                lines_with_trailing_whitespace.append(line_num)

        if lines_with_trailing_whitespace:
            result.warnings.append(
                f"行末に空白があります: 行 {', '.join(map(str, lines_with_trailing_whitespace[:5]))}"
            )

    def _validate_functionality(self, file_path: Path, template_type: str, result: ValidationResult):
        """機能チェック"""
        self.logger.debug(f"🧪 機能チェック: {file_path}")

        if template_type == "docker_compose":
            self._test_docker_compose_functionality(file_path, result)
        elif template_type == "github_workflows":
            self._test_github_workflow_functionality(file_path, result)
        elif template_type == "precommit":
            self._test_precommit_functionality(file_path, result)
        elif template_type == "env":
            self._test_env_functionality(file_path, result)

    def _test_docker_compose_functionality(self, file_path: Path, result: ValidationResult):
        """Docker Compose機能テスト"""
        try:
            # docker-compose configでの検証
            if shutil.which("docker") and shutil.which("docker-compose"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_file = Path(temp_dir) / "docker-compose.yml"
                    shutil.copy2(file_path, temp_file)

                    # 環境変数の設定
                    env = os.environ.copy()
                    env.update({"USER_ID": "1000", "GROUP_ID": "1000", "DOCKER_GID": "999"})

                    cmd_result = subprocess.run(
                        ["docker-compose", "-f", str(temp_file), "config"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        env=env,
                        cwd=temp_dir,
                    )

                    if cmd_result.returncode != 0:
                        result.functionality_valid = False
                        result.functionality_errors.append(f"Docker Compose設定エラー: {cmd_result.stderr}")
            else:
                result.warnings.append("DockerまたはDocker Composeが利用できないため機能テストをスキップしました")

        except subprocess.TimeoutExpired:
            result.warnings.append("Docker Compose機能テストがタイムアウトしました")
        except Exception as e:
            result.warnings.append(f"Docker Compose機能テストエラー: {str(e)}")

    def _test_github_workflow_functionality(self, file_path: Path, result: ValidationResult):
        """GitHub Workflow機能テスト"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 基本的なワークフロー要素の存在確認
            required_elements = ["name:", "on:", "jobs:"]
            missing_elements = []

            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)

            if missing_elements:
                result.functionality_valid = False
                result.functionality_errors.append(f"必須要素が不足: {', '.join(missing_elements)}")

            # actでの検証（利用可能な場合）
            if shutil.which("act"):
                cmd_result = subprocess.run(
                    ["act", "--dryrun", "-W", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if cmd_result.returncode != 0:
                    # act特有のエラーを除外
                    stderr = cmd_result.stderr
                    if "unable to get git repo" not in stderr.lower() and "no workflows found" not in stderr.lower():
                        result.warnings.append(f"Act検証警告: {stderr}")
            else:
                result.warnings.append("actが利用できないため詳細な機能テストをスキップしました")

        except Exception as e:
            result.warnings.append(f"GitHub Workflow機能テストエラー: {str(e)}")

    def _test_precommit_functionality(self, file_path: Path, result: ValidationResult):
        """pre-commit機能テスト"""
        try:
            # pre-commit設定の検証
            if shutil.which("pre-commit"):
                cmd_result = subprocess.run(
                    ["pre-commit", "validate-config", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if cmd_result.returncode != 0:
                    result.functionality_valid = False
                    result.functionality_errors.append(f"pre-commit設定エラー: {cmd_result.stderr}")
            else:
                result.warnings.append("pre-commitが利用できないため機能テストをスキップしました")

        except subprocess.TimeoutExpired:
            result.warnings.append("pre-commit機能テストがタイムアウトしました")
        except Exception as e:
            result.warnings.append(f"pre-commit機能テストエラー: {str(e)}")

    def _test_env_functionality(self, file_path: Path, result: ValidationResult):
        """環境変数ファイル機能テスト"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 重要な環境変数の存在確認
            important_vars = [
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "USER_ID",
                "GROUP_ID",
                "DOCKER_GID",
            ]

            missing_vars = []
            for var in important_vars:
                if f"{var}=" not in content:
                    missing_vars.append(var)

            if missing_vars:
                result.warnings.append(f"重要な環境変数が不足している可能性があります: {', '.join(missing_vars)}")

            # 環境変数の読み込みテスト
            env_vars = {}
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value

            if len(env_vars) == 0:
                result.functionality_valid = False
                result.functionality_errors.append("有効な環境変数が見つかりません")

        except Exception as e:
            result.warnings.append(f"環境変数ファイル機能テストエラー: {str(e)}")

    def _validate_security(self, file_path: Path, template_type: str, result: ValidationResult):
        """セキュリティチェック"""
        self.logger.debug(f"🔒 セキュリティチェック: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")

            # 秘密情報の検出
            secret_patterns = [
                (r'password\s*=\s*["\']?[^"\'\s#]{8,}', "平文パスワードの可能性"),
                (r'token\s*=\s*["\']?[a-zA-Z0-9_]{20,}', "実際のトークンの可能性"),
                (r'api_key\s*=\s*["\']?[a-zA-Z0-9+/_-]{20,}', "実際のAPIキーの可能性"),
                (
                    r'secret\s*=\s*["\']?[a-zA-Z0-9+/_-]{20,}',
                    "実際のシークレットの可能性",
                ),
            ]

            for pattern, description in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    # サンプル値やプレースホルダーは除外
                    matched_text = match.group().lower()
                    if any(
                        placeholder in matched_text
                        for placeholder in [
                            "your_",
                            "example",
                            "sample",
                            "dummy",
                            "placeholder",
                            "xxx",
                            "yyy",
                        ]
                    ):
                        continue

                    result.security_issues.append(f"行 {line_num}: {description}")

            # 権限設定の確認
            if template_type == "docker_compose":
                if "privileged: true" in content:
                    result.security_issues.append("特権モードが有効になっています")

                if "cap_add:" in content and "SYS_ADMIN" in content:
                    result.security_issues.append("危険なケーパビリティ (SYS_ADMIN) が追加されています")

            # ファイル権限の確認
            file_stat = file_path.stat()
            if file_stat.st_mode & 0o077:  # 他者に読み取り権限がある
                result.warnings.append("ファイル権限が緩すぎる可能性があります")

        except Exception as e:
            result.warnings.append(f"セキュリティチェックエラー: {str(e)}")

    def validate_all_templates(self, check_only: bool = False, test_only: bool = False) -> ValidationSummary:
        """全テンプレートの検証"""
        start_time = datetime.now()
        self.logger.info("🚀 テンプレート検証を開始...")

        template_files = self.find_template_files()
        results = []

        for template_type, files in template_files.items():
            for file_path in files:
                if check_only:
                    # 構文チェックのみ
                    result = self._syntax_check_only(file_path, template_type)
                elif test_only:
                    # 機能テストのみ
                    result = self._functionality_test_only(file_path, template_type)
                else:
                    # 完全な検証
                    result = self.validate_template(file_path, template_type)

                results.append(result)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # サマリーの生成
        total_templates = len(results)
        valid_templates = sum(1 for r in results if r.is_valid())
        invalid_templates = total_templates - valid_templates
        templates_with_warnings = sum(1 for r in results if r.warnings)

        summary = ValidationSummary(
            total_templates=total_templates,
            valid_templates=valid_templates,
            invalid_templates=invalid_templates,
            templates_with_warnings=templates_with_warnings,
            execution_time=execution_time,
            results=results,
        )

        self.logger.info(f"✅ 検証完了: {execution_time:.2f}秒")
        self.logger.info(f"📊 結果: {valid_templates}/{total_templates} 成功 ({summary.success_rate():.1f}%)")

        return summary

    def _syntax_check_only(self, file_path: Path, template_type: str) -> ValidationResult:
        """構文チェックのみ実行"""
        result = ValidationResult(
            file_path=str(file_path),
            template_type=template_type,
            syntax_valid=True,
            syntax_errors=[],
            functionality_valid=True,  # テストしないため True
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        start_time = datetime.now()
        self._validate_syntax(file_path, template_type, result)
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()

        return result

    def _functionality_test_only(self, file_path: Path, template_type: str) -> ValidationResult:
        """機能テストのみ実行"""
        result = ValidationResult(
            file_path=str(file_path),
            template_type=template_type,
            syntax_valid=True,  # テストしないため True
            syntax_errors=[],
            functionality_valid=True,
            functionality_errors=[],
            security_issues=[],
            warnings=[],
            execution_time=0.0,
        )

        start_time = datetime.now()
        self._validate_functionality(file_path, template_type, result)
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()

        return result

    def generate_report(self, summary: ValidationSummary, format_type: str = "text") -> str:
        """検証レポートの生成"""
        if format_type == "json":
            return json.dumps(asdict(summary), indent=2, ensure_ascii=False)

        # テキスト形式のレポート
        report_lines = [
            "=" * 80,
            "GitHub Actions Simulator - テンプレート検証レポート",
            "=" * 80,
            "",
            f"🕐 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"⏱️ 実行時間: {summary.execution_time:.2f}秒",
            f"📊 成功率: {summary.success_rate():.1f}%",
            "",
            "📋 サマリー:",
            f"  📁 総テンプレート数: {summary.total_templates}",
            f"  ✅ 有効なテンプレート: {summary.valid_templates}",
            f"  ❌ 無効なテンプレート: {summary.invalid_templates}",
            f"  ⚠️ 警告があるテンプレート: {summary.templates_with_warnings}",
            "",
        ]

        # テンプレートタイプ別の統計
        type_stats = {}
        for result in summary.results:
            template_type = result.template_type
            if template_type not in type_stats:
                type_stats[template_type] = {"total": 0, "valid": 0}
            type_stats[template_type]["total"] += 1
            if result.is_valid():
                type_stats[template_type]["valid"] += 1

        report_lines.extend(
            [
                "📊 テンプレートタイプ別統計:",
            ]
        )

        for template_type, stats in type_stats.items():
            success_rate = (stats["valid"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            report_lines.append(f"  {template_type}: {stats['valid']}/{stats['total']} ({success_rate:.1f}%)")

        report_lines.append("")

        # 詳細結果
        report_lines.extend(
            [
                "📋 詳細結果:",
                "-" * 80,
            ]
        )

        for result in summary.results:
            status_icon = "✅" if result.is_valid() else "❌"
            report_lines.append(f"{status_icon} {result.file_path} ({result.template_type})")

            if result.syntax_errors:
                report_lines.append("  🔍 構文エラー:")
                for error in result.syntax_errors:
                    report_lines.append(f"    - {error}")

            if result.functionality_errors:
                report_lines.append("  🧪 機能エラー:")
                for error in result.functionality_errors:
                    report_lines.append(f"    - {error}")

            if result.security_issues:
                report_lines.append("  🔒 セキュリティ問題:")
                for issue in result.security_issues:
                    report_lines.append(f"    - {issue}")

            if result.warnings:
                report_lines.append("  ⚠️ 警告:")
                for warning in result.warnings:
                    report_lines.append(f"    - {warning}")

            report_lines.append(f"  ⏱️ 実行時間: {result.execution_time:.3f}秒")
            report_lines.append("")

        # 推奨事項
        if summary.invalid_templates > 0:
            report_lines.extend(
                [
                    "💡 推奨事項:",
                    "  1. 構文エラーを修正してください",
                    "  2. 機能テストが失敗している場合は、依存ツールの確認を行ってください",
                    "  3. セキュリティ問題は優先的に対応してください",
                    "",
                ]
            )

        report_lines.extend(
            [
                "=" * 80,
                "検証完了",
                "=" * 80,
            ]
        )

        return "\n".join(report_lines)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="GitHub Actions Simulator テンプレート検証システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/validate-templates.py                    # 完全な検証
  python scripts/validate-templates.py --check-only       # 構文チェックのみ
  python scripts/validate-templates.py --test-only        # 機能テストのみ
  python scripts/validate-templates.py --format json      # JSON形式で出力
  python scripts/validate-templates.py --verbose          # 詳細ログ出力
        """,
    )

    parser.add_argument("--check-only", action="store_true", help="構文チェックのみ実行")

    parser.add_argument("--test-only", action="store_true", help="機能テストのみ実行")

    parser.add_argument("--verbose", action="store_true", help="詳細ログを出力")

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="出力形式 (デフォルト: text)",
    )

    parser.add_argument("--output", type=str, help="出力ファイルパス（指定しない場合は標準出力）")

    args = parser.parse_args()

    # 相互排他的なオプションのチェック
    if args.check_only and args.test_only:
        parser.error("--check-only と --test-only は同時に指定できません")

    try:
        # バリデーターの初期化
        validator = TemplateValidator(verbose=args.verbose)

        # 検証の実行
        summary = validator.validate_all_templates(check_only=args.check_only, test_only=args.test_only)

        # レポートの生成
        report = validator.generate_report(summary, args.format)

        # 出力
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"📊 レポートを {args.output} に出力しました")
        else:
            print(report)

        # 終了コード
        if summary.invalid_templates > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️ 検証が中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
