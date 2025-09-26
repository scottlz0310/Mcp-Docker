# GitHub Actions Simulator - ユーザー体験設計

## コンセプト

- **シンプル**: CLI / Make / スクリプトの 3 経路に体験を集約する。
- **即時**: ワンコマンドでワークフローを再現し、結果を Rich 表示と JSON で受け取る。
- **一貫性**: ローカル・pre-commit・CI がすべて同じコマンドを利用。

## エントリポイント

| 経路 | 想定ユーザー | 役割 |
| --- | --- | --- |
| CLI (`python -m services.actions.main`) | 高度なオプションを使いたい開発者 | 直接実行・自動化スクリプト |
| `make actions` | 通常の開発者 | インタラクティブにワークフローを選択 |
| `scripts/run-actions.sh` | 配布用 / CI | ワンショットで標準手順を実行 |

## CLI デザイン

### 基本構造

```bash
python -m services.actions.main <command> [options] <workflow>...
```

- `simulate`: act を用いてワークフローを再現。
- `validate`: Workflow Parser による YAML 検証。
- `list-jobs`: ジョブ一覧を表示。

### 主要オプション

| オプション | 説明 |
| --- | --- |
| `--engine {act,builtin}` | 実行エンジン。デフォルトは `act`。 |
| `--job JOB_ID` | 特定ジョブのみ実行。 |
| `--dry-run` | 実行せずにプランを表示。 |
| `--json` | JSON サマリーを標準出力 + `output/` に保存。 |
| `--env-file PATH` / `--env KEY=VAL` | 追加環境変数。 |
| `--verbose` / `--quiet` | 出力量を調整。 |

### 出力

- Rich テーブルで実行プランと結果を表示。
- `--json` 時は `SimulationResult` を JSON で出力。
- 失敗時はエラー原因と再現コマンドを案内。

## `make actions`

### 対話モード (デフォルト)

1. `.github/workflows/*.yml` を一覧表示。
2. 数字入力でワークフローを選択 (Enter で先頭)。
3. オプションに応じて act / builtin を切り替え、結果を Rich 表示。

### 変数と挙動

| 変数 | 役割 | 例 |
| --- | --- | --- |
| `WORKFLOW` | 実行対象ファイル | `WORKFLOW=.github/workflows/ci.yml` |
| `JOB` | 特定ジョブ | `JOB=test` |
| `ENGINE` | `act` or `builtin` | `ENGINE=act` |
| `DRY_RUN` | `1` でプランのみ | `DRY_RUN=1` |
| `JSON` | `1` で JSON 出力 | `JSON=1` |
| `CLI_ARGS` | その他オプション | `CLI_ARGS="--env NODE_ENV=test"` |

### 非対話モード

```bash
WORKFLOW=.github/workflows/ci.yml ENGINE=act JSON=1 make actions
```

- CI や自動化で利用。
- exit code をそのまま引き継ぎ、pre-commit / CI の判定に使用。

## ワンショットスクリプト (`scripts/run-actions.sh`)

### 処理フロー

1. Docker / Git / uv の存在とバージョンを確認。
2. `docker compose pull` で `actions-simulator` サービスを更新。
3. `docker compose run --rm actions-simulator make actions WORKFLOW=$1 ENGINE=${ENGINE:-act}` を実行。
4. 成功時は JSON サマリーのパスを表示、失敗時はログを案内。

### 代表コマンド

```bash
./scripts/run-actions.sh .github/workflows/ci.yml
ENGINE=builtin ./scripts/run-actions.sh .github/workflows/ci.yml
```

- 環境変数 `ACT_ARGS`, `CLI_ARGS`, `JSON=1` などを受け取り、内部で `make actions` に渡す。

## 出力 UX

| 状態 | 表示 | JSON |
| --- | --- | --- |
| 成功 | ✅ 緑色のサマリー、実行時間、成功ジョブ | `{"success": true, ...}` |
| 失敗 | ❌ 赤色のジョブ名と失敗ステップ | `{"success": false, "failed_job": ...}` |
| ドライラン | 📝 プランのみ | `{"success": true, "dry_run": true}` |

- JSON ファイルは `output/simulation-YYYYMMDD-HHMM.json` に保存。
- act の生ログを `output/act.log` に追記。

## pre-commit & CI からの利用

| フェーズ | コマンド | 備考 |
| --- | --- | --- |
| pre-commit | `uv run pytest`, `uv run bats`, `hadolint`, `shellcheck`, `yamllint` | 差分対象のみ実行 |
| optional | `ENGINE=act make actions WORKFLOW=.github/workflows/ci.yml` | 大きな変更時に手動で実行 |
| CI | `make lint`, `make test`, `make actions WORKFLOW=... JSON=1` | 同じコマンドで再利用 |

## エラーハンドリング UX

- 明示的なメッセージ: 「act バイナリが見つからない」「Docker デーモン未起動」などをガイド。
- exit code: act 由来の exit code を透過し、pre-commit / CI が判定できるようにする。
- 再現コマンド: 失敗時は `make actions` で再実行できるコマンド例を提示。

## ドキュメント / ヘルプ

- `python -m services.actions.main --help`
- `python -m services.actions.main simulate --help`
- `make actions help` (番号一覧、環境変数説明)
- `scripts/run-actions.sh --help`

すべての経路で同じオプションが使えるようにし、ユーザーが最小ステップでワークフローを検証できる体験を提供する。
