#!/usr/bin/env python3
"""
GitHub Actions Simulator - 包括的統合テスト実行スクリプト
タスク15: 統合テストと最終検証の完全実装

このスクリプトは以下のテストを順次実行し、最終的な検証レポートを生成します:
1. 全コンポーネントの統合テスト
2. 実際のワークフローファイルでのエンドツーエンドテスト
3. パフォーマンスと安定性の検証
4. 既存のテストスイートの実行
5. 最終的な要件検証レポートの生成
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# テストモジュールをインポート
from test_comprehensive_integration import ComprehensiveIntegrationTest
from test_end_to_end_validation import EndToEndValidationTest
from test_performance_stability_validation import PerformanceStabilityValidator

from services.actions.logger import ActionsLogger


class ComprehensiveTestRunner:
    """包括的テスト実行クラス"""

    def __init__(self):
        self.logger = ActionsLogger(verbose=True, debug=False)
        self.test_results = {}
        self.start_time = time.time()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def run_existing_test_suite(self) -> Dict[str, any]:
        """既存のテストスイートを実行"""
        self.logger.info("既存のテストスイートを実行中...")

        results = {
            "pytest_results": {},
            "bats_results": {},
            "integration_script_results": {},
        }

        # 1. pytest テストの実行
        self.logger.info("pytest テストを実行中...")
        pytest_files = [
            "tests/test_diagnostic_service.py",
            "tests/test_execution_tracer.py",
            "tests/test_enhanced_act_wrapper.py",
            "tests/test_hangup_detector.py",
            "tests/test_auto_recovery.py",
            "tests/test_hangup_scenarios_comprehensive.py",
            "tests/test_logger.py",
            "tests/test_workflow_parser.py",
            "tests/test_output.py",
            "tests/test_expression.py",
        ]

        for test_file in pytest_files:
            if Path(test_file).exists():
                try:
                    self.logger.info(f"実行中: {test_file}")
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5分でタイムアウト
                    )

                    results["pytest_results"][test_file] = {
                        "return_code": result.returncode,
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }

                    if result.returncode == 0:
                        self.logger.info(f"✅ {test_file} 成功")
                    else:
                        self.logger.error(
                            f"❌ {test_file} 失敗 (終了コード: {result.returncode})"
                        )

                except subprocess.TimeoutExpired:
                    self.logger.error(f"⏰ {test_file} タイムアウト")
                    results["pytest_results"][test_file] = {
                        "return_code": -1,
                        "success": False,
                        "error": "timeout",
                    }
                except Exception as e:
                    self.logger.error(f"❌ {test_file} 実行エラー: {e}")
                    results["pytest_results"][test_file] = {
                        "return_code": -1,
                        "success": False,
                        "error": str(e),
                    }
            else:
                self.logger.warning(f"⚠️ テストファイルが見つかりません: {test_file}")

        # 2. Bats テストの実行（利用可能な場合）
        self.logger.info("Bats テストを実行中...")
        bats_files = [
            "tests/test_docker_build.bats",
            "tests/test_services.bats",
            "tests/test_integration.bats",
            "tests/test_actions_simulator.bats",
        ]

        if self._is_bats_available():
            for bats_file in bats_files:
                if Path(bats_file).exists():
                    try:
                        self.logger.info(f"実行中: {bats_file}")
                        result = subprocess.run(
                            ["bats", bats_file],
                            capture_output=True,
                            text=True,
                            timeout=300,
                        )

                        results["bats_results"][bats_file] = {
                            "return_code": result.returncode,
                            "success": result.returncode == 0,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                        }

                        if result.returncode == 0:
                            self.logger.info(f"✅ {bats_file} 成功")
                        else:
                            self.logger.error(f"❌ {bats_file} 失敗")

                    except subprocess.TimeoutExpired:
                        self.logger.error(f"⏰ {bats_file} タイムアウト")
                        results["bats_results"][bats_file] = {
                            "return_code": -1,
                            "success": False,
                            "error": "timeout",
                        }
                    except Exception as e:
                        self.logger.error(f"❌ {bats_file} 実行エラー: {e}")
                        results["bats_results"][bats_file] = {
                            "return_code": -1,
                            "success": False,
                            "error": str(e),
                        }
        else:
            self.logger.warning(
                "⚠️ Bats が利用できません。Bats テストをスキップします。"
            )

        # 3. 統合テストスクリプトの実行
        integration_script = Path("tests/integration_test.sh")
        if integration_script.exists():
            try:
                self.logger.info("統合テストスクリプトを実行中...")
                result = subprocess.run(
                    ["bash", str(integration_script)],
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10分でタイムアウト
                )

                results["integration_script_results"] = {
                    "return_code": result.returncode,
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

                if result.returncode == 0:
                    self.logger.info("✅ 統合テストスクリプト 成功")
                else:
                    self.logger.error("❌ 統合テストスクリプト 失敗")

            except subprocess.TimeoutExpired:
                self.logger.error("⏰ 統合テストスクリプト タイムアウト")
                results["integration_script_results"] = {
                    "return_code": -1,
                    "success": False,
                    "error": "timeout",
                }
            except Exception as e:
                self.logger.error(f"❌ 統合テストスクリプト 実行エラー: {e}")
                results["integration_script_results"] = {
                    "return_code": -1,
                    "success": False,
                    "error": str(e),
                }

        return results

    def run_comprehensive_integration_tests(self) -> Dict[str, any]:
        """包括的統合テストを実行"""
        self.logger.info("包括的統合テストを実行中...")

        try:
            integration_tester = ComprehensiveIntegrationTest()
            return integration_tester.run_all_tests()
        except Exception as e:
            self.logger.error(f"包括的統合テスト中にエラー: {e}")
            return {"error": str(e), "summary": {"overall_success": False}}

    def run_end_to_end_validation(self) -> Dict[str, any]:
        """エンドツーエンド検証テストを実行"""
        self.logger.info("エンドツーエンド検証テストを実行中...")

        try:
            e2e_tester = EndToEndValidationTest()
            return e2e_tester.run_comprehensive_end_to_end_tests()
        except Exception as e:
            self.logger.error(f"エンドツーエンド検証テスト中にエラー: {e}")
            return {"error": str(e), "summary": {"overall_success": False}}

    def run_performance_stability_validation(self) -> Dict[str, any]:
        """パフォーマンス・安定性検証テストを実行"""
        self.logger.info("パフォーマンス・安定性検証テストを実行中...")

        try:
            perf_validator = PerformanceStabilityValidator()
            return perf_validator.run_comprehensive_performance_stability_tests()
        except Exception as e:
            self.logger.error(f"パフォーマンス・安定性検証テスト中にエラー: {e}")
            return {"error": str(e), "summary": {"overall_success": False}}

    def validate_requirements(self) -> Dict[str, bool]:
        """要件5.1-5.4の検証"""
        self.logger.info("要件検証を実行中...")

        validation_results = {}

        # Requirement 5.1: 様々なワークフローファイルでの成功実行
        e2e_results = self.test_results.get("end_to_end_validation", {})
        req_5_1 = (
            e2e_results.get("requirements_validation", {}).get("requirement_5_1", False)
            and e2e_results.get("summary", {}).get(
                "simulation_execution_success_rate", 0
            )
            >= 0.8
        )
        validation_results["requirement_5_1"] = req_5_1

        # Requirement 5.2: タイムアウトシナリオの適切な処理
        req_5_2 = (
            e2e_results.get("requirements_validation", {}).get("requirement_5_2", False)
            and e2e_results.get("summary", {}).get("timeout_handling_success_rate", 0)
            >= 0.8
        )
        validation_results["requirement_5_2"] = req_5_2

        # Requirement 5.3: 安定性とパフォーマンス
        perf_results = self.test_results.get("performance_stability_validation", {})
        integration_results = self.test_results.get("comprehensive_integration", {})

        req_5_3 = (
            perf_results.get("requirements_validation", {}).get(
                "requirement_5_3_stability", False
            )
            and perf_results.get("requirements_validation", {}).get(
                "requirement_5_3_performance", False
            )
            and perf_results.get("requirements_validation", {}).get(
                "requirement_5_3_memory_management", False
            )
            and integration_results.get("summary", {}).get(
                "performance_acceptable", False
            )
        )
        validation_results["requirement_5_3"] = req_5_3

        # Requirement 5.4: 様々なワークフロー設定の処理
        req_5_4 = (
            e2e_results.get("requirements_validation", {}).get("requirement_5_4", False)
            and e2e_results.get("summary", {}).get("workflow_parsing_success_rate", 0)
            >= 0.9
        )
        validation_results["requirement_5_4"] = req_5_4

        return validation_results

    def generate_final_report(self) -> Dict[str, any]:
        """最終的な検証レポートを生成"""
        total_time = time.time() - self.start_time

        # 要件検証
        requirements_validation = self.validate_requirements()

        # 既存テストスイートの成功率計算
        existing_tests = self.test_results.get("existing_test_suite", {})
        pytest_success_rate = self._calculate_test_success_rate(
            existing_tests.get("pytest_results", {})
        )
        bats_success_rate = self._calculate_test_success_rate(
            existing_tests.get("bats_results", {})
        )
        integration_script_success = existing_tests.get(
            "integration_script_results", {}
        ).get("success", False)

        # 新規テストの成功判定
        comprehensive_success = (
            self.test_results.get("comprehensive_integration", {})
            .get("summary", {})
            .get("overall_success", False)
        )
        e2e_success = (
            self.test_results.get("end_to_end_validation", {})
            .get("summary", {})
            .get("overall_success", False)
        )
        perf_success = (
            self.test_results.get("performance_stability_validation", {})
            .get("summary", {})
            .get("overall_success", False)
        )

        # 総合成功判定
        all_requirements_met = all(requirements_validation.values())
        all_new_tests_passed = all([comprehensive_success, e2e_success, perf_success])
        existing_tests_acceptable = (
            pytest_success_rate >= 0.8 and integration_script_success
        )

        overall_success = (
            all_requirements_met and all_new_tests_passed and existing_tests_acceptable
        )

        return {
            "test_execution_summary": {
                "start_time": datetime.fromtimestamp(
                    self.start_time, tz=timezone.utc
                ).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_duration_seconds": total_time,
                "total_duration_minutes": total_time / 60,
            },
            "requirements_validation": requirements_validation,
            "test_suite_results": {
                "existing_tests": {
                    "pytest_success_rate": pytest_success_rate,
                    "bats_success_rate": bats_success_rate,
                    "integration_script_success": integration_script_success,
                },
                "new_integration_tests": {
                    "comprehensive_integration_success": comprehensive_success,
                    "end_to_end_validation_success": e2e_success,
                    "performance_stability_success": perf_success,
                },
            },
            "detailed_results": self.test_results,
            "summary": {
                "overall_success": overall_success,
                "all_requirements_met": all_requirements_met,
                "all_new_tests_passed": all_new_tests_passed,
                "existing_tests_acceptable": existing_tests_acceptable,
                "task_15_completed": overall_success,
            },
            "recommendations": self._generate_recommendations(),
        }

    def _calculate_test_success_rate(self, test_results: Dict) -> float:
        """テスト成功率を計算"""
        if not test_results:
            return 0.0

        successful = sum(
            1 for result in test_results.values() if result.get("success", False)
        )
        total = len(test_results)

        return successful / total if total > 0 else 0.0

    def _is_bats_available(self) -> bool:
        """Batsが利用可能かチェック"""
        try:
            result = subprocess.run(
                ["bats", "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def _generate_recommendations(self) -> List[str]:
        """改善推奨事項を生成"""
        recommendations = []

        # 要件検証結果に基づく推奨事項
        requirements = self.validate_requirements()

        if not requirements.get("requirement_5_1", True):
            recommendations.append(
                "Requirement 5.1: ワークフロー実行の成功率を向上させる必要があります。エラーハンドリングとワークフロー解析の改善を検討してください。"
            )

        if not requirements.get("requirement_5_2", True):
            recommendations.append(
                "Requirement 5.2: タイムアウト処理の改善が必要です。タイムアウト検出とエラーメッセージの改善を検討してください。"
            )

        if not requirements.get("requirement_5_3", True):
            recommendations.append(
                "Requirement 5.3: パフォーマンスと安定性の改善が必要です。メモリ使用量の最適化と並行処理の安定性向上を検討してください。"
            )

        if not requirements.get("requirement_5_4", True):
            recommendations.append(
                "Requirement 5.4: ワークフロー設定の処理能力向上が必要です。複雑なワークフロー構文のサポート強化を検討してください。"
            )

        # テスト結果に基づく推奨事項
        existing_tests = self.test_results.get("existing_test_suite", {})
        pytest_success_rate = self._calculate_test_success_rate(
            existing_tests.get("pytest_results", {})
        )

        if pytest_success_rate < 0.9:
            recommendations.append(
                "既存のpytestテストの成功率が低いです。失敗しているテストの原因を調査し、修正してください。"
            )

        perf_results = self.test_results.get("performance_stability_validation", {})
        if not perf_results.get("summary", {}).get(
            "memory_leak_detection_passed", True
        ):
            recommendations.append(
                "メモリリークが検出されました。メモリ管理の改善とリソースの適切な解放を実装してください。"
            )

        if not perf_results.get("summary", {}).get(
            "concurrent_execution_stability_passed", True
        ):
            recommendations.append(
                "並行実行時の安定性に問題があります。スレッドセーフティとリソース競合の解決を検討してください。"
            )

        if not recommendations:
            recommendations.append(
                "全ての要件とテストが成功しています。現在の実装品質を維持し、継続的な監視を行ってください。"
            )

        return recommendations

    def run_all_tests(self) -> Dict[str, any]:
        """全ての統合テストを実行"""
        self.logger.info(
            "GitHub Actions Simulator 包括的統合テストスイートを開始します..."
        )
        self.logger.info("=" * 80)

        try:
            # 1. 既存のテストスイートを実行
            self.logger.info("フェーズ 1: 既存のテストスイート実行")
            self.test_results["existing_test_suite"] = self.run_existing_test_suite()

            # 2. 包括的統合テストを実行
            self.logger.info("フェーズ 2: 包括的統合テスト実行")
            self.test_results["comprehensive_integration"] = (
                self.run_comprehensive_integration_tests()
            )

            # 3. エンドツーエンド検証テストを実行
            self.logger.info("フェーズ 3: エンドツーエンド検証テスト実行")
            self.test_results["end_to_end_validation"] = (
                self.run_end_to_end_validation()
            )

            # 4. パフォーマンス・安定性検証テストを実行
            self.logger.info("フェーズ 4: パフォーマンス・安定性検証テスト実行")
            self.test_results["performance_stability_validation"] = (
                self.run_performance_stability_validation()
            )

            # 5. 最終レポートを生成
            self.logger.info("フェーズ 5: 最終レポート生成")
            final_report = self.generate_final_report()

            # レポートをファイルに保存
            report_file = self.output_dir / "final_integration_test_report.json"
            report_file.write_text(
                json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            self.logger.info(f"最終レポートが保存されました: {report_file}")

            return final_report

        except Exception as e:
            self.logger.error(f"統合テスト実行中に予期しないエラーが発生しました: {e}")
            return {
                "error": str(e),
                "summary": {"overall_success": False, "task_15_completed": False},
            }

    def print_summary_report(self, final_report: Dict[str, any]) -> None:
        """サマリーレポートを出力"""
        print("\n" + "=" * 80)
        print("GitHub Actions Simulator - 包括的統合テスト最終レポート")
        print("=" * 80)

        summary = final_report["summary"]
        requirements = final_report["requirements_validation"]
        test_suites = final_report["test_suite_results"]

        # 総合結果
        print(
            f"\n🎯 タスク15完了状況: {'✅ 完了' if summary['task_15_completed'] else '❌ 未完了'}"
        )
        print(f"📊 総合成功: {'✅ 成功' if summary['overall_success'] else '❌ 失敗'}")

        # 要件検証結果
        print("\n📋 要件検証結果:")
        print(
            f"  Requirement 5.1 (ワークフロー実行): {'✅' if requirements['requirement_5_1'] else '❌'}"
        )
        print(
            f"  Requirement 5.2 (タイムアウト処理): {'✅' if requirements['requirement_5_2'] else '❌'}"
        )
        print(
            f"  Requirement 5.3 (安定性・パフォーマンス): {'✅' if requirements['requirement_5_3'] else '❌'}"
        )
        print(
            f"  Requirement 5.4 (ワークフロー設定): {'✅' if requirements['requirement_5_4'] else '❌'}"
        )

        # テストスイート結果
        print("\n🧪 テストスイート結果:")
        existing = test_suites["existing_tests"]
        new_tests = test_suites["new_integration_tests"]

        print("  既存テスト:")
        print(f"    pytest成功率: {existing['pytest_success_rate']:.1%}")
        print(
            f"    統合スクリプト: {'✅' if existing['integration_script_success'] else '❌'}"
        )

        print("  新規統合テスト:")
        print(
            f"    包括的統合テスト: {'✅' if new_tests['comprehensive_integration_success'] else '❌'}"
        )
        print(
            f"    エンドツーエンド検証: {'✅' if new_tests['end_to_end_validation_success'] else '❌'}"
        )
        print(
            f"    パフォーマンス・安定性: {'✅' if new_tests['performance_stability_success'] else '❌'}"
        )

        # 実行時間
        execution = final_report["test_execution_summary"]
        print(f"\n⏱️  実行時間: {execution['total_duration_minutes']:.1f}分")

        # 推奨事項
        recommendations = final_report["recommendations"]
        if recommendations:
            print("\n💡 推奨事項:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

        print("\n" + "=" * 80)


def main():
    """メイン実行関数"""
    runner = ComprehensiveTestRunner()

    try:
        # 全テストを実行
        final_report = runner.run_all_tests()

        # サマリーレポートを出力
        runner.print_summary_report(final_report)

        # 終了コードを決定
        success = final_report["summary"]["overall_success"]
        task_completed = final_report["summary"]["task_15_completed"]

        if task_completed:
            print("🎉 タスク15「統合テストと最終検証」が正常に完了しました！")
            return 0
        elif success:
            print("⚠️ テストは成功しましたが、一部の要件が未達成です。")
            return 1
        else:
            print(
                "❌ 統合テストが失敗しました。詳細は上記のレポートを確認してください。"
            )
            return 2

    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによってテストが中断されました。")
        return 130
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
