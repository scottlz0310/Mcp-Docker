#!/usr/bin/env python3
"""
GitHub Actions Simulator - タイムアウトエスカレーション機能のデモ
改良されたProcessMonitorのタイムアウト処理とエスカレーション機能を実演します。
"""

import subprocess
import time
from services.actions.enhanced_act_wrapper import ProcessMonitor, MonitoredProcess
from services.actions.logger import ActionsLogger


def demo_timeout_escalation():
    """タイムアウトエスカレーション機能のデモ"""
    print("🚀 タイムアウトエスカレーション機能のデモを開始します")
    print("=" * 60)

    # ロガーとモニターを設定
    logger = ActionsLogger(verbose=True)
    monitor = ProcessMonitor(
        logger=logger,
        warning_timeout=5.0,      # 5秒で警告
        escalation_timeout=8.0,   # 8秒でエスカレーション
        heartbeat_interval=2.0,   # 2秒ごとにハートビート
        detailed_logging=True
    )

    print("📋 設定:")
    print("  - 警告タイムアウト: 5秒")
    print("  - エスカレーションタイムアウト: 8秒")
    print("  - 最終タイムアウト: 12秒")
    print("  - ハートビート間隔: 2秒")
    print()

    # 長時間実行されるプロセスをシミュレート（sleepコマンド）
    print("💤 長時間実行プロセスを開始します (sleep 15秒)...")

    try:
        # sleepプロセスを作成
        process = subprocess.Popen(
            ["sleep", "15"],  # 15秒間スリープ
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        monitored_process = MonitoredProcess(
            process=process,
            command=["sleep", "15"],
            start_time=time.time()
        )

        print(f"🔍 プロセス監視を開始: PID {process.pid}")
        print()

        # 改良されたプロセス監視を実行
        timed_out, deadlock_indicators = monitor.monitor_with_heartbeat(
            monitored_process,
            timeout=12  # 12秒でタイムアウト
        )

        print()
        print("📊 監視結果:")
        print(f"  - タイムアウト発生: {'はい' if timed_out else 'いいえ'}")
        print(f"  - 警告送信: {'はい' if monitor._warning_sent else 'いいえ'}")
        print(f"  - エスカレーション開始: {'はい' if monitor._escalation_started else 'いいえ'}")
        print(f"  - 強制終了: {'はい' if monitored_process.force_killed else 'いいえ'}")
        print(f"  - デッドロック指標数: {len(deadlock_indicators)}")

        # パフォーマンスメトリクスを表示
        metrics = monitor.get_performance_metrics()
        print()
        print("📈 パフォーマンスメトリクス:")
        for key, value in metrics["performance_metrics"].items():
            print(f"  - {key}: {value}")

    except KeyboardInterrupt:
        print("\n⚠️  ユーザーによって中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    finally:
        # プロセスが残っている場合はクリーンアップ
        if 'process' in locals() and process.poll() is None:
            print("\n🧹 プロセスクリーンアップを実行中...")
            monitor.force_cleanup_on_timeout(monitored_process)

    print()
    print("✅ デモ完了")


def demo_normal_completion():
    """正常完了のデモ"""
    print("\n🎯 正常完了のデモを開始します")
    print("=" * 60)

    logger = ActionsLogger(verbose=True)
    monitor = ProcessMonitor(
        logger=logger,
        warning_timeout=10.0,     # 10秒で警告（短いプロセスなので発生しない）
        escalation_timeout=15.0,  # 15秒でエスカレーション
        heartbeat_interval=1.0,   # 1秒ごとにハートビート
        detailed_logging=True
    )

    print("💤 短時間実行プロセスを開始します (sleep 3秒)...")

    try:
        # 短時間のsleepプロセスを作成
        process = subprocess.Popen(
            ["sleep", "3"],  # 3秒間スリープ
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        monitored_process = MonitoredProcess(
            process=process,
            command=["sleep", "3"],
            start_time=time.time()
        )

        print(f"🔍 プロセス監視を開始: PID {process.pid}")
        print()

        # プロセス監視を実行
        timed_out, deadlock_indicators = monitor.monitor_with_heartbeat(
            monitored_process,
            timeout=20  # 20秒でタイムアウト（十分な時間）
        )

        print()
        print("📊 監視結果:")
        print(f"  - タイムアウト発生: {'はい' if timed_out else 'いいえ'}")
        print(f"  - 正常完了: {'はい' if not timed_out else 'いいえ'}")
        print(f"  - 終了コード: {process.returncode}")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")

    print("✅ 正常完了デモ完了")


if __name__ == "__main__":
    print("🎭 GitHub Actions Simulator - タイムアウトエスカレーション機能デモ")
    print("=" * 80)
    print()

    # デモ1: タイムアウトエスカレーション
    demo_timeout_escalation()

    # デモ2: 正常完了
    demo_normal_completion()

    print()
    print("🎉 全てのデモが完了しました！")
    print()
    print("📝 このデモでは以下の機能を確認できました:")
    print("  ✓ 段階的タイムアウト処理（警告 → エスカレーション → 強制終了）")
    print("  ✓ 改良されたハートビートログ")
    print("  ✓ リソース使用量監視")
    print("  ✓ 詳細なプロセス診断")
    print("  ✓ 適切なリソース解放")
    print("  ✓ パフォーマンスメトリクス収集")
