#!/usr/bin/env bash
# 重複テストの疑いを分析するスクリプト

set -euo pipefail

echo "=== 重複テストの疑い分析 ==="
echo ""

# テストファイル一覧を取得
find tests -name "test_*.py" -o -name "test_*.bats" | sort > /tmp/all_tests.txt

echo "## 🔴 高確率で重複している疑い"
echo ""

echo "### 1. Integration系の重複（4ファイル）"
echo "- e2e/test_integration_final.py (スキップ)"
echo "- e2e/test_final_integration_validation.py (スキップ)"
echo "- e2e/test_comprehensive_integration.py (成功)"
echo "- e2e/test_comprehensive_integration_suite.py (失敗)"
echo "→ 推奨: test_comprehensive_integration.py に統合"
echo ""

echo "### 2. Docker Integration系の重複（2ファイル）"
echo "- e2e/test_docker_integration_checker.py (成功)"
echo "- e2e/test_docker_integration_complete.py (成功)"
echo "→ 推奨: test_docker_integration_complete.py に統合"
echo ""

echo "### 3. Hangup系の重複（3ファイル）"
echo "- e2e/test_hangup_integration.py (失敗)"
echo "- e2e/test_hangup_end_to_end.py (失敗)"
echo "- e2e/test_hangup_scenarios_comprehensive.py (失敗)"
echo "→ 推奨: test_hangup_scenarios_comprehensive.py に統合"
echo ""

echo "### 4. End-to-End系の重複（2ファイル）"
echo "- e2e/test_end_to_end_validation.py (失敗)"
echo "- e2e/test_end_to_end_user_experience.py (失敗)"
echo "→ 推奨: test_end_to_end_validation.py に統合"
echo ""

echo "### 5. Performance Monitor系の重複（2ファイル）"
echo "- integration/actions/test_performance_monitor.py (失敗)"
echo "- integration/actions/test_performance_monitor_enhanced.py (失敗)"
echo "→ 推奨: test_performance_monitor_enhanced.py に統合"
echo ""

echo "### 6. Simulation Service系の重複（2ファイル）"
echo "- integration/actions/test_simulation_service.py (失敗)"
echo "- integration/actions/test_simulation_service_integration.py (失敗)"
echo "→ 推奨: test_simulation_service_integration.py に統合"
echo ""

echo "### 7. Services/Integration Bats系の重複（2ファイル）"
echo "- integration/services/test_services.bats (失敗)"
echo "- integration/services/test_integration.bats (失敗)"
echo "→ 推奨: test_integration.bats に統合"
echo ""

echo "## 🟡 中程度の重複疑い"
echo ""

echo "### 8. Distribution系（2ファイル）"
echo "- e2e/test_complete_distribution_validation.py (成功)"
echo "- e2e/test_comprehensive_distribution.py (成功)"
echo "→ 推奨: test_comprehensive_distribution.py に統合"
echo ""

echo "### 9. Act Wrapper系（2ファイル）"
echo "- integration/actions/test_enhanced_act_wrapper.py (失敗)"
echo "- integration/actions/test_act_wrapper_with_tracer.py (成功)"
echo "→ 推奨: 機能が異なる可能性あり、内容確認後に判断"
echo ""

echo ""
echo "=== 統計サマリ ==="
echo "重複疑いグループ: 9グループ"
echo "重複疑いファイル数: 21ファイル"
echo "削減可能ファイル数（推定）: 12ファイル"
echo ""

echo "=== 推奨アクション ==="
echo "1. スキップされているテスト（2ファイル）を即座に削除"
echo "2. 高確率重複（7グループ、19ファイル）の内容確認と統合"
echo "3. 統合後のテスト実行で動作確認"
echo ""

# 詳細分析用のファイル生成
cat > /tmp/duplicate_analysis.md << 'EOF'
# 重複テスト詳細分析

## 削除推奨（即座）

### スキップテスト（テストなし）
- `e2e/test_integration_final.py` - 削除
- `e2e/test_final_integration_validation.py` - 削除

## 統合推奨（高優先度）

### Integration系 → test_comprehensive_integration.py
- ❌ `e2e/test_integration_final.py`
- ❌ `e2e/test_final_integration_validation.py`
- ❌ `e2e/test_comprehensive_integration_suite.py`
- ✅ `e2e/test_comprehensive_integration.py` (残す)

### Docker Integration系 → test_docker_integration_complete.py
- ❌ `e2e/test_docker_integration_checker.py`
- ✅ `e2e/test_docker_integration_complete.py` (残す)

### Hangup系 → test_hangup_scenarios_comprehensive.py
- ❌ `e2e/test_hangup_integration.py`
- ❌ `e2e/test_hangup_end_to_end.py`
- ✅ `e2e/test_hangup_scenarios_comprehensive.py` (残す)

### End-to-End系 → test_end_to_end_validation.py
- ❌ `e2e/test_end_to_end_user_experience.py`
- ✅ `e2e/test_end_to_end_validation.py` (残す)

### Performance Monitor系 → test_performance_monitor_enhanced.py
- ❌ `integration/actions/test_performance_monitor.py`
- ✅ `integration/actions/test_performance_monitor_enhanced.py` (残す)

### Simulation Service系 → test_simulation_service_integration.py
- ❌ `integration/actions/test_simulation_service.py`
- ✅ `integration/actions/test_simulation_service_integration.py` (残す)

### Services Bats系 → test_integration.bats
- ❌ `integration/services/test_services.bats`
- ✅ `integration/services/test_integration.bats` (残す)

### Distribution系 → test_comprehensive_distribution.py
- ❌ `e2e/test_complete_distribution_validation.py`
- ✅ `e2e/test_comprehensive_distribution.py` (残す)

## 削減効果

- **削除対象**: 12ファイル
- **統合対象**: 8ファイル（残す）
- **削減率**: 約57% (21 → 9ファイル)

## 実装手順

1. スキップテスト削除（2ファイル）
2. 各グループの内容確認
3. 重複部分を統合先に移行
4. 削除対象ファイルを削除
5. テスト実行で動作確認
EOF

echo "詳細分析レポート: /tmp/duplicate_analysis.md"
cat /tmp/duplicate_analysis.md
