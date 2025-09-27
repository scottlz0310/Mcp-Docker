# GitHub Actions Simulator - 実装計画書

## プロジェクト概要

Mcp-Docker プロジェクトに「軽量 GitHub Actions 事前チェック体験」を追加する。Docker で隔離された環境から nektos/act を呼び出し、ワンコマンドで lint / test / 軽量セキュリティ検査を実行できるシンプルなツールチェーンを提供することが目的である。

新しい方針では、常駐サーバーや重厚な管理コンポーネントは扱わない。以下の価値を最優先する:

- **軽量性**: act を必要なときだけ起動し、コンテナは最小構成で維持する。
- **即時性**: `make actions` もしくは配布用スクリプト 1 本でワークフローを再現する。
- **開発者体験**: Click/Rich ベースの CLI に統一し、pre-commit から lint / test / セキュリティを呼び出せる。
- **再現性**: Docker からのみ実行し、ホスト環境による差異を排除する。

## 現状レビュー (2025-09-26)

- ✅ `WorkflowParser` による YAML 構文・構造検証が安定動作。
- ✅ `WorkflowParser` が `needs` 依存解決と `strategy.matrix` 展開をカバーし、CLI から再利用可能。
- ✅ `ExpressionEvaluator` による `if:` 条件分岐評価とユニットテストが完了。
- ✅ CLI を Click/Rich 化し、マルチワークフロー / JSON サマリーなどの UX を強化 (T3 完了)。
- ✅ `make actions` から CLI をラップし、簡易対話モードと非対話モードを提供。
- ⚠️ act を含んだ Docker イメージは肥大化しており、キャッシュと依存整理が未着手。
- ⚠️ pre-commit 連携による lint / test / MegaLinter (Ruff/ShellCheck/Hadolint/Yamllint) / Trivy の自動実行は未整備。
- ⚠️ ワンショット配布用スクリプト（例: `scripts/run-actions.sh`）は雛形のみ。
- ❗ ドキュメントは旧ロードマップ (REST API や常駐サーバー) を前提に記述されており、現状と不一致。

## 新ロードマップ

### フェーズA: 軽量アーキテクチャの確立 (1 週間)

- ✅ A1. act + 必須バイナリのみを含むミニマル Docker イメージを作成。（`Dockerfile.actions` 追加, 2025-09-26）
- ✅ A2. CLI から act を呼び出すまでの経路と設定ファイルを整理（`services/actions/config/act-runner.toml` バンドル）。
- ✅ A3. `make actions` / `scripts/run-actions.sh` / `docker-compose` を一貫したエントリポイントに揃える。
- ✅ A4. Docker イメージから builtin 実行器用の依存物を削除し、act ベースに一本化。
- ✅ A5. Python 依存のインストールフローを uv (`uv run`) へ統一し、ドキュメントと Dockerfile を同時更新。

### フェーズB: 品質ゲートと自動化 (1 週間)

- ✅ **B1.** pre-commit 経由で `uv run pytest` / `uv run bats` / MegaLinter (Ruff/ShellCheck/Hadolint/Yamllint) を統合。（`scripts/run_bats.py` と `.pre-commit-config.yaml` 更新済み）
- ✅ **B2.** 軽量 Trivy スキャンを `uv run security-scan` に集約し、`Makefile` の `security` ターゲットからオプション実行可能にした（デフォルト 3 分以内、結果は `output/security/trivy` に保存）。
- ✅ **B3.** 実行ログと JSON サマリーを `output/actions` に保存し、CLI `actions summary` コマンドで最新結果を閲覧可能にした。

### フェーズC: 配布・体験強化 (1 週間)

- C1. ワンショット実行用スクリプトを配布形式に整備（ドキュメント・使い方含む）。
- C2. README / actions ディレクトリのドキュメントを刷新し、新方針・手順を反映。
- C3. 簡易テンプレート（例: `.github/workflows/local-ci.yml.sample`）を追加し、利用者がすぐに走らせられるようにする。

## 優先タスクリスト

