# ワークフロー棚卸し結果（2025年10月2日）

## サマリー

- **アクティブなワークフロー**: 8本
- **サンプルファイル**: 5本
- **合計サイズ**: 約100KB

## アクティブワークフロー分析

### 🔴 統合・削減が必要（Critical）

| ファイル名 | 行数/サイズ | 目的 | 実行頻度 | 優先度 | アクション |
|-----------|------------|------|---------|--------|-----------|
| **ci.yml** | 522行/18KB | メインCI | PR/Push | ⭐⭐⭐ | quality-gates.ymlと統合 |
| **quality-gates.yml** | 791行/31KB | 品質ゲート | PR/Push/定期 | ⭐⭐⭐ | ci.ymlに統合 |
| **basic-test.yml** | 3.3KB | 基本テスト | PR | ⭐⭐ | ci.ymlに統合 |
| **tmp-test-env.yml** | 288B | 一時テスト | 手動？ | ❌ | **削除** |

**問題点**:
- ci.yml（522行）とquality-gates.yml（791行）が重複した処理を実行
- 合計1,313行、49KBと過剰に肥大化
- basic-test.ymlは冗長（ci.ymlで実現可能）
- tmp-test-env.ymlは一時ファイルで不要

**統合提案**:
```
新ci.yml (200-300行)
├─ fast-lint (現ci.ymlから)
├─ unit-tests (新規）
├─ integration-tests (現quality-gates.ymlから)
├─ security-scan (現quality-gates.ymlから)
└─ build-validation (現basic-test.ymlから)
```

### 🟢 維持（Keep）

| ファイル名 | サイズ | 目的 | 実行頻度 | 優先度 | アクション |
|-----------|--------|------|---------|--------|-----------|
| **security.yml** | 5.2KB | セキュリティスキャン | PR/Push/定期 | ⭐⭐⭐ | 維持（軽微な最適化） |
| **release.yml** | 16KB | リリース自動化 | タグpush時 | ⭐⭐⭐ | 維持（軽微な最適化） |
| **dependabot-auto-merge.yml** | 817B | Dependabot自動マージ | Dependabot PR時 | ⭐⭐⭐ | 維持 |

### 🟡 要検討（Review）

| ファイル名 | サイズ | 目的 | 実行頻度 | 優先度 | アクション |
|-----------|--------|------|---------|--------|-----------|
| **template-validation.yml** | 19KB | テンプレート検証 | PR/Push | ⭐⭐ | 用途確認後、統合または削除 |

**検討ポイント**:
- template-validation.ymlの実際の用途が不明確
- プロジェクトがシンプル化されたため、必要性を再評価

## サンプルファイル分析

### 📁 整理が必要

| ファイル名 | サイズ | 状況 | アクション |
|-----------|--------|------|-----------|
| basic-test.yml.sample | 3.3KB | basic-test.ymlと同一？ | docs/examples/workflows/へ移動または削除 |
| comprehensive-tests.yml.sample | 16KB | 大規模テスト設定例 | docs/examples/workflows/へ移動 |
| docs-check.yml.sample | 3.4KB | ドキュメントチェック例 | docs/examples/workflows/へ移動 |
| local-ci.yml.sample | 37KB | ローカルCI設定（超大規模） | 簡略化してdocs/examples/workflows/へ移動 |
| security-scan.yml.sample | 12KB | セキュリティスキャン例 | docs/examples/workflows/へ移動 |

**問題点**:
- .sampleファイルが.github/workflows/に散在
- local-ci.yml.sampleが37KBと異常に大きい
- 用途・意図が不明確

**提案**:
```
docs/examples/workflows/
├─ basic-ci-example.yml          (basic-test.yml.sample)
├─ comprehensive-tests.yml       (comprehensive-tests.yml.sample)
├─ docs-validation.yml           (docs-check.yml.sample)
├─ local-development-ci.yml      (local-ci.yml.sample - 簡略化)
└─ security-scanning.yml         (security-scan.yml.sample)
```

## 重複処理の詳細分析

### ci.yml vs quality-gates.yml

**ci.yml** (522行):
```yaml
jobs:
  fast-lint:           # 30行 - 基本lint
  install-deps:        # 50行 - 依存関係インストール
  pytest:              # 80行 - Pytestテスト
  bats-test:           # 60行 - Batsテスト
  docker-build:        # 70行 - Dockerビルド
  security-basic:      # 50行 - 基本セキュリティ
  quality-check:       # 100行 - 品質チェック
  ... (その他)
```

