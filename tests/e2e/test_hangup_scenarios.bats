#!/usr/bin/env bats
# GitHub Actions Simulator - ハングアップシナリオ BATS テスト
# 実際のシェル環境でのハングアップ条件をテストします

load test_helper

setup() {
    # テスト用一時ディレクトリを作成
    TEST_TEMP_DIR="$(mktemp -d)"
    export TEST_TEMP_DIR

    # テスト用ワークフローファイルを作成
    create_test_workflows

    # 環境変数を設定
    export ACTIONS_SIMULATOR_ENGINE="mock"
    export ACTIONS_SIMULATOR_VERBOSE="true"
}

teardown() {
    # 一時ディレクトリをクリーンアップ
    if [ -n "$TEST_TEMP_DIR" ] && [ -d "$TEST_TEMP_DIR" ]; then
        rm -rf "$TEST_TEMP_DIR"
    fi

    # 環境変数をクリーンアップ
    unset ACTIONS_SIMULATOR_ENGINE
    unset ACTIONS_SIMULATOR_VERBOSE
}

create_test_workflows() {
    # 基本的なテストワークフロー
    cat > "$TEST_TEMP_DIR/basic_test.yml" << 'EOF'
name: Basic Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Simple echo
        run: echo "Hello World"
      - name: List files
        run: ls -la
EOF

    # 長時間実行ワークフロー
    cat > "$TEST_TEMP_DIR/long_running.yml" << 'EOF'
name: Long Running Test
on: [push]
jobs:
  long-task:
    runs-on: ubuntu-latest
    steps:
      - name: Long running task
        run: sleep 10
      - name: After long task
        run: echo "Completed"
EOF

    # エラーを含むワークフロー
    cat > "$TEST_TEMP_DIR/error_test.yml" << 'EOF'
name: Error Test
on: [push]
jobs:
  error-job:
    runs-on: ubuntu-latest
    steps:
      - name: Command that fails
        run: exit 1
      - name: Should not run
        run: echo "Should not reach here"
EOF
}

