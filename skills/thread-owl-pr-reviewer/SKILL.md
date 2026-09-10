---
name: thread-owl-pr-reviewer
description: thread-owl MCP を使う reviewer-side GitHub Pull Request review。PR URL または Thread Owl queue を起点に、初回レビュー、再レビュー、thread follow-up、summary-only を実行し、既存レビューと重複しない高価値な日本語コメントを投稿する。failure path、回帰、security、CI、packaging、テスト不足を独立検出するときに使う。コード変更、resolve、merge は行わない。
---

# Thread Owl PR Reviewer

Thread Owl を reviewer-side の GitHub App として使い、PR を独立レビューして必要な指摘だけを投稿する。

## 責務境界

- コード変更、commit、push、branch 操作、merge を行わない。
- review thread を resolve / unresolve しない。修正側 workflow の責務とする。
- `@thread-owl re-review requested` の投稿と、それに伴う `enqueue_review(reason: "re-review-requested")` による review queue への登録は、いずれも修正側 workflow の責務とする。reviewer 側からは行わない。
- レビュー完了時に、実装 CLI へ渡す次アクションを**テキストとして提示する**（「ハンドオフ提示」節）。提示にとどめ、修正側 skill を自分で起動しない。
- レビュー判断、コメント生成、merge readiness 判定を行う。Thread Owl 自体に LLM があると仮定しない。
- レビュー本文、GitHub 投稿、ユーザー報告を日本語で書く。
- token、cookie、Authorization header、秘密鍵、環境変数値を出力しない。

## レビュー原則

- 推測を事実として断定しない。仕様意図や実行条件が不足する場合は `question` にする。
- style nit、既存コードだけに由来する問題、PR の目的外の大規模改善を投稿しない。
- 既存レビューへの同意、言い換え、根拠の弱い追従を投稿しない。
- 再レビューで、初回に出さなかった軽微な指摘を後出ししない。
- 指摘がない場合はコメントを作らない。ただし `initial-review` / `re-review` で `verdict: approve`（後述の「Verdict」節を参照）と判定した場合は例外とし、「Verdict コメント投稿」節に従ってレビュー観点サマリーを含む Verdict コメントを投稿する。
- 書き込み失敗が曖昧な場合は、同じ投稿を即時再実行せず thread を再取得して重複を確認する。

## Thread Owl 契約

Thread Owl の logical alias `{OWL}` を、実行中 client の discovery 結果から解決して読み取り・投稿の第一候補にする。skill 本文に client 固有の server 名・tool 名・namespace を書かず、未ロードなら client-native の tool / resource discovery を行う。

| 操作 | 契約 |
| --- | --- |
| `{OWL}:get_pr` | `owner`、`repo`、`prNumber` から `pr` と `files` を返す。`pr.head.sha`、`pr.base.sha`、各 file の `patch` を記録する |
| `{OWL}:list_review_threads` | resolved / outdated 状態とコメントを含む review thread 一覧を返す |
| `{OWL}:post_inline_comment` | `commitId`、`path`、`line`、`body` を指定して current diff に投稿する |
| `{OWL}:reply_review_thread` | `threadId` へ返信する。thread の所属 repository は server 側でも allowlist 照合される |
| `{OWL}:post_summary_comment` | PR conversation に issue comment として summary を投稿する。blocking 0件・全 review thread resolved 時の Verdict コメント投稿にも使う（「Verdict コメント投稿」節参照） |
| `{OWL}:approve_pull_request` | `expectedHeadSha` と現在の head が一致する場合だけ APPROVE review を送る |

`{OWL}:get_pr` は CI status、check logs、通常の issue comment 全文を返さない。必要な read-only の補完だけ GitHub connector または `gh` で行う。Thread Owl で提供されない書き込みを別経路へ迂回しない。

Thread Owl は `REQUEST_CHANGES`、resolve、unresolve、merge を提供しない。`request changes` は verdict と blocking comment で表現し、未実装操作を代替経路で送らない。

### CI read capability

`get_check_runs` は client 固有の tool 名ではなく、PR 番号を入力として check run ごとの `status`、`conclusion`、対象 SHA（`head_sha` / `sha` または同等のフィールド）を返す論理 read capability として扱う。利用可能な client-native capability は schema で discovery し、候補が一つの場合だけこの run に binding する。候補が無い、複数候補を一意に選べない、または対象 SHA を返さない場合は `CI: unknown` とし、combined status や write 経路で代替しない。失敗ログ用の workflow run / job / log capability は任意の補助 capability であり、client ごとに有無が異なる。

### O-00: `{OWL}` の discovery と固定

`{OWL}` の候補は、tool / resource の表示名や client 固有の namespace の文字列一致ではなく、Thread Owl の logical capability と input / output schema で判定する。候補の識別単位は server instance / route と opaque handle の組み合わせであり、同名の tool が別 route に存在しても一つにまとめない。

1. PR URL 起点では `owner`、`repo`、`prNumber` を確定してから候補を列挙する。queue 起点では、まず review queue resource を discovery し、resource read で candidate の `owner`、`repo`、`prNumber`、`reason` を取得する。
2. host / client の設定に `{OWL}` の明示 binding があれば優先する。それがなければ、必要な read / write capability と schema を満たす候補が一つだけの場合に限り採用する。複数候補が残った場合は discovery 順や表示名だけで選ばず、`BLOCKED_MCP_DISCOVERY` として停止する。
3. 採用候補で、PR URL 起点なら `{OWL}:get_pr`、queue 起点なら queue resource read と `{OWL}:get_pr` のうち対象を確認できる最小 read を **1 回成功** させる。成功とは tool / resource error がなく、PR identity・head SHA などの minimum output schema を満たすことをいう。server 一覧、`Connected` 表示、schema 取得だけでは成功とみなさない。
4. `{OWL}` から選択済み server / route / handle への binding を run の状態に固定し、以後の全 read / write で同じ binding を使う。後続の接続失敗、schema 不一致、allowlist 拒否を別 candidate や GitHub connector / `gh` の write に切り替える理由にしてはならない。

候補を解決できない、未接続、schema 不一致、read 検証失敗、または複数候補を一意に選べない場合は、次の状態で停止する。

```text
termination_status = BLOCKED_MCP_DISCOVERY
status = blocked
```

対象 PR（確定済みの場合）、logical alias `{OWL}`、必要 capability、候補数、失敗分類（unresolved / not connected / schema mismatch / read failed / ambiguous）、read 検証結果、`writes performed: 0`、再実行に必要な設定変更を報告する。token・Authorization header・秘密情報は報告しない。別の MCP candidate、GitHub connector、`gh` write 経路へ進まず、レビューコメント・Verdict・APPROVEを投稿しない。

