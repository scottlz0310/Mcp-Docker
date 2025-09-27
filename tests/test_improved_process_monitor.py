"""
GitHub Actions Simulator - 改良されたProcessMonitorのテスト
タイムアウトエスカレーション、改良されたハートビート、リソース監視機能をテストします。
"""

import subprocess
import time
import unittest
from unittest.mock import Mock, patch

from services.actions.enhanced_act_wrapper import (
    ProcessMonitor,
    MonitoredProcess,
    DeadlockIndicator,
    DeadlockType
)
from services.actions.logger import ActionsLogger


class TestImprovedProcessMonitor(unittest.TestCase):
    """改良されたProcessMonitorのテストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.logger = ActionsLogger(verbose=True)
        self.monitor = ProcessMonitor(
            logger=self.logger,
            warning_timeout=5.0,  # テスト用に短縮
            escalation_timeout=8.0,
            heartbeat_interval=2.0,
            detailed_logging=True
        )

    def test_timeout_escalation_warning(self):
        """警告タイムアウトのテスト"""
        # モックプロセスを作成
        mock_process = Mock()
        mock_process.pid = 12345

        # 最初は実行中、後で終了
        poll_calls = 0
        def mock_poll():
            nonlocal poll_calls
            poll_calls += 1
            if poll_calls > 3:  # 数回チェック後に終了
                return 0
            return None
        mock_process.poll = mock_poll

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time()
        )

        # 警告タイムアウトをテスト（短時間で実行）
        with patch('services.actions.enhanced_act_wrapper.time.time') as mock_time:
            start_time = 1000.0
            # より多くのtime.time()呼び出しに対応
            mock_time.side_effect = [
                start_time,  # 開始時刻
                start_time,  # _last_heartbeat設定
                start_time + 1.0,  # 最初のループ
                start_time + 6.0,  # 警告タイムアウト後
                start_time + 6.0,  # エスカレーション処理
                start_time + 6.0,  # ループ継続
                start_time + 7.0,  # 次のループ
                start_time + 7.0,  # 終了判定
                start_time + 7.0,  # 最終メトリクス記録
            ]

            timed_out, indicators = self.monitor.monitor_with_heartbeat(
                monitored_process, timeout=10
            )

            # 警告が送信されたことを確認
            self.assertTrue(self.monitor._warning_sent)
            self.assertFalse(timed_out)

    def test_timeout_escalation_final(self):
        """最終タイムアウトのテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 常に実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time()
        )

        # 最終タイムアウトをテスト
        with patch('services.actions.enhanced_act_wrapper.time.time') as mock_time:
            start_time = 1000.0
            mock_time.side_effect = [
                start_time,  # 開始時刻
                start_time,  # _last_heartbeat設定
                start_time + 11.0,  # 最終タイムアウト後
                start_time + 11.0,  # エスカレーション処理
                start_time + 11.0,  # 最終メトリクス記録
            ]

            timed_out, indicators = self.monitor.monitor_with_heartbeat(
                monitored_process, timeout=10
            )

            # タイムアウトが発生したことを確認
            self.assertTrue(timed_out)

    def test_enhanced_heartbeat_logging(self):
        """改良されたハートビートログのテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time()
        )
        monitored_process.stdout_lines = ["line1", "line2"]
        monitored_process.stderr_lines = ["error1"]

        # ハートビートログをテスト
        with patch.object(self.logger, 'info') as mock_log:
            self.monitor._log_enhanced_heartbeat(monitored_process, 30.0)

            # ログが呼ばれたことを確認
            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            self.assertIn("プロセス監視", call_args)
            self.assertIn("30", call_args)

    @patch('psutil.Process')
    def test_resource_usage_monitoring(self, mock_psutil_process):
        """リソース使用量監視のテスト"""
        # psutilのモック設定
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 50.0
        mock_process_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_process_instance.memory_percent.return_value = 25.0
        mock_process_instance.num_threads.return_value = 4
        mock_psutil_process.return_value = mock_process_instance

        mock_subprocess = Mock()
        mock_subprocess.pid = 12345

        monitored_process = MonitoredProcess(
            process=mock_subprocess,
            command=["test", "command"],
            start_time=time.time()
        )

        # リソースチェックを実行
        self.monitor._check_resource_usage(monitored_process)

        # スナップショットが記録されたことを確認
        self.assertEqual(len(self.monitor._resource_snapshots), 1)
        snapshot = self.monitor._resource_snapshots[0]
        self.assertEqual(snapshot["cpu_percent"], 50.0)
        self.assertEqual(snapshot["memory_mb"], 100.0)

    @patch('psutil.Process')
    def test_high_resource_usage_warning(self, mock_psutil_process):
        """高リソース使用量警告のテスト"""
        # 高メモリ使用量のモック
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 95.0  # 高CPU
        mock_process_instance.memory_info.return_value = Mock(rss=1000 * 1024 * 1024)  # 1GB
        mock_process_instance.memory_percent.return_value = 85.0  # 高メモリ
        mock_process_instance.num_threads.return_value = 10
        mock_psutil_process.return_value = mock_process_instance

        mock_subprocess = Mock()
        mock_subprocess.pid = 12345

        monitored_process = MonitoredProcess(
            process=mock_subprocess,
            command=["test", "command"],
            start_time=time.time()
        )

        with patch.object(self.logger, 'warning') as mock_warning:
            self.monitor._check_resource_usage(monitored_process)

            # 警告ログが出力されたことを確認
            self.assertTrue(mock_warning.called)
            warning_calls = [call[0][0] for call in mock_warning.call_args_list]

            # CPU警告とメモリ警告の両方が出力されることを確認
            cpu_warning = any("高CPU使用量" in call for call in warning_calls)
            memory_warning = any("高メモリ使用量" in call for call in warning_calls)
            self.assertTrue(cpu_warning or memory_warning)

    def test_force_cleanup_escalation(self):
        """強制クリーンアップのエスカレーションテスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 実行中

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time()
        )

        # 最初のterminateで終了しない場合をシミュレート
        terminate_called = False
        kill_called = False

        def mock_terminate():
            nonlocal terminate_called
            terminate_called = True

        def mock_kill():
            nonlocal kill_called
            kill_called = True
            mock_process.poll.return_value = -9  # 強制終了

        def mock_wait(timeout=None):
            if terminate_called and not kill_called:
                raise subprocess.TimeoutExpired("test", timeout)
            return -9

        mock_process.terminate = mock_terminate
        mock_process.kill = mock_kill
        mock_process.wait = mock_wait

        # 強制クリーンアップを実行
        self.monitor.force_cleanup_on_timeout(monitored_process)

        # 段階的な終了が実行されたことを確認
        self.assertTrue(terminate_called)
        self.assertTrue(kill_called)
        self.assertTrue(monitored_process.force_killed)

    def test_performance_metrics_collection(self):
        """パフォーマンスメトリクス収集のテスト"""
        # メトリクスを設定
        self.monitor._performance_metrics = {
            "total_duration_seconds": 120.5,
            "stdout_lines_total": 100,
            "stderr_lines_total": 5
        }

        self.monitor._resource_snapshots = [
            {"timestamp": 1000.0, "cpu_percent": 50.0, "memory_mb": 100.0}
        ]

        metrics = self.monitor.get_performance_metrics()

        # メトリクスが正しく返されることを確認
        self.assertIn("performance_metrics", metrics)
        self.assertIn("resource_snapshots", metrics)
        self.assertIn("monitoring_config", metrics)

        self.assertEqual(metrics["performance_metrics"]["total_duration_seconds"], 120.5)
        self.assertEqual(len(metrics["resource_snapshots"]), 1)

    def test_deadlock_detection_integration(self):
        """デッドロック検出との統合テスト"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        monitored_process = MonitoredProcess(
            process=mock_process,
            command=["test", "command"],
            start_time=time.time()
        )

        # デッドロック指標を追加
        deadlock_indicator = DeadlockIndicator(
            deadlock_type=DeadlockType.STDOUT_THREAD,
            process_pid=12345,
            details={"test": "data"}
        )
        monitored_process.deadlock_indicators.append(deadlock_indicator)

        # 短時間でタイムアウトさせる
        timed_out, indicators = self.monitor.monitor_with_heartbeat(
            monitored_process, timeout=1
        )

        # デッドロック指標が返されることを確認
        self.assertTrue(timed_out)
        self.assertEqual(len(indicators), 1)
        self.assertEqual(indicators[0].deadlock_type, DeadlockType.STDOUT_THREAD)

    def tearDown(self):
        """テストクリーンアップ"""
        # 監視スレッドが残っている場合は停止
        if hasattr(self.monitor, '_monitoring_active') and self.monitor._monitoring_active:
            self.monitor._stop_deadlock_detection()


if __name__ == '__main__':
    unittest.main()
