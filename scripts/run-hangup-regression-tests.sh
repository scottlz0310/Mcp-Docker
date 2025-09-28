#!/bin/bash
# GitHub Actions Simulator - ハングアップリグレッションテスト実行スクリプト
#
# このスクリプトは継続的にハングアップ修正の効果を監視し、
# リグレッションを早期に検出するために使用されます。

set -euo pipefail

# スクリプト設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/output/regression-tests"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

# ログ設定
LOG_FILE="$OUTPUT_DIR/regression-test-$TIMESTAMP.log"
export PERFORMANCE_LOG="$OUTPUT_DIR/performance-$TIMESTAMP.json"

# 色付きログ関数
log_info() {
    echo -e "\033[32m[INFO]\033[0m $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1" | tee -a "$LOG_FILE"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "\033[36m[DEBUG]\033[0m $1" | tee -a "$LOG_FILE"
    fi
}

# 使用方法表示
show_usage() {
    cat << EOF
使用方法: $0 [オプション]

オプション:
    -h, --help              このヘルプを表示
    -v, --verbose           詳細ログを有効化
    -q, --quiet             静音モード
    -t, --timeout SECONDS   タイムアウト時間（デフォルト: 1800秒）
    -o, --output DIR        出力ディレクトリ（デフォルト: output/regression-tests）
    --performance-only      パフォーマンステストのみ実行
    --regression-only       リグレッションテストのみ実行
    --baseline              ベースライン測定モード
    --compare-with FILE     指定ファイルとの比較

例:
    $0                      # 全テスト実行
    $0 --performance-only   # パフォーマンステストのみ
    $0 --baseline          # ベースライン測定
    $0 --compare-with output/regression-tests/baseline.json
EOF
}

# デフォルト設定
VERBOSE=false
QUIET=false
TIMEOUT=1800
PERFORMANCE_ONLY=false
REGRESSION_ONLY=false
BASELINE_MODE=false
COMPARE_FILE=""

# コマンドライン引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            export VERBOSE=true
            DEBUG=true
            shift
            ;;
        -q|--quiet)
            export QUIET=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --performance-only)
            PERFORMANCE_ONLY=true
            shift
            ;;
        --regression-only)
            REGRESSION_ONLY=true
            shift
            ;;
        --baseline)
            BASELINE_MODE=true
            shift
            ;;
        --compare-with)
            COMPARE_FILE="$2"
            shift 2
            ;;
        *)
            log_error "不明なオプション: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 出力ディレクトリ作成
mkdir -p "$OUTPUT_DIR"

# 環境チェック
check_environment() {
    log_info "環境チェック開始"

    # 必要なコマンドチェック
    local required_commands=("docker" "uv")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "必要なコマンドが見つかりません: $cmd"
            exit 1
        fi
        log_debug "$cmd: $(command -v "$cmd")"
    done

    # Python環境チェック
    log_debug "Python: $(uv run python --version)"

    # Docker環境チェック
    if ! docker info &> /dev/null; then
        log_error "Docker デーモンに接続できません"
        exit 1
    fi
    log_debug "Docker: $(docker --version)"

    # uv環境チェック
    if ! uv --version &> /dev/null; then
        log_error "uv が正しくインストールされていません"
        exit 1
    fi
    log_debug "uv: $(uv --version)"

    log_info "環境チェック完了"
}

# システム情報収集
collect_system_info() {
    log_info "システム情報収集"

    local system_info_file="$OUTPUT_DIR/system-info-$TIMESTAMP.json"

    uv run python << EOF > "$system_info_file"
import json
import platform
import psutil
import subprocess
from datetime import datetime

system_info = {
    "timestamp": datetime.utcnow().isoformat(),
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    },
    "python": {
        "version": platform.python_version(),
        "implementation": platform.python_implementation()
    },
    "resources": {
        "cpu_count": psutil.cpu_count(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "memory_total": psutil.virtual_memory().total,
        "disk_total": psutil.disk_usage('/').total
    }
}

# Docker情報
try:
    docker_version = subprocess.check_output(['docker', '--version'], text=True).strip()
    system_info["docker"] = {"version": docker_version}
except:
    system_info["docker"] = {"version": "unknown"}

print(json.dumps(system_info, indent=2))
EOF

    log_debug "システム情報を保存: $system_info_file"
}

