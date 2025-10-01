# テストスイート・ワークフロー再構築計画（2025年10月1日）

## 背景

現状のMcp-Dockerプロジェクトは、pytestによるPythonテストとbatsによるシェルテストが混在し、テスト数・構成ともに複雑化しています。また、GitHub Actionsワークフローも多数存在し、役割が重複しているものや、サンプルファイルが散在しています。プロジェクト本体が大幅にシンプル化されたため、テストスイートとワークフローも現状に合わせて再設計・再構築する必要があります。

## 現状の課題

### テストスイートの課題

- pytestテスト: 70+本、冗長・重複・保守困難なものが多い
- batsテスト: 10本以上、Dockerやシェル操作のE2Eテストが中心
- テストの粒度・責務が不明瞭
- CI/CDやMakefileとの連携が複雑
- テスト失敗時の原因特定が困難

### ワークフローの課題

- **アクティブなワークフロー**: 8本（ci.yml, quality-gates.yml, basic-test.yml, security.yml, release.yml, template-validation.yml, dependabot-auto-merge.yml, tmp-test-env.yml）
- **サンプルファイル**: 5本（*.sample）が散在し、用途が不明確
- **責務の重複**: ci.ymlとquality-gates.ymlが類似した処理を実行（合計49KB）
- **過度に複雑な設定**: quality-gates.ymlが791行、ci.ymlが522行と大規模化
- **保守コスト**: 多数のワークフローの維持・更新が負担

## シンプル化方針

### テストスイートのシンプル化

1. **テストの責務を明確化**
   - ユニットテスト（Python/pytest）: ロジック単体の検証
   - 統合テスト（bats or Python）: サービス連携やDocker動作の検証
   - E2Eテスト: 主要ユースケースのシナリオ検証

2. **pytest/batsの役割分担を整理**
   - Pythonロジックはpytestに集約
   - シェル/コンテナ起動・外部連携はbatsに集約

3. **テストディレクトリ構成の見直し**
   - `tests/unit/` ... pytestによるユニットテスト
   - `tests/integration/` ... batsまたはpytestによる統合テスト
   - `tests/e2e/` ... E2Eシナリオテスト

4. **冗長・重複テストの削除・統合**
   - 重要なカバレッジを維持しつつ、重複・古いテストは削除

5. **Makefile/CIのテスト実行もシンプルに**
   - `make test`で全体テスト、`make test-unit`/`make test-integration`/`make test-e2e`で個別実行

### ワークフローのシンプル化

1. **ワークフローの統合・削減**
   - ci.ymlとquality-gates.ymlを統合し、1つのCIワークフローに
   - tmp-test-env.ymlなど一時的なファイルは削除
   - basic-test.ymlはci.ymlに統合

2. **サンプルファイルの整理**
   - *.sampleファイルをdocs/examples/workflows/に移動
   - または不要なものは削除

3. **ワークフローの役割を明確化**
   - `ci.yml` ... PR/main pushでの基本CI（lint, test, build）
   - `security.yml` ... セキュリティスキャン（dependabot等と連携）
   - `release.yml` ... リリース時の自動化
   - `template-validation.yml` ... テンプレート検証（必要なら残す、不要なら削除）
   - `dependabot-auto-merge.yml` ... Dependabot自動マージ

4. **ワークフローサイズの削減**
   - 現状の791行/522行を、それぞれ200行以内に削減
   - 共通処理はcomposite actionに切り出し

5. **実行時間の最適化**
   - 並列実行の活用
   - キャッシュの効率化
   - 不要なステップの削除

## 実施ステップ

### フェーズ1: 現状分析と計画策定

1. **テストの棚卸し**
   - 既存pytest/batsテストを分類・リスト化
   - 各テストの責務・カバレッジ・実行時間を記録

2. **ワークフローの棚卸し**
   - 各ワークフローの目的・実行頻度・実行時間を記録
   - 重複する処理を特定

### フェーズ2: テストスイート再構築

1. **新ディレクトリ構成の作成**
   - `tests/unit/`, `tests/integration/`, `tests/e2e/`を新設

2. **テストの再配置・統合・削除**
   - 各テストを責務ごとに再配置、不要なものは削除
   - 重複テストを統合

3. **Makefileの更新**
   - テスト実行コマンドを新構成に対応

### フェーズ3: ワークフロー再構築

1. **ワークフローの統合**
   - ci.ymlとquality-gates.ymlを統合
   - basic-test.ymlを統合またはci.ymlに吸収

2. **サンプルファイルの整理**
   - *.sampleファイルをdocs/examples/workflows/に移動または削除

3. **ワークフローの最適化**
   - 共通処理をcomposite actionに切り出し
   - 並列実行・キャッシュの最適化

### フェーズ4: 検証とドキュメント化

1. **動作検証**
   - 新しいテスト・ワークフロー構成で問題ないか確認

2. **ドキュメント整備**
   - テスト方針・実行方法を明記
   - ワークフローの役割・使い方を文書化

## 参考: 新構成イメージ

### テストディレクトリ構成

```text
tests/
  unit/              # ユニットテスト（pytest）
    test_*.py
  integration/       # 統合テスト（batsまたはpytest）
    test_*.py
    test_*.bats
  e2e/              # E2Eシナリオテスト
    test_*.py
  helpers/          # テストヘルパー
  fixtures/         # テストフィクスチャ
```

### ワークフロー構成

```text
.github/
  workflows/
    ci.yml                        # メインCI（lint, test, build）
    security.yml                  # セキュリティスキャン
    release.yml                   # リリース自動化
    dependabot-auto-merge.yml     # Dependabot自動マージ
  actions/                        # 再利用可能なアクション
    setup-environment/            # 環境セットアップ
    run-tests/                    # テスト実行

docs/
  examples/
    workflows/                    # ワークフロー例・サンプル
      *.yml.sample
```

## 期待される効果

### テストスイート

- テスト実行時間の短縮（重複削除による）
- テスト失敗時の原因特定が容易に
- 保守性の向上

### ワークフロー

- CI実行時間の短縮（統合・最適化による）
- ワークフロー管理コストの削減
- 明確な責務分担で理解しやすく

---

この計画に基づき、段階的にテストスイートとワークフローを再構築していきます。ご意見・ご要望はIssueまたはPRでお寄せください。
