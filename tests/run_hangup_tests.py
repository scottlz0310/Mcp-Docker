"""
GitHub Actions Simulator - ハングアップテスト実行スクリプト
包括的なハングアップシナリオテストを実行するためのスクリプト
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any


class HangupTestRunner:
    """ハングアップテスト実行クラス"""

    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.test_results: Dict[str, Any] = {}
        self.start_time = time.time()

    def run_unit_tests(self) -> bool:
        """単体テストを実行"""
        print("🧪 単体テスト実行中...")

        unit_test_files = [
            "test_diagnostic_service.py",
            "test_improved_process_monitor.py",
            "test_execution_tracer.py",
            "test_hangup_detector.py",
            "test_enhanced_act_wrapper.py",
            "test_auto_recovery.py",
        ]

        success_count = 0
        total_count = len(unit_test_files)

        for test_file in unit_test_files:
            test_path = Path("tests") / test_file
            if test_path.exists():
                print(f"  📝 実行中: {test_file}")
                success = self._run_single_test(test_path)
                if success:
                    success_count += 1
                    print(f"  ✅ 成功: {test_file}")
                else:
                    print(f"  ❌ 失敗: {test_file}")

                self.test_results[test_file] = {
                    "type": "unit",
                    "success": success,
                    "file": str(test_path),
                }
            else:
                print(f"  ⚠️ 見つかりません: {test_file}")

        print(f"📊 単体テスト結果: {success_count}/{total_count} 成功")
        return success_count == total_count

    def run_integration_tests(self) -> bool:
        """統合テストを実行"""
        print("🔗 統合テスト実行中...")

        integration_test_files = [
            "test_hangup_scenarios_comprehensive.py",
            "test_hangup_integration.py",
            "test_docker_integration_complete.py",
        ]

        success_count = 0
        total_count = len(integration_test_files)

        for test_file in integration_test_files:
            test_path = Path("tests") / test_file
            if test_path.exists():
                print(f"  📝 実行中: {test_file}")
                success = self._run_single_test(test_path)
                if success:
                    success_count += 1
                    print(f"  ✅ 成功: {test_file}")
                else:
                    print(f"  ❌ 失敗: {test_file}")

                self.test_results[test_file] = {
                    "type": "integration",
                    "success": success,
                    "file": str(test_path),
                }
            else:
                print(f"  ⚠️ 見つかりません: {test_file}")

        print(f"📊 統合テスト結果: {success_count}/{total_count} 成功")
        return success_count == total_count

    def run_end_to_end_tests(self) -> bool:
        """エンドツーエンドテストを実行"""
        print("🎯 エンドツーエンドテスト実行中...")

        e2e_test_files = ["test_hangup_end_to_end.py"]

        success_count = 0
        total_count = len(e2e_test_files)

        for test_file in e2e_test_files:
            test_path = Path("tests") / test_file
            if test_path.exists():
                print(f"  📝 実行中: {test_file}")
                success = self._run_single_test(test_path)
                if success:
                    success_count += 1
                    print(f"  ✅ 成功: {test_file}")
                else:
                    print(f"  ❌ 失敗: {test_file}")

                self.test_results[test_file] = {
                    "type": "e2e",
                    "success": success,
                    "file": str(test_path),
                }
            else:
                print(f"  ⚠️ 見つかりません: {test_file}")

        print(f"📊 エンドツーエンドテスト結果: {success_count}/{total_count} 成功")
        return success_count == total_count

    def run_performance_tests(self) -> bool:
        """パフォーマンステストを実行"""
        print("⚡ パフォーマンステスト実行中...")

        # パフォーマンステストの実装
        # 現在は基本的なメモリ使用量とレスポンス時間をチェック

        try:
            import psutil
            import time

            # メモリ使用量チェック
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # 簡単なパフォーマンステストを実行
            start_time = time.time()

            # DiagnosticServiceのパフォーマンステスト
            from services.actions.diagnostic import DiagnosticService
            from services.actions.logger import ActionsLogger

            logger = ActionsLogger(verbose=False)
            diagnostic_service = DiagnosticService(logger=logger)

            # 複数回実行してパフォーマンスを測定
            for _ in range(10):
                _ = diagnostic_service.run_comprehensive_health_check()

            end_time = time.time()
            execution_time = end_time - start_time

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(f"  📊 実行時間: {execution_time:.2f}秒")
            print(f"  💾 メモリ増加: {memory_increase:.2f}MB")

            # パフォーマンス基準をチェック
            performance_ok = (
                execution_time < 30.0  # 30秒以内
                and memory_increase < 100.0  # 100MB以内の増加
            )

            if performance_ok:
                print("  ✅ パフォーマンステスト成功")
            else:
                print("  ❌ パフォーマンステスト失敗")

            self.test_results["performance"] = {
                "type": "performance",
                "success": performance_ok,
                "execution_time": execution_time,
                "memory_increase": memory_increase,
            }

            return performance_ok

        except ImportError:
            print("  ⚠️ psutilが利用できません。パフォーマンステストをスキップします。")
            return True
        except Exception as e:
            print(f"  ❌ パフォーマンステストエラー: {e}")
            return False

    def run_stress_tests(self) -> bool:
        """ストレステストを実行"""
        print("💪 ストレステスト実行中...")

        try:
            import threading

            from services.actions.diagnostic import DiagnosticService
            from services.actions.hangup_detector import HangupDetector
            from services.actions.logger import ActionsLogger

            logger = ActionsLogger(verbose=False)

            # 並行実行テスト
            results = []

            def stress_worker():
                try:
                    diagnostic_service = DiagnosticService(logger=logger)
                    hangup_detector = HangupDetector(logger=logger)

                    # 複数の診断を並行実行
                    diagnostic_service.run_comprehensive_health_check()
                    hangup_detector.analyze_hangup_conditions()

                    results.append(True)
                except Exception as e:
                    print(f"  ❌ ストレステストエラー: {e}")
                    results.append(False)

            # 10個のスレッドで並行実行
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=stress_worker)
                threads.append(thread)
                thread.start()

            # 全スレッドの完了を待機
            for thread in threads:
                thread.join(timeout=30)

            success_count = sum(results)
            total_count = len(results)

            print(f"  📊 並行実行結果: {success_count}/{total_count} 成功")

            stress_success = success_count >= total_count * 0.8  # 80%以上成功

            if stress_success:
                print("  ✅ ストレステスト成功")
            else:
                print("  ❌ ストレステスト失敗")

            self.test_results["stress"] = {
                "type": "stress",
                "success": stress_success,
                "success_rate": success_count / total_count if total_count > 0 else 0,
            }

            return stress_success

        except Exception as e:
            print(f"  ❌ ストレステストエラー: {e}")
            return False

    def _run_single_test(self, test_path: Path) -> bool:
        """単一のテストファイルを実行"""
        try:
            # pytestを使用してテストを実行
            cmd = [sys.executable, "-m", "pytest", str(test_path), "-v"]

            if not self.verbose:
                cmd.extend(["-q", "--tb=short"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分のタイムアウト
            )

            if self.verbose and result.stdout:
                print(f"    📄 出力: {result.stdout}")

            if result.stderr and self.verbose:
                print(f"    ⚠️ エラー: {result.stderr}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"    ⏰ タイムアウト: {test_path}")
            return False
        except Exception as e:
            print(f"    ❌ 実行エラー: {e}")
            return False

    def generate_report(self) -> None:
        """テスト結果レポートを生成"""
        total_time = time.time() - self.start_time

        print("\n" + "=" * 60)
        print("📋 ハングアップテスト結果レポート")
        print("=" * 60)

        # カテゴリ別結果
        categories = {
            "unit": "単体テスト",
            "integration": "統合テスト",
            "e2e": "エンドツーエンドテスト",
            "performance": "パフォーマンステスト",
            "stress": "ストレステスト",
        }

        for category, name in categories.items():
            category_tests = [
                test
                for test, result in self.test_results.items()
                if result.get("type") == category
            ]

            if category_tests:
                success_count = sum(
                    1 for test in category_tests if self.test_results[test]["success"]
                )
                total_count = len(category_tests)

                status = "✅" if success_count == total_count else "❌"
                print(f"{status} {name}: {success_count}/{total_count}")

                if self.verbose:
                    for test in category_tests:
                        result = self.test_results[test]
                        test_status = "✅" if result["success"] else "❌"
                        print(f"    {test_status} {test}")

        # 全体統計
        total_tests = len(self.test_results)
        successful_tests = sum(
            1 for result in self.test_results.values() if result["success"]
        )

        print(f"\n📊 全体結果: {successful_tests}/{total_tests} 成功")
        print(f"⏱️ 実行時間: {total_time:.2f}秒")

        # 成功率
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 成功率: {success_rate:.1f}%")

        # 推奨事項
        if success_rate < 100:
            print("\n💡 推奨事項:")
            print("  - 失敗したテストのログを確認してください")
            print("  - Docker環境が正常に動作していることを確認してください")
            print("  - 必要な依存関係がインストールされていることを確認してください")

        print("=" * 60)

    def run_all_tests(self) -> bool:
        """全てのテストを実行"""
        print("🚀 ハングアップシナリオテスト開始")
        print("=" * 60)

        # 環境チェック
        self._check_environment()

        # テスト実行
        unit_success = self.run_unit_tests()
        integration_success = self.run_integration_tests()
        e2e_success = self.run_end_to_end_tests()
        performance_success = self.run_performance_tests()
        stress_success = self.run_stress_tests()

        # レポート生成
        self.generate_report()

        # 全体結果
        overall_success = all(
            [
                unit_success,
                integration_success,
                e2e_success,
                performance_success,
                stress_success,
            ]
        )

        if overall_success:
            print("\n🎉 全てのハングアップテストが成功しました！")
        else:
            print("\n⚠️ 一部のテストが失敗しました。詳細を確認してください。")

        return overall_success

    def _check_environment(self) -> None:
        """環境をチェック"""
        print("🔍 環境チェック中...")

        # Python バージョン
        python_version = sys.version.split()[0]
        print(f"  🐍 Python: {python_version}")

        # 必要なモジュールの確認
        required_modules = ["pytest", "unittest", "pathlib", "subprocess"]

        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"  ✅ {module}: 利用可能")
            except ImportError:
                missing_modules.append(module)
                print(f"  ❌ {module}: 見つかりません")

        if missing_modules:
            print(f"  ⚠️ 不足モジュール: {', '.join(missing_modules)}")
            print("  💡 pip install pytest でインストールしてください")

        # 作業ディレクトリ
        cwd = Path.cwd()
        print(f"  📁 作業ディレクトリ: {cwd}")

        # テストディレクトリの確認
        tests_dir = Path("tests")
        if tests_dir.exists():
            print(f"  ✅ テストディレクトリ: {tests_dir}")
        else:
            print(f"  ❌ テストディレクトリが見つかりません: {tests_dir}")

        print()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="GitHub Actions Simulator ハングアップテスト実行スクリプト"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="詳細な出力を表示")

    parser.add_argument(
        "--parallel", "-p", action="store_true", help="並行実行を有効にする"
    )

    parser.add_argument("--unit-only", action="store_true", help="単体テストのみ実行")

    parser.add_argument(
        "--integration-only", action="store_true", help="統合テストのみ実行"
    )

    parser.add_argument(
        "--e2e-only", action="store_true", help="エンドツーエンドテストのみ実行"
    )

    args = parser.parse_args()

    # テストランナーを初期化
    runner = HangupTestRunner(verbose=args.verbose, parallel=args.parallel)

    # 指定されたテストタイプのみ実行
    if args.unit_only:
        success = runner.run_unit_tests()
    elif args.integration_only:
        success = runner.run_integration_tests()
    elif args.e2e_only:
        success = runner.run_end_to_end_tests()
    else:
        # 全てのテストを実行
        success = runner.run_all_tests()

    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
