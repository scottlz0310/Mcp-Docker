"""
GitHub Actions Simulator - ExecutionTracer テスト
実行トレースと監視機能のテストケース
"""

import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch


from services.actions.execution_tracer import (
    ExecutionStage,
    ExecutionTracer,
    ThreadState,
)
from services.actions.logger import ActionsLogger


class TestExecutionTracer:
    """ExecutionTracerのテストクラス"""

    def test_start_and_end_trace(self):
        """トレースの開始と終了をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger, heartbeat_interval=1.0)

        # トレース開始
        trace = tracer.start_trace("test_trace")
        assert trace is not None
        assert trace.trace_id == "test_trace"
        assert trace.current_stage == ExecutionStage.INITIALIZATION
        assert trace.end_time is None

        # 少し待機
        time.sleep(0.1)

        # トレース終了
        final_trace = tracer.end_trace()
        assert final_trace is not None
        assert final_trace.trace_id == "test_trace"
        assert final_trace.end_time is not None
        assert final_trace.duration_ms > 0

    def test_stage_transitions(self):
        """実行段階の遷移をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        trace = tracer.start_trace("stage_test")

        # 段階を変更
        tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION, {"test": "data"})
        assert trace.current_stage == ExecutionStage.SUBPROCESS_CREATION
        assert ExecutionStage.SUBPROCESS_CREATION in trace.stages
        assert trace.metadata["test"] == "data"

        tracer.set_stage(ExecutionStage.DOCKER_COMMUNICATION)
        assert trace.current_stage == ExecutionStage.DOCKER_COMMUNICATION
        assert ExecutionStage.DOCKER_COMMUNICATION in trace.stages

        tracer.end_trace()

    def test_subprocess_tracing(self):
        """サブプロセストレースをテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("subprocess_test")

        # 簡単なコマンドを実行
        cmd = ["echo", "hello world"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # プロセストレースを開始
        process_trace = tracer.trace_subprocess_execution(cmd, process)
        assert process_trace.command == cmd
        assert process_trace.pid == process.pid

        # プロセス完了を待機
        stdout, stderr = process.communicate()
        return_code = process.returncode

        # プロセストレースを更新
        tracer.update_process_trace(
            process_trace,
            return_code=return_code,
            stdout_bytes=len(stdout.encode('utf-8')),
            stderr_bytes=len(stderr.encode('utf-8'))
        )

        assert process_trace.return_code == return_code
        assert process_trace.stdout_bytes > 0
        assert process_trace.end_time is not None

        tracer.end_trace()

    def test_docker_operation_monitoring(self):
        """Docker操作の監視をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("docker_test")

        # Docker操作を監視
        docker_op = tracer.monitor_docker_communication(
            "test_command",
            ["docker", "version"]
        )

        assert docker_op.operation_type == "test_command"
        assert docker_op.command == ["docker", "version"]
        assert docker_op.end_time is None

        # 操作を更新
        tracer.update_docker_operation(
            docker_op,
            success=True,
            return_code=0,
            stdout="Docker version info",
            stderr=""
        )

        assert docker_op.success is True
        assert docker_op.return_code == 0
        assert docker_op.stdout == "Docker version info"
        assert docker_op.end_time is not None
        assert docker_op.duration_ms is not None

        tracer.end_trace()

    def test_thread_lifecycle_tracking(self):
        """スレッドライフサイクルの追跡をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("thread_test")

        def test_function():
            time.sleep(0.1)

        # スレッドを作成
        thread = threading.Thread(target=test_function, name="TestThread")
        thread_trace = tracer.track_thread_lifecycle(thread, "test_function")

        assert thread_trace.thread_name == "TestThread"
        assert thread_trace.target_function == "test_function"
        assert thread_trace.state == ThreadState.CREATED

        # スレッドを開始
        thread.start()
        tracer.update_thread_state(thread_trace, ThreadState.RUNNING)
        assert thread_trace.state == ThreadState.RUNNING

        # スレッド完了を待機
        thread.join()
        tracer.update_thread_state(thread_trace, ThreadState.TERMINATED)

        assert thread_trace.state == ThreadState.TERMINATED
        assert thread_trace.end_time is not None
        assert thread_trace.duration_ms is not None

        tracer.end_trace()

    def test_heartbeat_logging(self):
        """ハートビートログをテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        trace = tracer.start_trace("heartbeat_test")

        # ハートビートログを記録
        process_info = {"pid": 12345, "status": "running"}
        tracer.log_heartbeat("Test heartbeat", process_info)

        assert trace.last_heartbeat is not None

        tracer.end_trace()

    def test_hang_detection(self):
        """ハングアップ検出をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("hang_test")

        # 最初はハングアップなし
        hang_info = tracer.detect_hang_condition(timeout_seconds=1.0)
        assert hang_info is None

        # ハートビートを記録
        tracer.log_heartbeat("Initial heartbeat")

        # 少し待機してからハングアップ検出
        time.sleep(1.1)
        hang_info = tracer.detect_hang_condition(timeout_seconds=1.0)
        assert hang_info is not None
        assert "最後のハートビートから" in hang_info

        tracer.end_trace()

    def test_resource_monitoring(self):
        """リソース監視をテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(
            logger=logger,
            heartbeat_interval=0.5,
            resource_monitoring_interval=0.2
        )

        trace = tracer.start_trace("resource_test")

        # 少し待機してリソース情報が収集されるのを待つ
        time.sleep(0.6)

        # リソース使用量が記録されているかチェック
        assert len(trace.resource_usage) > 0

        resource = trace.resource_usage[0]
        assert resource.timestamp is not None
        assert resource.cpu_percent >= 0
        assert resource.memory_mb >= 0

        tracer.end_trace()

    def test_trace_export(self):
        """トレース情報のエクスポートをテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("export_test")
        tracer.set_stage(ExecutionStage.COMPLETED)
        final_trace = tracer.end_trace()

        # 一時ファイルにエクスポート
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)

        try:
            tracer.export_trace(final_trace, output_path)

            # ファイルが作成されているかチェック
            assert output_path.exists()

            # JSONとして読み込み可能かチェック
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["trace_id"] == "export_test"
            assert data["current_stage"] == ExecutionStage.COMPLETED.value
            assert "duration_ms" in data

        finally:
            # 一時ファイルを削除
            if output_path.exists():
                output_path.unlink()

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_monitoring_with_mocks(self, mock_memory, mock_cpu):
        """モックを使用したリソース監視のテスト"""
        # モックの設定
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(used=1024*1024*512, percent=50.0)  # 512MB, 50%

        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        trace = tracer.start_trace("mock_resource_test")

        # リソース使用量を手動で記録
        tracer._record_resource_usage()

        assert len(trace.resource_usage) > 0
        resource = trace.resource_usage[0]
        assert resource.cpu_percent == 25.5
        assert resource.memory_percent == 50.0
        assert resource.memory_mb == 512.0

        tracer.end_trace()

    def test_multiple_traces(self):
        """複数のトレースが正しく処理されることをテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        # 最初のトレース
        trace1 = tracer.start_trace("trace1")
        assert tracer.get_current_trace() == trace1

        final_trace1 = tracer.end_trace()
        assert final_trace1.trace_id == "trace1"
        assert tracer.get_current_trace() is None

        # 2番目のトレース
        trace2 = tracer.start_trace("trace2")
        assert tracer.get_current_trace() == trace2
        assert trace2.trace_id == "trace2"

        final_trace2 = tracer.end_trace()
        assert final_trace2.trace_id == "trace2"

    def test_error_handling_in_tracing(self):
        """トレース中のエラーハンドリングをテスト"""
        logger = ActionsLogger(verbose=False)
        tracer = ExecutionTracer(logger=logger)

        tracer.start_trace("error_test")

        # 存在しないコマンドでプロセストレースを作成
        cmd = ["nonexistent_command"]
        process_trace = tracer.trace_subprocess_execution(cmd)

        # エラーメッセージを設定
        tracer.update_process_trace(
            process_trace,
            return_code=-1,
            error_message="Command not found"
        )

        assert process_trace.return_code == -1
        assert process_trace.error_message == "Command not found"

        tracer.end_trace()