# ベースライン測定
run_baseline_measurement() {
    log_info "ベースライン測定開始"

    local baseline_file="$OUTPUT_DIR/baseline-$TIMESTAMP.json"

    (timeout "$TIMEOUT" uv run python << EOF
import json
import sys
import time
import psutil
from datetime import datetime
from services.actions.diagnostic import DiagnosticService
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)

baseline_results = {
    "timestamp": datetime.utcnow().isoformat(),
    "test_type": "baseline",
    "measurements": {}
}

print("📊 ベースライン測定実行", file=sys.stderr)

# 診断サービスベースライン
print("1. 診断サービス測定", file=sys.stderr)
process = psutil.Process()
start_memory = process.memory_info().rss / 1024 / 1024

start_time = time.time()
service = DiagnosticService(logger=logger)
health_report = service.run_comprehensive_health_check()
end_time = time.time()

end_memory = process.memory_info().rss / 1024 / 1024

baseline_results["measurements"]["diagnostic_service"] = {
    "duration_seconds": end_time - start_time,
    "memory_start_mb": start_memory,
    "memory_end_mb": end_memory,
    "memory_delta_mb": end_memory - start_memory,
    "status": str(health_report.overall_status)
}

# ハングアップ検出ベースライン
print("2. ハングアップ検出測定", file=sys.stderr)
start_memory = process.memory_info().rss / 1024 / 1024

start_time = time.time()
detector = HangupDetector(logger=logger)
analysis = detector.analyze_hangup_conditions()
end_time = time.time()

end_memory = process.memory_info().rss / 1024 / 1024

baseline_results["measurements"]["hangup_detector"] = {
    "duration_seconds": end_time - start_time,
    "memory_start_mb": start_memory,
    "memory_end_mb": end_memory,
    "memory_delta_mb": end_memory - start_memory,
    "issues_found": len(analysis.issues)
}

# Docker統合ベースライン
print("3. Docker統合測定", file=sys.stderr)
start_time = time.time()
docker_issues = detector.detect_docker_socket_issues()
end_time = time.time()

baseline_results["measurements"]["docker_integration"] = {
    "duration_seconds": end_time - start_time,
    "issues_found": len(docker_issues)
}

print(json.dumps(baseline_results, indent=2))
EOF
    ) > "$baseline_file"

    if [[ -f "$baseline_file" ]]; then
        log_info "ベースライン測定完了: $baseline_file"

        # ベースラインファイルをデフォルトとしてコピー
        cp "$baseline_file" "$OUTPUT_DIR/baseline.json"
        log_debug "デフォルトベースラインファイルを更新"
    else
        log_error "ベースライン測定に失敗しました"
        exit 1
    fi
}

