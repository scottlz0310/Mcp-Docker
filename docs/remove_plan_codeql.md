# CodeQL サービス撤去計画

## 目的

- 未完成かつ利用頻度が低い CodeQL サービスをプロジェクトから削除し、ビルド時間・メンテナンスコストを削減する。
- Phase A の主目的である GitHub Actions Simulator (act ベース) に集中できる体制へ移行する。
- セキュリティ・品質チェックの代替手段を明示し、利用者の混乱を防ぐ。

## 現状整理

- `docker-compose.yml` に `codeql` サービスが定義され、`make codeql` でローカル実行可能。実処理は雛形レベル。
- `main.py` や `scripts/generate-docs.sh` では「未実装」とメッセージを出しており、本格運用に至っていない。
- README / docs / `scripts/setup.sh` など複数箇所で利用例を案内しており、削除時にはドキュメント全体に波及。
- GitHub Actions (`.github/workflows/security.yml`) では CodeQL 解析ジョブが稼働しているため、クラウド上のスキャンは継続中。

## 削除のメリット

- **ビルド時間短縮**: CodeQL イメージの pull や初期化が不要になり、Docker 関連処理が軽量化。
- **メンテナンス負荷軽減**: CodeQL CLI バージョン追随、設定ファイル更新、説明資料の整合性維持が不要に。
- **プロジェクトの焦点明確化**: Actions Simulator への投資に集中でき、未完成サービスを抱える必要がなくなる。

## 想定される影響と対策

| 影響 | 詳細 | 対策 |
| --- | --- | --- |
| セキュリティチェック減少 | ローカルでの CodeQL 静的解析が無くなる | `make security` の Trivy など既存スキャンを維持・強化。必要に応じて Bandit / Semgrep 等の軽量ツール導入を検討 |
| ドキュメントの不整合 | README / docs / スクリプトに CodeQL への言及が残ると混乱 | 一斉削除し、GitHub Actions 上での CodeQL 継続有無を明記 |
| 将来の再導入コスト | 完全削除後に復活させる際、ゼロから再構築が必要 | docs に「将来再導入する場合の参考情報」リンクを残しておく |

## 削除作業ステップ案

1. **docker-compose / Makefile**: `codeql` サービスと関連ターゲットを削除。
2. **コード / スクリプト**: `main.py`, `scripts/setup.sh`, `scripts/generate-docs.sh`, `scripts/update-readme.sh` などから CodeQL 分岐を除去し、`services/codeql/` ディレクトリを削除。
3. **ドキュメント更新**:
   - README, `docs/API.md`, `docs/usage.rst`, `docs/index.rst` など機能一覧から CodeQL を削除。
   - 「GitHub Actions 側で CodeQL を実行する場合は `.github/workflows/security.yml` を参照」と注記。
4. **CI ワークフロー整理**:
   - GitHub Actions の CodeQL ジョブの継続/停止を決定。
   - 継続する場合は README に「CI では GitHub Actions 側で実行」と明記。停止する場合はワークフロー修正を併せて行う。
5. **代替チェックの強化**:
   - `make security` に Trivy / pip-audit / Bandit など、既存 or 追加の軽量ツールを記載し、実行手順を README に反映。
6. **最終確認**:
   - `git grep codeql` で残存参照を確認。
   - `docker compose config` / `make help` で不要ターゲットが消えているか確認。
   - 必要に応じて `docs/actions/github-actions-simulator-design.md` など関連ドキュメントの整合性チェック。

## タイムラインの目安

| フェーズ | 作業内容 | 担当 | 目安 |
| --- | --- | --- | --- |
| 1 | 削除対象の洗い出し / 計画共有 | Actions team | 0.5 日 |
| 2 | 設定・コード・ドキュメントの削除対応 | Actions team | 1.0 日 |
| 3 | CI ワークフロー調整 (必要時) | DevOps | 0.5 日 |
| 4 | レビュー・最終確認・マージ | Actions + DevOps | 0.5 日 |

## フォローアップ

- セキュリティスキャン体制を `make security` と GitHub Actions のトリヴィ系ジョブで維持するか確認。
- 将来的に CodeQL を再導入する場合は、GitHub の公式ワークフローテンプレートや `.github/workflows/security.yml` の過去バージョンを参照する旨を docs に追記予定。
