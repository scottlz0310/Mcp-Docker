# レビュー完了待機のタイムアウト後の確認（Phase W 手順 4・R-22）

SKILL.md の「Phase W」で、購読が `NOTIFICATION_TIMEOUT` で終わり、`initialText` の `status` が `reviewed` / `approved` ではなかったときの手順。待機をエージェントから外す設計（D4）が入るまでの暫定で、Squirrel Notifier（v0.16.0 以降）が公開する `review-status.json` を使う。

## 原則

- **打ち切りは、時間ではなく状態で決める。** reviewer が動き出すまでの待ちと、reviewer の実行時間は、待ち行列の深さや PR の大きさで変わる（実測で 4〜20 分以上）。`--timeout-ms` は **1 回の購読の上限**であり、合計の待機の上限ではない。
- **完了の判定は、常に `review://status`（`status` と `headSha`）で行う。** `review-status.json` は、待ち続けるか打ち切るかの判断と、起動状態の報告にだけ使う。`outcome` / `exitCode` は reviewer のプロセスの終了結果で、Verdict ではない。

## 公開状態の読み方

同じ Windows ホストの `%LocalAppData%\SquirrelNotifier\review-status.json`（公開契約。`schemaVersion: 1`。Squirrel Notifier の `docs/review-status-contract.md`）を、読み取り専用で、開いてすぐ閉じて読む。内部ストアの `review-cycles.json` と `statusline-summary.json` は、この判断に使わない。知らないフィールドは無視する。

- **観測不能**: ファイルが無い（Squirrel Notifier が起動していない、または v0.16.0 未満）、読めない、CLI が別ホストにいる、`updatedAt` が現在時刻より 3 分以上古い（アプリは状態が変わらなくても 60 秒ごとに更新するので、止まっている）のいずれか。
- 対象 PR の `key` は、**小文字**の `owner/repo#N`（`review://status` の URI と同じ表記）。`items[]`（`waiting` / `running`）と `recent[]`（`finished`）から探す。`recent[]` は、`receivedAt` が `enqueued_after`（Phase W 手順 2 で控えた時刻）より後のものだけを、今回の分とみなす。前の round の `finished` を拾わない。

| 対象 PR の状態 | 扱い |
|---|---|
| `items[]` の `running` | reviewer が実行中。**待ち続ける** |
| `items[]` の `waiting` で、`holdReason` が `busy`（別のレビューの実行中）/ `ciPending`（required checks の確定待ち。最大 12 分）/ `autoPause`、または `holdReason` が無い（評価の途中） | 起動待ち。**待ち続ける** |
| `items[]` の `waiting` で、`holdReason` が `manual` | 自動起動が off、または手動運用で、**利用者の操作待ち**。打ち切る（`REVIEW_WAIT_TIMEOUT`）。「レビューする」か、別 CLI での reviewer 起動を案内する（SKILL.md の「reviewer 起動状態の確認」） |
| `recent[]` の `finished`（今回の分） | reviewer のプロセスが、Verdict を投稿せずに終了した。打ち切る（`REVIEW_WAIT_TIMEOUT`）。`outcome` / `exitCode` を報告する |
| どこにもない | queue event を受信していない。打ち切る（`REVIEW_WAIT_TIMEOUT`） |
| 観測不能 | 打ち切る（`REVIEW_WAIT_TIMEOUT`）。理由は「観測不能」 |

## 手順

1. **現在値を再取得する。** `--timeout-ms 10000` で、同じ URI を購読し直し、`initialText` を読む。
   - 終了した購読の `initialText` は、**購読の開始時点**の値である。待機中に `reviewed` になっても、`NOTIFICATION_TIMEOUT` で終わった購読の出力には現れない（実例: reviewer が 20 分 16 秒かかり、購読は約 20 秒前に終了した）。
   - `status` が `reviewed` / `approved` なら、Phase W 手順 4 の「HEAD 照合」へ進む。
   - `RESOURCE_NOT_FOUND` などの `errorCode` は、Phase W 手順 4 の表に従う。
2. **公開状態を確認する。** 上の表で、待ち続けるか、打ち切るかを決める。待ち続けるなら手順 3 へ。打ち切るなら、手順 2a を行ってから停止する。
2a. **打ち切る前に、現在値をもう一度取得する。** 手順 1 の再取得から、手順 2 の確認までの間に、reviewer が完了して、`items[]` から `recent[]` へ移った場合がある。公開状態の確認の**後**に、手順 1 と同じ `--timeout-ms 10000` の購読で `review://status` の現在値を読み、`reviewed` / `approved` なら HEAD 照合へ進む。`pending` のままなら、打ち切る。
3. **待ち続ける場合は、購読を起動し直す。** Phase W 手順 3 の購読（`--timeout-ms 1200000`）を、**`enqueue_review` をやり直さずに**起動する。再購読は、最初の購読を含めて最大 6 回まで（合計で最大約 2 時間）。上限に達したら、`REVIEW_WAIT_TIMEOUT` で停止し、公開状態の確認結果を報告する。

## 報告

- 待ち続ける間は、再購読のたびに 1 行で報告する（経過、起動待ち（`holdReason`）/ 実行中）。
- 停止するときは、R-22 の evidence に、再購読の回数、確認時刻、公開状態（`running` / `waiting`（`holdReason`）/ `finished`（`exitCode`）/ どこにもない / 観測不能）、`updatedAt` を含める。起動待ちのまま上限に達したら、`holdReason` を伝え、Recent review events の確認か「レビューする」を案内する（起動中の reviewer を重複起動しない）。

## 限界（暫定の理由）

- 待つ間、エージェントのセッションが占有される（10〜20 分ごとの再購読）。待機をエージェントから外す設計（D4）が入るまでの暫定である。