この binding は initial review、re-review、thread follow-up、summary-only の全モードで共通に使用する。再 discovery による途中の候補切り替えは禁止する。

## O-00〜O-21: reviewer-side 実行契約

各行の `primary tool` は O-00 で解決して固定した logical alias と、実行時に記録した input / output schema snapshot の組み合わせを指す。`reviewedHeadSha` は remote snapshot、CI、投稿位置、inline の `commitId`、APPROVE の `expectedHeadSha` で同一値を使う。queue の read と待機は別責務として扱い、allowlist 拒否を別の read 経路で迂回しない。

### O-00: queue 起点の待機

- `precondition`: PR URL が未指定で queue 起点のレビューを依頼され、対象 resource と待機 timeout を確定できる。
- `primary tool`: queue resource の native read と、購読・待機用 `mcp-resource-subscriber`（R-00 の schema snapshot）。
- `input / output`: resource URI、購読 URL、timeout を入力し、candidate の owner、repo、prNumber、reason、expected_head、route、finalText を出力する。
- `side effect`: read と待機だけを行う。GitHub、PR、review thread、queue への write は行わない。
- `guard`: re-review は `queue://review/re-review-requests` を使い、route が `subscription` または `pre-completion` であることを確認する。`timeout` / `failed` は完了扱いにしない。
- `fallback`: queue 内容の read は client-native resource read、購読・待機は native subscription が無い場合に subscriber CLI を使う。read 成功を待機完了と取り違えない。
- `failure / stop`: timeout、切断、failed route、必須フィールド欠落、JSON 不正は `QUEUE_WAIT_FAILED` として停止し、mode、PR read、投稿へ進まない。
- `evidence`: resource URI、candidate、reason、expected_head、route、timeout、終了理由を記録する（`observed`、秘密情報は除外）。

### O-01: モード選択

- `precondition`: PR URL または O-00 の queue candidate と依頼文を取得できる。
- `primary tool`: 依頼文と candidate の構造化フィールドを読む処理。外部 tool は使用しない。
- `input / output`: PR URL、queue reason、依頼モードを入力し、`initial-review` / `re-review` / `thread-follow-up` / `summary-only` を一つ出力する。
- `side effect`: なし。GitHub、queue、作業ツリーを変更しない。
- `guard`: `opened` / 通常の `synchronized` は initial、`re-review-requested` は re-review に固定する。指定 thread がある場合だけ thread-follow-up、明示された場合だけ summary-only とする。
- `fallback`: なし。reason や依頼文が曖昧な場合に、表示順・過去の文脈・推測で mode を補完しない。
- `failure / stop`: reason、対象 PR、mode の組み合わせを一意に決められない場合は `REVIEW_MODE_UNKNOWN` として停止し、本文取得や投稿を行わない。
- `evidence`: mode、入力 URL / candidate、reason、選択理由を記録する（入力事実は `observed`、判断は `inferred`）。

### O-02: Remote Snapshot の PR metadata

- `precondition`: O-00 の `{OWL}` binding と O-01 の mode、対象 owner / repo / PR が固定されている。
- `primary tool`: `{OWL}:get_pr`（R-00 の schema snapshot）。
- `input / output`: owner、repo、prNumber を入力し、PR identity、state、base SHA、head SHA、files、patch を出力する。head SHA を `reviewedHeadSha` として固定する。
- `side effect`: read-only。PR、レビュー、queue、作業ツリーを変更しない。
- `guard`: PR identity と minimum output schema、`pr.head.sha`、base SHA を検証し、branch 名だけをレビュー根拠にしない。allowlist は read にも適用される前提で扱う。
- `fallback`: なし。allowlist 拒否や get_pr の read failure を review-raven、GitHub route、`gh` で迂回して読み進めない。
- `failure / stop`: allowlist denied は理由を付した `BLOCKED_MCP_READ`、schema 欠落・read failure は `REMOTE_SNAPSHOT_READ_FAILED` として停止し、レビュー本文・投稿・APPROVEを行わない。
- `evidence`: binding、PR identity、base / reviewed head SHA、state、取得時刻、失敗分類を記録する（`observed`、token は除外）。

### O-03: Remote Snapshot の diff / files

- `precondition`: O-02 が成功し、`reviewedHeadSha` と変更ファイルの一覧が固定されている。
- `primary tool`: `{OWL}:get_pr` の files / patch（R-00 の schema snapshot）。
- `input / output`: 固定済み PR snapshot を入力し、filename、status、追加・削除行、patch、current diff 上の投稿可能位置を出力する。
- `side effect`: read-only。コード、PR、review thread を変更しない。
- `guard`: patch が `reviewedHeadSha` の snapshot に属することを確認し、巨大差分をファイル単位に分割しても branch 名で再取得しない。
- `fallback`: O-02 の read が成功した場合に限り、同じ PR identity と SHA を照合する read-only GitHub connector / `gh` で巨大 patch を補完できる。allowlist 拒否をこの補完で迂回しない。
- `failure / stop`: patch、filename、SHA の対応を検証できない場合は `DIFF_SNAPSHOT_INCOMPLETE` として停止し、位置を推測した投稿を行わない。
- `evidence`: file 数、patch 取得結果、SHA 照合、補完経路、投稿候補の位置を記録する（`observed`）。

### O-04: Repository State Guard

- `precondition`: O-02 の `reviewedHeadSha` が固定され、ローカル検証を行う必要がある。
- `primary tool`: `git status --porcelain --untracked-files=no`、`git rev-parse HEAD`、必要な `git fetch origin` / `git worktree add --detach`。
- `input / output`: 現在の worktree と reviewed head を入力し、clean 状態、HEAD 一致、隔離 worktree の有無を出力する。
- `side effect`: 必要な場合だけ一時 detached worktree を作成する。stash、discard、既存 worktree の上書きは行わない。
- `guard`: tracked file の dirty または HEAD mismatch はレビュー根拠にせず、元 worktree を破壊せずに reviewed head を隔離して検証する。
- `fallback`: 隔離環境を作成できない場合は `local verification: not performed` と明記する。未検証を success とせず、remote snapshot の SHA は維持する。
- `failure / stop`: dirty / mismatch を隔離できず、かつ必要な remote evidence も取得できない場合は `REPOSITORY_STATE_UNSAFE` として停止する。
- `evidence`: status、local HEAD、reviewedHeadSha、worktree path、実行時刻、local verification の扱いを記録する（`observed`）。

### O-05: Independent Stage の実装・テスト確認

