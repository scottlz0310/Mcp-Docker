# Docker特化実装ルール

- 日本語の応答、日本語の出力とエラーメッセージ、日本語のコメントとdocstring。
- 日本語でコミットメッセージを記入(Conventional Commitsは遵守)

## 🚫 禁止事項・必須ツール

### Python実行・依存関係管理
- **禁止**: `python3`, `pip`, `python -m pip` の使用
- **必須**: `uv run python`, `uv sync`, `uv add` の使用
- **理由**: モダンで高速な依存関係管理、仮想環境の自動管理

#### 正しいコマンド例
```bash
# ❌ 禁止
python3 -m pytest tests/
python3 main.py
pip install package

# ✅ 正しい
uv run python -m pytest tests/
uv run python main.py
uv add package
```

### パッケージ管理
- **禁止**: `apt`, `apt-get` の使用
- **推奨**: `homebrew` によるツール管理
- **理由**: クロスプラットフォーム対応、バージョン管理の一元化

### レガシーツール全般
- **方針**: レガシーなツールは使わずにモダンでスマートなツールを提案して使う

## Phase 1: 仕様策定・ドキュメント化・タスク管理

### 1.1 要件定義と設計

- 要件、アーキテクチャ、Docker設計を `.amazonq/rules/` に配置
- ADR（Architecture Decision Records）の作成と更新
- Docker設計レビューの実施と承認取得

### 1.2 実装計画策定

- 段階的実装フェーズの詳細計画
- 技術スタック選定: Docker, Docker Compose, Shell, YAML
- リスク評価と対策の策定

### 1.3 タスクリスト作成と進捗管理

- 実装タスクの細分化（サービス単位のPR）
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

- 小さなPR（サービス単位）での段階的コミット
- ドラフトPRの活用
- セルフマージ禁止の徹底

### 2.4 起動確認・動作検証

- 各実装段階でのDocker build確認
- サービス起動確認
- エラーハンドリングの検証

### 2.5 Exit Criteria

- 基本機能動作確認完了
- 実装レビュー完了
- 統合動作の確認完了

## Phase 3: 機能検証・AI協調デバッグ

### 3.1 人間による機能検証

- 全サービスの手動確認
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

**重要**: この段階では統合テストを優先

- Docker環境での動作確認を優先
- この段階では正式なテスト（CIに組み込む単体テスト・包括的テスト）は作成しないこと
- 理由: Docker設定が揺れており、包括的なテストを作成すると仕様変更時に大規模な手戻りを招くため
- 許容: 機能検証を目的とした一時的なテスト（動作確認用）は作成してよいが、最終成果物には含めないこと
- 包括的な統合テストは品質パート（Phase 4以降）に進んだ後に作成する

### 3.5 Exit Criteria

- 全機能確認完了
- 品質レビュー完了
- ドキュメント更新完了

## 開発環境・ツール要件

### Docker環境管理

基本方針: Docker & Docker Composeを標準ツールとする

推奨セットアップ:

```bash
# Docker Desktop (推奨)
# または Docker Engine + Docker Compose

# 基本確認
docker --version
docker-compose --version
```

基本ワークフロー:

```bash
docker build -t mcp-docker .     # イメージビルド
docker-compose up -d             # サービス起動
docker-compose logs              # ログ確認
docker-compose down              # サービス停止
```

制約:

- rootless Dockerを推奨（セキュリティ向上）
- CIではDocker layer cachingによる高速化必須

### コンテナバージョンポリシー

- サポート: Docker 20.10+, Docker Compose 2.0+をCIマトリクスで検証
- ベースイメージ: Alpine Linux最新安定版を使用
- 定期的なベースイメージ更新戦略

### 設定管理

- 全設定はdocker-compose.ymlに統合
- 環境変数は.env.templateで管理
- Dockerfileは単一責任原則に従う

### Makefileと開発者体験

標準ターゲット例:

- setup, build, start, stop, logs, test, clean, security
- ローカル最小ループ: `make build && make start && make test`

### OS差異・ローカル設定

- パス区切り文字の差異に配慮（Windows/Unix）
- ファイル権限の差異に注意（特にWindows）
- 改行コードはLF統一

## セキュリティ・秘密情報管理

### 秘密情報管理

- ローカル: .env（コミット禁止）
- CI: OIDC＋リポジトリ/環境シークレット
- ログ/CI出力のシークレットマスキングを強制

### .env.*（秘密情報はコミット禁止）

- 除外漏れはCIで検出・警告する
- .env.templateのみコミット

### 権限最小化

- GitHub Actionsのpermissionsを最小化（read標準、必要時writeを限定）
- トークン権限の最小化・短命化
- 非rootユーザーでのコンテナ実行

## ログ・時刻記録規則

### 構造化ログ

- JSONを標準。必須フィールド: timestamp（UTC, ISO8601）, level, event, message, service, container_id
- PIIはマスキング/匿名化。PlainなPII出力は禁止

### 時刻・日付記録規則

- 全ログはtimezone-aware UTCを使用する
- ドキュメント上の日時は原則CI/ビルド時に自動埋め込みする
- AIが手入力で日時を記載する場合は、dateコマンド等で実際の現在時刻を確認してから記載すること（UTC/ISO 8601など形式を統一）
  - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"`
  - 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`

## Docker特有の規約

### コンテナ設計原則

- **単一責任**: 1コンテナ1サービス
- **軽量化**: Alpine Linux使用、不要パッケージ削除
- **セキュリティ**: 非rootユーザー実行、最小権限
- **再現性**: 固定バージョン指定、決定論的ビルド

### イメージ管理・バージョニング

- セマンティックバージョニング（SemVer）準拠
- タグ戦略: latest, major.minor.patch, major.minor, major
- マルチステージビルドによる最適化

### ネットワーク・ストレージ

- 内部通信はDocker networkを使用
- 永続化データはnamed volumeを使用
- ポート公開は最小限に制限

### 設定注入

- 環境変数による設定注入を優先
- 設定ファイルはボリュームマウント
- シークレットはDocker secretsまたは環境変数

## データガバナンス

### データ分類

- 機微度分類（Public/Internal/Confidential/Restricted）と取り扱いルールを定義

### ライセンス/第三者イメージ

- 許容/禁止ライセンス一覧を維持
- 第三者イメージ/パッケージの利用条件を記録

### 保持・削除

- ログ保持期間・削除ポリシー
- イメージ・ボリューム管理戦略

---
遵守事項:

- 本ルールはプロジェクトの品質基盤であり、逸脱はレビュー承認が必要である
- 追加機能実装時はPhase 1からの完全サイクルを繰り返すこと
