# AI開発実装ルール

## Phase 1: 仕様策定・ドキュメント化・タスク管理

### 1.1 要件定義と設計
- 要件、アーキテクチャ、DB/API設計を `.amazonq/rules/` または `.kiro/steering/` に配置
- ADR（Architecture Decision Records）の作成と更新
- 設計レビューの実施と承認取得

### 1.2 実装計画策定
- 段階的実装フェーズの詳細計画
- 技術スタック選定と依存関係の整理
- リスク評価と対策の策定

### 1.3 タスクリスト作成と進捗管理
- 実装タスクの細分化（~300行目安のPR単位）
- 各タスクの優先度と依存関係の明確化
- 進捗追跡とマイルストーン設定

### 1.4 Exit Criteria
- 設計レビュー承認完了
- ADR更新完了
- 実装計画の承認取得

## Phase 2: 実装段階・コミット管理・動作確認

### 2.1 基盤実装
- 計画に基づく段階的実装
- README整備とドキュメント更新
- 基本機能の動作確認

### 2.2 コミット・ブランチ戦略
- trunk-based または簡易Git Flow
- ブランチ命名規則: `feature/`, `fix/`, `chore/`, `release/`
- Conventional Commits準拠（feat, fix, docs, refactor, test, chore, perf, build, ci）

### 2.3 各段階でのコミット管理
- 小さなPR（~300行目安）での段階的コミット
- ドラフトPRの活用
- セルフマージ禁止の徹底

### 2.4 起動確認・動作検証
- 各実装段階での動作確認
- 基本機能の確認
- エラーハンドリングの検証

### 2.5 Exit Criteria
- 基本機能動作確認完了
- 実装レビュー完了
- 統合動作の確認完了

## Phase 3: 機能検証・AI協調デバッグ

### 3.1 人間による機能検証
- 全機能の手動確認
- UX改善の実施
- 責務分離リファクタリング

### 3.2 AI協調でのデバッグ
- Amazon Q Developerセキュリティスキャンの活用
- 静的解析結果の確認と修正
- コード品質の向上

### 3.3 エラーハンドリング原則
- 問題発生時は前段階への戻り
- 根本原因の解決
- 重大設計変更時はPhase 1からの再開

### 3.4 テストに関する注釈
**重要**: この段階ではテストは後回しにする
- 機能実装と動作確認を優先
- この段階では正式なテスト（CIに組み込む単体テスト・包括的テスト）は作成しないこと。
- 理由: 機能が揺れており、包括的なテストを作成すると仕様変更時に大規模な手戻りを招くため。
- 許容: 機能検証を目的とした一時的なテスト（動作確認用）は作成してよいが、最終成果物には含めないこと。
- 包括的な単体テストは品質パート（Phase 4以降）に進んだ後に作成する。

### 3.5 Exit Criteria
- 全機能確認完了
- 品質レビュー完了
- ドキュメント更新完了

## 開発環境・ツール要件

### 仮想環境・依存管理（uv必須）
基本方針: uvを標準ツールとする。ロックファイル（uv.lock）は必ずコミット。

推奨セットアップ:
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
pipx install uv
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
scoop install uv
# 代替（CI等）
pip install uv
```

基本ワークフロー:
```bash
uv venv --python 3.13        # .venv に作成
uv lock                      # ロック生成
uv sync                      # 環境同期
uv add requests              # 依存追加
uv run python -m pytest      # 仮想環境で実行
```

制約:
- --systemは開発環境で禁止（CI/コンテナのみ許可）
- CIではuv syncによる再現性検証必須

### Pythonバージョンポリシー
- サポート: 直近LTSと最新安定版（例: 3.11/3.12/3.13）をCIマトリクスで検証
- EOL到来前にマイグレーション計画を作成
- pyproject.tomlのrequires-pythonを最新方針に整合

### 設定管理
- 全ツール設定はpyproject.tomlに統合（ruff, mypy, pytest, coverage等）
- requirements.txtは互換性維持のため自動同期生成可
- setup.py等の旧式構成は禁止

### Makefileと開発者体験
標準ターゲット例:
- bootstrap, lint, format, typecheck, test, cov, security, build, release, clean
- ローカル最小ループ: `make lint && make typecheck && make test`

### OS差異・ローカル設定
- 改行コード/パス/ロケール差異に配慮。テキストはLF統一
- ファイル監視/通知機構の差異に注意（特にWindows）

## セキュリティ・秘密情報管理

### 秘密情報管理
- ローカル: .env（コミット禁止）
- CI: OIDC＋リポジトリ/環境シークレット
- ログ/CI出力のシークレットマスキングを強制

### .env.*（秘密情報はコミット禁止）
- 除外漏れはCIで検出・警告する

### 権限最小化
- GitHub Actionsのpermissionsを最小化（read標準、必要時writeを限定）
- トークン権限の最小化・短命化

## ログ・時刻記録規則

### 構造化ログ
- JSONを標準。必須フィールド: timestamp（UTC, ISO8601）, level, event, message, logger, module, trace_id, span_id, user_id（あれば）、request_id
- PIIはマスキング/匿名化。PlainなPII出力は禁止

### 時刻・日付記録規則
- 全ログはtimezone-aware UTCを使用する
- ドキュメント上の日時は原則CI/ビルド時に自動埋め込みする
- AIが手入力で日時を記載する場合は、dateコマンド等で実際の現在時刻を確認してから記載すること（UTC/ISO 8601など形式を統一）
  - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"`
  - 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`

## AI特有の規約

### プロンプト設計
- テンプレート化と入力検証
- 秘密情報の持込み禁止
- プロンプトインジェクション対策を実施
- 依存データ（コンテキスト/ナレッジ）は出所と版を明記

### 実験管理・バージョニング
- seed固定、データセットバージョニング（DVC/MLflow/W&B等）
- モデルカード/リスク評価を作成

### ガードレール
- 出力フィルタ、コンテンツポリシー、PII検出/マスク
- 失敗時フォールバック、レート制御を設ける

### コスト管理
- トークン/推論コストのメトリクス化
- 上限設定、閾値超過のアラート

## データガバナンス

### データ分類
- 機微度分類（Public/Internal/Confidential/Restricted）と取り扱いルールを定義

### ライセンス/第三者データ
- 許容/禁止ライセンス一覧を維持
- 第三者データ/モデルの利用条件を記録

### 保持・削除
- 保持期間・削除ポリシー（GDPR/国内法等を考慮）
- 復旧計画と監査ログを保持

---
遵守事項:
- 本ルールはプロジェクトの品質基盤であり、逸脱はレビュー承認が必要である
- 追加機能実装時はPhase 1からの完全サイクルを繰り返すこと
