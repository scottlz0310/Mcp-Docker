#!/usr/bin/env python3
"""
GitHub Actions Simulator - 包括的テストスイート実行スクリプト
========================================================

このスクリプトは、タスク18で実装された包括的テストスイートを実行します。

実行内容:
1. 配布スクリプトの全機能テスト
2. ドキュメント整合性とテンプレート動作検証
3. エンドツーエンドの新規ユーザー体験テスト
4. 統合テストとパフォーマンス検証

使用方法:
    python tests/run_comprehensive_test_suite.py [options]

オプション:
    --quick         クイックテストのみ実行
    --full          フルテストスイートを実行
    --report        詳細レポートを生成
    --output FILE   結果をファイルに出力
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict


class ComprehensiveTestRunner:
    """包括的テストスイート実行クラス"""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_comprehensive_tests(self, quick_mode: bool = False) -> Dict:
        """包括的テストの実行"""
        self.start_time = datetime.now()

        print("🚀 GitHub Actions Simulator 包括的テストスイート開始")
        print(f"📅 開始時刻: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 プロジェクトルート: {self.project_root}")
        print()

        # テストスイートの定義
        test_suites = [
            {
                "name": "配布スクリプト機能テスト",
                "module": "tests.test_comprehensive_distribution",
                "essential": True,
                "timeout": 300,
            },
            {
                "name": "ドキュメント整合性テスト",
                "module": "tests.test_documentation_consistency",
                "essential": True,
                "timeout": 180,
            },
            {
                "name": "エンドツーエンドユーザー体験テスト",
                "module": "tests.test_end_to_end_user_experience",
                "essential": True,
                "timeout": 600,
            },
            {
                "name": "包括的統合テスト",
                "module": "tests.test_comprehensive_integration_suite",
                "essential": not quick_mode,
                "timeout": 900,
            },
            {
                "name": "テンプレート検証テスト",
                "module": "tests.test_template_validation",
                "essential": True,
                "timeout": 240,
            },
        ]

        # 実行するテストスイートをフィルタリング
        if quick_mode:
            test_suites = [
                suite for suite in test_suites if suite.get("essential", True)
            ]
            print("⚡ クイックモードで実行中...")
        else:
            print("🔍 フルテストスイートで実行中...")

        print(f"📋 実行予定テスト数: {len(test_suites)}")
        print()

        # 各テストスイートを実行
        for i, suite in enumerate(test_suites, 1):
            print(f"[{i}/{len(test_suites)}] {suite['name']} を実行中...")

            result = self._run_test_suite(
                suite["module"], suite["name"], suite.get("timeout", 300)
            )

            self.test_results[suite["name"]] = result

            # 結果の表示
            if result["success"]:
                print(f"✅ {suite['name']}: 成功 ({result['execution_time']:.2f}秒)")
            else:
                print(f"❌ {suite['name']}: 失敗 - {result['error']}")

            if result.get("warnings"):
                print(f"⚠️  警告: {len(result['warnings'])} 件")

            print()

        self.end_time = datetime.now()

        # 結果サマリーの生成
        summary = self._generate_summary()

        return {
            "summary": summary,
            "detailed_results": self.test_results,
            "execution_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration": (self.end_time - self.start_time).total_seconds(),
                "quick_mode": quick_mode,
            },
        }

    def _run_test_suite(self, module_name: str, suite_name: str, timeout: int) -> Dict:
        """個別テストスイートの実行"""
        start_time = time.time()

        try:
            # pytestを使用してテストを実行
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                module_name.replace(".", "/") + ".py",
                "-v",
                "--tb=short",
                "--disable-warnings",
            ]

            if self.verbose:
                cmd.append("-s")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
            )

            execution_time = time.time() - start_time

            # 結果の解析
            success = result.returncode == 0

            # 警告の抽出
            warnings = []
            if result.stdout:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "warning" in line.lower() or "warn" in line.lower():
                        warnings.append(line.strip())

            # テスト統計の抽出
            stats = self._extract_test_statistics(result.stdout)

            return {
                "success": success,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "warnings": warnings,
                "statistics": stats,
                "timeout_used": timeout,
            }

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "execution_time": execution_time,
                "error": f"テストがタイムアウトしました ({timeout}秒)",
                "timeout_expired": True,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "execution_time": execution_time,
                "error": f"テスト実行エラー: {str(e)}",
                "exception": True,
            }

    def _extract_test_statistics(self, output: str) -> Dict:
        """テスト統計情報の抽出"""
        stats = {"total_tests": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}

        try:
            lines = output.split("\n")
            for line in lines:
                # pytest の結果行を探す
                if "passed" in line and (
                    "failed" in line or "error" in line or "skipped" in line
                ):
                    # 例: "5 passed, 2 failed, 1 skipped in 10.5s"
                    import re

                    passed_match = re.search(r"(\d+)\s+passed", line)
                    if passed_match:
                        stats["passed"] = int(passed_match.group(1))

                    failed_match = re.search(r"(\d+)\s+failed", line)
                    if failed_match:
                        stats["failed"] = int(failed_match.group(1))

                    skipped_match = re.search(r"(\d+)\s+skipped", line)
                    if skipped_match:
                        stats["skipped"] = int(skipped_match.group(1))

                    error_match = re.search(r"(\d+)\s+error", line)
                    if error_match:
                        stats["errors"] = int(error_match.group(1))

                    stats["total_tests"] = (
                        stats["passed"]
                        + stats["failed"]
                        + stats["skipped"]
                        + stats["errors"]
                    )
                    break

        except Exception:
            # 統計抽出に失敗した場合はデフォルト値を使用
            pass

        return stats

    def _generate_summary(self) -> Dict:
        """テスト結果サマリーの生成"""
        total_suites = len(self.test_results)
        successful_suites = sum(
            1 for result in self.test_results.values() if result["success"]
        )
        failed_suites = total_suites - successful_suites

        total_execution_time = sum(
            result["execution_time"] for result in self.test_results.values()
        )

        # 全体統計の集計
        total_stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

        for result in self.test_results.values():
            stats = result.get("statistics", {})
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)

        # 警告の集計
        total_warnings = sum(
            len(result.get("warnings", [])) for result in self.test_results.values()
        )

        # 成功率の計算
        success_rate = (
            (successful_suites / total_suites * 100) if total_suites > 0 else 0
        )
        test_success_rate = (
            (total_stats["passed"] / total_stats["total_tests"] * 100)
            if total_stats["total_tests"] > 0
            else 0
        )

        return {
            "overall_success": failed_suites == 0,
            "success_rate": success_rate,
            "test_success_rate": test_success_rate,
            "suite_statistics": {
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "failed_suites": failed_suites,
            },
            "test_statistics": total_stats,
            "execution_summary": {
                "total_execution_time": total_execution_time,
                "average_suite_time": total_execution_time / total_suites
                if total_suites > 0
                else 0,
                "total_warnings": total_warnings,
            },
        }

    def generate_report(self, results: Dict, format_type: str = "text") -> str:
        """テストレポートの生成"""
        if format_type == "json":
            return json.dumps(results, indent=2, ensure_ascii=False)

        # テキスト形式のレポート
        summary = results["summary"]
        execution_info = results["execution_info"]

        report_lines = [
            "=" * 80,
            "GitHub Actions Simulator - 包括的テストスイート実行レポート",
            "=" * 80,
            "",
            f"🕐 実行時刻: {execution_info['start_time']} - {execution_info['end_time']}",
            f"⏱️ 総実行時間: {execution_info['total_duration']:.2f}秒",
            f"🏃 実行モード: {'クイック' if execution_info['quick_mode'] else 'フル'}",
            "",
            "📊 全体サマリー:",
            f"  🎯 全体成功率: {summary['success_rate']:.1f}%",
            f"  🧪 テスト成功率: {summary['test_success_rate']:.1f}%",
            f"  ✅ 成功スイート: {summary['suite_statistics']['successful_suites']}/{summary['suite_statistics']['total_suites']}",
            f"  ❌ 失敗スイート: {summary['suite_statistics']['failed_suites']}",
            "",
            "🧪 テスト統計:",
            f"  📋 総テスト数: {summary['test_statistics']['total_tests']}",
            f"  ✅ 成功: {summary['test_statistics']['passed']}",
            f"  ❌ 失敗: {summary['test_statistics']['failed']}",
            f"  ⏭️ スキップ: {summary['test_statistics']['skipped']}",
            f"  🚨 エラー: {summary['test_statistics']['errors']}",
            f"  ⚠️ 警告: {summary['execution_summary']['total_warnings']}",
            "",
            "📋 詳細結果:",
            "-" * 80,
        ]

        # 各テストスイートの詳細結果
        for suite_name, result in results["detailed_results"].items():
            status_icon = "✅" if result["success"] else "❌"
            report_lines.append(f"{status_icon} {suite_name}")
            report_lines.append(f"  ⏱️ 実行時間: {result['execution_time']:.2f}秒")

            if result.get("statistics"):
                stats = result["statistics"]
                if stats["total_tests"] > 0:
                    report_lines.append(
                        f"  🧪 テスト: {stats['passed']}/{stats['total_tests']} 成功"
                    )

            if result.get("warnings"):
                report_lines.append(f"  ⚠️ 警告: {len(result['warnings'])} 件")

            if not result["success"]:
                error_msg = result.get("error", "不明なエラー")
                report_lines.append(f"  🚨 エラー: {error_msg}")

            report_lines.append("")

        # 推奨事項
        if summary["suite_statistics"]["failed_suites"] > 0:
            report_lines.extend(
                [
                    "💡 推奨事項:",
                    "  1. 失敗したテストスイートの詳細ログを確認してください",
                    "  2. 依存関係とシステム要件を確認してください",
                    "  3. 必要に応じて個別のテストスイートを再実行してください",
                    "",
                ]
            )

        if summary["execution_summary"]["total_warnings"] > 0:
            report_lines.extend(
                [
                    "⚠️ 警告について:",
                    "  警告は機能に影響しない可能性がありますが、確認することを推奨します",
                    "",
                ]
            )

        report_lines.extend(
            [
                "=" * 80,
                f"テスト完了 - 全体成功: {'✅' if summary['overall_success'] else '❌'}",
                "=" * 80,
            ]
        )

        return "\n".join(report_lines)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="GitHub Actions Simulator 包括的テストスイート",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python tests/run_comprehensive_test_suite.py                    # フルテスト実行
  python tests/run_comprehensive_test_suite.py --quick           # クイックテスト実行
  python tests/run_comprehensive_test_suite.py --report          # 詳細レポート生成
  python tests/run_comprehensive_test_suite.py --output report.txt  # ファイル出力
        """,
    )

    parser.add_argument(
        "--quick", action="store_true", help="クイックテストのみ実行（必須テストのみ）"
    )

    parser.add_argument(
        "--full", action="store_true", help="フルテストスイートを実行（デフォルト）"
    )

    parser.add_argument("--report", action="store_true", help="詳細レポートを生成")

    parser.add_argument("--output", type=str, help="結果をファイルに出力")

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="出力形式（デフォルト: text）",
    )

    parser.add_argument("--verbose", action="store_true", help="詳細ログを出力")

    args = parser.parse_args()

    # プロジェクトルートの決定
    project_root = Path(__file__).parent.parent

    try:
        # テストランナーの初期化
        runner = ComprehensiveTestRunner(project_root, verbose=args.verbose)

        # テストの実行
        quick_mode = args.quick and not args.full
        results = runner.run_comprehensive_tests(quick_mode=quick_mode)

        # レポートの生成
        if args.report or args.output:
            report = runner.generate_report(results, args.format)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"📄 レポートを出力しました: {args.output}")
            else:
                print(report)
        else:
            # 簡潔なサマリーを表示
            summary = results["summary"]
            print("📊 テスト完了サマリー:")
            print(f"  全体成功: {'✅' if summary['overall_success'] else '❌'}")
            print(f"  成功率: {summary['success_rate']:.1f}%")
            print(f"  実行時間: {results['execution_info']['total_duration']:.2f}秒")

        # 終了コードの設定
        exit_code = 0 if results["summary"]["overall_success"] else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n⚠️ テスト実行が中断されました")
        sys.exit(130)

    except Exception as e:
        print(f"❌ テスト実行エラー: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