- `precondition`: O-02 / O-03 と O-04 が完了し、remote snapshot と検証環境の SHA が一致している。
- `primary tool`: reviewed head 固定の worktree での `git`、`rg`、build、test、static analysis。既存レビュー本文はまだ読まない。
- `input / output`: diff、関連実装、テスト、CI 情報を入力し、独立した failure path、回帰、security、packaging、テスト不足の候補を出力する。
- `side effect`: read-only。レビュー投稿、既存 thread の取得・返信、APPROVE は行わない。
- `guard`: Independent Stage が終わるまで既存 review comment、review thread、summary の本文を文脈へ入れない。確認対象は固定済み SHA に限定する。
- `fallback`: ローカル検証ができない場合は `local verification: not performed` として remote evidence だけで進め、未実施を pass と解釈しない。
- `failure / stop`: 検証結果を成功・失敗・未実施に分類できない場合は `LOCAL_VERIFICATION_UNKNOWN` とし、必要な根拠が不足する approve verdict を停止する。
- `evidence`: SHA、検証環境、コマンド、終了コード、テスト要約、独立候補を記録する（`observed`）。

### O-06: Independent Stage の CI

- `precondition`: O-02 で `reviewedHeadSha` が固定され、required checks の repository policy を確認できる。
- `primary tool`: 固定済み `{OWL}:get_pr` の直後に一回だけ実行する check-runs read capability の `get_check_runs`（R-00 の schema snapshot）。
- `input / output`: PR 番号と `reviewedHeadSha` を入力し、各 check run の対象 SHA、status、conclusion、required / optional、run / job ID を出力する。
- `side effect`: read-only。CI の再実行、設定変更、write 経路への切り替えは行わない。
- `guard`: 全 required check が対象 SHA に対して completed / success の場合だけ success とする。`combined status` は使用せず、対象 SHA が不明な run は成功扱いにしない。
- `fallback`: failure 時に workflow run / job / log capability があれば使い、無ければ `gh run view <run-id> --log-failed` を read-only で使う。どちらも同じ SHA を確認する。
- `failure / stop`: pending、failure、対象 SHA 不一致、結果不明はそれぞれ CI pending / failure / unknown として記録し、unknown のまま Verdict / APPROVE を投稿しない。
- `evidence`: reviewedHeadSha、全 check run、status / conclusion、SHA 比較、失敗ログ経路、最終 head 再確認を記録する（`observed`）。

### O-07: Independent Stage の候補生成

- `precondition`: O-05 の独立確認と O-06 の CI 確認結果を取得し、既存レビュー本文を未読のまま候補化できる。
- `primary tool`: Independent Stage の LLM 判断。外部 read / write tool は使用しない。
- `input / output`: diff、実装、テスト、CI、非主要パスの観測を入力し、候補ごとの根拠、影響、再現条件、重大度を出力する。
- `side effect`: なし。コメント、thread、Verdict、APPROVEを投稿しない。
- `guard`: 既存レビューの結論や言い換えを候補生成へ混ぜず、特定 diff 行または PR-level の根拠を持つ候補だけを作る。
- `fallback`: なし。独立評価が不足する場合に既存レビュー本文を先に読んで補完しない。
- `failure / stop`: 独立評価の根拠、再現条件、影響のいずれかを出力できない場合は `INDEPENDENT_REVIEW_INCOMPLETE` として停止する。
- `evidence`: 入力 snapshot、候補 ID、根拠、重大度、未確認項目を `observed` / `inferred` に分けて記録する。

### O-08: Filter Stage の既存 review / thread

- `precondition`: O-07 の独立候補生成が完了し、current `reviewedHeadSha` が固定されている。
- `primary tool`: `{OWL}:list_review_threads`（R-00 の schema snapshot）。
- `input / output`: PR の全 review thread、resolved / outdated 状態、root / reply comment を入力し、既存範囲、重複候補、残す候補を出力する。
- `side effect`: read-only。既存 thread の resolve / unresolve、返信、summary 投稿は行わない。
- `guard`: Independent Stage 終了後に初めて本文を読み、取得結果の全件性と current diff を確認する。allowlist は read にも適用される。
- `fallback`: なし。allowlist 拒否、未接続、schema 不一致を review-raven や GitHub route の read で迂回しない。読み取れない状態を「既存指摘なし」と解釈しない。
- `failure / stop`: allowlist denied は `BLOCKED_MCP_READ`、列挙・schema・接続失敗は `REVIEW_THREADS_READ_FAILED` として停止し、Filter、投稿、Verdictへ進まない。
- `evidence`: thread 数、comment 数、状態、取得範囲、allowlist 結果、重複除外理由を記録する（本文引用は必要最小限、`observed`）。

### O-09: Synthesis Stage

- `precondition`: O-05〜O-08 の trusted evidence、current diff、既存レビューとの比較結果が揃っている。
- `primary tool`: LLM の分類・投稿位置・再現条件の判断。外部 tool は使用しない。
- `input / output`: 独立候補と既存範囲を入力し、accept / reject、`blocking` 等の分類、inline / summary の投稿経路を出力する。
- `side effect`: なし。投稿前の draft 判断に限定する。
- `guard`: 同じ条件・結論・修正方針の重複を落とし、inline は current diff の有効行、横断論点は summary にする。
- `fallback`: なし。位置や重大度を推測で補わず、根拠が弱い候補は reject または question として残す。
- `failure / stop`: 分類、採否、位置、reject 理由のいずれかが未確定なら `SYNTHESIS_INCOMPLETE` として投稿を停止する。
- `evidence`: candidate ID、分類、採否、重複判断、投稿経路、reject 理由を記録する（判断は `inferred`）。

### O-10: 投稿前 Snapshot Guard

- `precondition`: O-09 で投稿候補が確定し、まだ GitHub write を行っていない。
- `primary tool`: `{OWL}:get_pr` と必要な local status read（R-00 の schema snapshot）。
- `input / output`: PR 番号、固定済み SHA、候補 path / line を入力し、current head、current diff、投稿可能位置を出力する。
- `side effect`: read-only。投稿、APPROVE、merge は行わない。
- `guard`: current PR head が `reviewedHeadSha` と一致し、path / line が current diff に存在する場合だけ O-11〜O-13 へ進む。inline の `commitId` と APPROVE の `expectedHeadSha` はこの同じ SHA に固定する。
- `fallback`: なし。stale head、位置不明、read failure を branch 名や古い snapshot で補完しない。
- `failure / stop`: head 移動は `STALE_REVIEW`、位置不一致は `INVALID_COMMENT_POSITION`、read failure は `SNAPSHOT_GUARD_FAILED` として該当 write を停止する。
- `evidence`: 再取得時刻、current head、reviewedHeadSha、path / line、local status、比較結果を記録する（`observed`）。

### O-11: Initial Review の inline 投稿

