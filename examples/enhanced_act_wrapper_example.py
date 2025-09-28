#!/usr/bin/env python3
"""
GitHub Actions Simulator - EnhancedActWrapper使用例
改良されたActWrapperの診断機能とプロセス監視機能のデモンストレーション
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.diagnostic import DiagnosticService
from services.actions.execution_tracer import ExecutionTracer
from services.actions.logger import ActionsLogger


def main():
    """EnhancedActWrapperの使用例"""
    print("=== GitHub Actions Simulator - EnhancedActWrapper デモ ===\n")

    # ログ設定
    logger = ActionsLogger(verbose=True)

    # 実行トレーサーを初期化
    execution_tracer = ExecutionTracer(
        logger=logger,
        heartbeat_interval=10.0,  # 10秒間隔でハートビート
        resource_monitoring_interval=2.0,  # 2秒間隔でリソース監視
        enable_detailed_logging=True,
    )

    # 診断サービスを初期化
    diagnostic_service = DiagnosticService(logger=logger)

    # EnhancedActWrapperを初期化
    wrapper = EnhancedActWrapper(
        working_directory=".",
        logger=logger,
        execution_tracer=execution_tracer,
        diagnostic_service=diagnostic_service,
        enable_diagnostics=True,
        deadlock_detection_interval=5.0,  # 5秒間隔でデッドロック検出
        activity_timeout=30.0,  # 30秒のアクティビティタイムアウト
    )

    # モックモードを有効にしてテスト実行
    os.environ["ACTIONS_SIMULATOR_ENGINE"] = "mock"
    os.environ["ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS"] = "1"

    try:
        print("1. システムヘルスチェックを実行中...")
        health_report = diagnostic_service.run_comprehensive_health_check()

        print("\n=== システムヘルスレポート ===")
        print(f"全体ステータス: {health_report.overall_status.value}")
        print(f"サマリー: {health_report.summary}")

        if health_report.has_errors:
            print("\n⚠️ エラーが検出されました:")
            for result in health_report.results:
                if result.status.value == "ERROR":
                    print(f"  - {result.component}: {result.message}")
                    for rec in result.recommendations:
                        print(f"    推奨: {rec}")

        if health_report.has_warnings:
            print("\n⚠️ 警告が検出されました:")
            for result in health_report.results:
                if result.status.value == "WARNING":
                    print(f"  - {result.component}: {result.message}")

        print("\n2. 診断機能付きワークフロー実行を開始...")

        # テスト用のワークフローファイルを作成
        test_workflow = Path("test_workflow_demo.yml")
        test_workflow.write_text("""
name: Demo Workflow
on: [push]
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - name: Demo step
        run: echo "Enhanced ActWrapper Demo!"
      - name: Another step
        run: echo "プロセス監視とデッドロック検出のテスト"
""")

        try:
            # 診断機能付きでワークフローを実行
            result = wrapper.run_workflow_with_diagnostics(
                workflow_file="test_workflow_demo.yml",
                dry_run=True,
                verbose=True,
                pre_execution_diagnostics=True,
            )

            print("\n=== 実行結果 ===")
            print(f"成功: {result.success}")
            print(f"終了コード: {result.returncode}")
            print(f"実行時間: {result.execution_time_ms:.2f}ms")
            print(f"コマンド: {result.command}")

            if result.stdout:
                print("\n標準出力:")
                print(result.stdout)

            if result.stderr:
                print("\n標準エラー:")
                print(result.stderr)

            # 診断結果を表示
            if result.diagnostic_results:
                print(f"\n=== 診断結果 ({len(result.diagnostic_results)}項目) ===")
                for diag in result.diagnostic_results:
                    status_icon = (
                        "✅"
                        if diag.status.value == "OK"
                        else "⚠️"
                        if diag.status.value == "WARNING"
                        else "❌"
                    )
                    print(f"{status_icon} {diag.component}: {diag.message}")

            # デッドロック指標を表示
            if result.deadlock_indicators:
                print(
                    f"\n=== デッドロック指標 ({len(result.deadlock_indicators)}項目) ==="
                )
                for indicator in result.deadlock_indicators:
                    print(f"⚠️ {indicator.deadlock_type.value}: {indicator.details}")
                    for rec in indicator.recommendations:
                        print(f"  推奨: {rec}")

            # プロセス監視データを表示
            if result.process_monitoring_data:
                print("\n=== プロセス監視データ ===")
                for key, value in result.process_monitoring_data.items():
                    print(f"  {key}: {value}")

            # ハングアップ分析を表示
            if result.hang_analysis:
                print("\n=== ハングアップ分析 ===")
                if result.hang_analysis.get("hang_detected"):
                    print("⚠️ ハングアップが検出されました")
                    for cause in result.hang_analysis.get("potential_causes", []):
                        print(f"  潜在的原因: {cause}")
                    for rec in result.hang_analysis.get("recommendations", []):
                        print(f"  推奨: {rec}")
                else:
                    print("✅ ハングアップは検出されませんでした")

        finally:
            # テストファイルをクリーンアップ
            if test_workflow.exists():
                test_workflow.unlink()

        print("\n3. 実行トレース情報...")
        current_trace = execution_tracer.get_current_trace()
        if current_trace:
            print(f"トレースID: {current_trace.trace_id}")
            print(f"現在のステージ: {current_trace.current_stage.value}")
            print(f"実行段階: {[stage.value for stage in current_trace.stages]}")
            print(f"リソース使用量記録数: {len(current_trace.resource_usage)}")
            print(f"プロセストレース数: {len(current_trace.process_traces)}")
            print(f"スレッドトレース数: {len(current_trace.thread_traces)}")
            print(f"Docker操作数: {len(current_trace.docker_operations)}")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 環境変数をクリーンアップ
        if "ACTIONS_SIMULATOR_ENGINE" in os.environ:
            del os.environ["ACTIONS_SIMULATOR_ENGINE"]
        if "ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS" in os.environ:
            del os.environ["ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS"]

    print("\n=== デモ完了 ===")


if __name__ == "__main__":
    main()