| ID | 内容 | 状態 | 補足 |
| --- | --- | --- | --- |
| T1 | `needs` 依存関係と並列実行 | ✅ | ワークフロー解析ロジックで DAG を解決 |
| T2 | `strategy.matrix` 展開 | ✅ | 行列展開と派生ジョブ生成を実装 |
| T3 | ExpressionEvaluator / CLI UX 改善 | ✅ | Click/Rich CLI と JSON サマリーを実装 |
| T4 | act ランナー最適化 | ✅ | `Dockerfile.actions` + act キャッシュボリューム + uv ベースインストール |
| T5 | 1 コマンド起動 (`make actions`/ スクリプト) の統一 | ✅ | `scripts/run-actions.sh` と Makefile/compose の統合済み |
| T6 | pre-commit & quality gate 導入 | ✅ | lint / test / セキュリティ・ログ集約を light-weight に統合 |
| T7 | ドキュメント刷新 (設計・UI・README) | 🔜 | 旧ロードマップの記述を軽量方針へ更新 |
| T8 | テンプレート・配布パッケージ整備 | 🔜 | `.env.example`, `.pre-commit-config.yaml`, スクリプト群 |

## 技術スタック整理

| 項目 | 現状 | 今後の扱い |
| --- | --- | --- |
| 言語 | Python 3.13 | 維持 (uv 経由でロック管理) |
| CLI | Click + Rich | 成果物サマリーのみ (HTML/REST は対象外) |
| 実行エンジン | act | act を標準化（builtin 実装は廃止しスタブ化） |
| コンテナ | Docker + multi-stage build | act と uv ランタイムのみを含む軽量イメージ |
| Lint/Test | MegaLinter (Ruff/ShellCheck/Hadolint/Yamllint), pytest, bats | pre-commit・CI 双方で統合 |
| セキュリティ | Trivy (軽量スキャン) | オプション扱い、CI とローカルで同一コマンド |

## ファイル構造 (再整理後の想定)

```text
services/actions/
├── __init__.py
├── expression.py
├── main.py            # Click CLI
├── simulator.py       # builtin シミュレーションのレガシースタブ
├── workflow_parser.py
├── act_wrapper.py
└── config/
    └── act-runner.toml (予定)

scripts/
├── run-actions.sh      # ワンショット起動スクリプト
└── setup.sh
```

## 開発工程 (新タイムライン)

| 週 | 目標 | 主なアウトプット |
| --- | --- | --- |
| Week 1 | フェーズA | 軽量 Dockerfile、act 設定、CLI エントリ調整 |
| Week 2 | フェーズB | pre-commit、Quality Gate、レポート整備 |
| Week 3 | フェーズC | ドキュメント刷新、ワンショット配布、テンプレート |

## テスト戦略

- **単体テスト**: `pytest` で Parser / Simulator / ExpressionEvaluator を継続カバー。
- **CLI/Bats テスト**: Click CLI の主要経路 (`simulate`, `validate`, `list-jobs`) のドライランを網羅。
- **統合テスト**: Docker コンテナ内で `scripts/run-actions.sh` を実行する簡易 E2E (CI で nightly)。
- **品質ゲート**: pre-commit & CI で MegaLinter (Ruff/ShellCheck/Hadolint/Yamllint) と `uv run pytest`, `uv run bats`。
- **セキュリティ (任意)**: Trivy を `make security` で呼び出し、主要イメージをスキャン。

## リスクと対応

| リスク | 緩和策 |
| --- | --- |
| act イメージが肥大化し CI が遅延 | multi-stage build、キャッシュボリューム、頻度の低いスキャンはオプション化 |
| ホスト差異 (Docker, Git, PATH) による再現性欠如 | `scripts/run-actions.sh` が環境チェックを実施し不足バージョンを警告 |
| lint / test の実行時間増大 | pre-commit では差分ファイルのみ、CI では並列ジョブ・キャッシュを活用 |
| ドキュメントの陳腐化 | T7 の継続的なドキュメント更新プロセスを採用 |

## ドキュメント整合タスク

- `github-actions-simulator-design.md` を軽量アーキテクチャに合わせて更新。
- `github-actions-simulator-summary.md` を新ロードマップへ刷新。
- `ui-design.md` を CLI + 配布スクリプト中心の内容に再構成。
- README と `docs/actions/README.md` に「軽量 act ベース」である旨を追記。

## まとめ

GitHub Actions Simulator は「軽量・即時・再現性」を重視したツールに転換する。Click CLI と Docker 化された act によって、開発者はワンショットで lint / test / セキュリティの結果を取得可能になる。REST API や常駐サーバーはロードマップから外し、代わりに pre-commit 連携と配布のしやすさに投資する。これにより、最小限のメンテナンスコストで CI 前の確信を得られる開発体験を提供する。
