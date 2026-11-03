# Mcp-Dockerの構成・配布の責務

レビュー基盤全体の責務・廃案・共通運用の正本はreviewers-forestへ統合した。`~/Dropbox/src/reviewers-forest/project_review-infra-architecture.md`と`docs/guidebook/review-infra-operations.md`を参照する。進捗は同ワークスペースの`docs/hand-off/cross.md`だけに保持する。

本repoはコンテナ構成、gateway接続設定、CLI登録、skillとinstructionの管理・配布を担当する。レビュー結果の判定・queue業務・実行待機は各サービス/skillに委ねる。

## このrepoに維持する構成契約

- gateway routeは`docker-compose.yml`の`mcp-gateway.environment.ROUTE_*`を入力とし、gatewayが実行時に参照する。
- `config/mcp-external.yml`はCLIへ直接登録する外部MCP URLの入力。gateway routeとは区別する。
- `config/mcp-profiles.yml`はCLI単位の登録profile。reviewer/reviewedの役割単位の露出制御とは区別する。再登録前にdry-runで実登録との差分を確認する。
- Playwrightは任意のprofile。GitHub MCPは残存利用者・skill依存を確認する前に撤去しない。新しいprofile化やroute生成を実装済みと扱わない。
- 秘密値は環境変数・mount・保管庫から注入し、imageや生成するクライアント設定へ焼き込まない。外部直接登録でtokenを必要とする場合は、そのCLIが対応する環境変数経由の方式を使う。

### ユーザー instruction source の責務

各 CLI へ共通 instruction を配布する場合も、本文を `Mcp-Docker` や公開リポジトリへ複製しない。ユーザー管理ファイルを source of truth とし、`mcp-docker instruction configure` が source の絶対パスと配置方式だけをユーザー設定へ保存する。`instruction link` / `instruction repair` は Claude、Copilot、Codex、Antigravity / Gemini のユーザー単位の入口から source への symlink を管理する。

既存の通常ファイルや異なるリンクは確認後にバックアップを作成し、配置先を staging へ移して実体を再確認してから作成専用の symlink へ更新する。同一リンクは変更せず、source と配置先が symlink / ハードリンク経由で同じ実体を指す場合は拒否する。配置先を置換直前と staging 後に再検証し、別の通常ファイル・symlink・ディレクトリへ変化した場合は新しい配置を上書きせず、復元または staging に保全して停止する。配置先がディレクトリの場合は停止し、symlink 作成失敗時に本文のコピーへフォールバックしない。`status` は source 消失を状態として表示し、`link` / `repair` は source 不在時に fail-closed で停止する。レビュー完了イベントの購読は `mcp-resource-subscriber`、reviewer の起動は Squirrel Notifier または別 CLI エージェントの責務であり、instruction 配置機能には含めない。


## 製品固有の運用・仕様

- 構成と登録コマンドは[README](../README.md)、[専用AppのCompose運用](review-raven-app-auth.md)。
- instructionの操作は[instruction-source](instruction-source.md)、完了記録の契約は[reviewgate](reviewed-side-completion-contract.md)。
- skillの正本は`skills/`。配置済みコピーを直接編集せず、対応APIの配備後に公開CLIから配布する。

[移管前の全体像・比較・未実装案](https://github.com/scottlz0310/Mcp-Docker/blob/08561187f82ef33dc73f6027d0a7eceec5397e1a/docs/architecture-review-platform.md)は履歴であり、現行の実装状況や追加作業の許可ではない。移管先一覧はreviewers-forestの`docs/reference/review-infra-document-map.md`を参照する。
