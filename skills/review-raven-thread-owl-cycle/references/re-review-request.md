# 再レビュー依頼後の起動モードの判定と queue への登録（Phase U6）

SKILL.md の「Phase U6」の「起動モードの判定」「queue への登録」「`--webhook-mcp-http` の場合は enqueue しない」から移した手順（内容は変更していない）。

### 起動モードの判定

thread-owl は queue への入口が異なる 2 つのモードで動く。**どちらで動いているかによって、この後の手順が変わる。**

| 起動モード | `POST /webhook` | `@thread-owl` コメントによる自動 enqueue | 明示 `enqueue_review` |
|---|---|---|---|
| `--mcp-http` | 提供しない | **されない** | **必須** |
| `--webhook-mcp-http` | 提供する | される | **行わない** |

判定方法:

1. thread-owl を Docker で運用している場合は compose 定義の `command` を見る。`docker compose config` または `docker-compose.yml` の `thread-owl` サービスを確認する。
2. **判定できない場合は手動 enqueue せず、ユーザーに確認して停止する。推測で投げない。** 誤って `--webhook-mcp-http` で手動 enqueue すると通知 listener が二重発火し、reviewer が二重起動し得る。逆に誤って `--mcp-http` で enqueue を省くとサイクルが静かに停止する。どちらも安全側ではないため、**判定を飛ばして先へ進んではならない。**

queue の観測結果から起動モードを推定してはならない。webhook はリトライを伴う非同期配送であり、ある時点で queue に載っていないことは `--mcp-http` である証拠にならない。

**Mcp-Docker の既定構成は `--mcp-http`**（`docker-compose.yml` の `thread-owl` サービスが `command: ["--mcp-http"]`）であり、この場合は次節の enqueue が必須である。

### queue への登録（`--mcp-http` では必須）

コメント投稿に続けて、**同一サイクル内で必ず** `{OWL}:enqueue_review` を実行する。ユーザーの指示を待たない。

- `owner`: `<owner>`
- `repo`: `<repo>`
- `prNumber`: `<pr>`
- `reason`: `"re-review-requested"`

**この手順を省略すると、レビューサイクルはここで静かに停止する。** `--mcp-http` は `POST /webhook` を提供しないため、`@thread-owl` コメントを投稿しても review queue には何も積まれない。queue に event が載って初めて Squirrel Notifier の Recent review events と通知ポップアップに「レビューする」ボタンが現れ、次の reviewer-side cycle を起動できる。

### `--webhook-mcp-http` の場合は enqueue しない

このモードでは `issue_comment.created` を受けて thread-owl 自身が `reason: "re-review-requested"` で enqueue する。コメント投稿だけでサイクルが進むため、**明示 `enqueue_review` を重ねて呼んではならない。**

同一 PR を二重に enqueue しても queue の中身は PR キーで dedup されるが、**enqueue のたびに購読者への通知 listener が発火する**。結果として `notifications/resources/updated` が 2 回飛び、自動レビュー開始が有効な環境では reviewer が二重起動し得る。webhook の delivery-id による重複排除は webhook 受信経路にしか効かず、MCP tool 呼び出しには効かない。

コメント投稿後に queue へ載ったことを確認できない場合でも、**手動 enqueue へ切り替えてはならない。** webhook はリトライを伴う非同期配送であり、ある時点で queue に無いことは「今後も到達しない」ことを意味しない。確認した直後に手動 enqueue し、その後で webhook 側の enqueue が届けば、結局 listener が二重発火する。thread-owl は配送結果を MCP に公開していないため、**未到達を確実に判定する手段は skill 側にない**。

この場合は cycle を完了扱いにせず、**queue に載ったことを確認できない旨をユーザーに報告して停止する**。webhook 経路の疎通（エンドポイントの公開状況、GitHub App 側の配送履歴）の確認と、`--mcp-http` へ切り替えるか webhook を疎通させるかの判断は、ユーザーに委ねる。

`reason` は `opened`（PR 新規作成）/ `synchronized`（既存 PR への push）/ `re-review-requested`（修正対応後の再レビュー）の 3 値である。reviewer 側 skill の起動モード（`initial-review` / `re-review`）とは別物なので混同しない。本スキルが使うのは常に `re-review-requested`。

enqueue は「レビュー対象として queue に載せる」操作であり、**それ自体は reviewer エージェントを起動しない**。したがって「PR を実装したエージェントは自己レビューしてはならない」という規約には抵触しない。自分が更新した PR に対する enqueue は破壊的操作の事前確認の対象外とし、確認なしで実行する。

`enqueue_review` が利用できない場合は、cycle を完了扱いにせず、**queue へ登録できなかったことをユーザーに明示して停止する**。Squirrel Notifier の「レビュー開始」（PR の URL と reason を手入力する導線）がフォールバックである旨も伝える。

**`--mcp-http` では、コメント投稿と enqueue を終えたら Phase W へ進み、レビュー完了を待ってから Phase U2 へ戻る。** ここでの enqueue は Phase W の手順 2 を兼ねるため、Phase W で重ねて呼ばない。`--webhook-mcp-http` では待機せず、コメント投稿をもって reviewed-side cycle を完了する（`review://status` を `pending` にリセットできるのは `enqueue_review` tool だけで、webhook 経由の enqueue ではリセットされないため、待機の完了判定が成り立たない）。
`--webhook-mcp-http` でも Squirrel Notifier の対象 PR の起動記録を読み取り専用で確認できる場合は、Phase W の「reviewer 起動状態の確認」と同じ区別で報告する。webhook 配送は非同期なので、記録が無い時点で未起動・配送失敗と断定せず、明示 enqueue もしない。
次の reviewer-side cycle は、queue event を受けた Squirrel Notifier の「レビューする」ボタン、または別 CLI エージェントへの `/thread-owl-pr-reviewer <owner>/<repo>#<pr> re-review` の明示的な起動指示によって開始される。待機中の reviewed-side はこの起動を行わない。
