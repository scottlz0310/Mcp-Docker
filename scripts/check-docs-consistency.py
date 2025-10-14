#!/usr/bin/env python3
"""
ドキュメント整合性チェックスクリプト

このスクリプトは以下の機能を提供します：
1. ドキュメント間のリンク有効性確認
2. バージョン情報の整合性チェック
3. 古い情報や矛盾する記述の検出
"""

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class LinkIssue:
    """リンクの問題を表すクラス"""

    source_file: Path
    line_number: int
    link_text: str
    target_path: str
    issue_type: str
    description: str


@dataclass
class VersionIssue:
    """バージョンの問題を表すクラス"""

    file_path: Path
    line_number: int
    found_version: str
    expected_version: str
    context: str


@dataclass
class ConsistencyIssue:
    """整合性の問題を表すクラス"""

    file_path: Path
    line_number: int
    issue_type: str
    description: str
    suggestion: Optional[str] = None


@dataclass
class DocumentationReport:
    """ドキュメント整合性チェックレポート"""

    timestamp: str
    total_files_checked: int
    link_issues: List[LinkIssue] = field(default_factory=list)
    version_issues: List[VersionIssue] = field(default_factory=list)
    consistency_issues: List[ConsistencyIssue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.link_issues) + len(self.version_issues) + len(self.consistency_issues)

    @property
    def has_critical_issues(self) -> bool:
        """重要な問題があるかどうか"""
        return len(self.link_issues) > 0 or len(self.version_issues) > 0