# パフォーマンステスト実行
run_performance_tests() {
    log_info "パフォーマンステスト開始"

    local performance_file="$OUTPUT_DIR/performance-$TIMESTAMP.json"

    (timeout "$TIMEOUT" uv run python << EOF
import json
import time
import psutil
import threading
from datetime import datetime
from services.actions.diagnostic import DiagnosticService
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)

performance_results = {
    "timestamp": datetime.utcnow().isoformat(),
    "test_type": "performance",
    "test_duration_seconds": 300,  # 5分間のテスト
    "measurements": []
}

print("⚡ パフォーマンステスト実行（5分間）", file=sys.stderr)

def performance_worker(worker_id, duration=300):
    """パフォーマンステストワーカー"""
    start_time = time.time()
    measurements = []

    while time.time() - start_time < duration:
        measurement_start = time.time()

        try:
            # システムリソース測定
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # 診断サービス実行
            service = DiagnosticService(logger=logger)
            diagnostic_start = time.time()
            health_report = service.run_comprehensive_health_check()
            diagnostic_duration = time.time() - diagnostic_start

            # ハングアップ検出実行
            detector = HangupDetector(logger=logger)
            detection_start = time.time()
            analysis = detector.analyze_hangup_conditions()
            detection_duration = time.time() - detection_start

            measurement = {
                "timestamp": datetime.utcnow().isoformat(),
                "worker_id": worker_id,
                "system_resources": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_mb": memory.used / 1024 / 1024
                },
                "performance": {
                    "diagnostic_duration": diagnostic_duration,
                    "detection_duration": detection_duration
                },
                "results": {
                    "health_status": str(health_report.overall_status),
                    "issues_detected": len(analysis.issues)
                }
            }

            measurements.append(measurement)

            # 次の測定まで少し待機
            elapsed = time.time() - measurement_start
            sleep_time = max(0, 10 - elapsed)  # 10秒間隔
            if sleep_time > 0:
                time.sleep(sleep_time)

        except Exception as e:
            print(f"Worker {worker_id} エラー: {e}", file=sys.stderr)
            time.sleep(10)

    return measurements

# 単一ワーカーで実行（CI環境での安定性を重視）
measurements = performance_worker(0, 300)
performance_results["measurements"] = measurements

# 統計計算
if measurements:
    diagnostic_times = [m["performance"]["diagnostic_duration"] for m in measurements]
    detection_times = [m["performance"]["detection_duration"] for m in measurements]
    cpu_usage = [m["system_resources"]["cpu_percent"] for m in measurements]
    memory_usage = [m["system_resources"]["memory_percent"] for m in measurements]

    performance_results["statistics"] = {
        "total_measurements": len(measurements),
        "diagnostic_performance": {
            "avg_duration": sum(diagnostic_times) / len(diagnostic_times),
            "max_duration": max(diagnostic_times),
            "min_duration": min(diagnostic_times)
        },
        "detection_performance": {
            "avg_duration": sum(detection_times) / len(detection_times),
            "max_duration": max(detection_times),
            "min_duration": min(detection_times)
        },
        "system_resources": {
            "avg_cpu_percent": sum(cpu_usage) / len(cpu_usage),
            "max_cpu_percent": max(cpu_usage),
            "avg_memory_percent": sum(memory_usage) / len(memory_usage),
            "max_memory_percent": max(memory_usage)
        }
    }

print(json.dumps(performance_results, indent=2))
EOF
    ) > "$performance_file"

    if [[ -f "$performance_file" ]]; then
        log_info "パフォーマンステスト完了: $performance_file"
    else
        log_error "パフォーマンステストに失敗しました"
        exit 1
    fi
}

