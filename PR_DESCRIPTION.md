feat: テストスイート・ワークフローの完全再構築

## 🎯 目的

プロジェクトのシンプル化に伴い、テストスイートとワークフローを抜本的に再構築し、保守性・実行効率を向上させる。

## 📋 変更内容

### 1. テストファイルの完全再編成

#### 新しい3層構造
- **unit/** (12本): ユニットテスト（外部依存なし、高速）
- **integration/** (20本): 統合テスト（Docker, pytest + bats）
- **e2e/** (11本): E2Eテスト（完全なシナリオ）

#### 削除・統合
- 不要なテストランナー6本を削除
- 重複ファイル（test_docs_consistency.py）を削除
- **合計19%削減** (53本 → 43本)

### 2. ワークフローの整理

- サンプルファイル5本を`docs/examples/workflows/`に移動
  - basic-ci-example.yml
  - comprehensive-tests.yml
  - docs-validation.yml
  - local-development-ci.yml
  - security-scanning.yml
- 一時ファイル（tmp-test-env.yml）を削除
- 各サンプルの使い方を記載したREADME追加

### 3. 開発環境の改善

#### Makefile拡張
```bash
make test-unit         # ユニットテストのみ（高速）
make test-integration  # 統合テスト（pytest + bats）
make test-e2e          # E2Eテスト（タイムアウト5分）
make test-quick        # 高速テスト（unit + integration）
```

#### pyproject.toml設定追加
- pytest設定（testpaths, markers, timeout）
- unit/integration/e2eマーカー定義

#### README更新
- 新テスト構成の説明
- 実行方法・用途を明記

### 4. 詳細ドキュメント

- **docs/test-suite/REBUILD_PLAN.md**: 4フェーズの再構築計画
- **docs/test-suite/TEST_INVENTORY.md**: 53本の詳細分析
- **docs/test-suite/WORKFLOW_INVENTORY.md**: 8本のワークフロー分析
- 各テストディレクトリにREADME（目的・用途・ベストプラクティス）

## 🎁 効果

### コードベースの改善
- **-2,227行削除** (約41%のコード削減)
- 明確な責務分担（unit/integration/e2e）
- テスト実行時間の最適化（必要なテストのみ実行可能）

### 開発体験の向上
- テストの目的が明確
- 高速フィードバック（ユニットテストのみ実行可能）
- 保守性の大幅向上

## ✅ チェックリスト

- [x] 全テストが新構造に移行
- [x] Makefileコマンド追加・動作確認
- [x] README更新
- [x] 詳細ドキュメント作成
- [x] pre-commitチェック通過
- [x] 既存機能への影響なし確認

## 🔍 レビューポイント

1. テストの分類（unit/integration/e2e）は適切か
2. Makefileコマンドは直感的か
3. ドキュメントは十分か
4. 削除したファイルに問題はないか

## 📖 次のステップ

この再構築により、今後以下が可能に：
- CI/CDパイプラインの最適化（並列実行等）
- テストカバレッジの可視化
- より効率的な開発ワークフロー
