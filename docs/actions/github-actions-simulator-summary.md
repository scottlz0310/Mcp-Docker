# GitHub Actions Simulator - 実装案総括

## 📋 ドキュメント構成

- **[技術設計書](./github-actions-simulator-design.md)**: 軽量 act ベースのアーキテクチャ設計
- **[実装計画書](./implementation-plan.md)**: ロードマップとタスク分解
- **[UI設計書](./ui-design.md)**: CLI / Make / スクリプトの操作体験

## 🎯 プロジェクト概要

### 目的

Docker 上で nektos/act を利用し、GitHub Actions を実行せずに lint / test / 軽量セキュリティチェックを事前実行できる「ワンショット CI シミュレーター」を提供する。

### キーメッセージ

- **軽量**: act + 必要最小限のツールだけを含むコンテナを提供。
- **即時**: `make actions` または配布スクリプト 1 本でワークフローを再現。
- **再現性**: すべて Docker 経由で実行し、ホスト依存を排除。
- **自動化**: pre-commit / CI から同一コマンドを呼び出し、品質ゲートを統一。

## 🏗️ アーキテクチャ概要

```text
Developer → Click CLI → Workflow Parser → Act Wrapper → Result Output
```

- `simulate/validate/list-jobs` の CLI が唯一のエントリポイント。
- エンジンは act に統一し、Builtin Simulator はレガシースタブとして廃止。
- 出力は Rich テーブルと JSON サマリーに集約。

## 🛠️ 技術スタック

| 分類 | 採用技術 | 役割 |
| --- | --- | --- |
| CLI | Click, Rich | コマンド構造と表示 |
| Parser | PyYAML | ワークフロー解析 |
| Runner | nektos/act | GitHub Actions の再現 |
| Quality | MegaLinter (Ruff/ShellCheck/Hadolint/Yamllint), pytest, bats | 品質ゲート |
| 配布 | Docker, docker compose, shell scripts | ワンショット実行 |

## 📅 ロードマップ (概要)

1. **フェーズA: 軽量アーキテクチャ確立**
   - ミニマル act イメージ
   - CLI ↔ act 設定の整理
   - builtin 実行器の依存削除と uv インストールフローへの移行
   - `make actions` / スクリプトの統一
2. **フェーズB: 品質ゲートと自動化**
   - pre-commit 導入
   - lint / test / 軽量セキュリティの統合
   - JSON サマリー・ログ集約
3. **フェーズC: 体験強化と配布**
   - ワンショットスクリプト整備
   - README / ドキュメント刷新
   - サンプルテンプレート配布

## 💻 使用イメージ

```bash
# 対話モード (make)
make actions

# ワンショットスクリプト
./scripts/run-actions.sh .github/workflows/ci.yml

# CLI 直接
uv run python main.py actions simulate .github/workflows/ci.yml --json
```

## 🔒 品質とセキュリティ

- pre-commit フックで lint/test を自動実行。
- Trivy/Grype をオプションとして `make security` で呼び出し。
- act キャッシュとログは `output/` および `/opt/act/cache` に整理。

## 📊 成功指標

| 指標 | 目標 |
| --- | --- |
| 1 コマンド起動 | `make actions` で 60 秒以内に結果取得 |
| 再現性 | Docker 上で同一の結果が得られる |
| pre-commit | lint/test を 2 分以内で完了 |
| ドキュメント | 新方針が `/docs/actions` に反映済み |

## ⚠️ リスクと前提

- act イメージの更新頻度 → バージョン固定とキャッシュ管理で吸収。
- ホストに Docker と Git が必要 → スクリプト内でチェックし、エラーを案内。
- 軽量セキュリティスキャンはあくまで補助 → 本番 CI の厳格チェックとは分離。

## 🚀 次のステップ

1. フェーズA の実装 (act イメージ最適化 + entrypoint 整理)
2. pre-commit 設定と品質ゲート整備
3. ドキュメントと配布資材の刷新

軽量アーキテクチャを軸に、「動かすまでの時間」「メンテナンス性」「開発者体験」を改善していく。
