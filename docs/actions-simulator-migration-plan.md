# GitHub Actions Simulator Migration Plan

**作成日**: 2025-10-14
**対象**: GitHub Actions Simulator (`services/actions/*`) → `act` ベース CI互換モード (`make actions-ci`)
**作成者**: MCP Docker Team

---

## 1. 背景と現状整理

- 旧実装: `services/actions/` 配下の Python サービス。CLI (`make actions-run`: Makefile:91) や Docker ランチャー (`scripts/run-actions.sh`) が依存し、診断・ハング検知・自動復旧などを内包。
- 新実装: `.actrc` でフル互換イメージ (`ghcr.io/catthehacker/ubuntu:full-24.04`) を固定し、`make actions-ci` が `act -W <workflow>` を直接実行（Makefile:276, .actrc:1）。
- テスト/ドキュメント: `rg` 調査で 30 ファイルが `services.actions` を参照（テスト: `tests/integration/actions/test_diagnostic_service.py` など、ドキュメント: `docs/COMMAND_USAGE_GUIDE.md` 他多数）。新実装へ切替えると現行テストの大半が失敗する。

### 1.1 現行利用状況インベントリ（2025-10-14調査）
- **エントリーポイント**: `Makefile:91-166`（旧 CLI 対話実行）、`scripts/run-actions.sh`（Docker 経由ランチャー）、`main.py`（Click CLI）。
- **自動化スクリプト**: `scripts/run-hangup-regression-tests.sh`, `scripts/run_bats.py`, `scripts/verify-container-startup.sh` が直接モジュールを import。
- **テスト**: 単体/統合/バッテリー（BATS）テストが `services.actions` に依存（例: `tests/unit/test_hangup_detector.py`, `tests/integration/actions/test_enhanced_act_wrapper.py`, `tests/e2e/test_hangup_scenarios.bats`）。テストデータやフィクスチャも旧 API 前提。
- **ドキュメント**: `docs/COMMAND_USAGE_GUIDE.md`, `docs/actions/API_REFERENCE.md`, `docs/guides/getting-started.md` が旧 CLI コマンドを案内。
- **アーカイブ/履歴**: `archive/docs/actions/actions-service-proposal.md` や `archive/reports/ACT_WRAPPER_MIGRATION_SUMMARY.md` にも旧サービスの詳細が残存。

### 1.2 旧サービスの主要機能モジュール
| 機能カテゴリ | 主担当モジュール | 概要 |
| --- | --- | --- |
| act 実行ラッパー | `services/actions/enhanced_act_wrapper.py`, `service.py` | act プロセス起動、ストリーミング監視、詳細レポート組み立て |
| 診断 / 事前検証 | `services/actions/diagnostic.py`, `docker_integration_checker.py` | Docker/act バイナリ検証、環境チェック |
| ハング検知 | `services/actions/hangup_detector.py`, `execution_tracer.py` | スレッド監視、デッドロック指標出力 |
| 自動復旧 | `services/actions/auto_recovery.py` | Docker 再接続やサブプロセス再起動ロジック |
| ロギング / 出力整理 | `services/actions/logger.py`, `output.py` | Rich ロガー、アーティファクト整形 |
| ワークフロー解析 | `services/actions/workflow_parser.py`, `expression.py`, `path_utils.py` | YAML 解析、パス解決、式評価 |

### 1.3 新 `act` ベースワークフローの状況
- `Makefile:276-340` が対話 UI を提供し `act -W` を直接呼び出す。イメージ指定は `.actrc:1-6`。
- `scripts/verify-ci-compatibility.sh:17` など周辺スクリプトも `act` 直接実行を想定。
- 高機能な診断/ハング検知は未移植で、新ターゲット利用時は得られない。

> 課題: 旧サービスの複雑な機能をどう扱うか、テストフレームワークの移行、ドキュメント更新の遅延が移行のボトルネック。

---

## 2. 目標

- 旧 `services/actions` 実装を段階的に廃止し、`act` ベースの CI 互換ワークフローに統一。
- ユーザー向け CLI / Make ターゲットを新実装に切り替えても違和感なく利用できる状態をつくる。
- テストスイートと補助スクリプトを新実装に追随させ、継続的な保守コストを削減。
- ロールバック・観測手段を確保し、移行による開発体験の劣化を防ぐ。

---

## 3. 対象範囲 / 非対象

**対象**
- `services/actions` モジュール群の依存洗い出しと段階的削除
- Makefile ターゲット・CLI (`main.py`) の統一方針
- テスト（ユニット/統合/E2E）と自動化スクリプトの更新
- ドキュメント・開発手順の刷新

**非対象**
- GitHub Release Watcher 等、Actions Simulator 以外のサービス
- Docker Compose 構成の抜本的見直し（必要な範囲の調整に留める）
- Windows/macOS 固有要件の追加対応（既存カバレッジを維持）

