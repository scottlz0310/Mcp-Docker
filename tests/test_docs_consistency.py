#!/usr/bin/env python3
"""
ドキュメント整合性チェッカーのテスト
"""

import tempfile
import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from check_docs_consistency import DocumentationChecker, DocumentationReport


class TestDocumentationChecker:
    """ドキュメント整合性チェッカーのテストクラス"""

    def setup_method(self):
        """テスト用の一時ディレクトリを作成"""
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)

        # テスト用のpyproject.tomlを作成
        pyproject_content = """[project]
name = "test-project"
version = "1.0.0"
"""
        (self.root_path / "pyproject.toml").write_text(pyproject_content)

    def test_project_version_detection(self):
        """プロジェクトバージョンの検出テスト"""
        checker = DocumentationChecker(self.root_path)
        assert checker.project_version == "1.0.0"

    def test_markdown_file_discovery(self):
        """Markdownファイルの発見テスト"""
        # テスト用のMarkdownファイルを作成
        (self.root_path / "README.md").write_text("# Test Project")
        (self.root_path / "docs").mkdir()
        (self.root_path / "docs" / "guide.md").write_text("# Guide")

        checker = DocumentationChecker(self.root_path)
        md_files = [f.name for f in checker.markdown_files]

        assert "README.md" in md_files
        assert "guide.md" in md_files

    def test_broken_link_detection(self):
        """壊れたリンクの検出テスト"""
        # 壊れたリンクを含むMarkdownファイルを作成
        content = """# Test Document

[Existing File](./README.md)
[Broken Link](./nonexistent.md)
[External Link](https://example.com)
"""
        (self.root_path / "test.md").write_text(content)
        (self.root_path / "README.md").write_text("# README")

        checker = DocumentationChecker(self.root_path)
        link_issues = checker.check_links()

        # 壊れたリンクが1つ検出されることを確認
        broken_links = [
            issue for issue in link_issues if issue.issue_type == "broken_link"
        ]
        assert len(broken_links) == 1
        assert "nonexistent.md" in broken_links[0].target_path

    def test_version_consistency_check(self):
        """バージョン整合性チェックのテスト"""
        # 異なるバージョンを含むMarkdownファイルを作成
        content = """# Test Document

Current version: 1.0.0
Old version: 0.9.0
Docker version: 24.0.0  # これは除外される
"""
        (self.root_path / "test.md").write_text(content)

        checker = DocumentationChecker(self.root_path)
        version_issues = checker.check_versions()

        # 古いバージョンのみが検出されることを確認
        assert len(version_issues) == 1
        assert version_issues[0].found_version == "0.9.0"

    def test_consistency_issues_detection(self):
        """整合性問題の検出テスト"""
        # 古い情報を含むMarkdownファイルを作成
        content = """# Installation Guide

Install dependencies:
```bash
pip install package
```

Also check requirements.txt file.
"""
        (self.root_path / "install.md").write_text(content)

        checker = DocumentationChecker(self.root_path)
        consistency_issues = checker.check_consistency()

        # pip使用とrequirements.txtの問題が検出されることを確認
        assert len(consistency_issues) >= 2
        issue_types = [issue.issue_type for issue in consistency_issues]
        assert any("pip" in issue_type for issue_type in issue_types)
        assert any("requirements" in issue_type for issue_type in issue_types)

    def test_report_generation(self):
        """レポート生成のテスト"""
        # 問題のないMarkdownファイルを作成
        (self.root_path / "clean.md").write_text("# Clean Document\n\nNo issues here.")

        checker = DocumentationChecker(self.root_path)
        report = checker.generate_report()

        assert isinstance(report, DocumentationReport)
        assert report.total_files_checked >= 1
        assert report.timestamp is not None

    def test_exclude_directories(self):
        """除外ディレクトリのテスト"""
        # 除外されるべきディレクトリにファイルを作成
        (self.root_path / ".git").mkdir()
        (self.root_path / ".git" / "config.md").write_text("# Git Config")

        checker = DocumentationChecker(self.root_path)
        md_files = [str(f) for f in checker.markdown_files]

        # .gitディレクトリのファイルが除外されることを確認
        assert not any(".git" in path for path in md_files)


def test_cli_integration():
    """CLI統合テスト"""
    import subprocess
    import sys

    # スクリプトが正常に実行できることを確認
    result = subprocess.run(
        [sys.executable, "scripts/check-docs-consistency.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ドキュメント整合性チェックツール" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
