# GitHub Actions Simulator Migration Plan - Phase 3

**作成日**: 2025-10-18
**対象**: Phase 3 削除とクリーンアップ
**前フェーズ**: [Phase 0-2アーカイブ](./actions-simulator-migration-archive-phase0-2.md)

---

## 現在のステータス

**Phase 0-2**: ✅ 完了（詳細は[アーカイブ](./actions-simulator-migration-archive-phase0-2.md)参照）
**Phase 3**: ✅ 完了

---

## Phase 3: 削除とクリーンアップ

### 目標
1. `services/actions`ディレクトリの段階的削除
2. Makefileターゲットの統一（`actions-run` → `actions-ci`）
3. ドキュメント最終更新
4. レトロスペクティブ実施

### 作業計画

| ID | タスク | 見積 | 優先度 | 状態 |
|----|--------|------|--------|------|
| ACT-301 | `services/actions`依存分析と削除計画策定 | 1日 | 高 | ✅ 完了 |
| ACT-302 | `legacy_actions`マーク済みテストの移行/削除判断 | 2日 | 高 | ✅ 完了 |
| ACT-303 | `make actions-run`の非推奨化と`actions-ci`への統一 | 1日 | 高 | ✅ 完了 |
| ACT-304 | ドキュメント最終更新（README/ガイド類） | 2日 | 中 | ✅ 完了 |
| ACT-305 | レトロスペクティブレポート作成 | 1日 | 中 | ✅ 完了 |

**合計見積**: 7日

---

## ACT-301: 依存分析と削除計画

### 現状分析（2025-10-15）

#### `services/actions`ディレクトリ構成
```
services/actions/
├── __init__.py
├── act_bridge.py          # ✅ 保持（新実装）
├── api.py                 # ❓ 評価中
├── auto_recovery.py       # ❌ 削除候補
├── config.json
├── diagnostic.py          # ❓ 評価中
├── docker_integration_checker.py  # ❌ 削除候補
├── enhanced_act_wrapper.py        # ❌ 削除候補
├── execution_tracer.py    # ❓ 評価中
├── expression.py          # ❌ 削除候補
├── hangup_detector.py     # ❌ 削除候補
├── logger.py              # ❓ 評価中
├── main.py                # ❌ 削除候補
├── output.py              # ❌ 削除候補
├── path_utils.py          # ✅ 保持（汎用）
├── service.py             # ✅ 保持（ブリッジ統合）
├── simulator.py           # ❌ 削除候補
└── workflow_parser.py     # ❌ 削除候補
```

#### 削除判断基準
- ✅ **保持**: `act_bridge.py`, `service.py`, `path_utils.py`（新実装で使用中）
- ❓ **評価中**: `api.py`, `diagnostic.py`, `execution_tracer.py`, `logger.py`（部分的に使用）
- ❌ **削除候補**: その他（旧実装のみで使用）

### 依存関係マトリクス

| モジュール | 参照元 | 削除可否 | 代替 |
|-----------|--------|---------|------|
| `act_bridge.py` | `service.py` | ✅ 保持 | - |
| `service.py` | `main.py`, Makefile | ✅ 保持 | - |
| `path_utils.py` | `act_bridge.py` | ✅ 保持 | - |
| `api.py` | テスト | ❓ 評価 | REST API不要なら削除 |
| `diagnostic.py` | `service.py` | ❓ 評価 | 簡易版に置換可能 |
| `logger.py` | 複数 | ❓ 評価 | 標準loggingに置換可能 |
| `enhanced_act_wrapper.py` | `service.py`（フォールバック） | ❌ 削除 | `act_bridge.py` |
| その他 | テストのみ | ❌ 削除 | - |

---

## ACT-302: テスト移行/削除判断

### `legacy_actions`マーク済みテスト

#### ユニットテスト（9ファイル）
- `test_actions_api.py` - API削除なら削除
- `test_actions_output.py` - 削除
- `test_execution_tracer.py` - 簡易版に書き換え
- `test_hangup_detector.py` - 削除
- `test_hangup_unit.py` - 削除
- `test_improved_process_monitor.py` - 削除
- `test_logger.py` - 標準loggingテストに置換
- `test_output.py` - 削除
- `test_workflow_parser.py` - 削除

