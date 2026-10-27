# レビュー完了待機（Phase W・R-22）

`--mcp-http` では、Node >=26.10.0で `resource-bridge-cli` をシェル実行し、JSONを同じセッションへ返す。MCP探索・登録にCLIを混ぜない。完了の判定は `review://status` の購読、進捗の途中報告は `watch-review-status`（v0.8.0 以降）で行い、2 つを混ぜない。

## Phase W: レビュー完了待機（`--mcp-http` のみ）

R-22 の実行契約に従い、reviewer-side のレビュー完了を `review://status` resource の更新通知で待つ。ポーリングの代替であり、同一セッションのコンテキストを保ったままレビュー対応へ進むためのステップである。

### 前提

- thread-owl v0.5.0 以降。`review://status/{owner}/{repo}/{prNumber}` resource は v0.4.3 で、reviewer-side が approve 時に使う `post_review_verdict` は v0.5.0 で追加された。v0.5.0 未満では、approve に至った reviewer-side が `VERDICT_TOOL_UNAVAILABLE` で完了通知を出さずに停止するので、待機は `REVIEW_WAIT_TIMEOUT` になる。
- reviewer-side（`thread-owl-pr-reviewer`）が `initial-review` / `re-review` の最後に完了通知 write を 1 回呼ぶこと（approve なら `post_review_verdict`、それ以外は `post_summary_comment`）。thread-owl の状態が `reviewed` になるのは `post_summary_comment` / `post_review_verdict`（または `approve_pull_request`）のときだけで、inline の投稿では変わらない。
- 状態は thread-owl の in-memory に直近 100 PR 分だけ保持され、thread-owl を再起動すると失われる。
- `reviewed` は「サマリーコメントが投稿された」ことだけを表し、未解決スレッドの有無は表さない。`approved` でも nit 等の未解決スレッドが残ることがある。

### 起動前の前提（購読）

enqueue の前に、Squirrel Notifier の公開状態（`%LocalAppData%/SquirrelNotifier/review-status.json`）の `subscription.state` を読む。読み取りの規則は「進捗の監視の出力の読み方」の節と同じ（読み取り専用で、開いてすぐ閉じる）。コンテナの起動が間に合わず Squirrel が未購読のときは、自動開始が止まり、待っても何も届かない。

| 観測 | 扱い |
|---|---|
| `subscription.state` が `running` | 正常。enqueue へ進む |
| `starting` / `error`（`authRequired` を除く） | 起動中、または Squirrel Notifier の自動回復中の可能性。上限 6 分まで待つ。待つのは 1 回のシェル待機（シェル側で状態を確認し続け、LLM が公開状態を繰り返し読まない）。6 分以内に `running` になれば enqueue へ進む。超えたら利用者へ報告して停止する |
| `authRequired` | 自動回復の対象ではない。待たない。enqueue しない。利用者へ再ログインを依頼して停止する |
| `stopped` / `stopping` | 利用者が停止した状態。待たない。enqueue しない。利用者へ報告して停止する（Squirrel Notifier の起動を依頼する） |
| `updatedAt` が 3 分以上古い | Squirrel Notifier が動いていない可能性。enqueue しない。利用者へ報告して停止する |

- `starting` と `error` の上限は、「打ち切りは、時間ではなく状態で決める」原則の例外である。起動の遅れと自動回復の間隔は状態から終わりが分からないため、時間で区切る。6 分は、Squirrel Notifier の自動回復の最大間隔（5 分）に起動の余裕を足した暫定値で、実機の E2E で実測して見直す。
- `error` が自動回復で `running` に戻れば、待機の中でそれを観測して enqueue へ進む。回復の後に人が enqueue し直す必要はない。戻らなければ上限で停止する。
- enqueue の後に `not_received`（2 分）が出ても、購読が `running` なら、配送の問題として扱う。再 enqueue は重複レビューの危険があるため、しない。
- 停止するときは、R-22 の evidence に、観測した `subscription.state`、`subscription.since`、`updatedAt` を含める。

### 手順