@test "診断サービス - Docker接続性チェック" {
    # 検証対象: DiagnosticService.check_docker_connectivity
    # 目的: Docker接続性診断の動作確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
service = DiagnosticService(logger=logger)
result = service.check_docker_connectivity()
print(f'Status: {result.status.name}')
print(f'Component: {result.component}')
assert result.component == 'Docker接続性'
print('Docker connectivity check completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Docker connectivity check completed" ]]
}

@test "診断サービス - actバイナリチェック" {
    # 検証対象: DiagnosticService.check_act_binary
    # 目的: actバイナリ診断の動作確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
service = DiagnosticService(logger=logger)
result = service.check_act_binary()
print(f'Status: {result.status.name}')
print(f'Component: {result.component}')
assert result.component == 'actバイナリ'
print('Act binary check completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Act binary check completed" ]]
}

@test "診断サービス - 包括的ヘルスチェック" {
    # 検証対象: DiagnosticService.run_comprehensive_health_check
    # 目的: 包括的システムヘルスチェックの動作確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
service = DiagnosticService(logger=logger)
report = service.run_comprehensive_health_check()
print(f'Overall Status: {report.overall_status.name}')
print(f'Results Count: {len(report.results)}')
print(f'Summary: {report.summary}')
assert len(report.results) > 0
print('Comprehensive health check completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Comprehensive health check completed" ]]
}

@test "実行トレーサー - 基本トレース機能" {
    # 検証対象: ExecutionTracer基本機能
    # 目的: 実行トレースの開始・終了・段階設定の動作確認

    run python -c "
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage
from services.actions.logger import ActionsLogger
import time

logger = ActionsLogger(verbose=True)
tracer = ExecutionTracer(logger=logger)

# トレース開始
trace = tracer.start_trace('test_trace')
print(f'Trace ID: {trace.trace_id}')
assert trace.trace_id == 'test_trace'

# 段階設定
tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION, {'test': 'data'})
print(f'Current Stage: {trace.current_stage}')

# ハートビート記録
tracer.log_heartbeat('Test heartbeat', {'status': 'running'})
print('Heartbeat logged')

# トレース終了
time.sleep(0.1)
final_trace = tracer.end_trace()
print(f'Duration: {final_trace.duration_ms}ms')
assert final_trace.duration_ms > 0
print('Execution tracer test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Execution tracer test completed" ]]
}

@test "プロセス監視 - タイムアウト処理" {
    # 検証対象: ProcessMonitor.monitor_with_heartbeat
    # 目的: プロセス監視とタイムアウト処理の動作確認

    run python -c "
from services.actions.enhanced_act_wrapper import ProcessMonitor, MonitoredProcess
from services.actions.logger import ActionsLogger
from unittest.mock import Mock
import time

logger = ActionsLogger(verbose=True)
monitor = ProcessMonitor(
    logger=logger,
    warning_timeout=1.0,
    escalation_timeout=2.0,
    heartbeat_interval=0.5
)

# モックプロセスを作成
mock_process = Mock()
mock_process.pid = 12345
mock_process.poll.return_value = 0  # 正常終了

monitored_process = MonitoredProcess(
    process=mock_process,
    command=['echo', 'test'],
    start_time=time.time()
)

# 短時間監視
timed_out, indicators = monitor.monitor_with_heartbeat(monitored_process, timeout=3)
print(f'Timed out: {timed_out}')
print(f'Indicators count: {len(indicators)}')
print('Process monitor test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Process monitor test completed" ]]
}

@test "ハングアップ検出器 - Docker問題検出" {
    # 検証対象: HangupDetector.detect_docker_socket_issues
    # 目的: Docker関連ハングアップ問題の検出確認

    run python -c "
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
detector = HangupDetector(logger=logger, confidence_threshold=0.5)

# Docker問題を検出
issues = detector.detect_docker_socket_issues()
print(f'Docker issues found: {len(issues)}')

for issue in issues:
    print(f'Issue: {issue.title} (Confidence: {issue.confidence_score})')

print('Hangup detector test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Hangup detector test completed" ]]
}

@test "ハングアップ検出器 - 包括的分析" {
    # 検証対象: HangupDetector.analyze_hangup_conditions
    # 目的: 包括的ハングアップ分析の動作確認

    run python -c "
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
detector = HangupDetector(logger=logger, confidence_threshold=0.5)

# 包括的分析を実行
analysis = detector.analyze_hangup_conditions()
print(f'Analysis ID: {analysis.analysis_id}')
print(f'Issues found: {len(analysis.issues)}')
print(f'Recovery suggestions: {len(analysis.recovery_suggestions)}')
print(f'Prevention measures: {len(analysis.prevention_measures)}')

assert analysis.analysis_id is not None
print('Comprehensive hangup analysis completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Comprehensive hangup analysis completed" ]]
}

@test "自動復旧 - Docker再接続" {
    # 検証対象: AutoRecovery.attempt_docker_reconnection
    # 目的: Docker再接続機能の動作確認

    run python -c "
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)

# Docker再接続を試行
result = recovery.attempt_docker_reconnection()
print(f'Docker reconnection result: {result}')
print('Auto recovery docker reconnection test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Auto recovery docker reconnection test completed" ]]
}

@test "自動復旧 - フォールバックモード" {
    # 検証対象: AutoRecovery.execute_fallback_mode
    # 目的: フォールバック実行モードの動作確認

    run python -c "
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger
from pathlib import Path

logger = ActionsLogger(verbose=True)
recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)

# テスト用ワークフローファイル
workflow_file = Path('$TEST_TEMP_DIR/basic_test.yml')
original_command = ['act', '--list']

# フォールバックモードを実行
result = recovery.execute_fallback_mode(workflow_file, original_command)
print(f'Fallback success: {result.success}')
print(f'Fallback method: {result.fallback_method}')
print(f'Execution time: {result.execution_time_ms}ms')

assert result.success == True
print('Auto recovery fallback mode test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Auto recovery fallback mode test completed" ]]
}

@test "EnhancedActWrapper - モックモード実行" {
    # 検証対象: EnhancedActWrapper.run_workflow_with_diagnostics
    # 目的: モックモードでのワークフロー実行確認

    run python -c "
from services.actions.enhanced_act_wrapper import EnhancedActWrapper
from services.actions.diagnostic import DiagnosticService
from services.actions.execution_tracer import ExecutionTracer
from services.actions.logger import ActionsLogger
import os

logger = ActionsLogger(verbose=True)
execution_tracer = ExecutionTracer(logger=logger)
diagnostic_service = DiagnosticService(logger=logger)

wrapper = EnhancedActWrapper(
    working_directory='$TEST_TEMP_DIR',
    logger=logger,
    execution_tracer=execution_tracer,
    diagnostic_service=diagnostic_service
)

# モックモードで実行
os.environ['ACTIONS_SIMULATOR_ENGINE'] = 'mock'
result = wrapper.run_workflow_with_diagnostics(
    workflow_file='basic_test.yml',
    pre_execution_diagnostics=False,
    dry_run=True
)

print(f'Execution success: {result.success}')
print(f'Return code: {result.returncode}')
print(f'Execution time: {result.execution_time_ms}ms')

assert result.success == True
print('Enhanced ActWrapper mock mode test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Enhanced ActWrapper mock mode test completed" ]]
}

@test "統合テスト - エラーレポート生成" {
    # 検証対象: HangupDetector.generate_detailed_error_report
    # 目的: エラーレポート生成機能の統合確認

    run python -c "
from services.actions.hangup_detector import HangupDetector, HangupAnalysis, HangupIssue, HangupType, HangupSeverity
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)
detector = HangupDetector(logger=logger)

# サンプル分析を作成
analysis = HangupAnalysis(analysis_id='test_analysis')
analysis.primary_cause = HangupIssue(
    issue_type=HangupType.DOCKER_SOCKET_ISSUE,
    severity=HangupSeverity.HIGH,
    title='テスト問題',
    description='テスト用の問題',
    confidence_score=0.8
)

# エラーレポートを生成
report = detector.generate_detailed_error_report(hangup_analysis=analysis)
print(f'Report ID: {report.report_id}')
print(f'System info keys: {list(report.system_information.keys())}')
print(f'Docker status keys: {list(report.docker_status.keys())}')
print(f'Troubleshooting guide items: {len(report.troubleshooting_guide)}')

assert report.report_id is not None
print('Error report generation test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Error report generation test completed" ]]
}

@test "統合テスト - デバッグバンドル作成" {
    # 検証対象: HangupDetector.create_debug_bundle
    # 目的: デバッグバンドル作成機能の統合確認

    run python -c "
from services.actions.hangup_detector import HangupDetector, ErrorReport
from services.actions.logger import ActionsLogger
from pathlib import Path

logger = ActionsLogger(verbose=True)
detector = HangupDetector(logger=logger)

# サンプルエラーレポート
report = ErrorReport(report_id='test_report')
report.system_information = {'test': 'data'}

# デバッグバンドルを作成
output_dir = Path('$TEST_TEMP_DIR')
bundle = detector.create_debug_bundle(
    error_report=report,
    output_directory=output_dir,
    include_logs=True,
    include_system_info=True,
    include_docker_info=True
)

print(f'Bundle ID: {bundle.bundle_id}')
print(f'Bundle path exists: {bundle.bundle_path.exists() if bundle.bundle_path else False}')
print(f'Included files: {len(bundle.included_files)}')
print(f'Total size: {bundle.total_size_bytes} bytes')

assert bundle.bundle_id is not None
print('Debug bundle creation test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Debug bundle creation test completed" ]]
}

@test "統合テスト - 包括的復旧セッション" {
    # 検証対象: AutoRecovery.run_comprehensive_recovery
    # 目的: 包括的復旧セッションの統合確認

    run python -c "
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger
from pathlib import Path

logger = ActionsLogger(verbose=True)
recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)

# 包括的復旧を実行
workflow_file = Path('$TEST_TEMP_DIR/basic_test.yml')
session = recovery.run_comprehensive_recovery(
    workflow_file=workflow_file,
    original_command=['act', '--list']
)

print(f'Session ID: {session.session_id}')
print(f'Start time: {session.start_time}')
print(f'End time: {session.end_time}')
print(f'Attempts count: {len(session.attempts)}')
print(f'Overall success: {session.overall_success}')

assert session.session_id is not None
assert len(session.attempts) > 0
print('Comprehensive recovery session test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Comprehensive recovery session test completed" ]]
}

@test "パフォーマンステスト - 診断サービス応答時間" {
    # 検証対象: DiagnosticService応答時間
    # 目的: 診断サービスのパフォーマンス確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.logger import ActionsLogger
import time

logger = ActionsLogger(verbose=False)  # ログを抑制
service = DiagnosticService(logger=logger)

# 実行時間を測定
start_time = time.time()
for _ in range(5):
    report = service.run_comprehensive_health_check()
end_time = time.time()

execution_time = end_time - start_time
avg_time = execution_time / 5

print(f'Total execution time: {execution_time:.2f}s')
print(f'Average time per check: {avg_time:.2f}s')
print(f'Performance acceptable: {avg_time < 10.0}')

assert avg_time < 10.0  # 10秒以内
print('Diagnostic service performance test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Diagnostic service performance test completed" ]]
}

@test "ストレステスト - 並行診断実行" {
    # 検証対象: 並行実行時の安定性
    # 目的: 複数の診断が同時実行されても安定動作することを確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger
import threading
import time

logger = ActionsLogger(verbose=False)
results = []

def worker():
    try:
        service = DiagnosticService(logger=logger)
        detector = HangupDetector(logger=logger)

        # 診断を実行
        health_report = service.run_comprehensive_health_check()
        analysis = detector.analyze_hangup_conditions()

        results.append(True)
    except Exception as e:
        print(f'Worker error: {e}')
        results.append(False)

# 5つのスレッドで並行実行
threads = []
for _ in range(5):
    thread = threading.Thread(target=worker)
    threads.append(thread)
    thread.start()

# 全スレッドの完了を待機
for thread in threads:
    thread.join(timeout=30)

success_count = sum(results)
total_count = len(results)

print(f'Concurrent execution results: {success_count}/{total_count}')
print(f'Success rate: {success_count/total_count*100:.1f}%')

assert success_count >= total_count * 0.8  # 80%以上成功
print('Concurrent execution stress test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Concurrent execution stress test completed" ]]
}

@test "エンドツーエンドテスト - 完全なハングアップ復旧フロー" {
    # 検証対象: 全コンポーネント統合フロー
    # 目的: ハングアップ検出から復旧までの完全なフローの動作確認

    run python -c "
from services.actions.diagnostic import DiagnosticService
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage
from services.actions.hangup_detector import HangupDetector
from services.actions.auto_recovery import AutoRecovery
from services.actions.logger import ActionsLogger
from pathlib import Path

logger = ActionsLogger(verbose=True)

# 1. 事前診断
print('Step 1: Pre-execution diagnostics')
diagnostic_service = DiagnosticService(logger=logger)
health_report = diagnostic_service.run_comprehensive_health_check()
print(f'Health check status: {health_report.overall_status.name}')

# 2. 実行トレース
print('Step 2: Execution tracing')
execution_tracer = ExecutionTracer(logger=logger)
trace = execution_tracer.start_trace('e2e_test')
execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)
execution_tracer.log_heartbeat('Test execution started')
final_trace = execution_tracer.end_trace()
print(f'Trace completed: {final_trace.trace_id}')

# 3. ハングアップ分析
print('Step 3: Hangup analysis')
hangup_detector = HangupDetector(logger=logger)
analysis = hangup_detector.analyze_hangup_conditions(execution_trace=final_trace)
print(f'Analysis completed: {analysis.analysis_id}')

# 4. エラーレポート生成
print('Step 4: Error report generation')
report = hangup_detector.generate_detailed_error_report(hangup_analysis=analysis)
print(f'Report generated: {report.report_id}')

# 5. 自動復旧
print('Step 5: Auto recovery')
auto_recovery = AutoRecovery(logger=logger, enable_fallback_mode=True)
workflow_file = Path('$TEST_TEMP_DIR/basic_test.yml')
recovery_session = auto_recovery.run_comprehensive_recovery(
    workflow_file=workflow_file,
    original_command=['act', '--list']
)
print(f'Recovery session: {recovery_session.session_id}')

# 全ステップが完了したことを確認
assert health_report is not None
assert final_trace.trace_id == 'e2e_test'
assert analysis.analysis_id is not None
assert report.report_id is not None
assert recovery_session.session_id is not None

print('End-to-end hangup recovery flow test completed')
"

    echo "Output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "End-to-end hangup recovery flow test completed" ]]
}
