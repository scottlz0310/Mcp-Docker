#!/usr/bin/env python3
"""
GitHub Actions Simulator - AutoRecovery デモンストレーション
自動復旧メカニズムの機能をデモンストレーションします。
"""

import tempfile
from pathlib import Path

from services.actions.auto_recovery import AutoRecovery
from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.logger import ActionsLogger


def demo_auto_recovery_basic():
    """基本的な自動復旧機能のデモ"""
    print("=== AutoRecovery 基本機能デモ ===")

    logger = ActionsLogger(verbose=True)
    auto_recovery = AutoRecovery(logger=logger)

    print("\n1. Docker再接続テスト")
    success = auto_recovery.attempt_docker_reconnection()
    print(f"Docker再接続結果: {'成功' if success else '失敗'}")

    print("\n2. 出力バッファクリア")
    auto_recovery.clear_output_buffers()
    print("出力バッファクリア完了")

    print("\n3. コンテナ状態リセット")
    success = auto_recovery.reset_container_state()
    print(f"コンテナ状態リセット結果: {'成功' if success else '失敗'}")

    print("\n4. 復旧統計情報")
    stats = auto_recovery.get_recovery_statistics()
    print(f"復旧統計: {stats}")


def demo_fallback_execution():
    """フォールバック実行のデモ"""
    print("\n=== フォールバック実行デモ ===")

    logger = ActionsLogger(verbose=True)
    auto_recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)

    # 一時的なワークフローファイルを作成
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("""
name: Demo Workflow
on: push
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - name: Hello World
        run: echo "Hello, World!"
      - name: Show Date
        run: date
""")
        workflow_file = Path(f.name)

    try:
        print(f"\n1. ワークフローファイル作成: {workflow_file}")

        print("\n2. フォールバック実行テスト")
        result = auto_recovery.execute_fallback_mode(workflow_file, ["act", "--list"])

        print(f"フォールバック実行結果: {'成功' if result.success else '失敗'}")
        print(f"使用方法: {result.fallback_method}")
        print(f"実行時間: {result.execution_time_ms:.2f}ms")

        if result.limitations:
            print(f"制限事項: {result.limitations}")

        if result.warnings:
            print(f"警告: {result.warnings}")

        if result.stdout:
            print(f"出力:\n{result.stdout[:200]}...")

    finally:
        workflow_file.unlink()


def demo_enhanced_act_wrapper_with_recovery():
    """EnhancedActWrapper with AutoRecovery のデモ"""
    print("\n=== EnhancedActWrapper with AutoRecovery デモ ===")

    logger = ActionsLogger(verbose=True)
    wrapper = EnhancedActWrapper(logger=logger, enable_diagnostics=True)

    # 一時的なワークフローファイルを作成
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("""
name: Test Workflow
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test Step
        run: echo "Testing AutoRecovery"
""")
        workflow_file = f.name

    try:
        print(f"\n1. ワークフローファイル: {workflow_file}")

        print("\n2. 自動復旧統計（実行前）")
        stats_before = wrapper.get_auto_recovery_statistics()
        print(f"実行前統計: {stats_before}")

        print("\n3. 自動復旧機能付きワークフロー実行（ドライランモード）")
        result = wrapper.run_workflow_with_auto_recovery(
            workflow_file=workflow_file,
            dry_run=True,
            enable_recovery=True,
            max_recovery_attempts=1,
        )

        print(f"実行結果: {'成功' if result.success else '失敗'}")
        print(f"終了コード: {result.returncode}")
        print(f"実行時間: {result.execution_time_ms:.2f}ms")

        if result.diagnostic_results:
            print(f"\n診断結果数: {len(result.diagnostic_results)}")
            for i, diag in enumerate(result.diagnostic_results[:3]):  # 最初の3個のみ表示
                print(f"  {i + 1}. {diag.component}: {diag.message}")

        print("\n4. 自動復旧統計（実行後）")
        stats_after = wrapper.get_auto_recovery_statistics()
        print(f"実行後統計: {stats_after}")

    finally:
        Path(workflow_file).unlink()


def demo_comprehensive_recovery():
    """包括的復旧処理のデモ"""
    print("\n=== 包括的復旧処理デモ ===")

    logger = ActionsLogger(verbose=True)
    auto_recovery = AutoRecovery(logger=logger)

    # 一時的なワークフローファイルを作成
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("name: recovery-test\non: push")
        workflow_file = Path(f.name)

    try:
        print(f"\n1. ワークフローファイル: {workflow_file}")

        print("\n2. 包括的復旧処理実行")
        session = auto_recovery.run_comprehensive_recovery(
            workflow_file=workflow_file, original_command=["act", "--dry-run"]
        )

        print(f"復旧セッションID: {session.session_id}")
        print(f"全体的成功: {'はい' if session.overall_success else 'いいえ'}")
        print(f"フォールバックモード使用: {'はい' if session.fallback_mode_activated else 'いいえ'}")
        print(f"復旧試行数: {len(session.attempts)}")

        if session.attempts:
            print("\n復旧試行詳細:")
            for i, attempt in enumerate(session.attempts):
                print(f"  {i + 1}. {attempt.recovery_type.value}: {attempt.status.value}")
                if attempt.message:
                    print(f"     メッセージ: {attempt.message}")

        if session.recovery_context:
            print(f"\n復旧コンテキスト: {session.recovery_context}")

    finally:
        workflow_file.unlink()


def main():
    """メインデモ実行"""
    print("GitHub Actions Simulator - AutoRecovery デモンストレーション")
    print("=" * 60)

    try:
        # 基本機能デモ
        demo_auto_recovery_basic()

        # フォールバック実行デモ
        demo_fallback_execution()

        # EnhancedActWrapper統合デモ
        demo_enhanced_act_wrapper_with_recovery()

        # 包括的復旧処理デモ
        demo_comprehensive_recovery()

        print("\n" + "=" * 60)
        print("デモンストレーション完了!")
        print("\nAutoRecovery機能の主な特徴:")
        print("- Docker再接続とサブプロセス再起動")
        print("- バッファクリアとコンテナ状態リセット")
        print("- フォールバック実行モード")
        print("- 包括的復旧セッション管理")
        print("- EnhancedActWrapperとの統合")

    except KeyboardInterrupt:
        print("\nデモが中断されました")
    except Exception as e:
        print(f"\nデモ実行中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