1. 「起動モードの判定」節（R-13）で起動モードを確定する。`--webhook-mcp-http` なら待機せず、待機エントリーでは Phase U2 へ、再レビュー依頼後は cycle 完了とする。判定できなければ停止する。
2. 「起動前の前提（購読）」の節を満たしてから、`{OWL}:enqueue_review` をこの round で **1 回だけ**呼ぶ。`pending` へのリセットと `resources/list` への登録を兼ねるため省略できない。呼ぶ直前に `{GH}:get_pr` で PR head SHA を読み、ローカル HEAD と一致することを確認して `expected_head` として固定し、あわせて呼ぶ直前の時刻（UTC）を、**小数秒つき**で `enqueued_after` として控える（bash: `date -u +%Y-%m-%dT%H:%M:%S.%NZ`、PowerShell: `[DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")`）。秒に切り捨てると、同じ秒に起きた enqueue と受信の前後を判定できない。
   - `reason`: PR 新規作成の直後は `opened`、既存 PR への push の直後は `synchronized`、Phase U6 の再レビュー依頼では `re-review-requested`（「queue への登録」節で実行済み）。
   - 同一セッションで直前に同じ PR・同じ head に対して enqueue 済みで、その後 push していない場合は再度呼ばない。二重に呼ぶと queue の通知 listener が二重発火する。
3. **その直後に** subscriber を起動する。`--uri` の owner / repo は必ず小文字にする（通知 URI は小文字に正規化され、`subscriptions/listen` の URI 照合は完全一致のため）。thread-owl の MCP URL は次の順で解決する（Mcp-Docker の compose は thread-owl をホストへ公開しないので、mcp-gateway の route を経由する）。

   1. 環境変数 `MCP_PROBE_URL` が設定されていれば、subscriber がそれを `--url` として読むので `--url` を省略する。
   2. 未設定で `MCP_GATEWAY_PUBLIC_URL` が設定されていれば、`<MCP_GATEWAY_PUBLIC_URL>/mcp/thread-owl`（末尾の `/` は重ねない）を `--url` に渡す。
   3. どちらも未設定なら URL を推測せず、`REVIEW_WAIT_FAILED`（URL 未解決）として停止し、どちらかの設定をユーザーに依頼する。

   ```powershell
   # MCP_PROBE_URL が設定済みの場合は --url 行を省く
   bunx resource-bridge-cli `
     --url "$($env:MCP_GATEWAY_PUBLIC_URL.TrimEnd('/'))/mcp/thread-owl" `
     --uri review://status/<owner>/<repo>/<prNumber> `
     --timeout-ms 1200000 `
     --json
   ```

   - gateway の認証は subscriber のトークンキャッシュを使う。`errorCode = AUTH_LOGIN_REQUIRED` の場合は、対話ログインが必要なので停止し、ユーザーに `bunx resource-bridge-cli --login --url <同じ URL>` の実行を依頼する。
   - `--timeout-ms` は 20 分。reviewer の起動前の CI 確定待ち（Squirrel Notifier。最大 12 分）と reviewer のレビュー（実測で 4〜7 分）が、enqueue の直後に始まるこの待機の内側に入るため。20 分は多くの CLI の shell tool のタイムアウトを超えるので、バックグラウンド実行で終了を待つ。shell tool 側のタイムアウトで subscriber を打ち切らない。この値は **1 回の購読の上限で、合計の待機の上限ではない**（待ち行列や reviewer の実行時間で 20 分を超える。タイムアウト後は手順 4 の表）。
   - `enqueue_review` より前に起動すると `RESOURCE_NOT_FOUND` になる。
   - 待機中は対象 PR へ push も enqueue もしない。reviewer の作業中に新しい round を始めると、前 round の完了が新 round の完了として記録され得る。


   **進捗の監視（`watch-review-status`、v0.8.0 以降）**: subscriber を待機させたまま、**並べて**起動する。MCP 接続・認証は不要で、同じ Windows ホストの Squirrel Notifier（v0.16.0 以降）の公開状態を読む。完了の判定には使わない。

   ```powershell
   resource-bridge-cli watch-review-status --key <owner>/<repo>#<prNumber> --after <enqueued_after> --timeout-ms 1500000
   ```

   - 状態が変わるたびに 1 行 1 JSON が出る（`updatedAt` だけの更新では出ない）。逐次通知を受け取れるクライアント（Claude Code の `Monitor` など）では、その行を途中報告として使う。受け取れないクライアントでは、バックグラウンドで実行し、subscriber の終了時に、出力の最後の行を読む。
   - `"terminal": true` の行で終了する。終了コード: 完了 0 / reviewer の失敗で終了 1 / 引数エラー 2 / 手動待ち 3 / 上限 4。
   - 各行の扱いは、「進捗の監視の出力の読み方」の表に従う。確認できた事実と推測を分けてユーザーへ短く伝え、subscriber の待機を続ける。`waiting` や queue 登録だけで起動済みとは言わない。未確認を理由に再 enqueue したり、この実装側セッションで reviewer skill を起動したりしない。
