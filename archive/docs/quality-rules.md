# AI開発品質ルール

## Phase 4: リンティング・コード品質

### 4.1 リンター・フォーマッター・型
標準ツール:
- ruff（lint/format）, mypy（型）, pytest（テスト）

基本コマンド:
```bash
ruff check .
ruff format .
mypy .
pytest -q
```

補足:
- ruffを一次フォーマッタとし、blackは必要時のみ。二重整形の衝突は回避
- import順序はruffのimport-orderルールに準拠
- pyupgrade/UP系、B, C90x, I, T20x（print検出）を適用推奨

### 4.2 スタイルガイド
- PEP 8準拠。行長: コード88文字、コメント/Docstring 72文字
- PEP 257（Docstring）、NumPyもしくはGoogleスタイルをプロジェクトで統一
- 公開関数/クラス/モジュールにはDocstringを必須

### 4.3 型ヒント
- PEP 484準拠。Any使用時はPRで理由を明記
- 段階的厳格化: prototypeでは緩和、stagingで強化、productionでmypy strict相当へ
  - 推奨フラグ例: disallow-any-generics, no-implicit-optional, warn-redundant-casts等

### 4.4 セキュリティ静的解析
- 開発中スキャン: Amazon Q Developerセキュリティースキャン等
- 補助: bandit等のセキュリティlinterを導入可

### 4.5 デバッグ・ログ
- print使用は禁止。loggingを使用。ruff T20xで検出
- 構造化ログ（JSON）を標準とする。lazy loggingを徹底
- ログレベルの運用: DEBUG/INFO/WARNING/ERRORを適切に使用

### 4.6 推奨ruffルール（例）
- E/F/W（pycodestyle/pyflakes）, I（import order）, UP（pyupgrade）, B（bugbear）, C90x, T20x（print禁止）

### 4.7 推奨mypy strict設定（例）
```
warn_unused_ignores = True
warn_redundant_casts = True
no_implicit_optional = True
disallow_any_generics = True
warn_return_any = True
strict_equality = True
```

## Phase 5: テスト戦略・カバレッジ

### 5.1 構成
- フレームワーク: pytest
- 配置: tests/ディレクトリ配下、ファイル名はtest_*.py
- pytest-covによるカバレッジ測定をCIゲート化（行/分岐）

### 5.2 カバレッジ目標
- 最終目標: 80%以上（production）
- CIで閾値を設定し、未達はブロック
- カバレッジ設定は段階的厳格化がしやすいようにpyproject.tomlで一元管理する

### 5.3 段階別方針
```
prototype:
  - 単体テスト中心、mypy緩和、カバレッジ目標なし
staging:
  - 統合テスト追加、mypy厳格化、カバレッジ60%
production:
  - E2E/パフォーマンス、mypy strict、カバレッジ80%以上必須
```

### 5.4 絶対ルール

禁止:
- テスト成功を目的とする条件緩和・簡素化
- テスト失敗を回避する目的の@pytest.mark.skip
- カバレッジ稼ぎのみを目的としたテスト
  - 関数呼び出しだけでassertなし
  - assert True / assert None / 定数の固定判定
  - 既存テストと入力・期待結果が同一のコピー
  - test_coverage_booster.py等といった明らかなカバレッジ稼ぎ
- 無意味な__str__ / __repr__呼び出し
- 既存のテストtest_*.pyに対しtest_*_expanded.pyなど既存テストと重複するファイルの作成

必須:
- 各テストは以下のいずれかを含むこと
  - 入力と出力の関係を正しく検証
  - 想定される例外を検証
  - 副作用（ファイル生成、状態変更など）を検証
- 新規テスト作成は例外的な場合のみ
  - 既存テストが肥大化する場合
  - 新しい入力条件や例外パターンを扱う場合
- 各テストには目的をコメントで明記
  - 例: # 検証対象: foo() # 目的: 無効入力で例外を確認
- カバレッジレポート（pytest-covの出力: coverage.xml / term-missing）を必ず確認し、未カバー行を特定して重点的にテストを追加すること
- カバレッジ向上は既存test_*.py内で行い、未カバー行に対応する差分を追加すること

### 5.5 テストデータと再現性
- 疑似乱数のseed固定。時刻依存は固定注入（UTC）
- タイムゾーンは常にUTC。I/Oは安定化（並び順・ロケール固定）
- スナップショット/ゴールデンファイルは差分レビュープロセスを定義

### 5.6 契約/統合/E2E/パフォーマンス
- 外部APIは契約テストまたは信頼できるスタブで検証
- DB/メッセージブローカーは実体/軽量代替で統合テスト
- ベンチマークの基準値を設定し、回帰を検出。自動リトライは原則禁止

### 5.7 Mock戦略
- 各プラットフォーム(Windows,Linux,macOS)依存のテストは実環境を優先して、Mockによる代替は行わない
- 実環境に合わないテストはSKIP処理を用いて適切に除外する
- Mockの使用は最小限とするが、以下のケースでは適切にMockを使用する
 - 外部依存に関係する部分
 - 破壊的変更が起こるケース
 - 非決定的挙動を含む処理
 - エッジケースの再現が必要な場合

## Phase 6: CI/CD・自動化

### 6.1 マトリクス・キャッシュ
- OS × Pythonバージョンのマトリクス（Windows/Linux/macOS × 3.11/3.12/3.13目安）
- キャッシュキーはpyproject.tomlとuv.lockを含める

### 6.2 必須チェック
- 依存再現性（uv sync）
- lint（ruff）、type（mypy）、test+cov>=閾値
- セキュリティスキャン（CodeQL/SCA/Secret scan/SBOM）
- 秘密情報検出