- `precondition`: O-09 で根拠の固い投稿候補があり、O-10 の Snapshot Guard が成功している。
- `primary tool`: `{OWL}:post_inline_comment`（R-00 の schema snapshot）。
- `input / output`: owner、repo、prNumber、`commitId = reviewedHeadSha`、path、line、body を入力し、comment / thread ID と URL を出力する。
- `side effect`: current diff の一行へ review comment を一件投稿する。resolve、APPROVE、merge は行わない。
- `guard`: blocking 等の分類、current diff 上の位置、同一候補の未投稿を確認し、本文に再現条件・影響・次の行動を含める。
- `fallback`: なし。Thread Owl の allowlist・head guard を GitHub connector や `gh` の write で迂回しない。
- `failure / stop`: 投稿失敗または受理結果不明は `INLINE_POST_FAILED` とし、同一投稿を即時再実行せず thread を再取得して重複を確認する。
- `evidence`: comment / thread ID、URL、commitId、path、line、分類、投稿結果を記録する（`observed`）。

### O-12: Initial / Re-review の summary・Verdict

- `precondition`: initial-review または re-review で Verdict を投稿する条件が確定し、O-10 の SHA guard が成功している。
- `primary tool`: `{OWL}:post_summary_comment`（R-00 の schema snapshot）。
- `input / output`: レビュー観点、CI、coverage、残存リスク、`reviewedHeadSha`、Verdict の状態を入力し、PR-level summary / comment ID / URL を出力する。
- `side effect`: PR conversation へ summary を一件投稿する。コード、thread、queue、merge は変更しない。
- `guard`: approve のときだけ固定見出し `## @thread-owl Review Verdict: APPROVED`、`Reviewed HEAD SHA`、`Status: READY_TO_MERGE` を正確に含める。summary-only では明示されない投稿を行わない。
- `fallback`: なし。Verdict を GitHub connector の review や issue comment で代替投稿しない。
- `failure / stop`: summary の投稿失敗・状態キー欠落・SHA 不一致は `SUMMARY_POST_FAILED` として停止し、マージ可能と報告しない。
- `evidence`: comment ID / URL、mode、観点、CI SHA、Verdict、Status、投稿結果を記録する（`observed`）。

### O-13: APPROVE 投稿

- `precondition`: ユーザーがチャット上で APPROVE 投稿を明示的に依頼し、Verdict approve、CI success、全 thread resolved、O-10 の current head 一致が揃っている。
- `primary tool`: `{OWL}:approve_pull_request`（R-00 の schema snapshot）。
- `input / output`: owner、repo、prNumber、`expectedHeadSha = reviewedHeadSha` を入力し、APPROVE review の ID / URL / 結果を出力する。
- `side effect`: GitHub review を APPROVE として一件投稿する。merge、branch 操作、Issue クローズは行わない。
- `guard`: 実行直前に get_pr と CI を再確認し、`expectedHeadSha`、CI 対象 SHA、current head を一致させる。明示許可なしの自律 APPROVE は禁止する。
- `fallback`: なし。GitHub connector の APPROVE や `gh` で Thread Owl の guard を迂回しない。
- `failure / stop`: 許可欠如、CI unknown / failure、未解決 thread、SHA 不一致、受理結果不明は `APPROVE_BLOCKED` として投稿せず停止する。
- `evidence`: 明示指示、Verdict、current / expected SHA、CI 結果、thread 数、投稿結果を記録する（`observed`）。

### O-14: Re-review の queue candidate と前回差分

- `precondition`: O-01 が re-review で、O-00 の candidate または PR URL を取得できる。
- `primary tool`: O-00 の queue resource read と `{OWL}:get_pr`（R-00 の schema snapshot）。
- `input / output`: candidate の owner、repo、prNumber、reason、expected_head、前回の handled 状態を入力し、re-review 対象と固定済み `reviewedHeadSha` を出力する。
- `side effect`: read-only。queue、PR、review thread を変更しない。
- `guard`: queue reason は `re-review-requested` に限定し、`expected_head` と current `pr.head.sha` を比較する。PR URL 起点では queue 待機を挿入しない。
- `fallback`: PR URL が明示されている場合だけ O-02 の direct snapshot を使う。queue read failure や stale candidate から対象 PR を推測しない。
- `failure / stop`: candidate の schema 欠落、reason 不一致、expected head 不一致は `STALE_REREVIEW_REQUEST` として停止し、古い差分で投稿・APPROVEを行わない。
- `evidence`: resource URI、candidate、reason、expected_head、current head、前回差分の範囲、比較結果を記録する（`observed`）。

### O-15: Re-review の thread 状態・CI 再確認

- `precondition`: O-14 で re-review 対象と current `reviewedHeadSha` が固定されている。
- `primary tool`: `{OWL}:get_pr`、`{OWL}:list_review_threads`、check-runs read capability（R-00 の schema snapshot）。
- `input / output`: 前回 thread、現 head の差分、CI、実装者対応を入力し、resolved / outdated / unresolved と残存回帰を出力する。
- `side effect`: read-only。返信、inline、summary、APPROVEはこの行では行わない。
- `guard`: candidate の expected head、current diff、全 thread 状態、CI 対象 SHA を突合し、未解決 thread と対応差分が導入した重大回帰だけを次の候補にする。
- `fallback`: O-00 で固定した `{OWL}` の read capability のみを使う。allowlist、current head、列挙失敗を別 route で隠さない。
- `failure / stop`: thread / CI の状態または SHA を確認できない場合は `REREVIEW_STATE_UNKNOWN` として投稿・Verdict・APPROVEを停止する。
- `evidence`: current head、前回 head、thread ID / 状態、CI run、対応差分、残存候補を記録する（`observed`）。

### O-16: Re-review の unresolved thread への返信

- `precondition`: O-15 で元 thread が unresolved であり、同じ論点の残存条件を具体化できる。
- `primary tool`: `{OWL}:reply_review_thread`（R-00 の schema snapshot）。
- `input / output`: threadId、返信本文、current head の根拠を入力し、返信 comment ID / URL / 結果を出力する。
- `side effect`: 元 thread への返信だけを行う。thread の resolve / unresolve、new thread、APPROVEは行わない。
- `guard`: thread の owner / repo / ID と残存再現条件を確認し、resolve は reviewed-side に任せる。独立した新論点を混ぜない。
- `fallback`: なし。GitHub connector や `gh` の comment write で返信を代替しない。
- `failure / stop`: 投稿失敗または受理結果不明は `THREAD_REPLY_FAILED` とし、同じ返信を再実行せず再取得で重複を確認する。
- `evidence`: thread ID、current head、返信 ID / URL、本文要約、resolve=false、結果を記録する（`observed`）。

### O-17: Re-review の current diff 上の新規 inline