---

## 4. ステークホルダー

- **Migration Owner**: Actions Simulator 開発担当
- **QA / Testing**: テスト自動化担当
- **Dev Experience**: 内部利用者 (開発チーム)
- **Ops / CI**: CI/CD パイプライン管理者

---

## 5. フェーズ別計画

### Phase 0: 調査と設計確定（~1 週間）
- `services/actions` 参照の 30 ファイルについて、目的・優先度・移行先案をスプレッドシートで整理。
- 旧サービス機能と `act` ベース代替手段のギャップ分析（診断・ハング検知・アーティファクト出力）。
- `make actions-run` / `scripts/run-actions.sh` の実行フローを時系列図にし、ブリッジ挿入ポイントを特定。
- 成果物:
  - 依存マトリクス（ファイル/テスト/ドキュメント別）
  - 機能ギャップ報告と優先度
  - ブリッジ設計ドラフト（I/O、設定項目、ロギング方針）

### Phase 1: ブリッジとテスト対応（~2 週間）
- 旧サービス CLI (`SimulationService`, `EnhancedActWrapper`) から `act` を呼び出すブリッジ実装 & Feature Flag 導入。
- 単体テスト (`tests/unit/test_*`) を新ブリッジ経由に書き換え、BATS/E2E はフラグで段階的に切替。
- `Makefile:91` / `scripts/run-actions.sh` に警告表示を追加し、新ターゲット導線を案内。ドキュメントは暫定で両モード併記。
- 成果物:
  - ブリッジ層コード + 設定フラグ
  - テストマトリクス（移行済/残存）
  - 更新済み README / COMMAND ガイド（旧モード注意記載）

### Phase 2: フル切り替え準備（~2 週間）
- BATS/E2E テストを `act` 直接実行へ切替え、`services/actions` 依存をゼロへ。未移行テストは削除 or 代替を判断。
- ハング検知/診断/自動復旧の代替を CLI フック（例: `scripts/run-actions.sh` での前後処理）または独立ツールとして再提供。
- リンター（`ruff` or カスタムスクリプト）で `services.actions` import を禁止し、CI で検知。
- 成果物:
  - 100% `act` ベースのテストスイート
  - 代替ツールまたは仕様策定完了
  - CI チェック（Import 禁止）と移行完了レポート

### Phase 3: 削除とクリーンアップ（~1 週間）
- 旧 `services/actions` ディレクトリを削除し、関連依存（インポート・設定・ドキュメント）を整理。
- Makefile・CLI・スクリプトから旧ターゲット/オプションを外し、`make actions-run` を `make actions-ci` に統一。
- 最終ドキュメント更新、学習共有（事後レビュー）を実施。
- 成果物:
  - クリーンなコードベース（旧実装削除）
  - 更新済みドキュメント一式
  - レトロスペクティブレポート

---

## 6. テスト戦略

- **段階的移行**: Phase 1 で互換層を有効化し、`pytest` と BATS (`tests/e2e/test_hangup_scenarios.bats`) を緑のまま維持。
- **サニティチェック**: `make actions-ci` と `scripts/verify-ci-compatibility.sh` を Nightly で実行し、`act` 単体のリグレッションを検出。
- **比較検証**: 旧サービスの詳細ログ（`services/actions/output.py`）と `act` 出力を diff し、失われるメトリクスをリスト化。
- **テストタグ運用**: `pytest.ini` に `@pytest.mark.legacy_actions` を導入し、残存テストを可視化。BATS も `LEGACY_ACTIONS=1` 等のフラグで制御。

---

## 7. リスクと対策

| リスク | 説明 | 対策 |
| ------ | ---- | ---- |
| 旧機能の未提供 | 診断/トレース/自動復旧など | 必要な機能をモジュール化し、`act` 実行前後にフックを提供 |
| テスト保守コスト増 | 暫定ブリッジ期間中の二重実装 | ブリッジの期間を最小化し、利用状況をダッシュボードで追跡 |
| ドキュメント不整合 | 新旧手順が混在 | フェーズごとに公開ドキュメントを更新し、旧手順には明確な警告を付与 |
| 開発者体験の劣化 | ローカル実行が遅くなる可能性 | `act` のキャッシュ設定、軽量オプションの周知、ハードウェア要件の明記 |

---

## 8. 成功指標

- `services/actions` 配下のコードが参照されなくなる（静的解析でゼロ）。
- CI / ローカル双方で `make actions-ci` のみで主要ワークフローが完遂。
- テストスイートが `act` ベースで安定的に緑を維持。
- ドキュメントの更新が完了し、旧手順の問い合わせがゼロ化。

---

## 9. オープンクエスチョン