### 6.3 デプロイ・環境保護
- 環境別に承認ゲートを設定（stg→prod）
- Branch Protection: 必須チェック、force-push禁止、linear history、必須レビュー人数を設定

### 6.4 失敗時通知
- Slack/Teams/GitHub通知を自動化。MTTA/MTTRの短縮を図る

### 6.5 Pre-commit規約
- 自動修正時はgit commit --amend --no-editを使用し、元メッセージは変更しない
- 自動修正のみ: "fix: pre-commitによる自動修正"

### 6.6 コミット規約・バージョニング
- Conventional Commits（feat, fix, docs, refactor, test, chore, perf, build, ci）
- SemVer準拠。重大変更はPR/CHANGELOGで明示

### 6.7 署名・DCO
- 署名コミット（GPG/SSH）またはDCOの採用を推奨。プロジェクトで統一

### 6.8 リリース
- タグ付与・GitHub Releaseの自動ノート生成。pre-releaseの扱いを定義
- バージョン整合（pyproject.toml / CHANGELOG / タグ）をCIで検証

### 6.9 CIワークフロー項目（参考）
- トリガ: PR, push（main）, schedule
- ジョブ: setup-uv → uv sync → lint → type → test+cov → security（CodeQL/SCA/Secret）→ sbom
- マトリクス: os=[ubuntu-latest, windows-latest, macos-latest], python=[3.11, 3.12, 3.13]
- permissions: contents: read, pull-requests: write（必要時のみ）等
- キャッシュキー: hashFiles('pyproject.toml', 'uv.lock')

## Phase 7: セキュリティ・品質保証

### 7.1 継続的セキュリティチェック
- GitHub Advanced Security（CodeQL, Secret scanning, Dependabot）を有効化
- SCA（Software Composition Analysis）をCIに組込

### 7.2 依存監査・SBOM・ライセンス
- SBOM生成（CycloneDX等）を定期的に実施
- ライセンス監査: 許容/禁止ライセンス一覧を維持。例：GPLv3の扱いは事前合意必須

### 7.3 秘密情報管理
- ローカル: .env（コミット禁止）。CI: OIDC＋リポジトリ/環境シークレット
- ログ/CI出力のシークレットマスキングを強制

### 7.4 権限最小化
- GitHub Actionsのpermissionsを最小化（read標準、必要時writeを限定）
- トークン権限の最小化・短命化

### 7.5 コンテナセキュリティ（該当時）
- ベースイメージの定期更新。Trivy等でスキャン
- ルートレス/最小権限実行、不要パッケージ削減

### 7.6 セキュリティ例外の承認
- 例外は期限・迂回策・再評価日を文書化し、承認者を明記

## Phase 8: 観測性・監視

### 8.1 構造化ログ
- JSONを標準。必須フィールド: timestamp（UTC, ISO8601）, level, event, message, logger, module, trace_id, span_id, user_id（あれば）、request_id
- PIIはマスキング/匿名化。PlainなPII出力は禁止

### 8.2 トレーシング/メトリクス
- OpenTelemetryを採用可。相関ID（trace_id/request_id）を各層で伝搬

### 8.3 時刻・日付記録規則
- 全ログはtimezone-aware UTCを使用する
- ドキュメント上の日時は原則CI/ビルド時に自動埋め込みする
- やむを得ず手入力で日時を記載する場合は、dateコマンド等で実際の現在時刻を確認してから記載すること（UTC/ISO 8601など形式を統一）
  - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"`
  - 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`

## AI特有の品質要件

### 評価・回帰
- 自動評価フレーム（正確性/安全性/バイアス/コスト/レイテンシ）を整備
- 回帰テストを導入

### 実験管理・バージョニング
- seed固定、データセットバージョニング（DVC/MLflow/W&B等）
- モデルカード/リスク評価を作成

### ガードレール
- 出力フィルタ、コンテンツポリシー、PII検出/マスク
- 失敗時フォールバック、レート制御を設ける

### コスト管理
- トークン/推論コストのメトリクス化
- 上限設定、閾値超過のアラート

## レビュー体制・品質ゲート

### レビュー体制/CODEOWNERS
- CODEOWNERSで責任範囲を明確化。必須レビュア数を設定
- 設計/実装/品質/セキュリティレビューを各フェーズ終盤に実施

### 品質ゲート
- 各Phaseの完了条件（Exit Criteria）を満たすまで次段階に進まない
- Phase 4: セキュリティレビュー完了、未解決脆弱性0
- Phase 5: デプロイ承認、環境保護設定完了
- Phase 6: 安定運用開始、Runbook整備

---

## 付録

### 付録A. 推奨.gitignore追記
```
__pycache__/
.venv/
output/
.cache/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.log
*.tmp
*.bak
.coverage
coverage.xml
htmlcov/
dist/
build/
pip-wheel-metadata/
.tox/
.DS_Store
.idea/
.vscode/
.env
.env.*
.python-version
```

### 付録B. 推奨Makefileターゲット例
```Makefile
.PHONY: bootstrap lint format typecheck test cov security build release clean
bootstrap:
	uv venv --python 3.13
	uv sync
	pre-commit install

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

test:
	uv run pytest -q

cov:
	uv run pytest --cov=src --cov-report=term-missing

security:
	# 例: bandit -r src || true
	echo "Run security scans in CI"

build:
	uv build

release:
	# タグ生成やリリースノート自動化をフック
	echo "Release pipeline"

clean:
	rm -rf .venv .cache .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage
```

---
遵守事項:
- 本ルールはプロジェクトの品質基盤であり、逸脱はレビュー承認が必要である
- 品質要件は段階的に厳格化し、最終的にproduction品質を達成すること