- `precondition`: 元 thread が resolved / outdated だが問題が残り、O-10 で current diff に有効な位置がある。
- `primary tool`: `{OWL}:post_inline_comment`（R-00 の schema snapshot）。
- `input / output`: 新規 thread の body、current path / line、`commitId = reviewedHeadSha` を入力し、comment / thread ID / URL を出力する。
- `side effect`: current diff 上に新しい unresolved thread を一件投稿する。元 thread への重複返信は行わない。
- `guard`: stale な元行ではなく current diff の有効行へ投稿し、以前の指摘の継続であることと現 head の具体的な再現条件を記載する。
- `fallback`: current diff に位置がない場合は O-18 の PR-level summary へ分岐する。stale な行への投稿や別 write 経路への切り替えはしない。
- `failure / stop`: Snapshot Guard 不一致、位置不正、投稿失敗は `REREVIEW_INLINE_FAILED` として停止し、対応済みと報告しない。
- `evidence`: 元 thread ID、current thread ID、reviewedHeadSha、path / line、body 要約、投稿結果を記録する（`observed`）。

### O-18: Re-review / Follow-up の current diff 外論点

- `precondition`: 残存問題を確認できるが、current diff 上に安全な投稿位置がない。
- `primary tool`: `{OWL}:post_summary_comment`（R-00 の schema snapshot）。
- `input / output`: blocking / 残存条件、影響、再現手順、`reviewedHeadSha` を入力し、PR-level summary の ID / URL を出力する。
- `side effect`: PR conversation に summary を一件投稿する。stale な inline thread は作成しない。
- `guard`: 位置がない理由とマージへの影響を明記し、過去の行番号へ投稿しない。blocking なら Verdict approve を抑止する。
- `fallback`: なし。current diff 外の論点を無理に inline へ移さず、GitHub connector / `gh` の write へ迂回しない。
- `failure / stop`: summary 投稿失敗・SHA 不一致は `REREVIEW_SUMMARY_FAILED` として停止し、残存問題を解消済みと扱わない。
- `evidence`: current head、元 thread、位置判定、残存条件、summary ID / URL、blocking 判定を記録する（`observed`）。

### O-19: Thread Follow-up

- `precondition`: 指定 thread、対象 PR、current `reviewedHeadSha` が確定し、指定された文脈だけを確認する。
- `primary tool`: `{OWL}:get_pr`、`{OWL}:list_review_threads` と O-16〜O-18 の適切な write tool（R-00 の schema snapshot）。
- `input / output`: root comment、全返信、thread 状態、対応差分を入力し、resolved in code / partially resolved / not resolved / needs clarification と投稿結果を出力する。
- `side effect`: 状態に応じて元 thread への返信、新規 inline、または summary を一件投稿する。resolve / unresolve / merge は行わない。
- `guard`: current head と指定 thread を再確認し、独立論点を同じ thread に混ぜない。unresolved は O-16、current diff 位置ありは O-17、位置なしは O-18 に固定する。
- `fallback`: current diff の位置が失われた場合だけ O-18 summary に分岐する。別 route や stale line への write は行わない。
- `failure / stop`: thread read、状態判定、選択した write のいずれかが不確実なら `THREAD_FOLLOWUP_INCOMPLETE` として停止する。
- `evidence`: thread ID、current head、読んだ返信範囲、判定、選択経路、投稿結果を記録する（`observed` / `inferred`）。

### O-20: Verdict 判定

- `precondition`: initial-review / re-review の独立確認、Filter、Synthesis、必要な投稿、CI、全 thread 状態が確定している。
- `primary tool`: LLM の verdict 判定。approve 時の summary 投稿だけ O-12 を使う。
- `input / output`: blocking 数、全 thread の resolved 状態、主要リスクの検証、CI と対象 SHA、残存リスクを入力し、approve / request changes / comment only / needs follow-up を一つ出力する。
- `side effect`: approve の場合だけ O-12 の Verdict summary を投稿できる。APPROVE、merge、Issue クローズは自動実行しない。
- `guard`: 新規 blocking 0、全 thread resolved、主要リスクの検証あり、CI success、CI head と `reviewedHeadSha` の一致をすべて満たす場合だけ approve とする。unknown を success としない。
- `fallback`: CI、thread、SHA、独立検証が unknown の場合は comment only / needs follow-up として報告し、approve へ寄せない。
- `failure / stop`: 必須 evidence、分類、状態のいずれかが欠ける場合は `VERDICT_INCOMPLETE` として Verdict / APPROVEを停止する。
- `evidence`: 判定表、条件、CI SHA、thread 数、残存リスク、O-12 の投稿結果を記録する（事実は `observed`、判定は `inferred`）。

### O-21: ユーザー報告・ハンドオフ

- `precondition`: mode、current / reviewed head、CI、Verdict、thread、投稿数、queue route、残存リスクが確定している。
- `primary tool`: なし。日本語の固定 Markdown 報告を出力する。
- `input / output`: O-00〜O-20 の evidence を入力し、PR、mode、reviewed head、CI head、verdict、CI 状態、投稿数、blocking 数、残存リスク、queue URI / reason / route を出力する。
- `side effect`: なし。外部 API、PR、Issue、queue、作業ツリーへの write は行わない。
- `guard`: approve、request changes、comment only、needs follow-up、blocked を混同せず、未確認を成功と書かない。token、cookie、Authorization header、秘密情報を含めない。
- `fallback`: 必須値が得られない場合は unknown / blocked と明記し、推測で補完しない。
- `failure / stop`: 報告に必要な evidence が欠ける場合は `REPORT_EVIDENCE_INCOMPLETE` として停止し、merge ready と報告しない。
- `evidence`: 実行順、logical alias / schema snapshot、observed / inferred / simulated の区別、未実施項目、次の実装側アクションを固定フォーマットで記録する。

## Queue 契約

PR が明示されず queue 待機を依頼された場合だけ subscription を使う。

| Resource | 用途 |
| --- | --- |
| `queue://review/queue` | `opened` / `synchronized` / `re-review-requested` を含む通常レビュー起動 |
| `queue://review/re-review-requests` | `re-review-requested` だけを受ける reviewer-side handoff |

再レビュー待機では必ず `queue://review/re-review-requests` を使う。通常 queue では先行する `synchronized` 通知で待機が終了し、直後の再レビュー依頼を見逃す可能性がある。

native `subscriptions/listen` が使えなければ、repository の運用ガイドに従って `mcp-resource-subscriber`（v0.6.0 以降）を使う。

```powershell
bunx mcp-resource-subscriber `
  --url $env:THREAD_OWL_MCP_URL `
  --uri queue://review/re-review-requests `
  --timeout-ms 900000 `
  --json
```