# リグレッションテスト実行
run_regression_tests() {
    log_info "リグレッションテスト開始"

    local regression_file="$OUTPUT_DIR/regression-$TIMESTAMP.json"

    (timeout "$TIMEOUT" uv run python << EOF
import json
from datetime import datetime
from services.actions.diagnostic import DiagnosticService
from services.actions.hangup_detector import HangupDetector
from services.actions.logger import ActionsLogger

logger = ActionsLogger(verbose=True)

regression_results = {
    "timestamp": datetime.utcnow().isoformat(),
    "test_type": "regression",
    "tests": {}
}

print("🔄 リグレッションテスト実行", file=sys.stderr)

service = DiagnosticService(logger=logger)
detector = HangupDetector(logger=logger)

# 既知の修正済み問題のリスト
fixed_issues = [
    {
        "name": "docker_socket_communication",
        "description": "Docker Socket通信問題",
        "test_function": lambda: service.check_docker_connectivity()
    },
    {
        "name": "subprocess_deadlock",
        "description": "サブプロセスデッドロック",
        "test_function": lambda: detector.detect_subprocess_deadlock()
    },
    {
        "name": "timeout_handling",
        "description": "タイムアウト処理問題",
        "test_function": lambda: detector.detect_timeout_problems()
    },
    {
        "name": "permission_issues",
        "description": "権限問題",
        "test_function": lambda: detector.detect_permission_issues()
    }
]

regression_found = False

for issue in fixed_issues:
    print(f"テスト: {issue['description']}", file=sys.stderr)

    try:
        if issue["name"] == "docker_socket_communication":
            result = issue["test_function"]()
            test_passed = result.status != "ERROR"
            details = {"status": result.status, "message": result.message}
        else:
            issues = issue["test_function"]()
            critical_issues = [i for i in issues if i.severity.value >= 3]
            test_passed = len(critical_issues) == 0
            details = {
                "total_issues": len(issues),
                "critical_issues": len(critical_issues),
                "issue_titles": [i.title for i in critical_issues]
            }

        regression_results["tests"][issue["name"]] = {
            "description": issue["description"],
            "passed": test_passed,
            "details": details
        }

        if not test_passed:
            regression_found = True
            print(f"❌ 回帰検出: {issue['description']}", file=sys.stderr)
        else:
            print(f"✅ 問題なし: {issue['description']}", file=sys.stderr)

    except Exception as e:
        regression_results["tests"][issue["name"]] = {
            "description": issue["description"],
            "passed": False,
            "error": str(e)
        }
        regression_found = True
        print(f"❌ テストエラー: {issue['description']} - {e}", file=sys.stderr)

regression_results["regression_detected"] = regression_found
regression_results["summary"] = {
    "total_tests": len(fixed_issues),
    "passed_tests": sum(1 for test in regression_results["tests"].values() if test["passed"]),
    "failed_tests": sum(1 for test in regression_results["tests"].values() if not test["passed"])
}

print(json.dumps(regression_results, indent=2))
EOF
    ) > "$regression_file"

    if [[ -f "$regression_file" ]]; then
        log_info "リグレッションテスト完了: $regression_file"

        # リグレッション検出チェック
        if uv run python -c "
import json
with open('$regression_file') as f:
    data = json.load(f)
exit(1 if data.get('regression_detected', False) else 0)
"; then
            log_info "リグレッション検出なし"
        else
            log_warn "リグレッションが検出されました"
            return 1
        fi
    else
        log_error "リグレッションテストに失敗しました"
        exit 1
    fi
}

