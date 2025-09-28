#!/usr/bin/env python3
"""
GitHub Actions Simulator - ドキュメント整合性テストスイート
========================================================

このテストスイートは、ドキュメント間の整合性とテンプレート動作の自動検証を行います。

テスト内容:
- ドキュメント間のリンク有効性チェック
- バージョン情報の整合性確認
- テンプレートファイルの動作検証
- ドキュメント構造の一貫性チェック
- コード例の動作確認

実行方法:
    pytest tests/test_documentation_consistency.py -v
    python -m pytest tests/test_documentation_consistency.py::TestDocumentationConsistency::test_readme_links -v
"""

import json
import os
import re
import subprocess
import tempfile
import pytest
import yaml
from pathlib import Path
from typing import List, Optional


class TestDocumentationConsistency:
    """ドキュメント整合性テストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def documentation_files(self, project_root):
        """ドキュメントファイルのリスト"""
        doc_patterns = [
            "README.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "docs/**/*.md",
            ".github/**/*.md",
        ]

        doc_files = []
        for pattern in doc_patterns:
            doc_files.extend(project_root.glob(pattern))

        return [f for f in doc_files if f.is_file()]

    def test_all_documentation_files_exist(self, project_root):
        """必須ドキュメントファイルの存在確認"""
        required_docs = [
            "README.md",
            "CONTRIBUTING.md",
            "docs/TROUBLESHOOTING.md",
            "docs/actions/README.md",
            "docs/PLATFORM_SUPPORT.md",
            "docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md",
        ]

        missing_docs = []
        for doc_path in required_docs:
            full_path = project_root / doc_path
            if not full_path.exists():
                missing_docs.append(doc_path)

        assert not missing_docs, f"必須ドキュメントが不足しています: {missing_docs}"

    def test_readme_structure(self, project_root):
        """メインREADMEの構造確認"""
        readme_path = project_root / "README.md"
        assert readme_path.exists(), "README.mdが見つかりません"

        content = readme_path.read_text(encoding="utf-8")

        # 必須セクションの確認
        required_sections = [
            "# GitHub Actions Simulator",
            "## 概要",
            "## クイックスタート",
            "## 主要機能",
            "## インストール",
            "## 使用方法",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        assert (
            not missing_sections
        ), f"README.mdに必須セクションが不足: {missing_sections}"

    def test_internal_links_validity(self, documentation_files, project_root):
        """内部リンクの有効性確認"""
        broken_links = []

        for doc_file in documentation_files:
            content = doc_file.read_text(encoding="utf-8")

            # Markdownリンクを抽出
            link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
            links = re.findall(link_pattern, content)

            for link_text, link_url in links:
                # 外部リンクはスキップ
                if link_url.startswith(("http://", "https://", "mailto:")):
                    continue

                # アンカーリンクはスキップ（#で始まる）
                if link_url.startswith("#"):
                    continue

                # 相対パスの解決
                if link_url.startswith("./"):
                    link_url = link_url[2:]

                target_path = doc_file.parent / link_url

                # パスの正規化
                try:
                    target_path = target_path.resolve()
                    if not target_path.exists():
                        broken_links.append(
                            {
                                "file": str(doc_file.relative_to(project_root)),
                                "link_text": link_text,
                                "link_url": link_url,
                                "target_path": str(target_path),
                            }
                        )
                except (OSError, ValueError):
                    broken_links.append(
                        {
                            "file": str(doc_file.relative_to(project_root)),
                            "link_text": link_text,
                            "link_url": link_url,
                            "error": "パス解決エラー",
                        }
                    )

        if broken_links:
            error_msg = "無効な内部リンクが見つかりました:\n"
            for link in broken_links[:10]:  # 最初の10個のみ表示
                error_msg += (
                    f"  - {link['file']}: [{link['link_text']}]({link['link_url']})\n"
                )
            if len(broken_links) > 10:
                error_msg += f"  ... および他 {len(broken_links) - 10} 個\n"

            assert False, error_msg

    def test_version_consistency(self, project_root):
        """バージョン情報の整合性確認"""
        version_files = {
            "pyproject.toml": self._extract_version_from_pyproject,
            "docker-compose.yml": self._extract_version_from_docker_compose,
            "README.md": self._extract_version_from_readme,
        }

        versions = {}
        for file_name, extractor in version_files.items():
            file_path = project_root / file_name
            if file_path.exists():
                version = extractor(file_path)
                if version:
                    versions[file_name] = version

        # バージョンが複数ある場合、一貫性をチェック
        if len(versions) > 1:
            version_values = list(versions.values())
            first_version = version_values[0]

            inconsistent_files = []
            for file_name, version in versions.items():
                if version != first_version:
                    inconsistent_files.append(f"{file_name}: {version}")

            if inconsistent_files:
                assert False, f"バージョン情報が不一致です。基準: {first_version}, 不一致: {inconsistent_files}"

    def _extract_version_from_pyproject(self, file_path: Path) -> Optional[str]:
        """pyproject.tomlからバージョンを抽出"""
        try:
            import tomllib

            with open(file_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version")
        except (ImportError, Exception):
            # Python 3.11未満またはファイル読み取りエラー
            content = file_path.read_text(encoding="utf-8")
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            return version_match.group(1) if version_match else None

    def _extract_version_from_docker_compose(self, file_path: Path) -> Optional[str]:
        """docker-compose.ymlからバージョンを抽出"""
        try:
            content = file_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            # サービス内のイメージタグからバージョンを抽出
            services = data.get("services", {})
            for service_name, service_config in services.items():
                image = service_config.get("image", "")
                if ":" in image and "actions-simulator" in image:
                    return image.split(":")[-1]

            return None
        except Exception:
            return None

    def _extract_version_from_readme(self, file_path: Path) -> Optional[str]:
        """README.mdからバージョンを抽出"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # バージョンバッジやバージョン表記を探す
            version_patterns = [
                r"version[:\s]+v?(\d+\.\d+\.\d+)",
                r"v(\d+\.\d+\.\d+)",
                r"Version\s+(\d+\.\d+\.\d+)",
            ]

            for pattern in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)

            return None
        except Exception:
            return None

    def test_code_examples_syntax(self, documentation_files):
        """ドキュメント内のコード例の構文確認"""
        syntax_errors = []

        for doc_file in documentation_files:
            content = doc_file.read_text(encoding="utf-8")

            # コードブロックを抽出
            code_blocks = re.findall(r"```(\w+)?\n(.*?)\n```", content, re.DOTALL)

            for language, code in code_blocks:
                if language in ["bash", "sh", "shell"]:
                    errors = self._validate_shell_syntax(code, doc_file)
                    syntax_errors.extend(errors)
                elif language in ["yaml", "yml"]:
                    errors = self._validate_yaml_syntax(code, doc_file)
                    syntax_errors.extend(errors)
                elif language in ["json"]:
                    errors = self._validate_json_syntax(code, doc_file)
                    syntax_errors.extend(errors)

        if syntax_errors:
            error_msg = "コード例に構文エラーがあります:\n"
            for error in syntax_errors[:10]:  # 最初の10個のみ表示
                error_msg += f"  - {error}\n"
            if len(syntax_errors) > 10:
                error_msg += f"  ... および他 {len(syntax_errors) - 10} 個\n"

            assert False, error_msg

    def _validate_shell_syntax(self, code: str, doc_file: Path) -> List[str]:
        """Shell構文の検証"""
        errors = []

        try:
            # 一時ファイルに書き込んで構文チェック
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ["bash", "-n", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    errors.append(
                        f"{doc_file.name}: Shell構文エラー - {result.stderr.strip()}"
                    )

            finally:
                os.unlink(temp_file)

        except Exception as e:
            errors.append(f"{doc_file.name}: Shell構文チェックエラー - {str(e)}")

        return errors

    def _validate_yaml_syntax(self, code: str, doc_file: Path) -> List[str]:
        """YAML構文の検証"""
        errors = []

        try:
            yaml.safe_load(code)
        except yaml.YAMLError as e:
            errors.append(f"{doc_file.name}: YAML構文エラー - {str(e)}")
        except Exception as e:
            errors.append(f"{doc_file.name}: YAML検証エラー - {str(e)}")

        return errors

    def _validate_json_syntax(self, code: str, doc_file: Path) -> List[str]:
        """JSON構文の検証"""
        errors = []

        try:
            json.loads(code)
        except json.JSONDecodeError as e:
            errors.append(f"{doc_file.name}: JSON構文エラー - {str(e)}")
        except Exception as e:
            errors.append(f"{doc_file.name}: JSON検証エラー - {str(e)}")

        return errors

    def test_template_files_consistency(self, project_root):
        """テンプレートファイルの整合性確認"""
        template_files = [
            ".env.example",
            "docker-compose.override.yml.sample",
            ".pre-commit-config.yaml.sample",
            ".github/workflows/local-ci.yml.sample",
            ".github/workflows/basic-test.yml.sample",
            ".github/workflows/security-scan.yml.sample",
        ]

        missing_templates = []
        invalid_templates = []

        for template_path in template_files:
            full_path = project_root / template_path

            if not full_path.exists():
                missing_templates.append(template_path)
                continue

            # テンプレートファイルの基本的な検証
            try:
                content = full_path.read_text(encoding="utf-8")

                # 空ファイルでないことを確認
                if not content.strip():
                    invalid_templates.append(f"{template_path}: 空ファイル")
                    continue

                # ファイル形式に応じた構文チェック
                if template_path.endswith((".yml", ".yaml")):
                    yaml.safe_load(content)
                elif template_path.endswith(".json"):
                    json.loads(content)

            except Exception as e:
                invalid_templates.append(f"{template_path}: {str(e)}")

        errors = []
        if missing_templates:
            errors.append(f"テンプレートファイルが不足: {missing_templates}")
        if invalid_templates:
            errors.append(f"無効なテンプレートファイル: {invalid_templates}")

        assert not errors, "\n".join(errors)

    def test_documentation_cross_references(self, documentation_files, project_root):
        """ドキュメント間の相互参照の確認"""
        # ドキュメント間で参照されているファイルを収集
        referenced_files = set()

        for doc_file in documentation_files:
            content = doc_file.read_text(encoding="utf-8")

            # ファイルパスの参照を抽出
            file_references = re.findall(
                r"`([^`]+\.(md|py|sh|yml|yaml|json|toml))`", content
            )
            for file_ref, _ in file_references:
                if not file_ref.startswith(("http://", "https://")):
                    referenced_files.add(file_ref)

            # リンクでのファイル参照も抽出
            link_references = re.findall(
                r"\]\(([^)]+\.(md|py|sh|yml|yaml|json|toml))\)", content
            )
            for file_ref, _ in link_references:
                if not file_ref.startswith(("http://", "https://")):
                    referenced_files.add(file_ref)

        # 参照されているファイルが実際に存在するかチェック
        missing_referenced_files = []

        for file_ref in referenced_files:
            # 相対パスの解決を試行
            possible_paths = [
                project_root / file_ref,
                project_root / file_ref.lstrip("./"),
            ]

            if not any(path.exists() for path in possible_paths):
                missing_referenced_files.append(file_ref)

        if missing_referenced_files:
            assert (
                False
            ), f"参照されているが存在しないファイル: {missing_referenced_files}"

    def test_makefile_targets_documentation(self, project_root):
        """Makefileターゲットとドキュメントの整合性"""
        makefile_path = project_root / "Makefile"

        if not makefile_path.exists():
            pytest.skip("Makefileが存在しません")

        # Makefileからターゲットを抽出
        makefile_content = makefile_path.read_text(encoding="utf-8")
        targets = re.findall(
            r"^([a-zA-Z][a-zA-Z0-9_-]*):(?!.*=)", makefile_content, re.MULTILINE
        )

        # ドキュメントでMakeターゲットが言及されているかチェック
        documented_targets = set()

        for doc_file in [project_root / "README.md", project_root / "CONTRIBUTING.md"]:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8")

                # make コマンドの参照を抽出
                make_commands = re.findall(r"make\s+([a-zA-Z][a-zA-Z0-9_-]*)", content)
                documented_targets.update(make_commands)

        # 重要なターゲットがドキュメント化されているかチェック
        important_targets = {"setup", "build", "test", "clean", "actions", "diagnostic"}
        existing_important_targets = [t for t in important_targets if t in targets]
        undocumented_important_targets = [
            t for t in existing_important_targets if t not in documented_targets
        ]

        if undocumented_important_targets:
            assert False, f"重要なMakeターゲットがドキュメント化されていません: {undocumented_important_targets}"


class TestTemplateValidationIntegration:
    """テンプレート検証統合テストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    def test_template_validation_script_execution(self, project_root):
        """テンプレート検証スクリプトの実行テスト"""
        validation_script = project_root / "scripts" / "validate-templates.py"

        if not validation_script.exists():
            pytest.skip("テンプレート検証スクリプトが存在しません")

        result = subprocess.run(
            ["python", str(validation_script), "--check-only"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root,
        )

        # スクリプトが正常に実行されることを確認
        assert result.returncode in [
            0,
            1,
        ], f"テンプレート検証スクリプトが失敗: {result.stderr}"

        # 出力に検証結果が含まれることを確認
        output = result.stdout + result.stderr
        assert (
            "テンプレート" in output
            or "検証" in output
            or "validation" in output.lower()
        )

    def test_ci_template_validation_integration(self, project_root):
        """CI用テンプレート検証の統合テスト"""
        ci_validation_script = project_root / "scripts" / "ci-validate-templates.sh"

        if not ci_validation_script.exists():
            pytest.skip("CI用テンプレート検証スクリプトが存在しません")

        result = subprocess.run(
            ["bash", str(ci_validation_script)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=project_root,
        )

        # CI検証が適切に動作することを確認
        output = result.stdout + result.stderr
        assert len(output) > 0, "CI検証スクリプトが出力を生成しませんでした"

        # エラーがある場合は適切に報告されることを確認
        if result.returncode != 0:
            assert (
                "エラー" in output
                or "error" in output.lower()
                or "failed" in output.lower()
            )


class TestDocumentationAccessibility:
    """ドキュメントアクセシビリティテストクラス"""

    @pytest.fixture
    def project_root(self):
        """プロジェクトルートディレクトリ"""
        return Path(__file__).parent.parent

    def test_readme_accessibility(self, project_root):
        """README.mdのアクセシビリティ確認"""
        readme_path = project_root / "README.md"
        content = readme_path.read_text(encoding="utf-8")

        # 見出し構造の確認
        headings = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)

        # 見出しレベルが適切に階層化されているかチェック
        prev_level = 0
        heading_issues = []

        for heading_marks, heading_text in headings:
            current_level = len(heading_marks)

            # レベルが2以上飛ばないことを確認
            if current_level > prev_level + 1 and prev_level > 0:
                heading_issues.append(
                    f"見出しレベルが飛んでいます: {heading_marks} {heading_text}"
                )

            prev_level = current_level

        if heading_issues:
            assert False, "見出し構造に問題があります:\n" + "\n".join(heading_issues)

    def test_image_alt_text(self, project_root):
        """画像のalt属性確認"""
        doc_files = list(project_root.glob("**/*.md"))

        missing_alt_text = []

        for doc_file in doc_files:
            content = doc_file.read_text(encoding="utf-8")

            # 画像リンクを抽出
            images = re.findall(r"!\[([^\]]*)\]\([^)]+\)", content)

            for alt_text in images:
                if not alt_text.strip():
                    missing_alt_text.append(f"{doc_file.name}: 空のalt属性")

        if missing_alt_text:
            assert False, "画像にalt属性が不足しています:\n" + "\n".join(
                missing_alt_text
            )


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])