`json.route` が `"subscription"` または `"pre-completion"` であることを確認し、`json.finalText` をパースして `owner`、`repo`、`prNumber`、`reason` を取得する。`route` が `"timeout"` または `"failed"` の場合はレビュー完了として扱わない。

## モード選択

依頼から次のモードを選ぶ。PR URL だけでレビューを依頼された場合は `initial-review` とする。

モードを決めた直後、queue 待機またはレビュー本文の取得に入る前に O-00 を実行する。`{OWL}` の binding と read 検証が成功するまで、Independent Stage、Filter Stage、各種コメント投稿、Verdict、APPROVEへ進まない。

### `initial-review`

PR 全体を初回レビューする。queue candidate の `reason` が `opened` または通常の `synchronized` の場合も使う。

### `re-review`

前回指摘への対応、未解決 thread、対応後の重大な回帰、CI の変化を確認する。candidate の `reason` が `re-review-requested` の場合はこのモードにする。

### `thread-follow-up`

指定 thread の文脈、実装者の返信、対応差分だけを確認して返信する。

### `summary-only`

インラインコメントを投稿せず、merge readiness と残存リスクをまとめる。ユーザーが投稿を明示していなければ draft のみ返す。

## Snapshot Guard & Repository State Guard

### 1. Remote Snapshot の原則
- レビュアーは現在のローカル作業ツリーをレビュー対象として信頼してはならない。GitHub から取得した PR HEAD SHA（`reviewedHeadSha`）を唯一のレビュー対象として固定する。
- PR metadata / diff / 変更ファイルは `{OWL}:get_pr` を第一候補にする。
- GitHub connector や `gh` で補完する場合も、必ず `reviewedHeadSha` を明示して取得する。branch 名だけを指定した読み取りは禁止する（レビュー中に branch が更新されて内容が変化し得るため、commit SHA を使用する）。

### 2. ローカル検証時の Repository State Guard
ローカル環境でコード参照、ビルド、テスト、静的解析等を行う場合は、開始前に以下を確認する。
1. `git status --porcelain --untracked-files=no` が空（tracked file に変更がない状態）であること
2. `git rev-parse HEAD` が `reviewedHeadSha` と一致すること
いずれかを満たさない場合、現在の worktree をレビュー根拠として使用してはならない。

- **dirty/mismatched な状態の扱い:**
  - 未 commit 変更を stash / discard してレビューを続行してはならない（実装担当の作業状態を破壊しないため）。
  - detached worktree または一時的な clone を作成し、`reviewedHeadSha` を checkout して検証する。
    - 推奨例:
      ```bash
      git fetch origin <reviewedHeadSha>
      git worktree add --detach <temporary-path> <reviewedHeadSha>
      # 検証完了後
      git worktree remove <temporary-path>
      ```
  - 隔離検証環境を作成できない場合は、ローカル検証を行わず `local verification: not performed` としてレビューを進行する。

### 3. 検証後の再確認ゲート
ビルドやテストが完了した後、かつ投稿処理（Snapshot Guard）の直前に、以下を再確認する。
1. 検証環境の `HEAD` が `reviewedHeadSha` のままであること
2. 検証環境の `git status --porcelain --untracked-files=no` が空であり、tracked file に変更がないこと
3. 現在の GitHub 上の PR HEAD SHA が `reviewedHeadSha` のままであること

次の場合は stale review として投稿（inline comment や APPROVE）を停止する。
- レビュー中に PR HEAD が変更された
- 検証処理によって tracked file が書き換えられた、または HEAD が意図せず移動した
（生成物などの untracked file は許容するが、tracked file の変更は厳禁とする）

### 4. CI 検証の SHA 固定
- **状態集約**: CI 判定の直前に固定済み `{OWL}:get_pr` を read し、現在の PR HEAD SHA を `reviewedHeadSha` として固定する。その直後に check-runs read capability の `get_check_runs` を PR 番号で **1 call** 実行する。`get_check_runs` は SHA を受け取らないため、返却された各 check run の `head_sha` / `sha`（または同等の対象 SHA）が `reviewedHeadSha` と一致することを確認する。対象 SHA を確認できない応答は `CI: unknown` とし、成功扱いにしない。
- `CI: success` は、`reviewedHeadSha` に対するすべての required checks が `status: completed` かつ `conclusion: success` の場合だけにする。required check が未返却、または `queued` / `in_progress` / `pending` の場合は `CI: pending`、required check に `failure` / `cancelled` / `timed_out` / `action_required` / `startup_failure` / `skipped`（リポジトリ方針で明示的に許可されていない場合）などの結論があれば `CI: failure` とする。optional check の結果は別途記録する。`combined status` は使用禁止であり、その応答を「実行中」や成功の根拠にしてはならない。
- **失敗ログ**: `CI: failure` の場合、現在の client に workflow run / job / log の read capability があれば、その capability で失敗 job のログを取得する。client にその capability がなければ `gh run view <run-id> --log-failed` を read-only のフォールバックとして使う。失敗ログ取得の可否は client 依存であり、いずれの経路も利用できない場合は `CI: unknown` として記録し、Verdict / APPROVE を投稿せず停止する。
- 最終的な verdict（判定）の根拠とした CI の対象 SHA を確認・記録する。
- **HEAD 移動時の再確認**: 検証結果の採用または APPROVE 投稿の直前に、`{OWL}:get_pr` を再度 read して PR HEAD が `reviewedHeadSha` のままであることを確認する。HEAD が動いた場合は、以前の check runs 結果を破棄し、新しい current head を固定して `get_check_runs` を再実行する。再取得または SHA 照合ができない場合は `CI: unknown` とし、Verdict / APPROVE を停止する。

### 5. 再レビュー依頼の期待 HEAD 照合
- candidate queue などの再レビュー依頼に `expected_head` が含まれる場合、開始時に `candidate.expected_head` と、固定済み `{OWL}` binding の `get_pr(...).pr.head.sha` を比較する。
- 不一致の場合は古い再レビュー依頼とみなし、そのまま APPROVE せず、最新の HEAD を新しいレビュー対象としてレビューをやり直すか、明示的に処理を停止する。

### 6. 既存 Snapshot Guard の維持
- `{OWL}:post_inline_comment.commitId` と `{OWL}:approve_pull_request.expectedHeadSha` には、最終確認済みの同じ head SHA (`reviewedHeadSha`) を使う。
- inline の `path` と `line` が current diff 上の投稿可能な位置であることを確認する。確実でなければ PR-level summary にする。

## Initial Review

初回レビューは次の順序を守る。Independent Stage が終わるまで、既存 review comment、review thread、review summary の本文を読まない。

### 1. Independent Stage

