#!/usr/bin/env bash
# テストフォルダごとに実行して失敗を特定するスクリプト

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 結果保存用配列
declare -a PASSED_TESTS=()
declare -a FAILED_TESTS=()
declare -a SKIPPED_TESTS=()

# ログファイル
LOG_DIR="test-results"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SUMMARY_LOG="${LOG_DIR}/test-summary-${TIMESTAMP}.log"

echo "=== テストフォルダごとの実行開始 ===" | tee "${SUMMARY_LOG}"
echo "実行時刻: $(date)" | tee -a "${SUMMARY_LOG}"
echo "" | tee -a "${SUMMARY_LOG}"

# テスト実行関数
run_test() {
    local test_path="$1"
    local test_name="$2"
    local log_file="${LOG_DIR}/${test_name//\//_}-${TIMESTAMP}.log"

    echo -e "${BLUE}[実行中]${NC} ${test_name}" | tee -a "${SUMMARY_LOG}"

    if [[ "${test_path}" == *.bats ]]; then
        # Batsテスト
        if bats "${test_path}" > "${log_file}" 2>&1; then
            echo -e "${GREEN}[成功]${NC} ${test_name}" | tee -a "${SUMMARY_LOG}"
            PASSED_TESTS+=("${test_name}")
            return 0
        else
            echo -e "${RED}[失敗]${NC} ${test_name}" | tee -a "${SUMMARY_LOG}"
            FAILED_TESTS+=("${test_name}")
            echo "  ログ: ${log_file}" | tee -a "${SUMMARY_LOG}"
            return 1
        fi
    else
        # Pytestテスト
        if uv run pytest "${test_path}" -v --tb=short > "${log_file}" 2>&1; then
            echo -e "${GREEN}[成功]${NC} ${test_name}" | tee -a "${SUMMARY_LOG}"
            PASSED_TESTS+=("${test_name}")
            return 0
        else
            local exit_code=$?
            if grep -q "no tests ran" "${log_file}" || grep -q "collected 0 items" "${log_file}"; then
                echo -e "${YELLOW}[スキップ]${NC} ${test_name} (テストなし)" | tee -a "${SUMMARY_LOG}"
                SKIPPED_TESTS+=("${test_name}")
                return 0
            else
                echo -e "${RED}[失敗]${NC} ${test_name}" | tee -a "${SUMMARY_LOG}"
                FAILED_TESTS+=("${test_name}")
                echo "  ログ: ${log_file}" | tee -a "${SUMMARY_LOG}"
                return 1
            fi
        fi
    fi
}

# ユニットテスト
echo -e "\n${BLUE}=== ユニットテスト ===${NC}" | tee -a "${SUMMARY_LOG}"
if [[ -d "tests/unit" ]]; then
    run_test "tests/unit/" "unit/all" || true
fi

# 統合テスト - Actions
echo -e "\n${BLUE}=== 統合テスト (Actions) ===${NC}" | tee -a "${SUMMARY_LOG}"
if [[ -d "tests/integration/actions" ]]; then
    for test_file in tests/integration/actions/*.py; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/actions/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done

    for test_file in tests/integration/actions/*.bats; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/actions/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done
fi

# 統合テスト - Services
echo -e "\n${BLUE}=== 統合テスト (Services) ===${NC}" | tee -a "${SUMMARY_LOG}"
if [[ -d "tests/integration/services" ]]; then
    for test_file in tests/integration/services/*.py; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/services/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done

    for test_file in tests/integration/services/*.bats; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/services/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done
fi

# 統合テスト - Common
echo -e "\n${BLUE}=== 統合テスト (Common) ===${NC}" | tee -a "${SUMMARY_LOG}"
if [[ -d "tests/integration/common" ]]; then
    for test_file in tests/integration/common/*.py; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/common/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done

    for test_file in tests/integration/common/*.bats; do
        [[ -f "${test_file}" ]] || continue
        test_name="integration/common/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done
fi

# E2Eテスト
echo -e "\n${BLUE}=== E2Eテスト ===${NC}" | tee -a "${SUMMARY_LOG}"
if [[ -d "tests/e2e" ]]; then
    for test_file in tests/e2e/*.py; do
        [[ -f "${test_file}" ]] || continue
        test_name="e2e/$(basename "${test_file}")"
        run_test "${test_file}" "${test_name}" || true
    done
fi

# サマリ表示
echo -e "\n${BLUE}=== テスト結果サマリ ===${NC}" | tee -a "${SUMMARY_LOG}"
echo "成功: ${#PASSED_TESTS[@]}" | tee -a "${SUMMARY_LOG}"
echo "失敗: ${#FAILED_TESTS[@]}" | tee -a "${SUMMARY_LOG}"
echo "スキップ: ${#SKIPPED_TESTS[@]}" | tee -a "${SUMMARY_LOG}"

if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
    echo -e "\n${RED}=== 失敗したテスト ===${NC}" | tee -a "${SUMMARY_LOG}"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - ${test}" | tee -a "${SUMMARY_LOG}"
    done
fi

if [[ ${#SKIPPED_TESTS[@]} -gt 0 ]]; then
    echo -e "\n${YELLOW}=== スキップされたテスト ===${NC}" | tee -a "${SUMMARY_LOG}"
    for test in "${SKIPPED_TESTS[@]}"; do
        echo "  - ${test}" | tee -a "${SUMMARY_LOG}"
    done
fi

echo -e "\n詳細ログ: ${LOG_DIR}/" | tee -a "${SUMMARY_LOG}"
echo "サマリ: ${SUMMARY_LOG}" | tee -a "${SUMMARY_LOG}"

# 終了コード
if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
    exit 1
else
    exit 0
fi