# 結果比較
compare_results() {
    if [[ -z "$COMPARE_FILE" ]]; then
        log_debug "比較ファイルが指定されていません"
        return 0
    fi

    if [[ ! -f "$COMPARE_FILE" ]]; then
        log_error "比較ファイルが見つかりません: $COMPARE_FILE"
        return 1
    fi

    log_info "結果比較開始: $COMPARE_FILE"

    local latest_performance
    latest_performance=$(find "$OUTPUT_DIR" -name "performance-*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)

    if [[ -z "$latest_performance" ]]; then
        log_warn "比較用のパフォーマンスデータがありません"
        return 1
    fi

    uv run python << EOF
import json

# ベースラインデータ読み込み
with open("$COMPARE_FILE") as f:
    baseline = json.load(f)

# 現在のデータ読み込み
with open("$latest_performance") as f:
    current = json.load(f)

print("📊 パフォーマンス比較結果")

if "measurements" in baseline and "statistics" in current:
    # ベースラインから統計を計算
    if "diagnostic_service" in baseline["measurements"]:
        baseline_diagnostic = baseline["measurements"]["diagnostic_service"]["duration_seconds"]
        current_diagnostic = current["statistics"]["diagnostic_performance"]["avg_duration"]

        change_percent = ((current_diagnostic - baseline_diagnostic) / baseline_diagnostic) * 100
        print(f"診断サービス性能変化: {change_percent:+.1f}% ({baseline_diagnostic:.2f}s → {current_diagnostic:.2f}s)")

        if abs(change_percent) > 20:
            print(f"⚠️  大きな性能変化が検出されました: {change_percent:+.1f}%")

    if "hangup_detector" in baseline["measurements"]:
        baseline_detection = baseline["measurements"]["hangup_detector"]["duration_seconds"]
        current_detection = current["statistics"]["detection_performance"]["avg_duration"]

        change_percent = ((current_detection - baseline_detection) / baseline_detection) * 100
        print(f"ハングアップ検出性能変化: {change_percent:+.1f}% ({baseline_detection:.2f}s → {current_detection:.2f}s)")

        if abs(change_percent) > 20:
            print(f"⚠️  大きな性能変化が検出されました: {change_percent:+.1f}%")

print("✅ 比較完了")
EOF

    log_info "結果比較完了"
}

# レポート生成
generate_report() {
    log_info "レポート生成開始"

    local report_file="$OUTPUT_DIR/regression-report-$TIMESTAMP.md"

    cat > "$report_file" << EOF
# ハングアップリグレッションテスト結果レポート

## 実行概要
- **実行日時**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **実行モード**: $(if [[ "$BASELINE_MODE" == "true" ]]; then echo "ベースライン測定"; elif [[ "$PERFORMANCE_ONLY" == "true" ]]; then echo "パフォーマンステストのみ"; elif [[ "$REGRESSION_ONLY" == "true" ]]; then echo "リグレッションテストのみ"; else echo "完全テスト"; fi)
- **タイムアウト**: ${TIMEOUT}秒
- **出力ディレクトリ**: $OUTPUT_DIR

## 実行されたテスト

EOF

    # 各テストファイルの存在確認とサマリー追加
    {
        if [[ -f "$OUTPUT_DIR/baseline-$TIMESTAMP.json" ]]; then
            echo "### ベースライン測定"
            echo "✅ 実行済み - \`baseline-$TIMESTAMP.json\`"
            echo ""
        fi

        if [[ -f "$OUTPUT_DIR/performance-$TIMESTAMP.json" ]]; then
            echo "### パフォーマンステスト"
            echo "✅ 実行済み - \`performance-$TIMESTAMP.json\`"
            echo ""
        fi

        if [[ -f "$OUTPUT_DIR/regression-$TIMESTAMP.json" ]]; then
            echo "### リグレッションテスト"
            echo "✅ 実行済み - \`regression-$TIMESTAMP.json\`"
            echo ""
        fi
    } >> "$report_file"

    cat >> "$report_file" << EOF
## 推奨事項

### 継続的監視
- 定期的なリグレッションテストの実行
- パフォーマンス基準値の見直し
- 新しいテストケースの追加

### 問題対応
- リグレッション検出時の迅速な対応
- パフォーマンス劣化の原因分析
- 修正後の再テスト実行

## ファイル一覧

EOF

    # 生成されたファイルのリスト追加
    find "$OUTPUT_DIR" -name "*$TIMESTAMP*" -type f | while read -r file; do
        echo "- \`$(basename "$file")\`" >> "$report_file"
    done

    log_info "レポート生成完了: $report_file"
}

# メイン実行関数
main() {
    log_info "ハングアップリグレッションテスト開始"
    log_info "タイムスタンプ: $TIMESTAMP"

    # 環境チェック
    check_environment

    # システム情報収集
    collect_system_info

    # テスト実行
    if [[ "$BASELINE_MODE" == "true" ]]; then
        run_baseline_measurement
    elif [[ "$PERFORMANCE_ONLY" == "true" ]]; then
        run_performance_tests
    elif [[ "$REGRESSION_ONLY" == "true" ]]; then
        run_regression_tests
    else
        # 全テスト実行
        if [[ ! -f "$OUTPUT_DIR/baseline.json" ]]; then
            log_info "ベースラインファイルが存在しないため、ベースライン測定を実行します"
            run_baseline_measurement
        fi

        run_performance_tests
        run_regression_tests
    fi

    # 結果比較
    compare_results

    # レポート生成
    generate_report

    log_info "ハングアップリグレッションテスト完了"
    log_info "結果ディレクトリ: $OUTPUT_DIR"
}

# エラーハンドリング
trap 'log_error "スクリプトが異常終了しました"; exit 1' ERR

# メイン実行
main "$@"