4. JSON 出力を判定する。

   | 出力 | 扱い |
   |------|------|
   | `route` が `subscription` / `pre-completion`、かつ `finalText` の `status` が `reviewed` / `approved`、かつ owner / repo / prNumber が対象 PR と一致 | HEAD 照合（下記）へ |
   | `errorCode = NOTIFICATION_TIMEOUT` で、`initialText` の `status` が `reviewed` / `approved` | 待機前に完了していたとみなし、`initialText` で HEAD 照合（下記）へ |
   | `errorCode = NOTIFICATION_TIMEOUT`（上記以外） | `references/review-wait.md`（現在値の再取得、Squirrel Notifier の公開状態の確認、再購読）を必ず読み、その規則に従う。読めない場合は `REVIEW_WAIT_TIMEOUT` で停止する |
   | `errorCode = RESOURCE_NOT_FOUND` | `enqueue_review` 前の起動か、thread-owl の再起動による状態消失。手順 2 からのやり直しを 1 回だけ行い、再発したら `REVIEW_STATUS_NOT_FOUND` で停止する |
   | `errorCode = SUBSCRIPTION_NOT_HONORED` | `--uri` が小文字か確認する。大文字が含まれていた場合だけ小文字にして手順 3 を 1 回だけ再実行し、それ以外は `REVIEW_WAIT_FAILED` で停止する |
   | `errorCode = AUTH_LOGIN_REQUIRED` | `REVIEW_WAIT_FAILED` で停止し、`--login` の実行を依頼する |
   | 上記以外の `failed` / `timeout`、JSON 不正、対象 PR 不一致 | `REVIEW_WAIT_FAILED` で停止する |

   **HEAD 照合（fail-closed）**: 完了とみなした状態の `headSha` を、手順 2 で固定した `expected_head` と文字列全体で比較する。あわせて `{GH}:get_pr` で current PR head を再取得する。`headSha` と current PR head がどちらも `expected_head` と一致する場合だけ手順 5 へ進む。それ以外は古い HEAD や前 round の結果を受理しないよう `REVIEW_HEAD_MISMATCH` で停止し、自動で再 enqueue しない（無人ループを避けるため）。
   - `headSha` が null: reviewer-side がレビュー対象 HEAD を渡していない（`headSha` 対応前の `thread-owl-pr-reviewer` か、完了通知 write の呼び出し漏れ）。reviewer skill の更新を依頼する。
   - `headSha` が `expected_head` と不一致、または current PR head が移動した: 待機中の push か、古い round の完了の混入。current head に対して手順 2 からやり直すか（再 enqueue・再レビュー）をユーザーに確認する。

5. 完了したら、Phase 0 の手順 4〜5（必須コメント投稿者ゲートとサイクル状態の復元）を再実行してから **Phase U2** へ進む。`status` だけで指摘の有無を判断しない。
   - 未解決スレッドや actionable な指摘がある（`reviewed` / `approved` のどちらでも）→ Phase 3 以降の通常手順。
   - 未解決の指摘が 0 件 → `READY_TO_MERGE` として Phase 6.5 → 6.6 → 7 → 7.5 → 8 へ進む。approve 相当かどうかは Phase 7 の Verdict 照合で判定し、Verdict が無ければ `AWAITING_THREAD_OWL_VERDICT` として報告する。どちらの場合もマージは人の判断を待つ。

### 停止時の報告

`REVIEW_WAIT_TIMEOUT` / `REVIEW_STATUS_NOT_FOUND` / `REVIEW_WAIT_FAILED` / `REVIEW_HEAD_MISMATCH` で停止した場合は、ポーリングで待ち続けず、R-22 の evidence と次のフォールバック手順を報告する。

