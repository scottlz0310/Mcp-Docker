# GitHub Actions Simulator - 実装計画書

## プロジェクト概要

既存のMcp-Dockerプロジェクトに、GitHub ActionsワークフローをDockerベースでローカル実行・検証する「CI事前チェック機能」を追加実装します。

## 現状レビュー (2025-09-25)

- ✅ `services/actions/workflow_parser.py` による基本的なYAML解析・検証が動作している。
- ✅ `services/actions/simulator.py` で単一ジョブの逐次実行・`run`/一部`uses`ステップのシミュレーション、`--dry-run`/環境変数読み込みが可能。
- ✅ CLI は `python -m services.actions.main` 経由で `simulate`/`validate`/`list-jobs` を提供し、`main.py actions ...` から起動できる。
- ⚠️ `act_wrapper.py` は存在するものの CLI からは未接続で、`--engine act` オプションは未実装状態。
- ⚠️ 並列実行・`needs` 依存関係・`strategy.matrix`・シークレット/環境管理・HTMLレポート生成などフェーズ2以降の機能は未着手。
- ⚠️ ドキュメント内で予定されていた `click`/`rich` ベースのUI、`config_manager.py`、`report_generator.py` などのモジュールは未実装。
- ❗ `docs/actions` 配下の設計/要約ドキュメントには未実装機能が完了済みとして記載されており、整合性を取る必要がある。

## 実装戦略

### 段階的開発アプローチ

#### フェーズ1: MVP（Minimum Viable Product） - 2週間

**目標**: 基本的なワークフロー実行機能の実装

##### 主要機能（実装状況・拡張）

- [x] **YAML解析エンジン** — `WorkflowParser` が `.github/workflows/*.yml` を読み込み、必須フィールド検証と簡易バリデーションを提供。
- [x] **シンプルジョブ実行** — `WorkflowSimulator` が単一ジョブを逐次実行し、`run`/一部`uses`をホストシェル上で再現（Dockerランナーは未実装）。
- [x] **基本CLI** — `services/actions/main.py` に `simulate` / `validate` / `list-jobs` コマンドを実装。`argparse` ベースで動作（Click移行は未着手）。

#### フェーズ2: 拡張機能 - 3週間

**目標**: 実用的な CI/CD シナリオへの対応。

- [ ] `needs` 依存関係・並列実行のサポート（T1）。
- [ ] `strategy.matrix` 展開と動的ジョブ生成（T2）。
- [ ] `if:` 条件評価の強化と CLI UX 改善（T3）。
- [ ] Secrets / 環境変数管理の強化（T4）。
- [ ] `act` 連携による Docker ランナー実行、`uses` アクション再現（T5）。
- [ ] 構造化ログと HTML/JSON レポート生成（T6/T7）。

#### フェーズ3: 統合・最適化 - 2週間

**目標**: プロダクション品質とサービス統合を完了する。

- [ ] 常駐サービス化・REST API 化、`docker-compose` 改善（T8）。
- [ ] Docker イメージとランナー性能の最適化、実行時間 KPI 達成（T9）。
- [ ] IDE 連携 / Git hooks など開発者体験強化（T10）。
- [ ] 実ワークフロー統合テスト・CI パイプライン構築（T11）。
- [ ] セキュリティ監査・運用ガイド整備（T12）。
- [ ] 関連ドキュメントのアップデート（T13）。

## 優先タスクリスト（T 番号は上記参照）

| ID | 内容 | 目的 / 補足 |
| --- | --- | --- |
| T1 | `WorkflowSimulator` でジョブ依存関係・並列実行・失敗伝播を実装 | `needs` DAG と並列ワーカーを追加し、フェーズ2の柱を実現 |
| T2 | `strategy.matrix` と動的ジョブ展開 | 大規模ワークフロー対応。`WorkflowParser`/`WorkflowSimulator` 拡張 |
| T3 | `if:` 条件評価と CLI 移行（Click + Rich） | 表現式評価ライブラリ導入と UX 向上 |
| T4 | Secrets / 設定管理レイヤー（`config_manager`） | `.env` 以上の安全なシークレット管理と設定統一 |
| T5 | `act` エンジン統合 (`--engine act`) | Docker ランナー対応と `uses` ステップ実行を現実的に再現 |
| T6 | 構造化ログ / メトリクス出力 | `rich` ログ、JSON ログ、実行統計を収集 |
| T7 | レポート生成・成果物永続化 | HTML/JSON レポート、`output/` 保存、履歴閲覧 |
| T8 | 常駐サービス化・REST/CLI 統合 | `actions` サービスを長時間起動し他サービスと連携 |
| T9 | パフォーマンス最適化・Docker イメージ調整 | 5 分/70% 要件達成、Dockerfile 最適化 |
| T10 | 開発者体験（VS Code、Git hooks） | 即時検証や IDE 連携で adoption を促進 |
| T11 | 統合テスト（pytest/Bats）、CI パイプライン | 実ワークフローを自動検証し回 regression を防止 |
| T12 | セキュリティ監査（権限、ネットワーク、シークレット） | ローカル実行リスクを低減し安全性を確保 |
| T13 | `docs/actions` 配下ドキュメントの整合性更新 | 設計書・要約の記述を実装状態と同期 |

## 技術スタック（現状とフォローアップ）