1. 旧サービスにのみ存在するハング検知・自動復旧機能をどこまで再実装するか？
2. `act` 実行時のログ収集/可視化要件をどのように満たすか？
3. Windows/WSL 利用者に向けたガイドをどこまで整備するか？
4. ブリッジ期間中のサポート窓口（問い合わせ管理方法）は？

---

## 10. 次のステップ

1. Phase 0 の担当と締切を決定し、調査タスクをチケット化。
2. `services/actions` 依存箇所の一覧を作成し、優先度順に移行スケジュールを組む。
3. フィーチャーパリティ要件に基づいて必要なラッパー／ツール再実装の見積もりを実施。
4. ドキュメント公開タイミングとコミュニケーションプラン（社内説明会等）を調整。

---

## 11. 調査ログ（2025-10-14）

- `rg "services\\.actions"` により 30 ファイルが依存していることを確認（Python/シェル/ドキュメント混在）。
- `Makefile` 内で旧 (`actions-run`) / 新 (`actions-ci`) の並存を確認、`actions-ci` は `act -W` を直呼び。`actions-run` は Python CLI 前提。
- `.actrc` が full イメージ固定 (`ghcr.io/catthehacker/ubuntu:full-24.04`) であることを確認。キャッシュ/ログオプションは未設定。
- `scripts/run-actions.sh` は詳細な診断ロジックを実装しており、移行時も残したい要素（エラーガイダンス、ログ収集）を特定。
- `services/actions` モジュール一覧を棚卸しし、再提供が必要な機能カテゴリを表形式で整理。

---

## 12. 依存ファイル一覧（2025-10-14 時点）

| 区分 | 件数 | 主な対象 | コメント |
| ---- | ---- | -------- | -------- |
| テスト (`tests/`) | 19 | 単体・統合・BATS・Pytest設定 | 旧 API に密接依存。移行時はマーカー導入と段階的書換えが必要。 |
| スクリプト (`scripts/`) | 3 | `run-hangup-regression-tests.sh` ほか | 旧サービスのモジュールを直接 import / 実行。ブリッジ経由での再実装が必要。 |
| ドキュメント (`docs/`) | 5 | コマンドリファレンス、入門ガイド等 | 旧 CLI 手順が掲載。Phase 1 で注意喚起、Phase 3 で全面差し替え。 |
| コードエントリ (`main.py`) | 1 | Click CLI | ブリッジを挿入して `act` 直呼びに切り替える想定。 |
| サービス実装 (`services/actions/`) | 1 | `enhanced_act_wrapper.py` | 旧機能の中心。ブリッジ期間中も参照される。 |
| アーカイブ (`archive/`) | 2 | 過去の提案・レポート | 情報資産として残すが、最新手順との差異を注記する。 |
| この計画書 | 1 | `docs/actions-simulator-migration-plan.md` | 旧実装を記述しているため依存検出対象に含まれる。 |

> 詳細リストは別途スプレッドシート（Phase 0 成果物）で管理する想定。

---

## 13. 機能ギャップ分析（Phase 0 結果）

| 機能カテゴリ | 旧サービス提供内容 | 新 `act` モード現状 | ギャップ / 対応方針 |
| --- | --- | --- | --- |
| 診断 | `DiagnosticService` による Docker/act チェック、権限診断 | `act` 直実行、事前診断なし | Phase 1 で CLI 前処理フックとして復元（`scripts/run-actions.sh` 等に統合） |
| ハング検知 | `HangupDetector`・`ExecutionTracer` がスレッド/IO 監視 | act 単体では未提供 | Phase 2 で `act` 実行ラッパーにオプション追加、または外部モニタリングスクリプト化 |
| 自動復旧 | Docker 再接続や再実行制御 (`AutoRecovery`) | act 失敗で終了 | Phase 2 で再試行ラッパーを提供（再実行ポリシー定義が必要） |
| ログ/アーティファクト | 実行ログ整形、JSON/HTML サマリ出力 (`output.py`) | act 標準出力のみ | Phase 1 で最小限のログ保存をブリッジで実装、Phase 2 で必要な場合に詳細サマリを再導入 |
| ワークフロー解析 | YAML 解析・式評価 (`workflow_parser.py`, `expression.py`) | act にまかせきり | 解析ユースケース（ジョブ一覧化等）を整理し、代替が必要なら別コマンド化 |
| CLI UX | Rich UI と詳細ログ表示 | act 対話は素の CLI | Phase 1 でメッセージ整備、Phase 3 で完全統一 |

---

## 14. ブリッジ設計ドラフト（Phase 0 結果）

1. **エントリポイント**  
   - `SimulationService.run_simulation` で Feature Flag (`ACTIONS_USE_ACT_BRIDGE`) を確認。ON の場合は新しい `ActBridgeRunner` を介して `act` を実行。  
   - `Makefile:91` と `scripts/run-actions.sh` からは従来通り Python CLI を呼び出しつつ、Flag をデフォルト ON に設定。

