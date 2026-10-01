# レビュー完了待機のタイムアウト後の確認（Phase W 手順 4・R-22）

SKILL.md の「Phase W」で、購読が `NOTIFICATION_TIMEOUT` で終わり、`initialText` の `status` が `reviewed` / `approved` ではなかったときの手順。待機をエージェントから外す設計（D4）が入るまでの暫定で、Squirrel Notifier の公開状態を使う。

## 原則

- **打ち切りは、時間ではなく状態で決める。** reviewer が動き出すまでの待ち（別のレビューの実行、CI の確定待ち、Auto-Pause）と、reviewer の実行時間は、待ち行列の深さや PR の大きさで変わる（実測で 4〜20 分以上）。`--timeout-ms` は **1 回の購読の上限**であり、合計の待機の上限ではない。
- **完了の判定は、常に `review://status`（`status` と `headSha`）で行う。** Squirrel Notifier の状態は、待ち続けるか打ち切るかの判断にだけ使い、完了の判定には使わない。

## 手順

1. **現在値を再取得する。** `--timeout-ms 10000` で、同じ URI を購読し直し、`initialText` を読む。
   - 終了した購読の `initialText` は、**購読の開始時点**の値である。待機中に `reviewed` になっても、`NOTIFICATION_TIMEOUT` で終わった購読の出力には現れない（実例: reviewer が 20 分 16 秒かかり、購読はその約 20 秒前にタイムアウトした）。
   - `status` が `reviewed` / `approved` なら、Phase W 手順 4 の「HEAD 照合」へ進む。
   - `RESOURCE_NOT_FOUND` などの `errorCode` は、Phase W 手順 4 の表に従う。
2. **Squirrel Notifier の公開状態を確認する。** 同じ Windows ホストの `%LocalAppData%\SquirrelNotifier\statusline-summary.json`（公開契約。`schemaVersion: 1`）を読み取り専用で読み、`queue.items[]` と `activeReviews[]` に、対象 PR（`repository` は大文字小文字を区別せず、`prNumber`）があるかを見る。内部ストアの `review-cycles.json` は、この判断に使わない。

   | 結果 | 扱い |
   |---|---|
   | `activeReviews[]` にある | reviewer が実行中。**待ち続ける** |
   | `queue.items[]` にある | 起動待ち。**待ち続ける**（保留の理由は、この契約では分からない。自動起動が off の場合も含まれ得る） |
   | どちらにもない | **打ち切る**（`REVIEW_WAIT_TIMEOUT`）。理由は「公開状態に対象 PR が無い（reviewer が Verdict を投稿せずに終了した、または queue event を受信していない）」 |
   | ファイルが無い・読めない・CLI が別ホストにいる | 観測できない。**打ち切る**（`REVIEW_WAIT_TIMEOUT`）。理由は「観測不能」 |

   - このファイルは、状態が変わったときだけ更新される。`updatedAt` は最後の状態変化の時刻なので、古いことだけで異常とは判断しない。アプリが異常終了すると、ファイルが残る場合があるため、手順 3 の再購読の上限を置く。
3. **待ち続ける場合は、購読を起動し直す。** Phase W 手順 3 の購読（`--timeout-ms 1200000`）を、**`enqueue_review` をやり直さずに**起動する。再購読は、最初の購読を含めて最大 6 回まで（合計で最大約 2 時間）。上限に達したら、`REVIEW_WAIT_TIMEOUT` で停止し、公開状態の確認結果を報告する。
4. 待機中は、対象 PR へ push も `enqueue_review` もしない（Phase W 手順 3 と同じ）。

## 報告

- 待ち続ける間は、再購読のたびに 1 行で報告する（経過、PR の状態: 起動待ち / 実行中）。
- 停止するときは、R-22 の evidence に、再購読の回数、確認時刻、公開状態（`activeReviews` / `queue` / どちらにもない / 観測不能）を含める。
- 起動待ちのまま上限に達した場合は、自動起動が off、または Auto-Pause・別のレビューの実行などで保留されている可能性を伝え、Squirrel Notifier の Recent review events で確認するか、「レビューする」で起動するよう案内する（Phase W「停止時の報告」と同じ。既に起動中の reviewer を重複起動しない）。

## 限界（暫定の理由）

- 待つ間、エージェントのセッションが占有される（10〜20 分ごとの再購読）。
- 起動待ちの理由（自動起動 off、Auto-Pause、CI の確定待ち）が、公開契約では区別できないため、起動待ちのまま上限まで待つことがある。Squirrel Notifier が理由と時刻を公開する契約（`review-status.json`）を出せば、区別して打ち切れる。