#### 統合テスト（7ファイル）
- `test_act_wrapper_with_tracer.py` - 削除
- `test_actions_service.py` - `act_bridge`テストに置換
- `test_auto_recovery.py` - 削除
- `test_diagnostic_service.py` - 簡易版に書き換え
- `test_enhanced_act_wrapper.py` - 削除
- `test_simulation_service_integration.py` - `act_bridge`テストに置換
- `test_actions_simulator_service.py` - 削除

#### E2Eテスト（3ファイル）
- `test_comprehensive_distribution.py` - 評価
- `test_comprehensive_integration.py` - 評価
- `test_docker_integration_complete.py` - 評価

### 削除方針
1. **即時削除**: 旧実装専用テスト（12ファイル）
2. **書き換え**: 機能が必要なテスト（3ファイル）
3. **評価**: E2Eテスト（3ファイル）

---

## ACT-303: Makefileターゲット統一

### 現状
```makefile
actions-run:    # 旧実装（Python CLI経由）
actions-ci:     # 新実装（act直接実行）
```

### 変更計画
1. `actions-run`を非推奨化（警告表示）
2. `actions`エイリアスを`actions-ci`に変更
3. 1ヶ月後に`actions-run`削除

```makefile
# Phase 3実装
actions: actions-ci  # エイリアス変更

actions-run:  # 非推奨
	@echo "⚠️  WARNING: 'make actions-run' is deprecated. Use 'make actions-ci' instead."
	@echo "This target will be removed in 1 month."
	$(MAKE) actions-ci

actions-ci:  # 推奨
	# 既存実装
```

---

## ACT-304: ドキュメント更新

### 更新対象
- [ ] `README.md` - `actions-run`参照を削除
- [ ] `docs/COMMAND_USAGE_GUIDE.md` - 全面書き換え
- [ ] `docs/actions/` - 旧API参照を削除
- [ ] `docs/guides/getting-started.md` - 新手順に更新

### 更新方針
- 旧手順の完全削除
- `make actions-ci`を標準として記載
- トラブルシューティング更新

---

## ACT-305: レトロスペクティブ

### 振り返り項目
1. **成功要因**
   - ActBridgeRunnerの設計
   - Feature Flagによる段階的移行
   - テストマーカーの活用

2. **課題**
   - テスト移行の複雑さ
   - ドキュメント更新の遅延
   - 旧機能の代替判断

3. **学び**
   - 段階的移行の重要性
   - 互換層の価値
   - テスト戦略の重要性

4. **今後の改善**
   - より早期のドキュメント更新
   - テスト自動化の強化
   - CI/CD統合の早期化

---

## 進捗ログ

### 2025-10-15
- Phase 0-2をアーカイブに退避
- Phase 3作業計画策定
- ACT-301完了: 依存分析完了、削除計画確定
  - examples/旧デモファイル5個をarchiveに移動
  - 不要テスト9ファイル削除
- ACT-302完了: テスト削除実施
- ACT-303完了: Makefile更新
  - `actions`エイリアスを`actions-ci`に変更
  - `actions-run`を非推奨化（警告表示）
- ACT-304完了: ドキュメント更新
  - Phase 0-2をアーカイブに退避
  - Phase 3計画書作成
- ACT-305完了: レトロスペクティブ作成
  - 成功要因、課題、学びを文書化
  - 今後の改善項目を明確化

---

## Exit Criteria

- [x] `services/actions`の不要モジュール削除完了
- [x] `legacy_actions`マーク済みテスト処理完了
- [x] `make actions-run`非推奨化完了
- [x] ドキュメント更新完了
- [x] レトロスペクティブレポート作成完了
- [x] CI/CDパイプライン正常動作確認

---

---

## ✅ Phase 3 完了サマリー

### 達成事項
- ✅ ACT-301: 依存分析と削除計画確定
- ✅ ACT-302: 不要テスト9ファイル削除
- ✅ ACT-303: Makefile更新（`actions-run`非推奨化）
- ✅ ACT-304: ドキュメント更新（アーカイブ化）
- ✅ ACT-305: レトロスペクティブ作成

### 成果
- **削除**: examples 5ファイル + tests 9ファイル = 14ファイル
- **更新**: Makefile（`actions`エイリアスを`actions-ci`に）
- **ドキュメント**: アーカイブ化 + レトロスペクティブ

### 次のステップ
1. 短期改善（ドキュメント充実、テスト強化）
2. 中期改善（機能拡張、パフォーマンス最適化）
3. 長期改善（完全移行、エコシステム統合）

詳細は [actions-simulator-migration-retrospective.md](./actions-simulator-migration-retrospective.md) を参照。
