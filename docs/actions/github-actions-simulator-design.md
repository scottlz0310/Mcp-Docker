# GitHub Actions Simulator - 技術設計書

## 概要

本ドキュメントは、軽量な GitHub Actions シミュレーターを Docker 上で再現するための技術設計を示す。目標は「act を使った最小限の CI 事前チェック体験」であり、常駐サービスや Web UI を伴う重厚な構成は採用しない。システムは Click/Rich ベースの CLI、act 実行ラッパー、Workflow Parser / Simulator の 3 層を中心に構成する。

## 目的と制約

### 目的

- GitHub Actions を実行せずに lint / test / 軽量セキュリティ検査のフィードバックを得る。
- Docker で隔離されたクリーン環境を維持し、ホスト差異を排除する。
- ワンコマンドでの起動と pre-commit 連携を容易にする。

### 非目標

- 常駐 API サーバー、Web UI、HTML レポート、ジョブ監視ダッシュボード。
- GitHub 全機能の完全再現（セルフホステッドランナーや GitHub サービス固有機能など）。

## 全体アーキテクチャ

```text
┌─────────────────────────────┐
│          CLI (Click/Rich)        │
│  simulate / validate / list-jobs │
└──────────────┬──────────────────┘
               │
     ┌─────────▼──────────┐
     │ Workflow Parser &   │
     │ Builtin Simulator   │
     └─────────┬──────────┘
               │
      ┌────────▼─────────┐
      │   Act Wrapper     │  ──▶  nektos/act (Docker in Docker)
      └────────┬─────────┘
               │
      ┌────────▼─────────┐
      │  Output Manager   │  ──▶  console / json / output/
      └───────────────────┘
```

- **CLI**: ユーザーの唯一のインターフェース。Click でコマンド構造を定義し、Rich でテーブルやサマリーを描画する。
- **Workflow Parser & Builtin Simulator**: YAML 構文と依存関係の検証、`simulate --engine builtin` のテスト用途を担う。
- **Act Wrapper**: `--engine act` で呼ばれる実行器。Docker コンテナ内から act CLI を起動し、ワークフローを実行する。
- **Output Manager**: 実行ログ / JSON サマリー / exit code を整理し、CLI から提示する。

## コンポーネント詳細

### CLI (`services/actions/main.py`)

- Click グループ `cli` に `simulate`, `validate`, `list-jobs` を実装。
- グローバルオプション: `--engine`, `--dry-run`, `--job`, `--verbose`, `--quiet`, `--json` など。
- リッチフォーマット: 実行プラン、ジョブ一覧、結果サマリーをテーブル表示。
- `make actions` / `scripts/run-actions.sh` から呼び出し可能な共通エントリーとする。

### Workflow Parser (`services/actions/workflow_parser.py`)

- `.github/workflows/*.yml` を読み込み、GitHub Actions のジョブ構造を抽象化。
- `needs`, `strategy.matrix`, `if` 条件を解決し、 `SimulationPlan` として CLI に供給。

### Builtin Simulator (`services/actions/simulator.py`)

- ドライラン / ユニットテスト向けの最小シミュレータ。
- `run` ステップをホスト shell で実行する既存ロジックは keep するが、`act` がデフォルトになった後も fallback として維持。

### Act Wrapper (`services/actions/act_wrapper.py`)

- act CLI をサブプロセス起動し、`--workflows`, `--job`, `--eventpath` などを CLI 引数化。
- Docker ソケットと `.github` ディレクトリをマウント。
- Act のバージョン固定とキャッシュボリュームの制御 (後述) を担当。

### Output Manager

- CLI で表示するサマリー構造体 (`SimulationResult`) を生成。
- `--json` 指定時は `output/simulation-*.json` へ保存。
- pre-commit / CI では JSON を機械読み取りして判定に利用可能。

## Docker / act 設計

### ベースイメージ

- `python:3.13-slim` をベースに uv / act / hadolint / shellcheck をインストール。
- multi-stage build で act バイナリ、pre-commit フック用ツールをまとめる。
- `ACT_CACHE_DIR` を `/opt/act/cache` とし、ホスト側にボリュームマウント。

### 実行フロー

```text
make actions
  └─ docker compose run actions-simulator \
       python main.py actions simulate <workflow> --engine act
          └─ ActWrapper.run()
               └─ act --workflows <file> --job <job> --eventpath <temp.json>
```

- CLI は act 実行前に `temp_event.json` を生成し、`--eventpath` に渡す。
- `.env` から読み込んだ環境変数は act の `--env` 引数として注入。
- 実行ログは標準出力で Rich 表示しつつ、`output/act.log` にも保存。

## 設定とテンプレート

### TOML 設定 (予定)

```toml
# services/actions/config/act-runner.toml (草案)
[runner]
image = "ghcr.io/catthehacker/ubuntu:act-latest"
platforms = ["ubuntu-latest", "ubuntu-22.04"]
container_workdir = "/github/workspace"

[exec]
cleanup = true
reuse = false
cache_dir = "/opt/act/cache"

[env]
GITHUB_USER = "local-runner"
```

### ワンショットスクリプト (`scripts/run-actions.sh`)

1. Docker / act / uv のバージョンを確認。
2. `docker compose pull` で最新イメージを取得。
3. `docker compose run --rm actions-simulator make actions WORKFLOW=$1` を実行。
4. 結果コードを引き継いで終了。

## pre-commit / CI 連携

- `.pre-commit-config.yaml` に以下のフックを定義:
  - `uv run pytest` (差分対象のみ)
  - `uv run bats tests/test_actions_simulator.bats`
  - `hadolint Dockerfile`
  - `shellcheck scripts/*.sh`
  - `yamllint .github/workflows`
- CI では同じスクリプトを `make lint` / `make test` / `make security` で呼び出す。
- act 実行は手動トリガーまたは nightly ジョブで実施し、CI 時間を最小化。

## 出力仕様

| 種別 | 保存先 | 説明 |
| --- | --- | --- |
| 標準出力 | CLI (Rich) | テーブル/サマリー。 |
| JSON サマリー | `output/simulation-YYYYMMDD-HHMM.json` | `success`, `jobs`, `engine`, `duration`。 |
| act ログ | `output/act.log` | act の標準出力・標準エラーを転記。 |
| キャッシュ | `/opt/act/cache` | Act のイメージ/依存ダウンロード結果。 |

## セキュリティ・リソース管理

- Docker コンテナは非 root ユーザーで実行。必要な場合のみ `docker.sock` をマウント。
- Trivy スキャンは `make security` で on-demand 実行。
- `cleanup` オプションで実行後にコンテナを削除し、ディスク使用を抑制。

## テスト計画

1. **Unit**: Parser / ExpressionEvaluator / ActWrapper (引数生成) を pytest で検証。
2. **CLI**: Bats で `simulate`, `validate`, `list-jobs`, `make actions` 経路を検証。
3. **Integration**: Docker 内で `scripts/run-actions.sh sample.yml` を実行し exit code を確認。
4. **Regression**: `uv run pytest` + `uv run bats` を pre-commit と CI で共通化。

## 将来拡張 (任意)

- act のカスタムイメージ選択 (`--platform` 対応)。
- 成果物 (artifacts) の簡易ダウンロード。
- Slack/Teams 通知など外部連携はオプションとして個別スクリプトで対応。

## まとめ

アーキテクチャを CLI + act の 2 層に絞ることで、保守コストを最小化しつつ Docker 上での再現性を確保する。Click/Rich の表現力でユーザー体験を担保し、pre-commit / CI から同じコマンドを呼び出すことで「軽量で一貫した開発フロー」を実現する。