2. **ブリッジ構成要素**  
   - `ActBridgeRunner`: `act` コマンド生成、`.actrc` 設定読み込み、環境変数/シークレット引き継ぎ。  
   - `BridgeDiagnostics`: 旧 `DiagnosticService` のサブセットを呼び出し、エラー時はガイダンス表示。  
   - `BridgeResultAdapter`: act の終了コードと標準出力を逆変換して `SimulationResult` 互換のレスポンスを構築。ログ収集は最小限に抑え、必要に応じて JSON サマリを出力。

3. **設定項目**  
   - `actions_bridge.enabled`（bool, default true）  
   - `actions_bridge.retry_limit`（int, default 0）  
   - `actions_bridge.capture_logs`（enum: none/basic/full）  
   - 旧設定との互換性を確保するため、未指定の場合は既存フィールドからの継承を試みる。

4. **移行ステップ**  
   - Phase 1: Flag ON をデフォルトにし、主要テストをブリッジ経由で実行。  
   - Phase 2: 旧コードへのフォールバックを削除、ブリッジを単体 `act` 実行へリネーム。  
   - Phase 3: `ActBridgeRunner` を正式な CLI 層に昇格させ、旧 `EnhancedActWrapper` を削除。

---

## 15. Phase 0 完了判定

- [x] 依存関係の洗い出しと分類（セクション 1.1, 12）  
- [x] 機能ギャップ分析と対応方針整理（セクション 13）  
- [x] ブリッジ設計ドラフトの策定（セクション 14）

Phase 0 の成果物を満たしたため、Phase 1 に着手可能。

---

## 16. Phase 1 作業計画（チケット化）

| チケットID (案) | タスク概要 | 担当 | 期限目安 | 依存 |
| --- | --- | --- | --- | --- |
| ACT-101 | `SimulationService` に Feature Flag を追加し、`ActBridgeRunner` のスケルトン実装を作成 | Backend Owner | Week 1 | Phase 0 |
| ACT-102 | `Makefile` / `scripts/run-actions.sh` から Flag を既定で有効化し、旧 CLI からの警告導線を追加 | Dev Experience | Week 1 | ACT-101 |
| ACT-103 | 単体テストをブリッジ経由に更新し、`pytest.mark.legacy_actions` を導入 | QA Lead | Week 2 | ACT-101 |
| ACT-104 | BATS / E2E テストを Flag 切替に対応させ、`make actions-ci` サニティを Nightly に登録 | QA Lead + Ops | Week 2 | ACT-103 |
| ACT-105 | README / COMMAND ガイドを暫定更新し、コミュニケーションプランを整理 | Docs Owner | Week 2 | ACT-102 |
| ACT-106 | ブリッジ経由の実行を CI ジョブに組み込み、失敗時の再試行ルールを定義 | Ops | Week 3 | ACT-104 |

**アクションアイテム**
- 各担当はチケットをプロジェクト管理ツールに登録し、詳細タスクとレビュアを紐付ける。
- Week 1 初日にキックオフを設定し、Flag 有効化手順とテスト切替手順を共有。
- 週次スタンドアップで進捗を確認し、リスク（テスト失敗、Flag オフ要望など）は即座にエスカレーション。

Phase 1 の実行体制とスケジュールを上記のとおり確定。

---

## 17. Phase 1 進捗ログ

- 2025-10-14: ACT-101 完了。`ActBridgeRunner` スケルトン導入と `ACTIONS_USE_ACT_BRIDGE` フラグ実装。
- 2025-10-14: ACT-102 完了。`make actions-run` / `scripts/run-actions.sh` がブリッジフラグを既定で有効化。
- 2025-10-14: ACT-103 着手。`pytest.mark.legacy_actions` を導入し、旧 API 依存ユニットテストをマーク。
- 2025-10-14: ACT-104 準備。BATS/E2E/CI ワークフローで `ACTIONS_USE_ACT_BRIDGE=1` を既定化し、サマリーにブリッジモードを記録。

---

## 18. テスト準備チェックリスト（Phase 1）

- [ ] `ActBridgeRunner` の実行パスを実装し、フォールバックログが出力されないことを確認
- [ ] `legacy_actions` マーカーを段階的に削減し、移行済みテストを通常スイートへ戻す
- [ ] Nightly CI による `make actions-ci` サニティジョブを導入し、ブリッジ経路との差分を可視化
- [ ] ブリッジモードのメトリクス（成功/フォールバック回数）をダッシュボード化
- 2025-10-14: ACT-104 準備として BATS/E2E テストで `ACTIONS_USE_ACT_BRIDGE=1` を既定化し、統合テストがブリッジ経路を通過するよう更新。