**quality-gates.yml** (791行):
```yaml
jobs:
  distribution-quality:     # 150行 - 配布品質
  documentation-validation: # 120行 - ドキュメント検証
  template-validation:      # 100行 - テンプレート検証
  end-to-end-validation:    # 200行 - E2E検証
  security-comprehensive:   # 150行 - 包括的セキュリティ
  performance-validation:   # 71行 - パフォーマンス
  ... (その他)
```

**重複している処理**:
1. 環境セットアップ（両方で実行）
2. 依存関係インストール（両方で実行）
3. 基本テスト（ci.ymlとquality-gates.ymlで類似）
4. セキュリティスキャン（security-basicとsecurity-comprehensive）
5. ドキュメント検証（両方で実行）

**統合後の想定構造**:
```yaml
# 新ci.yml (250-300行目標)
jobs:
  # --- Phase 1: Fast Checks (並列実行) ---
  fast-lint:              # 20行 - 高速lint（ruff, shellcheck等）

  # --- Phase 2: Build & Unit Tests (並列実行) ---
  docker-build:           # 40行 - Dockerイメージビルド
  unit-tests:             # 50行 - ユニットテスト（pytest）

  # --- Phase 3: Integration Tests (並列実行) ---
  integration-tests:      # 60行 - 統合テスト（pytest + bats）
  security-scan:          # 40行 - セキュリティスキャン

  # --- Phase 4: E2E & Validation (条件付き実行) ---
  e2e-tests:             # 50行 - E2Eテスト（mainブランチのみ）
  performance-check:      # 40行 - パフォーマンス検証（mainブランチのみ）
```

## composite actionへの切り出し候補

### 共通処理を再利用可能なアクションに

```
.github/actions/
├─ setup-environment/       # 環境セットアップ（Python, uv, Docker等）
│  └─ action.yml
├─ install-dependencies/    # 依存関係インストール
│  └─ action.yml
├─ run-unit-tests/         # ユニットテスト実行
│  └─ action.yml
├─ run-integration-tests/  # 統合テスト実行
│  └─ action.yml
└─ run-security-scan/      # セキュリティスキャン実行
   └─ action.yml
```

**期待効果**:
- 各ワークフローで再利用可能
- メンテナンス性の向上
- ワークフローファイルの大幅な削減

## 推奨アクション

### 即座に実施可能

1. **tmp-test-env.ymlの削除** ✂️
2. **サンプルファイルをdocs/examples/workflows/に移動** 📁
3. **basic-test.ymlをci.ymlに統合** 🔄

### 段階的に実施

4. **composite actionの作成** 🔧
   - setup-environment
   - install-dependencies
   - run-tests

5. **ci.ymlとquality-gates.ymlの統合** 🔄
   - 新ci.ymlに統合（250-300行目標）
   - 並列実行・キャッシュの最適化

6. **template-validation.ymlの用途確認** 🔍
   - 必要なら維持、不要なら削除または統合

### ドキュメント化

7. **ワークフロー実行ガイドの作成** 📝
   - 各ワークフローの目的・実行タイミングを明記
   - トラブルシューティングガイド

## 推定削減効果

| 項目 | 現状 | 目標 | 削減率 |
|-----|------|------|--------|
| アクティブワークフロー | 8本 | 5本 | 37.5% |
| 合計行数 | 約2,000行 | 約600行 | 70% |
| 合計サイズ | 約100KB | 約30KB | 70% |
| CI実行時間（推定） | 15-20分 | 8-12分 | 40-50% |

## 実行時間の最適化戦略

### 並列実行の活用

```yaml
# 現状: 直列実行（遅い）
lint → tests → build → security → docs

# 改善: 並列実行（速い）
Phase 1: lint (2分)
Phase 2: [unit-tests, docker-build] (3分)
Phase 3: [integration-tests, security-scan] (5分)
Phase 4: e2e-tests (mainのみ, 7分)
```

### キャッシュの最適化

1. **uvキャッシュ**: Python依存関係（~2分短縮）
2. **Dockerレイヤーキャッシュ**: イメージビルド（~3分短縮）
3. **npmキャッシュ**: フロントエンド依存関係（該当する場合）

### 条件付き実行

- **E2Eテスト**: mainブランチ・リリース時のみ
- **パフォーマンステスト**: mainブランチのみ
- **包括的セキュリティスキャン**: 定期実行（daily）