| 項目 | 現状 | 課題・次ステップ |
| --- | --- | --- |
| 言語 | Python 3.13（プロジェクト標準） | 維持 |
| CLI | `argparse` ベース | Click + Rich へ移行しコマンド体系を統一（T3） |
| 実行エンジン | ホストシェル (`subprocess.run`) | `act` / Docker ランナーに接続（T5） |
| 解析 | `PyYAML` + 独自検証 | Matrix/needs/if サポート拡張（T1/T2/T3） |
| ロギング | 標準 `logging` + ANSI | `rich` での整形表示 + JSON ログ出力（T6） |
| 設定 | `config.json` を手動読み込み（未使用） | `config_manager` で統一管理・ Secrets マスキング（T4） |
| 依存関係 | `pyyaml`, `click`, `rich`, `docker` | 未使用ライブラリの活用/整理、`jinja2` 等必要に応じ追加 |
| テスト | `pytest` による単体テスト | 統合テスト/Bats 導入、CI 自動化（T11） |

## ファイル構造（2025-09-25 時点）

```text
services/actions/
├── __init__.py
├── act_wrapper.py
├── config.json
├── logger.py
├── main.py
├── simulator.py
└── workflow_parser.py
```

予定されている追加モジュール:

- `config_manager.py`（T4）
- `report_generator.py`（T7）
- `models/` ディレクトリ（ワークフロー/実行モデル、T2/T7）
- `tests/fixtures/` 配下の統合テスト資産（T11）

## 開発工程とマイルストーン

| 期間 | 目標 | 主なアウトプット |
| --- | --- | --- |
| Week 1-2 | フェーズ1 完了 | CLI / Parser / Simulator MVP、単体テスト |
| Week 3 | 依存関係・並列実行対応 | T1 着手、設計レビュー |
| Week 4 | Matrix / Secrets / act 連携 | T2, T4, T5 開発と検証 |
| Week 5 | レポート・ログ強化 | T6, T7 実装、ユーザーフィードバック反映 |
| Week 6 | 常駐サービス・最適化 | T8, T9 実装、Docker 最適化 |
| Week 7 | テスト拡充・ドキュメント更新 | T10-T13、リリース候補の検証 |

## テスト戦略

- **単体テスト**: `pytest` で Parser/Simulator/Logger をカバー（既存テストを発展、T11）。
- **統合テスト**: 実際の `.github/workflows/*.yml` を使った end-to-end 実行、Bats シナリオで CLI を検証（T11）。
- **パフォーマンステスト**: 中規模ワークフローを用いた 5 分以内達成の検証（T9）。
- **セキュリティテスト**: 禁止コマンドやシークレット漏洩を防ぐテストケース（T12）。

## セキュリティと運用の考慮

- 非 root 実行・ネットワーク隔離・リソース制限を Docker 側で徹底（T12）。
- シークレットは暗号化ファイル/環境変数で管理し、ログではマスキング（T4/T12）。
- 実行ログは JSON 形式で収集し、異常検知に活用（T6）。

## 既存システムとの統合

`main.py` での呼び出し例（現状）:

```python
elif service == "actions":
    args = sys.argv[2:]
    cmd = ["python", "-m", "services.actions.main", *args]
    subprocess.run(cmd, check=True)
```

`docker-compose.yml` のサービス定義（今後の改善余地あり）:

```yaml
  actions-simulator:
    build: .
    volumes:
      - ./.github:/app/.github:ro
      - ./output:/app/output:rw
      - /var/run/docker.sock:/var/run/docker.sock
    command: python main.py actions simulate .github/workflows/ci.yml
```

- 上記コマンドは単発実行のため、常駐モードや API 化を T8 で検討。

## 成功指標・KPI

- [ ] 既存ワークフロー 5 本すべてがローカルシミュレーターで成功（T1-T5）。
- [ ] GitHub Actions の実行結果と 95% 以上一致（T5/T7/T11）。
- [ ] 実行時間を本家の 70% 以内に短縮（T5/T9）。
- [ ] CLI ワンコマンド起動と分かりやすいレポート（T3/T7）。

## リスクと対策

| リスク | 内容 | 対策 |
| --- | --- | --- |
| Docker API 互換性 | ホストの Docker 依存 | LTS 版で検証し fallback 手段を用意 |
| GitHub Actions 仕様変更 | 新機能追従の遅延 | コア機能に集中しプラガブルな設計にする |
| パフォーマンス不足 | 大規模ワークフローでの遅延 | 早期にベンチマークし並列化・キャッシュを最適化 |
| シークレット漏洩 | ログや一時ファイルからの漏洩 | マスキング・自動削除・アクセス制御を強化 |

## ドキュメント整合タスク

- [ ] `docs/actions/github-actions-simulator-design.md` を現状の機能範囲へ合わせる（T13）。
- [ ] `docs/actions/github-actions-simulator-summary.md` の完了状況を更新（T13）。
- [ ] `docs/actions/ui-design.md` で CLI/UI の最新仕様を反映（T13）。

## まとめ

MVP は CLI / Parser / Simulator の最小機能が揃い、ローカルでワークフローを試行できる段階に到達しました。今後は `needs`・`act`・レポート生成といったフェーズ2の中核機能を集中的に実装し、常駐サービス化とテスト自動化まで仕上げることで、GitHub Actions を安全かつ高速にローカル検証できるプロダクション水準の体験を提供します。