- `watch-review-status` の出力を再確認し、起動待ち（`holdReason`）・実行中・Verdict なしの終了（`outcome` / `exitCode`）・受信していない（`not_received`）・観測不能（`unobservable`）を区別して報告する。`action_required`（`holdReason = manual`。自動起動 off または手動運用）なら、Squirrel Notifier の「レビューする」か別 CLI エージェントでの `/thread-owl-pr-reviewer <owner>/<repo>#<pr> initial-review|re-review` を案内する。既に起動中の reviewer を重複起動しない。
- reviewer が `VERDICT_TOOL_UNAVAILABLE` で停止していた場合は、稼働中の thread-owl が v0.5.0 未満である。PR には Verdict も完了サマリーも投稿されていないので、thread-owl を v0.5.0 以降へ更新してから reviewer を再起動する（`post_summary_comment` での Verdict の代替投稿は依頼しない）。
- レビュー投稿後は、このスキルをコールドスタートで起動し直す。

---

## レビュー完了待機のタイムアウト後の確認（Phase W 手順 4・R-22）

SKILL.md の「Phase W」で、購読が `NOTIFICATION_TIMEOUT` で終わり、`initialText` の `status` が `reviewed` / `approved` ではなかったときの手順。待機をエージェントから外す設計（D4）が入るまでの暫定で、Squirrel Notifier（v0.16.0 以降）の公開状態を `watch-review-status` で読む。

### 原則

- **打ち切りは、時間ではなく状態で決める。** reviewer が動き出すまでの待ちと、reviewer の実行時間は、待ち行列の深さや PR の大きさで変わる（実測で 4〜20 分以上）。`--timeout-ms` は **1 回の購読の上限**であり、合計の待機の上限ではない。
- **完了の判定は、常に `review://status`（`status` と `headSha`）で行う。** `watch-review-status`（公開状態）は、待ち続けるか打ち切るかの判断と、起動状態の報告にだけ使う。`outcome` / `exitCode` は reviewer のプロセスの終了結果で、Verdict ではない（Verdict の投稿は、`finished` より先に届くのが普通）。

### 進捗の監視の出力の読み方

`watch-review-status`（v0.8.0 以降）の出力で判断する。この監視は、Squirrel Notifier の公開状態（`%LocalAppData%/SquirrelNotifier/review-status.json`、`schemaVersion: 1`）から、対象 PR（小文字の `owner/repo#N`）の、`--after`（`enqueued_after`）より**後に受信した**項目だけを読む。前の round の `finished` を拾わない。

| 出力（`type`） | 扱い |
|---|---|
| `state`（`running`） | reviewer が実行中。**待ち続ける** |
| `state`（`waiting`。`holdReason` が `busy`（別のレビューの実行中）/ `ciPending`（required checks の確定待ち。最大 12 分）/ `autoPause`、または無い） | 起動待ち。**待ち続ける** |
| `action_required`（終了コード 3。`holdReason = manual`） | 自動起動が off、または手動運用で、**利用者の操作待ち**。打ち切る（`REVIEW_WAIT_TIMEOUT`）。「レビューする」か、別 CLI での reviewer 起動を案内する |
| `state`（`finished`。終了コード 0 / 1） | reviewer のプロセスが終了した。**打ち切る前に、手順 2a（`review://status` の再取得）を行う**。`reviewed` / `approved` なら HEAD 照合へ。`pending` のままなら、Verdict を投稿せずに終了したので、打ち切る（`REVIEW_WAIT_TIMEOUT`）。`outcome` / `exitCode` を報告する。終了コード 1（失敗で終了）の原因は、Squirrel Notifier のログ `%LocalAppData%/SquirrelNotifier/logs/winui3.log` で確認する |
| `not_received` | queue event を受信していない（enqueue から 2 分）。購読の状態を確認する（「起動前の前提（購読）」の節）。購読が `running` なら、再 enqueue せず、利用者へ報告して停止する（`REVIEW_WAIT_TIMEOUT`）。購読が `running` でなければ、その状態の扱いに従う |
| `unobservable`（`reason`: `no_file` / `unreadable` / `unsupported_schema` / `stale`） | 観測不能（Squirrel Notifier が起動していない、v0.16.0 未満、別ホスト、`schemaVersion` が 1 でない、更新が 3 分以上止まっている）。利用者の操作が要るため、即エスカレートする（再試行しない。Squirrel Notifier の起動、コンテナの起動、v0.16.0 以降への更新を依頼して停止する。`REVIEW_WAIT_TIMEOUT`）。理由は「観測不能」。`recovered` が続いたときは、待ち続けてよい |
| `heartbeat` | 生存確認（状態は変わっていない）。1 行で報告する |
| `timeout`（終了コード 4） | 監視の上限。完了の判定は `review://status` で行う（再購読の判断は下の手順） |
| `error`（終了コード 2） | 引数エラー（`--key` / `--after`）。直して起動し直す |

