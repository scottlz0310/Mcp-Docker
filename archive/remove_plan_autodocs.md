# 自動ドキュメント生成ワークフロー撤去計画

## 目的

- 使われていない Sphinx ベースのドキュメント生成基盤と、その自動ビルド用ワークフローを整理し、メンテナンスコストと CI 実行時間を削減する。
- `archive/workflows/` へ退避した `docs.yml` を除き、残存するドキュメント関連アーティファクトを体系的に移設または削除する方針を明確化する。
- README など利用者向け資料からの参照を整理し、現状提供している機能との整合性を確保する。

> **進捗メモ (2025-09-27)**: Sphinx プロジェクトは `archive/docs/sphinx/` に、関連スクリプトは `archive/scripts/` に退避済み。

## 現状整理

- Sphinx プロジェクト一式が `docs/` 配下に存在し、`.rst` ファイルや `conf.py` を通じて HTML 生成が可能。（→ 退避完了）
- `scripts/generate-docs.sh` など複数のユーティリティがドキュメント生成・公開のために残存。（→ `archive/scripts/` へ移設済み）
- Makefile の `docs` / `docs-serve` / `docs-clean` ターゲット、および README・CONTRIBUTING・CHANGELOG 等でドキュメントサイトへの言及がある。
- GitHub Actions で運用していた `docs.yml` ワークフローは `archive/workflows/docs.yml` へ退避済みだが、その他の参照は未整理。
- Sphinx 用依存関係が `pyproject.toml` の `[dependency-groups.docs]` で管理され、`uv.lock` にもパッケージが残る。

## 影響範囲サマリー

| カテゴリ | 対象ファイル/設定 | 期待される対応 |
| --- | --- | --- |
| ソース | `docs/**/*.rst`, `docs/conf.py`, `docs/index.rst` など | アーカイブ用ディレクトリへの移設 or 削除（完了） |
| スクリプト | `scripts/generate-docs.sh`, `scripts/update-readme.sh` のドキュメント関連処理 | アーカイブ移設、機能削除、README 更新（移設済み） |
| ビルド設定 | Makefile ターゲット、`pyproject.toml` docs 依存グループ、`uv.lock` | 該当ターゲット削除、依存関係整理（完了） |
| CI / ワークフロー | `.github/workflows/` の残存参照、`archive/workflows/docs.yml` | 退避済みのことを明記し、必要ならアーカイブ構成整備 |
| ドキュメント | README、CONTRIBUTING、`docs/actions/*.md` など | 自動生成手順や公開手順の記述を削除 or 修正（継続対応） |

## 想定メリット

- CI 実行時間の削減とワークフローの単純化。
- 使われないパッケージの削除による依存グラフの縮小。
- プロジェクト内の情報整理と、現行機能との乖離解消。

## リスクと対策

| リスク | 内容 | 緩和策 |
| --- | --- | --- |
| 過去ドキュメント参照が失われる | 旧ドキュメントが必要なケースへの配慮 | `archive/docs/` に HTML or rst をまとめて保管し、README に「旧仕様はアーカイブ参照」と追記 |
| 将来の再導入コスト | Sphinx 設定を削除すると復活が面倒 | `docs/remove_plan_autodocs.md` に復元手順リンクを保持し、アーカイブに `conf.py` など主要ファイルを残す |
| 未整理参照の取りこぼし | README やスクリプトに Doc 参照が残る可能性 | 作業完了後に `git grep -i docs` で確認する運用を取り入れる |

## 撤去作業ステップ案

1. **情報収集の確定**
   - `docs/` 配下と関連スクリプトの参照関係を確認 (`git grep`, `ripgrep`).
   - アーカイブ先の構成方針を決定 (`archive/docs/` など)。
2. **アーカイブ用ディレクトリの準備**
   - `archive/docs/` 等を作成し、現行 Sphinx プロジェクトを丸ごと移動。
   - 必要に応じて README をアーカイブ内に同梱。
3. **ビルド/スクリプト整備**
   - Makefile から `docs` 系ターゲットを削除。
   - `scripts/generate-docs.sh` などをアーカイブ化 or 機能削除。
   - `pyproject.toml` の `[dependency-groups.docs]` をアーカイブ計画に合わせて削除し、`uv lock` を再生成。
4. **CI ワークフロー更新**
   - `.github/workflows/` 内でドキュメント関連ジョブが残っていないか確認。
   - `archive/workflows/docs.yml` にアーカイブした旨と再有効化手順を注記。
5. **ドキュメント・README 更新**
   - README / CONTRIBUTING などからドキュメントサイトの案内やコマンド例を削除。
   - 代わりに「ドキュメントは現在静的アーカイブのみ」と記載。
6. **整合性チェック**
   - `git grep -i "docs"` などで残存参照を洗い出し。
   - `make help` や `python -m pip list` (uv) で不要エントリが消えているか確認。
7. **レビューフェーズ**
   - 主要関係者に変更内容を共有し、合意を得てからマージ。

## 検証と引き継ぎポイント

- 退避した Sphinx プロジェクトに README (復元手順) を添付。
- 依存関係が減ったことを `uv pip list` や `uv tree` で確認。
- CI からドキュメント関連ジョブが実行されていないことを GitHub Actions 画面で確認。

## タイムライン（目安）

| フェーズ | 作業内容 | 担当 | 目安 |
| --- | --- | --- | --- |
| 1 | 抽出対象の確認と計画共有 | Actions/Docs 担当 | 0.5 日 |
| 2 | ファイル退避・設定削除 | Actions/Docs 担当 | 1.0 日 |
| 3 | 依存関係整理 (`uv lock` 更新) | Actions/Infra | 0.5 日 |
| 4 | ドキュメント整合性チェック & レビュー | Actions/Docs | 0.5 日 |

## フォローアップ

- アーカイブ化したドキュメントをどこで閲覧できるか（例: リポジトリの `archive/docs/`）を README に明記。
- 将来ドキュメント生成を再開する場合、この計画書を基点に復元手順を検討する。
- `docs/remove_plan_codeql.md` と合わせて、未使用コンポーネント整理の進捗をリリースノートに反映する。