1. PR の owner、repo、番号、title、description、base/head、head SHA を確認する。
2. diff、変更ファイル、関連実装、テスト差分を読む。
3. CI は Snapshot Guard の check-runs 契約（current head SHA を先に固定し、`get_check_runs` の対象 SHA を照合する）で確認する。failed/skipped checks、packaging、docs、release への影響も確認し、確認経路がなければ `CI: unknown` と記録する。
4. 既存レビューを参照せず、独立した懸念候補を作る。
5. 次の非主要パスを横断確認する。
   - 空、null、不正値、境界値、巨大入力、重複入力
   - 初回実行、再実行、二重実行、キャンセル、部分成功、失敗後リトライ
   - timeout、fallback、例外変換、権限不足、secret 欠落、token 失効
   - 既存設定、既存データ、旧バージョン、migration、後方互換性
   - Windows / Linux / macOS、local / CI、開発 / 配布環境の差
   - UI / domain / infrastructure / persistence / CLI / CI の責務境界
   - エラーメッセージ、ログ、通知、復旧導線
6. テストが実装詳細ではなく、PR が壊してはならない仕様を固定しているか確認する。

この段階では候補を投稿しない。

### 2. Filter Stage

1. `{OWL}:list_review_threads` と必要な GitHub 読み取り経路で、既存 review、thread、実装者返信を初めて読む。
2. 既存レビューが扱った行、条件、リスク種別、edge case、修正方針を整理する。
3. Independent Stage の候補から次を削除する。
   - 同じ条件、結論、修正方針を繰り返すもの
   - 新しい再現条件や影響範囲を加えないもの
   - resolved、outdated、または現 head で対応済みのもの
   - 同意、言い換え、根拠の弱い追従
4. 次だけを残す。
   - 未指摘の failure path、edge case、integration point
   - より具体的な再現条件、影響範囲、テスト観点を示せるもの
   - 同じファイルでも別責務、別経路、別ユースケースの問題
   - マージ後に発覚すると手戻りが大きい問題

既存レビューはレビュー範囲の上限ではなく、重複投稿を防ぐマスクとして扱う。

### 3. Synthesis Stage

各候補について、根拠、重大度、投稿位置、対応可能性を確認する。

1. `blocking` / `non-blocking` / `question` / `note` / `praise` に分類する。
2. 特定 diff 行に直接対応する指摘だけ inline にする。
3. 複数ファイルにまたがる設計、運用、CI、packaging、release の問題は PR-level summary にする。
4. 再現条件、影響、期待する次の行動を短く書く。
5. 根拠が弱い、差分価値が薄い、対応方法が不明、コメント過多を招く候補を削除する。
6. Snapshot Guard を再確認してから投稿する。

## コメント分類

- `blocking`: correctness、security、privacy、data loss、主要ユースケース、CI、packaging、release の明確な問題。
- `non-blocking`: merge を止めない保守性、テスト、UX、DX 改善。後続対応可能であることを明記する。
- `question`: 仕様意図や既存仕様を確認しないと断定できない論点。
- `note`: docs、release note、follow-up issue で追う価値がある論点。
- `praise`: 回帰リスク低減、責務分離、テスト容易性など明確な価値がある判断。過剰に投稿しない。

投稿本文は簡潔にする。

```markdown
[blocking] XXX の条件では YYY となり、ZZZ が失敗します。
AAA のケースをテストで固定し、BBB の処理を見直してください。
```

```markdown
[question] この分岐は AAA も対象にする意図でしょうか？
既存仕様では BBB と読めるため、期待する挙動を確認したいです。
```

## 投稿判断

PR URL を示してレビューと投稿を依頼された場合、根拠が固い inline comment と通常の review comment は投稿まで行う。次は投稿前にユーザーへ確認する。

- PR 全体方針を覆す大きな指摘
- blocking 判定が微妙
- release / operation の意思決定を含む
- 既存コメントとの重複が疑わしい
- コメント候補が 5 件を超える
- 投稿対象 PR、head、line、thread を確実に特定できない
- `summary-only` の summary 投稿を明示されていない

### Verdict コメント投稿

reviewed-side workflow は、マージ判断時に「thread-owl から現在の PR HEAD に対するレビュー完了の証拠が GitHub 上に存在するか」を確認する。指摘がなく沈黙すると、この証拠が残らずマージ判断が進まないデッドロックになる。これを避けるため、次の条件でだけ Verdict コメントを投稿する。

**トリガー条件**

`initial-review` または `re-review` において `verdict: approve` と判定した場合（判定基準は「Verdict」節を参照）。

**振る舞い**

- `{OWL}:approve_pull_request` は呼ばない。GitHub native の APPROVE 権限を自律実行する変更ではない。
- 代わりに `{OWL}:post_summary_comment` でレビュー観点・検証結果のサマリーを含む Verdict コメントを、本節冒頭の投稿判断基準に従って投稿する。
- **reviewed-side 連携の必須要件**: reviewed-side workflow（`review-raven`）は `## @thread-owl Review Verdict: APPROVED`、`Reviewed HEAD SHA`、`Status: READY_TO_MERGE` を機械的に検出してマージゲートを判定する。そのため、**見出し行および末尾のメタデータ行の形式・文言は変更せず、その間にレビューサマリーを記述する**こと。

```markdown
## @thread-owl Review Verdict: APPROVED

すべての対象コードの検証が完了しました。技術的・品質的にマージ可能な状態である（マージ推奨）と判定しました。

### レビューサマリー
- **主な確認観点**:
  - （例: 境界値・異常系入力に対する堅牢性、エラーハンドリング）
  - （例: 既存仕様・設定との後方互換性やマイグレーション影響）
  - （例: 型安全性、テストコードによる仕様の固定状況）
  - （例: CI（build, test, lint, coverage）の成否と実行対象 SHA の一致）
- **判定根拠**: （なぜ問題なし・マージ可能と判断したかの具体的要約。再レビューの場合は前回指摘事項の解消確認を含む）

---
- Reviewed HEAD SHA: `<reviewedHeadSha>`
- Status: `READY_TO_MERGE`
```

- サマリー内容は固定定型文の羅列で済ませず、Independent Stage や Synthesis Stage で実際に確認・評価した PR 固有の観点・根拠を反映すること。
- `<reviewedHeadSha>` は Snapshot Guard で確認済みの `reviewedHeadSha` と一致させる。
- この Verdict コメント投稿自体は、上記の投稿判断基準（本節冒頭のリスト）にそのまま従う。承認不要の新たな自律アクションとして追加するものではない。

### APPROVE 投稿とマージ判断について

`{OWL}:approve_pull_request` はユーザーが明示的に APPROVE 投稿を依頼した場合だけ実行する。実行直前に `{OWL}:get_pr` で head SHA と CI を再確認する。CI が unknown、blocking が残る、または head が変わった場合は実行しない。