class DocumentationChecker:
    """ドキュメント整合性チェッカー"""

    def __init__(self, root_path: Path, config_path: Optional[Path] = None):
        self.root_path = root_path
        self.config = self._load_config(config_path)
        self.project_version = self._get_project_version()
        self.markdown_files = self._find_markdown_files()

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        if config_path is None:
            config_path = self.root_path / ".docs-check.yaml"

        if not config_path.exists():
            # デフォルト設定
            return {
                "exclude_dirs": {
                    ".git",
                    ".mypy_cache",
                    ".pytest_cache",
                    ".ruff_cache",
                    ".venv",
                    "node_modules",
                    "__pycache__",
                    "archive",
                },
                "version_check": {
                    "exclude_patterns": [
                        r"^20\.\d+\.\d+$",
                        r"^24\.\d+\.\d+$",
                        r"^2\.\d+\.\d+$",
                        r"^0\.2\.\d+$",
                        r"^0\.0\.\d+$",
                    ]
                },
            }

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _get_project_version(self) -> str:
        """pyproject.tomlからプロジェクトバージョンを取得"""
        pyproject_path = self.root_path / "pyproject.toml"
        if not pyproject_path.exists():
            return "unknown"

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
        except Exception:
            return "unknown"

    def _find_markdown_files(self) -> List[Path]:
        """Markdownファイルを再帰的に検索"""
        markdown_files = []

        # 除外するディレクトリ（設定ファイルから取得）
        exclude_dirs = set(self.config.get("exclude_dirs", []))

        for md_file in self.root_path.rglob("*.md"):
            # 除外ディレクトリをチェック
            if any(part in exclude_dirs for part in md_file.parts):
                continue
            markdown_files.append(md_file)

        return sorted(markdown_files)

    def check_links(self) -> List[LinkIssue]:
        """ドキュメント間のリンク有効性をチェック"""
        issues = []

        # Markdownリンクのパターン
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for md_file in self.markdown_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    matches = link_pattern.findall(line)

                    for link_text, target in matches:
                        # 外部リンクはスキップ
                        if target.startswith(("http://", "https://", "mailto:")):
                            continue

                        # アンカーリンクを分離
                        if "#" in target:
                            target_path, anchor = target.split("#", 1)
                        else:
                            target_path, anchor = target, None

                        if not target_path:  # アンカーのみの場合
                            continue

                        # 相対パスを絶対パスに変換
                        if target_path.startswith("/"):
                            # ルートからの絶対パス
                            full_path = self.root_path / target_path.lstrip("/")
                        else:
                            # 相対パス
                            full_path = (md_file.parent / target_path).resolve()

                        # ファイルの存在確認
                        if not full_path.exists():
                            issues.append(
                                LinkIssue(
                                    source_file=md_file,
                                    line_number=line_num,
                                    link_text=link_text,
                                    target_path=target,
                                    issue_type="broken_link",
                                    description=f"リンク先ファイルが存在しません: {full_path}",
                                )
                            )

                        # アンカーの存在確認（Markdownファイルの場合）
                        elif anchor and full_path.suffix == ".md":
                            if not self._check_anchor_exists(full_path, anchor):
                                issues.append(
                                    LinkIssue(
                                        source_file=md_file,
                                        line_number=line_num,
                                        link_text=link_text,
                                        target_path=target,
                                        issue_type="broken_anchor",
                                        description=f"アンカーが見つかりません: #{anchor}",
                                    )
                                )

            except Exception as e:
                issues.append(
                    LinkIssue(
                        source_file=md_file,
                        line_number=0,
                        link_text="",
                        target_path="",
                        issue_type="read_error",
                        description=f"ファイル読み込みエラー: {e}",
                    )
                )

        return issues

    def _check_anchor_exists(self, file_path: Path, anchor: str) -> bool:
        """Markdownファイル内のアンカーの存在確認"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # ヘッダーパターン
            header_pattern = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
            headers = header_pattern.findall(content)

            # アンカー形式に変換（GitHub形式）
            for header in headers:
                # 特殊文字を除去してアンカー形式に変換
                anchor_text = re.sub(r"[^\w\s-]", "", header.lower())
                anchor_text = re.sub(r"[-\s]+", "-", anchor_text).strip("-")

                if anchor_text == anchor.lower():
                    return True

            return False

        except Exception:
            return False

    def check_versions(self) -> List[VersionIssue]:
        """バージョン情報の整合性をチェック"""
        issues = []

        # プロジェクトバージョンのパターン（より具体的に）
        version_patterns = [
            (
                re.compile(r'version["\s]*[:=]["\s]*([0-9]+\.[0-9]+\.[0-9]+)', re.IGNORECASE),
                "設定ファイル",
            ),
            (
                re.compile(
                    r'mcp-docker["\s]*[:=]["\s]*v?([0-9]+\.[0-9]+\.[0-9]+)',
                    re.IGNORECASE,
                ),
                "プロジェクトバージョン",
            ),
            (
                re.compile(r"リリース\s*v?([0-9]+\.[0-9]+\.[0-9]+)", re.IGNORECASE),
                "リリースバージョン",
            ),
        ]

        for md_file in self.markdown_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern, context in version_patterns:
                        matches = pattern.findall(line)

                        for version in matches:
                            if version != self.project_version and version != "unknown":
                                # 明らかに異なるバージョンのみ報告
                                if self._is_version_mismatch(version, self.project_version):
                                    issues.append(
                                        VersionIssue(
                                            file_path=md_file,
                                            line_number=line_num,
                                            found_version=version,
                                            expected_version=self.project_version,
                                            context=context,
                                        )
                                    )

            except Exception:
                continue

        return issues

    def _is_version_mismatch(self, found: str, expected: str) -> bool:
        """バージョンの不整合を判定"""
        try:
            # 除外するバージョンパターン（設定ファイルから取得）
            excluded_patterns = self.config.get("version_check", {}).get("exclude_patterns", [])

            for pattern in excluded_patterns:
                if re.match(pattern, found):
                    return False

            found_parts = [int(x) for x in found.split(".")]
            expected_parts = [int(x) for x in expected.split(".")]

            # プロジェクトバージョンと明らかに異なる場合のみ報告
            # メジャーバージョンが大きく異なる場合
            if abs(found_parts[0] - expected_parts[0]) > 1:
                return True

            # 同じメジャーバージョンでマイナーバージョンが大きく異なる場合
            if found_parts[0] == expected_parts[0] and abs(found_parts[1] - expected_parts[1]) > 2:
                return True

            return False

        except (ValueError, IndexError):
            return False

    def check_consistency(self) -> List[ConsistencyIssue]:
        """古い情報や矛盾する記述をチェック"""
        issues = []

        # 古い情報のパターン
        outdated_patterns = [
            (
                re.compile(r"pip\s+install", re.IGNORECASE),
                "pip使用",
                "uvを使用してください",
            ),
            (
                re.compile(r"npm\s+install", re.IGNORECASE),
                "npm使用",
                "uvまたは適切なパッケージマネージャーを使用してください",
            ),
            (
                re.compile(r"python\s+-m\s+pip", re.IGNORECASE),
                "pip使用",
                "uvを使用してください",
            ),
            (
                re.compile(r"requirements\.txt", re.IGNORECASE),
                "requirements.txt",
                "pyproject.tomlを使用してください",
            ),
        ]

        # 矛盾する記述のパターン
        contradiction_patterns = [
            (
                re.compile(r"Docker\s+Desktop.*必須", re.IGNORECASE),
                "Docker Desktop必須",
                "Docker Engineでも動作します",
            ),
            (
                re.compile(r"root.*権限.*必要", re.IGNORECASE),
                "root権限必要",
                "rootless Dockerを推奨しています",
            ),
        ]

        for md_file in self.markdown_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    # 古い情報のチェック
                    for pattern, issue_type, suggestion in outdated_patterns:
                        if pattern.search(line):
                            issues.append(
                                ConsistencyIssue(
                                    file_path=md_file,
                                    line_number=line_num,
                                    issue_type=f"outdated_{issue_type}",
                                    description=f"古い情報が含まれています: {issue_type}",
                                    suggestion=suggestion,
                                )
                            )

                    # 矛盾する記述のチェック
                    for pattern, issue_type, suggestion in contradiction_patterns:
                        if pattern.search(line):
                            issues.append(
                                ConsistencyIssue(
                                    file_path=md_file,
                                    line_number=line_num,
                                    issue_type=f"contradiction_{issue_type}",
                                    description=f"矛盾する記述があります: {issue_type}",
                                    suggestion=suggestion,
                                )
                            )

            except Exception:
                continue

        return issues

    def generate_report(self) -> DocumentationReport:
        """包括的なドキュメント整合性レポートを生成"""
        print("🔍 ドキュメント整合性チェックを開始...")

        print("📋 リンク有効性をチェック中...")
        link_issues = self.check_links()

        print("🔢 バージョン整合性をチェック中...")
        version_issues = self.check_versions()

        print("📝 内容整合性をチェック中...")
        consistency_issues = self.check_consistency()

        return DocumentationReport(
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            total_files_checked=len(self.markdown_files),
            link_issues=link_issues,
            version_issues=version_issues,
            consistency_issues=consistency_issues,
        )


def print_report(
    report: DocumentationReport,
    verbose: bool = False,
    ci_mode: bool = False,
    fix_suggestions: bool = False,
) -> None:
    """レポートを表示"""
    if ci_mode:
        # CI/CD環境向けの簡潔な出力
        print(f"docs-check: {report.total_files_checked} files, {report.total_issues} issues")
        if report.has_critical_issues:
            print(
                f"docs-check: CRITICAL - {len(report.link_issues)} broken links, {len(report.version_issues)} version mismatches"
            )
        return

    print("\n📊 ドキュメント整合性チェック結果")
    print(f"⏰ 実行時刻: {report.timestamp}")
    print(f"📁 チェック対象ファイル数: {report.total_files_checked}")
    print(f"🚨 総問題数: {report.total_issues}")

    if report.link_issues:
        print(f"\n🔗 リンクの問題 ({len(report.link_issues)}件):")
        for issue in report.link_issues:
            rel_path = issue.source_file.relative_to(Path.cwd())
            print(f"  ❌ {rel_path}:{issue.line_number}")
            print(f"     リンク: [{issue.link_text}]({issue.target_path})")
            print(f"     問題: {issue.description}")
            if verbose:
                print(f"     タイプ: {issue.issue_type}")
            if fix_suggestions and issue.issue_type == "broken_link":
                print("     💡 修正提案: ファイルパスを確認し、正しいパスに修正してください")

    if report.version_issues:
        print(f"\n🔢 バージョンの問題 ({len(report.version_issues)}件):")
        for v_issue in report.version_issues:
            rel_path = v_issue.file_path.relative_to(Path.cwd())
            print(f"  ❌ {rel_path}:{v_issue.line_number}")
            print(f"     発見: {v_issue.found_version} → 期待: {v_issue.expected_version}")
            print(f"     コンテキスト: {v_issue.context}")
            if fix_suggestions:
                print(f"     💡 修正提案: バージョンを {v_issue.expected_version} に更新してください")

    if report.consistency_issues:
        print(f"\n📝 整合性の問題 ({len(report.consistency_issues)}件):")
        for c_issue in report.consistency_issues:
            rel_path = c_issue.file_path.relative_to(Path.cwd())
            print(f"  ⚠️  {rel_path}:{c_issue.line_number}")
            print(f"     問題: {c_issue.description}")
            if c_issue.suggestion:
                print(f"     提案: {c_issue.suggestion}")

    if fix_suggestions and report.total_issues > 0:
        print("\n🔧 修正コマンド例:")
        if report.link_issues:
            print("  # 壊れたリンクの修正")
            print(
                "  find docs -name '*.md' -exec grep -l 'QUICK_START.md' {} \\; | xargs sed -i 's|QUICK_START.md|../QUICK_START.md|g'"
            )
        if report.version_issues:
            print("  # バージョン情報の一括更新")
            print(
                f"  find . -name '*.md' -exec sed -i 's/version: [0-9]\\+\\.[0-9]\\+\\.[0-9]\\+/version: {report.version_issues[0].expected_version if report.version_issues else '1.2.0'}/g' {{}} \\;"
            )

    if report.total_issues == 0:
        print("\n✅ 問題は見つかりませんでした！")
    elif report.has_critical_issues:
        print(f"\n🚨 重要な問題が {len(report.link_issues) + len(report.version_issues)} 件見つかりました。")
        print("   修正をお勧めします。")
    else:
        print(f"\n⚠️  軽微な問題が {len(report.consistency_issues)} 件見つかりました。")
        print("   必要に応じて修正してください。")


def save_report_json(report: DocumentationReport, output_path: Path) -> None:
    """レポートをJSONファイルに保存"""

    def convert_to_dict(obj: Any) -> Any:
        if hasattr(obj, "__dict__"):
            result: Dict[str, Any] = {}
            for key, value in obj.__dict__.items():
                if isinstance(value, Path):
                    result[key] = str(value)
                elif isinstance(value, list):
                    result[key] = [convert_to_dict(item) for item in value]
                else:
                    result[key] = value
            return result
        return obj

    report_dict = convert_to_dict(report)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    print(f"📄 詳細レポートを保存しました: {output_path}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="ドキュメント整合性チェックツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                          # 基本チェック
  %(prog)s --verbose                # 詳細表示
  %(prog)s --output report.json     # JSONレポート出力
  %(prog)s --root /path/to/project  # 別のプロジェクトをチェック
        """,
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="プロジェクトルートディレクトリ (デフォルト: 現在のディレクトリ)",
    )

    parser.add_argument("--output", type=Path, help="JSONレポートの出力先ファイル")

    parser.add_argument("--verbose", "-v", action="store_true", help="詳細な情報を表示")

    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="問題が見つかった場合に終了コード1で終了",
    )

    parser.add_argument("--ci-mode", action="store_true", help="CI/CD環境向けの簡潔な出力")

    parser.add_argument("--fix-suggestions", action="store_true", help="修正提案を表示")

    parser.add_argument("--config", type=Path, help="設定ファイルのパス (デフォルト: .docs-check.yaml)")

    args = parser.parse_args()

    try:
        checker = DocumentationChecker(args.root, args.config)
        report = checker.generate_report()

        print_report(report, args.verbose, args.ci_mode, args.fix_suggestions)

        if args.output:
            save_report_json(report, args.output)

        # 終了コードの決定
        if args.fail_on_issues and report.has_critical_issues:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  チェックが中断されました。")
        sys.exit(130)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