`resource-bridge-cli` が v0.8.0 未満で `watch-review-status` が使えないときは、同じ公開状態を、次の規則で直接読んでもよい。

- 読み取り: `%LocalAppData%\SquirrelNotifier\review-status.json`（公開契約。`schemaVersion: 1`。Squirrel Notifier の `docs/review-status-contract.md`）を、読み取り専用で、**開いてすぐ閉じて**読む（Squirrel Notifier の置換を妨げない）。知らないフィールドは無視する。内部ストアの `review-cycles.json` と `statusline-summary.json` は、この判断に使わない。
- 対象 PR: `key` は**小文字**の `owner/repo#N`（`review://status` の URI と同じ表記）。`items[]`（`waiting` / `running`）と `recent[]`（`finished`）から探し、`receivedAt` が `enqueued_after`（Phase W 手順 2 で控えた時刻）より**後**のものだけを、今回の分とみなす。時刻は小数秒まで比較する。前の round の `finished` を拾わない。
- 観測不能: ファイルが無い、読めない、`schemaVersion` が 1 ではない、`updatedAt` が現在時刻より 3 分以上古い（アプリは 60 秒ごとに更新するので、止まっている）。
- 扱い: 上の表と同じ（`items[]` の `running` / `waiting` は `state`、`holdReason = manual` は `action_required`、`recent[]` の `finished` は `finished`、どこにもない場合は `not_received`）。

### 手順

1. **現在値を再取得する。** `--timeout-ms 10000` で、同じ URI を購読し直し、`initialText` を読む。
   - 終了した購読の `initialText` は、**購読の開始時点**の値である。待機中に `reviewed` になっても、`NOTIFICATION_TIMEOUT` で終わった購読の出力には現れない（実例: reviewer が 20 分 16 秒かかり、購読は約 20 秒前に終了した）。
   - `status` が `reviewed` / `approved` なら、Phase W 手順 4 の「HEAD 照合」へ進む。
   - `RESOURCE_NOT_FOUND` などの `errorCode` は、Phase W 手順 4 の表に従う。
2. **公開状態を確認する。** 上の表で、待ち続けるか、打ち切るかを決める（監視が終了しているときは、同じ引数に `--timeout-ms 10000` を付けて起動し直し、最初の行を読む）。待ち続けるなら手順 3 へ。打ち切るなら、手順 2a を行ってから停止する。
2a. **打ち切る前に、現在値をもう一度取得する。** 手順 1 の再取得から、手順 2 の確認までの間に、reviewer が完了して、`finished` へ移った場合がある。公開状態の確認の**後**に、手順 1 と同じ `--timeout-ms 10000` の購読で `review://status` の現在値を読み、`reviewed` / `approved` なら HEAD 照合へ進む。`pending` のままなら、打ち切る。
3. **待ち続ける場合は、購読を起動し直す。** Phase W 手順 3 の購読（`--timeout-ms 1200000`）を、**`enqueue_review` をやり直さずに**起動する。再購読は、最初の購読を含めて最大 6 回まで（合計で最大約 2 時間）。上限に達したら、`REVIEW_WAIT_TIMEOUT` で停止し、公開状態の確認結果を報告する。

### 報告

- 待ち続ける間は、再購読のたびに 1 行で報告する（経過、起動待ち（`holdReason`）/ 実行中）。
- 停止するときは、R-22 の evidence に、再購読の回数、確認時刻、公開状態（`running` / `waiting`（`holdReason`）/ `finished`（`exitCode`）/ どこにもない / 観測不能）、`updatedAt` を含める。起動待ちのまま上限に達したら、`holdReason` を伝え、Recent review events の確認か「レビューする」を案内する（起動中の reviewer を重複起動しない）。

### 限界（暫定の理由）

- 待つ間、エージェントのセッションが占有される（10〜20 分ごとの再購読）。待機をエージェントから外す設計（D4）が入るまでの暫定である。
