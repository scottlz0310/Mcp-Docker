# テスト棚卸し結果（2025年10月2日）

## サマリー

- **Pytestテストファイル**: 47本、合計16,853行
- **Batsテストファイル**: 6本、合計1,261行
- **合計**: 53本のテストファイル、18,114行

## Pytestテスト分類（提案）

### 🟢 ユニットテスト候補（Unit Tests）- 12本

純粋なロジックテスト、外部依存なし

| ファイル名 | 行数 | 分類理由 | 優先度 |
|-----------|------|---------|--------|
| test_logger.py | N/A | ロギング機能の単体テスト | ⭐⭐⭐ |
| test_execution_tracer.py | 316 | トレーサーロジックの単体テスト | ⭐⭐⭐ |
| test_hangup_detector.py | 468 | ハングアップ検出ロジック | ⭐⭐⭐ |
| test_performance_monitor.py | 435 | パフォーマンス監視ロジック | ⭐⭐⭐ |
| test_performance_monitor_enhanced.py | 453 | 拡張パフォーマンス監視 | ⭐⭐ |
| test_improved_process_monitor.py | 276 | プロセス監視ロジック | ⭐⭐ |
| test_workflow_parser.py | 299 | ワークフローパーサー | ⭐⭐⭐ |
| test_expression.py | 294 | 式評価ロジック | ⭐⭐⭐ |
| test_output.py | N/A | 出力処理のテスト | ⭐⭐ |
| test_actions_output.py | N/A | アクション出力テスト | ⭐⭐ |
| test_actions_api.py | N/A | Actions API単体テスト | ⭐⭐⭐ |
| test_hangup_unit.py | N/A | ハングアップ単体テスト | ⭐⭐⭐ |

### 🟡 統合テスト候補（Integration Tests）- 20本

サービス連携、Docker操作を含む

| ファイル名 | 行数 | 分類理由 | 優先度 |
|-----------|------|---------|--------|
| test_docker_integration_checker.py | 338 | Docker統合チェック | ⭐⭐⭐ |
| test_docker_integration_complete.py | 287 | Docker完全統合テスト | ⭐⭐⭐ |
| test_actions_service.py | N/A | Actionsサービス統合 | ⭐⭐⭐ |
| test_diagnostic_service.py | 342 | 診断サービス統合 | ⭐⭐⭐ |
| test_simulation_service.py | N/A | シミュレーションサービス | ⭐⭐⭐ |
| test_simulation_service_integration.py | 348 | シミュレーション統合 | ⭐⭐⭐ |
| test_auto_recovery.py | 433 | 自動リカバリ統合 | ⭐⭐⭐ |
| test_enhanced_act_wrapper.py | 701 | 拡張Act wrapper統合 | ⭐⭐⭐ |
| test_act_wrapper_with_tracer.py | N/A | Act wrapper + tracer | ⭐⭐ |
| test_hangup_integration.py | 448 | ハングアップ統合テスト | ⭐⭐⭐ |
| test_integration_final.py | 313 | 最終統合テスト | ⭐⭐ |
| test_support_integration.py | 457 | サポート機能統合 | ⭐⭐ |
| test_docs_consistency.py | N/A | ドキュメント整合性 | ⭐⭐ |
| test_documentation_consistency.py | 547 | ドキュメント整合性v2 | ⭐⭐ |
| test_template_validation.py | 718 | テンプレート検証 | ⭐⭐ |
| test_platform_support.py | 415 | プラットフォームサポート | ⭐⭐ |
| test_comprehensive_integration.py | 683 | 包括的統合テスト | ⭐ |
| test_comprehensive_integration_suite.py | 752 | 包括的統合スイート | ⭐ |
| test_complete_distribution_validation.py | 537 | 配布検証 | ⭐ |
| test_comprehensive_distribution.py | 501 | 包括的配布テスト | ⭐ |

### 🔴 E2Eテスト候補（End-to-End Tests）- 9本

エンドツーエンドシナリオテスト

| ファイル名 | 行数 | 分類理由 | 優先度 |
|-----------|------|---------|--------|
| test_end_to_end_validation.py | 1065 | E2E検証（大規模） | ⭐⭐⭐ |
| test_end_to_end_user_experience.py | 634 | ユーザー体験E2E | ⭐⭐⭐ |
| test_hangup_end_to_end.py | 823 | ハングアップE2E | ⭐⭐⭐ |
| test_hangup_scenarios_comprehensive.py | 530 | ハングアップシナリオ | ⭐⭐ |
| test_final_integration_validation.py | 1054 | 最終統合検証（大規模） | ⭐ |
| test_performance_stability_validation.py | 802 | パフォーマンス安定性 | ⭐⭐ |