安全性の観点（自動マージや自動デプロイがトリガーされるリスク等）から、明示的な許可（指示）がない限り、自律的に `APPROVE` を送信してはならない。

マージ判断の伝わりやすさを担保するため、以下の運用ルールを適用する。
- **レビュー結果の明記:** レビューの要約やコメントにおいて、「技術的・品質的にマージ可能な状態である（マージ推奨）」という評価自体は日本語で明確に報告する。
- **ユーザーの指示による実行:** ユーザーから「APPROVEを投稿してください」という明示的な許可（指示）をチャット上でいただいた段階で、エージェントが実際の `approve_pull_request` 送信を実行する（マージ処理自体は別ワークフローの責務であり、本スキルでは行わない）。

## Re-review

1. queue 起点なら `reason = re-review-requested` と対象 PR を確認する。
2. 前回 thread、実装者返信、現 head、前回レビュー後の差分を読む。
3. 各 thread の `isResolved` / `isOutdated` 状態と、現 head での対応状況を確認する。
4. 未解決 thread と、対応差分が導入した重大な回帰だけを確認する。
5. CI の変化を確認する。
6. 次の投稿経路表に従って各 thread を処理する。

| 元 thread の状態 | 現 head での状態 | 投稿方法 |
| --- | --- | --- |
| unresolved | resolved in code | 元 thread へ簡潔に返信する。thread 自体は resolve しない |
| unresolved | partially resolved / not resolved / needs clarification | 元 thread へ残存再現条件を具体的に返信する |
| resolved / outdated | resolved in code | 新規コメントを投稿しない。必要なら PR summary のみで解消を報告する |
| resolved / outdated | partially resolved / not resolved / needs clarification | current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 unresolved thread を作る |

新規 inline comment には、以前の指摘の継続であることと、現 head に残る具体的な再現条件を記載する。元 thread への重複返信は行わない。

current diff 上に投稿可能な行がない場合は、無理に stale な位置へ投稿せず PR-level summary に blocking と残存条件を明示する。

新規 inline を投稿する前に Snapshot Guard を再実行し、現 head SHA と投稿可能行を確認する。

7. 初回レビューで出さなかった軽微な新規指摘を追加しない。
8. 新しい blocking がある場合だけ新規 inline comment を検討する。

## Thread Follow-up

1. 指定 thread と current head を特定する。
2. thread の `isResolved` / `isOutdated` 状態を確認する。
3. thread の root comment、全返信、対応差分だけを読む。
4. `resolved in code` / `partially resolved` / `not resolved` / `needs clarification` を判断する。
5. 新しい独立論点を同じ thread に混ぜない。
6. Re-review の投稿経路表と同じルールを適用する。
   - thread が unresolved なら `{OWL}:reply_review_thread` で返信する。resolve は行わない。
   - thread が resolved / outdated で問題が残るなら、current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 thread を作る。元 thread への返信は行わない。
   - current diff 上に投稿可能な行がない場合は PR-level summary にする。

## Verdict

- `approve`: 新規 `blocking` 指摘がなく、既存 review thread がすべて resolved であり（分類を問わない。`non-blocking` / `question` の未解決も許容しない）、主要リスクのテストまたは説明があり、CI が成功している。「技術的・品質的にマージ可能な状態である（マージ推奨）」という判断結果であり、ユーザーへの報告で明記する。明示的な許可（指示）がない限り、実際の `APPROVE` 投稿は行わない。`initial-review` / `re-review` でこの判定に至った場合は「Verdict コメント投稿」節に従って Verdict コメントを投稿する。
- `request changes`: blocking が残る。Thread Owl に REQUEST_CHANGES tool はないため、blocking comment と verdict の報告に留める。
- `comment only`: 判断材料が不足し、question が中心。
- `needs follow-up`: merge 可能だが、別 issue または後続 PR で追う論点がある。

## ユーザー報告

```markdown
## Review result

- PR: ...
- mode: initial-review | re-review | thread-follow-up | summary-only
- reviewed head: <SHA>
- source of truth: remote PR snapshot
- local verification: isolated worktree | clean matching worktree | not performed
- local verification head: <SHA | n/a>
- CI head: <SHA | unknown>
- verdict: approve | request changes | comment only | needs follow-up
- CI: success | failure | unknown
- posted: 新規inline N 件、thread 返信 N 件、summary N 件、approve N 件
- blocking: N 件（新規inline N 件 / thread 返信 N 件）
- residual risk: ...

## Independent review delta

- 既存レビューで扱われていた範囲: ...
- 今回追加で確認した死角: ...
- 投稿を見送った重複候補: ...
```

queue を使った場合は resource URI、candidate reason、subscription route も報告する。指摘がない場合は、レビュー済み範囲と残存リスクだけを報告する。

## ハンドオフ提示

`initial-review` / `re-review` を終えたら、ユーザー報告の**最後に**次アクションを提示する。レビュー指摘への対応は、その PR を実装した CLI エージェントが同一セッションで引き受けるのが最良であり（実装時の設計意図・トレードオフ・棄却案がコンテキストに残っており、リポジトリとスレッドの再調査が要らない）、reviewer 側がここで停止して実装側へ渡すのが正しい。`thread-follow-up` / `summary-only` では提示しない。

verdict によって提示内容を分ける。

### 対応が必要な場合（`request changes` / `comment only` / `needs follow-up`）

そのまま実装 CLI へ貼り付けられる 1 行を、**コードブロックに単独で**出力する。前後に説明を混ぜず、コピーしてそのまま使える形にする。

```
/review-raven-thread-owl-cycle <owner>/<repo>#<pr> のレビュー指摘に対応してください
```

続けて 1 行で、投稿した blocking 件数と未解決 thread 数を添える。

### サイクル終了とみなせる場合（`verdict: approve`）

対応プロンプトは出さない。新規 `blocking` がなく全 thread が resolved でありサイクルが終了したことを示し、次アクションが**人によるマージ判断**であることを述べる。

```
レビューサイクル完了: <owner>/<repo>#<pr>（Verdict: APPROVED / Reviewed HEAD SHA: <SHA>）
```

### 制約

- 提示はテキスト出力に限る。**このスキルは実装側 skill を自分で起動しない。** reviewer と reviewed は別セッションで動かす。
- `<owner>` / `<repo>` / `<pr>` / `<SHA>` は実際の値に展開する。プレースホルダーのまま出力しない。
- コードブロックにはプロンプト 1 行だけを入れる。ここは機械的に読み取られる前提の出力である（Squirrel Notifier のハンドオフポップアップがこの行をコピー対象として扱う）。
- 実際にマージするかどうかは判断しない。マージは常に人の明示的な操作を挟む。