### ⚫ 削除候補（Redundant/Obsolete）- 6本

重複または用途不明

| ファイル名 | 理由 | アクション |
|-----------|------|-----------|
| run_comprehensive_test_suite.py | 他のテストランナーと重複 | 削除または統合 |
| run_comprehensive_integration_tests.py | 他のテストランナーと重複 | 削除または統合 |
| run_hangup_tests.py | pytest直接実行で十分 | 削除 |
| integration_test.sh | 古いシェルスクリプト | 削除またはbatsに統合 |
| integration_test_summary.py | 用途不明 | 削除 |
| TEST_SUMMARY.md | 古いドキュメント | 削除または更新 |

## Batsテスト分類（提案）

### 🟡 統合テスト（Integration Tests）- 5本

| ファイル名 | 行数 | 分類理由 | 優先度 |
|-----------|------|---------|--------|
| test_docker_build.bats | 37 | Docker build統合テスト | ⭐⭐⭐ |
| test_services.bats | 110 | サービス起動テスト | ⭐⭐⭐ |
| test_integration.bats | 99 | 一般統合テスト | ⭐⭐ |
| test_security.bats | 107 | セキュリティチェック | ⭐⭐⭐ |
| test_actions_simulator.bats | 275 | Actions simulator統合 | ⭐⭐⭐ |

### 🔴 E2Eテスト（End-to-End Tests）- 1本

| ファイル名 | 行数 | 分類理由 | 優先度 |
|-----------|------|---------|--------|
| test_hangup_scenarios.bats | 633 | ハングアップシナリオE2E | ⭐⭐⭐ |

## 重複・統合候補

### ドキュメント整合性テスト

- `test_docs_consistency.py` vs `test_documentation_consistency.py`
- **提案**: 新しい方（documentation_consistency）を残し、古い方を削除

### 包括的テスト

- `test_comprehensive_integration.py` (683行)
- `test_comprehensive_integration_suite.py` (752行)
- `test_comprehensive_distribution.py` (501行)
- **提案**: 重複機能を整理し、1つに統合

### ハングアップテスト

- `test_hangup_unit.py` → unit/
- `test_hangup_detector.py` → unit/
- `test_hangup_integration.py` → integration/
- `test_hangup_end_to_end.py` → e2e/
- `test_hangup_scenarios_comprehensive.py` → e2e/（または統合）
- `test_hangup_scenarios.bats` → e2e/
- **提案**: 責務を明確化し、重複を削除

### パフォーマンステスト

- `test_performance_monitor.py` → unit/
- `test_performance_monitor_enhanced.py` → unit/（または統合）
- `test_performance_stability_validation.py` → e2e/
- **提案**: enhanced版をメインとし、古い版は削除検討

## 推奨アクション

### 即座に削除可能

1. `run_comprehensive_test_suite.py`
2. `run_comprehensive_integration_tests.py`
3. `run_hangup_tests.py`
4. `integration_test.sh`
5. `integration_test_summary.py`
6. `TEST_SUMMARY.md`（または大幅更新）
7. `test_docs_consistency.py`（documentation_consistency版を残す）

### 統合・簡略化

1. comprehensive系テストを1つに統合
2. ハングアップテストの責務を明確化
3. パフォーマンステストの重複削除

### 新ディレクトリへの移行優先順位

**⭐⭐⭐ 最優先（必須テスト）**:
- unit/: test_execution_tracer.py, test_hangup_detector.py, test_workflow_parser.py, test_expression.py
- integration/: test_docker_integration_checker.py, test_actions_service.py, test_diagnostic_service.py
- e2e/: test_end_to_end_validation.py, test_end_to_end_user_experience.py

**⭐⭐ 中優先**:
- unit/: test_performance_monitor_enhanced.py
- integration/: test_enhanced_act_wrapper.py, test_auto_recovery.py
- e2e/: test_hangup_end_to_end.py

**⭐ 低優先（整理後に判断）**:
- comprehensive系、distribution系

## 推定削減効果

- **現状**: 53ファイル、18,114行
- **目標**: 30ファイル、10,000行程度
- **削減率**: 約45%の削減
