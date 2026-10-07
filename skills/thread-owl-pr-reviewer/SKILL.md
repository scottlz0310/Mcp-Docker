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
- PR の挙動・仕様意図に関する確認は `AskUserQuestion` で尋ねず、対象 PR の `[question]` コメントへ記録する。投稿先を確定できない場合は、停止コードで報告する。
- style nit、既存コードだけに由来する問題、PR の目的外の大規模改善を投稿しない。
- 既存レビューへの同意、言い換え、根拠の弱い追従を投稿しない。
- 再レビューで、初回に出さなかった軽微な指摘を後出ししない。
- 指摘がない場合は inline comment や thread 返信を作らない。ただし `initial-review` / `re-review` は、verdict にかかわらず最後に完了通知 write を**ちょうど 1 回**呼んで終える（「レビュー完了サマリー」節）。
- 書き込み失敗が曖昧な場合は、同じ投稿を即時再実行せず thread を再取得して重複を確認する。

## references の索引

手順の詳細は、該当する手順に入るときだけ `references/`（この SKILL.md と同じ skill ディレクトリ）から読む。同じ規則を SKILL.md に書き足さない。読めない場合は、規則を推測で補わず、次の動作に従う。

| 手順に入る条件 | 読むもの | 読めないとき |
| --- | --- | --- |
| 最初の操作（O-00。全モード） | `references/discovery.md` | `REFERENCE_UNREADABLE` |
| PR が明示されず queue 待機を依頼されたとき | `references/queue-wait.md` | `QUEUE_WAIT_FAILED` |
| worktree が dirty または `reviewedHeadSha` と不一致で、ローカル検証をするとき | `references/local-verification.md` | `local verification: not performed` |
| CI を判定するとき（O-06、O-15、Snapshot Guard の手順 4） | `references/ci-check.md` | `CI: unknown`（Verdict / APPROVE を投稿しない） |
| `verdict: approve` の Verdict を投稿するとき（O-12） | `references/verdict.md` | `VERDICT_FORMAT_INVALID` |
| `re-review` / `thread-follow-up` | `references/re-review.md` | `REFERENCE_UNREADABLE`（inline も thread 返信も行わない） |

## Thread Owl 契約

Thread Owl の logical alias `{OWL}` を、実行中 client の discovery 結果から解決して読み取り・投稿の第一候補にする（O-00）。skill 本文に client 固有の server 名・tool 名・namespace を書かず、未ロードなら client-native の tool / resource discovery を行う。

| 操作 | 契約 |
| --- | --- |
| `{OWL}:get_pr` | `owner`、`repo`、`prNumber` から `pr`・`files`・`origin` を返す。`pr.head.sha`、`pr.base.sha`、各 file の `patch` を記録する。`origin`（`allowed`、拒否のときは `reason`）は、thread-owl が `ALLOWED_AUTHORS` と fork で判定した PR の作成元の結果である。skill は許可リストを持たない |
| `{OWL}:list_review_threads` | resolved / outdated 状態とコメントを含む review thread 一覧を返す |
| `{OWL}:post_inline_comment` | `commitId`、`path`、`line`、`body` を指定して current diff に投稿する |
| `{OWL}:reply_review_thread` | `threadId` へ返信する。thread の所属 repository は server 側でも allowlist 照合される |
| `{OWL}:post_summary_comment` | PR conversation に issue comment として summary を投稿する。`headSha` には `reviewedHeadSha` を渡す。呼び出すと `review://status/{owner}/{repo}/{prNumber}` が `reviewed` になり、待機中の reviewed-side へ完了が通知される。Verdict コメントの投稿には使わない |
| `{OWL}:post_review_verdict` | `owner`、`repo`、`prNumber`、`headSha`（= `reviewedHeadSha`）、`summary`（自由記述部分だけ）から APPROVED の Verdict コメントを投稿し、`commentId` を返す。見出し・`- Reviewed HEAD SHA:` 行・`- Status:` 行は server 側で組み立てる。`headSha` が current PR head と一致しない、または `summary` が予約された文言を含む場合は、投稿せず error を返す（`references/verdict.md`）。呼び出すと `review://status` が `reviewed` になる（thread-owl v0.5.0 以降） |
| `{OWL}:approve_pull_request` | `expectedHeadSha` と現在の head が一致する場合だけ APPROVE review を送る |

- `{OWL}:get_pr` は CI status、check logs、通常の issue comment 全文を返さない。必要な read-only の補完だけ GitHub connector または `gh` で行う。Thread Owl で提供されない書き込みを別経路へ迂回しない。
- `{OWL}:post_review_verdict` は approve 経路だけで使う必須 capability である。この tool が無い（thread-owl v0.5.0 未満）、または schema が一致しない場合でも、approve 以外のレビューは続行できる。approve に至った時点で `VERDICT_TOOL_UNAVAILABLE` として停止し、`{OWL}:post_summary_comment` で Verdict を手組みして代替投稿しない。
- Thread Owl は `REQUEST_CHANGES`、resolve、unresolve、merge を提供しない。`request changes` は verdict と blocking comment で表現し、未実装操作を代替経路で送らない。
- `{RAVEN}`（review-raven の logical alias）は、この skill では CI check runs の read（`list_check_runs_for_sha`）だけに使う。PR metadata、diff、review thread、コメント投稿、resolve には使わず、`{OWL}` の read が失敗したときの代替にもしない（実行ユーザーの GitHub token を使う別の認証経路である）。discovery と経路の固定は `references/ci-check.md` の「1. 経路の固定」に従い、`{RAVEN}` の未解決は停止条件にしない。

### CI 判定の不変条件

詳細は `references/ci-check.md` にだけ書く。

- `CI: success` は、`reviewedHeadSha` に対するすべての required checks が成功の場合だけである（required 未定義のときは、報告済みの check run すべて）。required の集合または provider を確定できない場合、取得できない場合、SHA を照合できない場合、`pagination.complete` が `true` でない場合は `CI: unknown` とし、unknown を success としない。
- 根拠は、固定済みの `reviewedHeadSha` を入力とする check runs の read だけである。PR 番号を入力とし `head_sha` を返さない capability（公式 GitHub MCP の `get_check_runs` など）と `combined status` は根拠にしない。
- 取得経路は discovery 時点で固定し、実行時の失敗では切り替えず、`CI: unknown` とする。

## O-00〜O-21: reviewer-side 実行契約

次の表は、操作ごとの契約である。行に書かない項目は、次の既定に従う。

- **tool**: `{OWL}` / `{RAVEN}` は、O-00 で固定した binding と、実行時に記録した input / output schema snapshot の組み合わせを指す。`reviewedHeadSha` は、remote snapshot・CI・投稿位置・inline の `commitId`・APPROVE の `expectedHeadSha` で同一値を使う。
- **side effect**: 行に書かない限り read-only である（PR・レビュー・thread・queue・作業ツリーを変更しない）。
- **fallback**: なし。allowlist 拒否・未接続・schema 不一致・read 失敗を、別 candidate・review-raven・GitHub connector・`gh` の read / write で迂回しない。読み取れない状態を「問題なし」「既存指摘なし」と解釈しない。行に書いた補完経路だけが例外である。
- **停止**: 行の停止コードで停止する（「停止コード」節）。
- **evidence**: 実行した read / write の結果（SHA・ID・件数・状態・失敗分類）を、観測した事実（`observed`）と判断（`inferred`）に分けて記録する。秘密情報は記録しない。

| ID | 操作と tool | 入力 → 出力 | 既定との差分 | 停止コード |
| --- | --- | --- | --- | --- |
| O-00 | queue 起点の待機。queue resource の native read と `resource-bridge-cli` | resource URI・購読 URL・timeout → candidate（`owner`・`repo`・`prNumber`・`reason`・`expected_head`）・route | read と待機だけを行う。re-review は `queue://review/re-review-requests` を使い、route が `subscription` / `pre-completion` であること。`timeout` / `failed` は完了扱いにしない。購読は native subscription が無い場合だけ CLI を使う。手順は `references/queue-wait.md` | `QUEUE_WAIT_FAILED` |
| O-00 | `{OWL}` の discovery と固定（全モード）。手順は `references/discovery.md` | PR URL または queue candidate → `{OWL}` の binding（run の状態に固定） | 候補は capability と schema で判定し、明示 binding を優先、無ければ一意の候補だけを採用する。最小 read を 1 回成功させる。固定後の失敗で、別 candidate・connector・`gh` の write へ切り替えない | `BLOCKED_MCP_DISCOVERY` |
| O-01 | モード選択（外部 tool なし） | PR URL・queue reason・依頼 → mode（`initial-review` / `re-review` / `thread-follow-up` / `summary-only`） | `opened` と通常の `synchronized` は initial、`re-review-requested` は re-review。thread-follow-up は指定 thread がある場合だけ、summary-only は明示された場合だけ。曖昧なとき、表示順・過去の文脈・推測で補完しない | `REVIEW_MODE_UNKNOWN` |
| O-02 | Remote Snapshot の PR metadata。`{OWL}:get_pr` | owner・repo・prNumber → PR identity・base / head SHA・files・`origin`（head SHA を `reviewedHeadSha` に固定） | PR identity・minimum output schema・`pr.head.sha`・base SHA を検証する。branch 名だけをレビュー根拠にしない。allowlist は read にも適用され、拒否や read failure を review-raven・GitHub route・`gh` で迂回しない。全 mode で、O-04 以降（ローカル検証・Independent Stage・投稿）より前に、`origin.allowed` が `true` であることを確認する。`origin` が無い（thread-owl が未対応）、または `true` でない場合は、`reason` を報告して停止し、`gh`・GitHub connector・review-raven で PR を取得して続行しない（許可外の作成者・fork の PR のコードを、ローカルで実行しないため） | `BLOCKED_MCP_READ`、`BLOCKED_PR_ORIGIN`、`REMOTE_SNAPSHOT_READ_FAILED` |
| O-03 | Remote Snapshot の diff / files。`{OWL}:get_pr` の files / patch | PR snapshot → patch と投稿可能位置 | patch が `reviewedHeadSha` の snapshot に属することを確認し、branch 名で再取得しない。O-02 が成功した場合に限り、同じ PR identity と SHA を照合する read-only の connector / `gh` で、巨大 patch を補完できる | `DIFF_SNAPSHOT_INCOMPLETE` |
| O-04 | Repository State Guard。`git status`・`git rev-parse HEAD`・必要な `git fetch origin` / `git worktree add --detach` | worktree・`reviewedHeadSha`・`SQUIRREL_REVIEW_SCRATCH_DIR` → 検証環境（clean・HEAD 一致）の有無と配置先 | 必要な場合だけ一時 worktree / clone を作る（scratch dir があればその配下。不正値は既定パスへフォールバックしない）。tracked file の dirty / mismatch はレビュー根拠にせず、元 worktree を壊さず隔離して検証する。隔離できなければ `local verification: not performed`（未検証を success としない）。片付けはランチャーの責務。手順は `references/local-verification.md` | `REPOSITORY_STATE_UNSAFE` |
| O-05 | Independent Stage の実装・テスト確認。固定した worktree での `git`・`rg`・build・test・static analysis | diff・実装・テスト → 独立した候補（failure path・回帰・security・packaging・テスト不足） | Independent Stage が終わるまで、既存 review comment・thread・summary の本文を文脈へ入れない。確認対象は固定済み SHA に限る。未実施を pass と解釈しない | `LOCAL_VERIFICATION_UNKNOWN` |
| O-06 | Independent Stage の CI。`{OWL}:get_pr` の直後に、固定した経路の check runs read | `reviewedHeadSha` → `CI: success` / `pending` / `failure` / `unknown` と根拠 | 読み取り・応答の検証・判定は `references/ci-check.md` の規則だけに従う。CI の再実行・設定変更はしない。`CI: unknown`（同文書を読めない場合を含む）のまま Verdict / APPROVE を投稿しない | なし（`CI:` の状態として記録する） |
| O-07 | Independent Stage の候補生成（LLM 判断。外部 tool なし） | O-05・O-06 の観測 → 候補ごとの根拠・影響・再現条件・重大度 | 何も投稿しない。既存レビューの結論や言い換えを混ぜず、特定 diff 行または PR-level の根拠を持つ候補だけを作る。独立評価が不足するとき、既存レビュー本文を先に読んで補完しない | `INDEPENDENT_REVIEW_INCOMPLETE` |
| O-08 | Filter Stage の既存 review / thread。`{OWL}:list_review_threads` | 全 review thread・PR conversation → 既存範囲・重複候補・残す候補 | Independent Stage の後に初めて本文を読み、取得結果の全件性と current diff を確認する。PR conversation は `gh api repos/<owner>/<repo>/issues/<prNumber>/comments --paginate` などの read-only 経路で取得する。未回答の同一質問を重複投稿しない。`{RAVEN}` は review thread の read に使わない | `BLOCKED_MCP_READ`、`REVIEW_THREADS_READ_FAILED` |
| O-09 | Synthesis Stage（LLM 判断。外部 tool なし） | 候補と既存範囲 → accept / reject・分類・投稿経路 | 投稿前の draft 判断に限る。重複を落とし、inline は current diff の有効行、横断論点は summary にする。仕様確認は観測事実・判断できない点・期待動作を含む `[question]` とし、既存 question の回答を根拠に再評価する。位置や重大度を推測で補わず、根拠が弱い候補は reject か question にする | `SYNTHESIS_INCOMPLETE` |
| O-10 | 投稿前 Snapshot Guard。`{OWL}:get_pr` と必要な local status read | 固定済み SHA・path / line → current head・投稿可能位置 | current PR head が `reviewedHeadSha` と一致し、path / line が current diff に存在する場合だけ O-11〜O-13 へ進む。inline の `commitId` と APPROVE の `expectedHeadSha` は同じ SHA に固定する。stale head・位置不明・read failure を branch 名や古い snapshot で補完しない | `STALE_REVIEW`、`INVALID_COMMENT_POSITION`、`SNAPSHOT_GUARD_FAILED` |
| O-11 | Initial Review の inline 投稿。`{OWL}:post_inline_comment` | `commitId = reviewedHeadSha`・path・line・body → comment / thread の ID | current diff の一行へ一件投稿する（resolve・APPROVE・merge はしない）。指摘には再現条件・影響・次の行動を、`[question]` には観測事実・判断できない点・期待動作を含める。allowlist・head guard を connector や `gh` の write で迂回しない | `INLINE_POST_FAILED` |
| O-12 | Initial / Re-review の完了サマリー・Verdict。approve は `{OWL}:post_review_verdict`、それ以外は `{OWL}:post_summary_comment` | 観点・CI・残存リスク・投稿件数・current diff 外の指摘・`headSha = reviewedHeadSha` → comment の ID（approve は自由記述だけを `summary` に渡し、`commentId` を記録する） | O-20 の verdict と他の投稿がすべて確定し、O-10 が成功している場合だけ。`review://status` を `reviewed` にする。この run の最後の GitHub write として、どちらか一方を 1 回だけ呼び、`headSha` は省略しない（「レビュー完了サマリー」節）。approve は `references/verdict.md` に従い、投稿前に `summary`、投稿後に `commentId` の本文を検証する。Verdict を `post_summary_comment` や connector で代替せず、検証に失敗したコメントを再投稿しない。summary-only では明示されない投稿をしない | `VERDICT_TOOL_UNAVAILABLE`、`VERDICT_FORMAT_INVALID`、`STALE_REVIEW`、`VERDICT_POST_FAILED`、`SUMMARY_POST_FAILED` |
| O-13 | APPROVE 投稿。`{OWL}:approve_pull_request` | `expectedHeadSha = reviewedHeadSha` → APPROVE review の ID | ユーザーがチャットで明示的に依頼し、Verdict approve・CI success・全 thread resolved・O-10 の current head 一致がそろう場合だけ。実行直前に get_pr と CI を再確認し、`expectedHeadSha`・CI 対象 SHA・current head を一致させる。merge・branch 操作・Issue クローズはしない。connector や `gh` の APPROVE で guard を迂回しない | `APPROVE_BLOCKED` |
| O-14 | Re-review の queue candidate と前回差分。O-00 の queue resource read と `{OWL}:get_pr` | candidate の `reason`・`expected_head` → re-review 対象と `reviewedHeadSha` | queue reason は `re-review-requested` に限り、`expected_head` と current `pr.head.sha` を比較する。PR URL 起点では queue 待機を挿入せず、O-02 の direct snapshot を使う。queue read failure や stale candidate から対象 PR を推測しない | `STALE_REREVIEW_REQUEST` |
| O-15 | Re-review の thread 状態・CI の再確認。`{OWL}:get_pr`・`{OWL}:list_review_threads`・固定した CI read 経路 | 前回 thread・PR conversation・現 head の差分・CI → resolved / outdated / unresolved と残存回帰 | candidate の expected head・current diff・全 thread 状態・CI 対象 SHA を突合し、CI は current head を固定し直して `references/ci-check.md` の手順で再確認する。PR conversation も read-only で取得し、作成者の回答を根拠に再評価する。未回答の同一質問・同内容の返信を繰り返さず、未解決 thread と対応差分が導入した重大回帰だけを次の候補にする | `REREVIEW_STATE_UNKNOWN` |
| O-16 | Re-review の unresolved thread への返信。`{OWL}:reply_review_thread` | threadId・返信本文 → 返信 comment の ID | 元 thread への返信だけを行う（resolve / unresolve・new thread・APPROVE はしない）。残存再現条件を具体化し、作成者の回答を反映する。同内容の返信や未回答の `[question]` を繰り返さず、resolve は reviewed-side に任せる。独立した新論点を混ぜない。connector や `gh` で代替しない | `THREAD_REPLY_FAILED` |
| O-17 | Re-review の current diff 上の新規 inline。`{OWL}:post_inline_comment` | current path / line・`commitId = reviewedHeadSha` → 新規 thread の ID | 元 thread が resolved / outdated で問題が残り、O-10 で current diff に有効な位置がある場合だけ。新しい unresolved thread を一件投稿し、元 thread へ重複返信しない。以前の指摘の継続であることと現 head の具体的な再現条件を書く。位置が無ければ O-18 | `REREVIEW_INLINE_FAILED` |
| O-18 | Re-review / Follow-up の current diff 外の論点。re-review は O-12 の完了サマリーの「current diff 外の指摘」に含める。thread-follow-up は `{OWL}:post_summary_comment` | blocking / 残存条件・影響・再現手順 → PR-level summary の ID | re-review では別の `post_summary_comment` を呼ばない（途中で呼ぶと、reviewed-side の待機がレビュー完了前に終わる）。位置がない理由とマージへの影響を明記し、過去の行番号へ投稿しない。blocking なら Verdict approve を抑止する。無理に inline へ移さない | `REREVIEW_SUMMARY_FAILED` |
| O-19 | Thread Follow-up。`{OWL}:get_pr`・`{OWL}:list_review_threads` と、O-16〜O-18 の適切な write | root comment・全返信・対応差分 → resolved in code / partially resolved / not resolved / needs clarification / declined-by-implementer の判定と投稿結果 | 指定 thread の文脈だけを確認する。必要な場合だけ、返信・新規 inline・summary のいずれかを一件投稿する（resolve / unresolve / merge はしない）。question なら作成者の回答を根拠に再評価し、未回答の既存 question と同内容の返信は投稿しない。unresolved は O-16、current diff に位置があれば O-17、無ければ O-18。独立論点を同じ thread に混ぜない | `THREAD_FOLLOWUP_INCOMPLETE` |
| O-20 | Verdict 判定（LLM 判断。投稿は O-12） | blocking・thread・question・主要リスク・CI・残存リスク → `approve` / `request changes` / `comment only` / `needs follow-up` | 判定基準は「Verdict」節。APPROVE・merge・Issue クローズは自動実行しない。CI・thread・SHA・独立検証のいずれかが unknown なら、approve に寄せず comment only / needs follow-up にする | `VERDICT_INCOMPLETE` |
| O-21 | ユーザー報告・ハンドオフ（外部 tool なし。「ユーザー報告」「ハンドオフ提示」の固定 Markdown を出力する） | O-00〜O-20 の evidence → 固定フォーマットの報告 | 何も write しない。approve / request changes / comment only / needs follow-up / blocked を混同せず、未確認を成功と書かない。必須値が得られない場合は unknown / blocked と明記し、推測で補完しない | `REPORT_EVIDENCE_INCOMPLETE` |

## 停止コード

この表が、停止コードの定義の正本である。停止するときは、`termination_status = <コード>` と `status = blocked` を示し、対象 PR（確定済みの場合）・mode・停止した行 ID・失敗分類・確認できた事実・`writes performed` の件数・再実行に必要な変更を報告する。token・Authorization header・秘密情報は報告しない。以後のコメント・Verdict・APPROVE の write、別 candidate・connector・`gh` の write 経路への切り替えを行わない。これが全コード共通の動作で、表の右列はそれに加える動作である。

| コード | 条件 | 既定に加える動作 |
| --- | --- | --- |
| `BLOCKED_MCP_DISCOVERY` | O-00: `{OWL}` の候補を解決できない、未接続、schema 不一致、read 検証失敗、複数候補を一意に選べない | `writes performed: 0` |
| `BLOCKED_MCP_READ` | O-02 / O-08: allowlist 拒否 | 理由を付して報告する |
| `BLOCKED_PR_ORIGIN` | O-02: `origin` が無い（schema 欠落の中でも、この項目の欠落はこのコードを使う）、または `origin.allowed` が `true` でない | `reason`（`author_not_allowed`・`fork` など）を報告する。`writes performed: 0` |
| `REFERENCE_UNREADABLE` | 「references の索引」の `discovery.md` / `re-review.md` を読めない | 何も投稿せず、読めなかったことを報告する |
| `QUEUE_WAIT_FAILED` | O-00 の queue 待機: timeout・切断・failed route・必須フィールド欠落・JSON 不正・購読 URL 未設定、`queue-wait.md` を読めない | mode・PR read・投稿へ進まない |
| `REVIEW_MODE_UNKNOWN` | O-01: reason・対象 PR・mode の組み合わせを一意に決められない | 本文取得や投稿を行わない |
| `REMOTE_SNAPSHOT_READ_FAILED` | O-02: schema 欠落・read failure | レビュー本文・投稿・APPROVE を行わない |
| `DIFF_SNAPSHOT_INCOMPLETE` | O-03: patch・filename・SHA の対応を検証できない | 位置を推測した投稿をしない |
| `REPOSITORY_STATE_UNSAFE` | O-04: dirty / mismatch を隔離できず、必要な remote evidence も取得できない | |
| `LOCAL_VERIFICATION_UNKNOWN` | O-05: 検証結果を成功・失敗・未実施に分類できない | 根拠が不足する approve を止める |
| `INDEPENDENT_REVIEW_INCOMPLETE` | O-07: 独立評価の根拠・再現条件・影響のいずれかを出力できない | |
| `REVIEW_THREADS_READ_FAILED` | O-08: thread / PR conversation の列挙・schema・接続の失敗 | Filter・投稿・Verdict へ進まない |
| `SYNTHESIS_INCOMPLETE` | O-09: 分類・採否・位置・reject 理由のいずれかが未確定 | 投稿を止める |
| `STALE_REVIEW` | PR head が `reviewedHeadSha` から動いた（O-10、Snapshot Guard の手順 3、O-12 の head 不一致 error） | 該当する write を止める |
| `INVALID_COMMENT_POSITION` | O-10: path / line が current diff に無い | 該当する write を止める |
| `SNAPSHOT_GUARD_FAILED` | O-10: read failure | 該当する write を止める |
| `INLINE_POST_FAILED` | O-11: 投稿の失敗・受理結果不明 | 即時再実行せず、thread を再取得して重複を確認する |
| `VERDICT_TOOL_UNAVAILABLE` | O-12: approve に至ったが、binding に `{OWL}:post_review_verdict` が無い、または schema 不一致 | `post_summary_comment` で代替投稿しない |
| `VERDICT_FORMAT_INVALID` | O-12: 投稿前の `summary` 検証または投稿後の書式検証の不一致、`verdict.md` を読めない | 再投稿しない。マージ可能と報告しない |
| `VERDICT_POST_FAILED` | O-12: Verdict の投稿失敗（head 不一致以外）・結果不明 | 即時再実行しない。マージ可能と報告しない |
| `SUMMARY_POST_FAILED` | O-12: summary の投稿失敗・状態キー欠落 | マージ可能と報告しない |
| `APPROVE_BLOCKED` | O-13: 許可欠如・CI unknown / failure・未解決 thread・SHA 不一致・受理結果不明 | 投稿しない |
| `STALE_REREVIEW_REQUEST` | O-14: candidate の schema 欠落・reason 不一致・expected head 不一致 | 古い差分で投稿・APPROVE しない |
| `REREVIEW_STATE_UNKNOWN` | O-15: thread / PR conversation / CI の状態または SHA を確認できない | 投稿・Verdict・APPROVE を止める |
| `THREAD_REPLY_FAILED` | O-16: 返信の失敗・受理結果不明 | 同じ返信を再実行せず、再取得で重複を確認する |
| `REREVIEW_INLINE_FAILED` | O-17: Snapshot Guard 不一致・位置不正・投稿失敗 | 対応済みと報告しない |
| `REREVIEW_SUMMARY_FAILED` | O-18: summary の投稿失敗・SHA 不一致 | 残存問題を解消済みと扱わない |
| `THREAD_FOLLOWUP_INCOMPLETE` | O-19: thread read・状態判定・選択した write のいずれかが不確実 | |
| `VERDICT_INCOMPLETE` | O-20: 必須 evidence・分類・状態のいずれかが欠ける | Verdict / APPROVE を止める |
| `REPORT_EVIDENCE_INCOMPLETE` | O-21: 報告に必要な evidence が欠ける | merge ready と報告しない |

## モード選択

依頼から次のモードを選ぶ（O-01）。PR URL だけでレビューを依頼された場合は `initial-review` とする。

モードを決めた直後、queue 待機またはレビュー本文の取得に入る前に O-00 を実行する。`{OWL}` の binding と read 検証が成功するまで、Independent Stage、Filter Stage、各種コメント投稿、Verdict、APPROVE へ進まない。PR が明示されず queue 待機を依頼された場合だけ subscription を使い、その手順は `references/queue-wait.md` に従う。

- `initial-review`: PR 全体を初回レビューする。queue candidate の `reason` が `opened` または通常の `synchronized` の場合も使う。
- `re-review`: 前回指摘への対応、未解決 thread、対応後の重大な回帰、CI の変化を確認する。candidate の `reason` が `re-review-requested` の場合はこのモードにする。
- `thread-follow-up`: 指定 thread の文脈、実装者の返信、対応差分だけを確認して返信する。
- `summary-only`: インラインコメントを投稿せず、merge readiness と残存リスクをまとめる。ユーザーが投稿を明示していなければ draft のみ返す。

## Snapshot Guard & Repository State Guard

1. **Remote Snapshot**: レビュー対象は、GitHub から取得した PR HEAD SHA（`reviewedHeadSha`）だけである。現在のローカル作業ツリーをレビュー対象として信頼しない。connector や `gh` で補完する場合も `reviewedHeadSha` を明示し、branch 名だけを指定した読み取りはしない（レビュー中に branch が更新されて内容が変わり得るため）。O-02 の `origin.allowed` が `true` でなければ、以降へ進まない（`BLOCKED_PR_ORIGIN`）。
2. **ローカル検証の開始前**: `git status --porcelain --untracked-files=no` が空で、`git rev-parse HEAD` が `reviewedHeadSha` と一致すること。満たさない worktree をレビュー根拠にせず、未 commit 変更の stash / discard もしない（実装担当の作業状態を破壊しないため）。隔離検証の手順（O-04）は `references/local-verification.md` に従う。
3. **検証後・投稿直前**: 検証環境の `HEAD` が `reviewedHeadSha` のままで tracked file に変更がなく、GitHub 上の PR HEAD も `reviewedHeadSha` のままであることを再確認する。PR HEAD が動いた場合、または検証処理が tracked file を書き換えた・HEAD を意図せず動かした場合は、stale review として投稿（inline comment や APPROVE）を止める。生成物などの untracked file は許容する。
4. **CI の SHA 固定**: CI 判定の直前に `{OWL}:get_pr` で現在の PR HEAD を `reviewedHeadSha` として固定し、`references/ci-check.md` の規則（結果の採用・APPROVE の直前の再確認を含む）で判定する。verdict の根拠にした CI の対象 SHA を確認・記録する。
5. **再レビュー依頼の期待 HEAD**: candidate に `expected_head` がある場合は、開始時に `get_pr(...).pr.head.sha` と比較する。不一致なら古い依頼とみなし、APPROVE せず、最新の HEAD を新しい対象としてやり直すか、停止する（O-14）。
6. **投稿位置**: inline の `path` と `line` が current diff 上の投稿可能な位置であることを確認し、確実でなければ PR-level summary にする（O-10）。

## Initial Review

初回レビューは次の順序を守る。Independent Stage が終わるまで、既存 review comment・review thread・review summary の本文を読まない。

### 1. Independent Stage

1. PR の title、description、base/head、head SHA（O-02）と、diff・変更ファイル・関連実装・テスト差分（O-03）を読む。
2. CI を Snapshot Guard の手順 4 で確認する（O-06）。failed/skipped checks、packaging、docs、release への影響も確認する。
3. 既存レビューを参照せず、独立した懸念候補を作る（O-07）。
4. 次の非主要パスを横断確認する。
   - 空、null、不正値、境界値、巨大入力、重複入力
   - 初回実行、再実行、二重実行、キャンセル、部分成功、失敗後リトライ
   - timeout、fallback、例外変換、権限不足、secret 欠落、token 失効
   - 既存設定、既存データ、旧バージョン、migration、後方互換性
   - Windows / Linux / macOS、local / CI、開発 / 配布環境の差
   - UI / domain / infrastructure / persistence / CLI / CI の責務境界
   - エラーメッセージ、ログ、通知、復旧導線
5. テストが実装詳細ではなく、PR が壊してはならない仕様を固定しているか確認する。

この段階では候補を投稿しない。

### 2. Filter Stage

`{OWL}:list_review_threads` と必要な GitHub 読み取り経路で、既存 review・thread・実装者返信を初めて読む。既存レビューが扱った行・条件・リスク種別・edge case・修正方針を整理し、Independent Stage の候補を次の基準で絞る。

- 削除する: 同じ条件・結論・修正方針を繰り返すもの。新しい再現条件や影響範囲を加えないもの。resolved、outdated、または現 head で対応済みのもの。同意、言い換え、根拠の弱い追従。
- 残す: 未指摘の failure path・edge case・integration point。より具体的な再現条件・影響範囲・テスト観点を示せるもの。同じファイルでも別責務・別経路・別ユースケースの問題。マージ後に発覚すると手戻りが大きい問題。

既存レビューはレビュー範囲の上限ではなく、重複投稿を防ぐマスクとして扱う。

### 3. Synthesis Stage

各候補について、根拠、重大度、投稿位置、対応可能性を確認する。

1. 「コメント分類」の 5 種に分類する。
2. 特定 diff 行に直接対応する指摘・質問だけ inline にする。複数ファイルにまたがる設計、運用、CI、packaging、release の問題・質問と current diff 外の質問は PR-level summary にする（「レビュー完了サマリー」節の 1 件にまとめる）。
3. 再現条件、影響、期待する次の行動を短く書く。根拠が弱い、差分価値が薄い、対応方法が不明、コメント過多を招く候補は削除する。
4. Snapshot Guard（O-10）を再確認してから投稿する。

## コメント分類

- `blocking`: correctness、security、privacy、data loss、主要ユースケース、CI、packaging、release の明確な問題。
- `non-blocking`: merge を止めない保守性、テスト、UX、DX 改善。後続対応可能であることを明記する。
- `question`: PR の挙動・仕様意図や既存仕様を確認しないと断定できない論点。`AskUserQuestion` では尋ねず、対象 PR に `[question]` として投稿する。観測した事実、判断できない点、作成者に確認する期待動作を分けて書き、推測を事実として断定しない。
- `note`: docs、release note、follow-up issue で追う価値がある論点。
- `praise`: 回帰リスク低減、責務分離、テスト容易性など明確な価値がある判断。過剰に投稿しない。

投稿本文は簡潔にする。

```markdown
[blocking] XXX の条件では YYY となり、ZZZ が失敗します。
AAA のケースをテストで固定し、BBB の処理を見直してください。
```

```markdown
[question] 現在の差分では AAA の分岐に BBB が含まれています。既存仕様では CCC と読め、AAA でも BBB を適用する意図か判断できません。AAA の場合に期待する動作を確認したいです。
```

## 投稿判断

PR URL を示してレビューと投稿を依頼された場合、根拠が固い inline comment と通常の review comment、および仕様意図の `[question]` は投稿まで行う。内容の曖昧さを PR 作成者に確認できる場合は `[question]` にする。回答待ちでレビュー実行を止めず、独立して確認できる範囲を進めて既定の完了通知を行う。次の条件は内容質問で解決できないため、投稿前にユーザーへ確認するか、停止コードで報告する。

- ユーザーの承認を要する release / operation などの操作
- 既存コメントを取得できず、重複を判定できない
- コメント候補が 5 件を超える
- 投稿対象 PR、mode、Thread Owl binding、reviewed HEAD を確定できない、または投稿先の line / thread を安全に特定できない（停止コードで報告し、推測で投稿しない）
- `summary-only` の summary 投稿を明示されていない

### レビュー完了サマリー

`initial-review` / `re-review` は、verdict にかかわらず最後の GitHub write として完了通知 write を**ちょうど 1 回**呼ぶ。完了通知 write とは `{OWL}:post_summary_comment` と `{OWL}:post_review_verdict` の呼び出しの合計であり、run 全体でこの合計が 1 回になる（approve で両方を呼ぶと 2 回になるので違反する）。thread-owl の `review://status/{owner}/{repo}/{prNumber}` が `reviewed` になるのはこの 2 つ（または `approve_pull_request`）を呼んだときだけで、inline の投稿では変わらない。呼ばずに終えると、reviewed-side の待機（`review-raven-thread-owl-cycle` の Phase W）は完了を検知できずタイムアウトする。

- `headSha` には `reviewedHeadSha` を渡す。
- 途中で呼ばない。current diff 外の指摘・質問や、複数ファイルにまたがる論点（Synthesis Stage の手順 2、O-18）も、別の summary にせずこの 1 件にまとめる。
- `verdict: approve` の場合は、次節の `{OWL}:post_review_verdict` がこの 1 回になる。`{OWL}:post_summary_comment` は呼ばない。
- それ以外（`request changes` / `comment only` / `needs follow-up`）は `{OWL}:post_summary_comment` で次の書式で投稿する。見出しに `Review Verdict` を含めない（reviewed-side が Verdict 候補として照合し、書式不一致と報告するため）。
- `thread-follow-up` / `summary-only` はこの節の対象外とする。

```markdown
## @thread-owl Review Result: CHANGES_REQUESTED | COMMENT_ONLY | NEEDS_FOLLOW_UP

（判定の要約）

### 投稿した指摘
- 新規 inline: N 件（blocking N 件）
- thread 返信: N 件

### current diff 外の指摘
- なし | [blocking] …（再現条件・影響・期待する次の行動）

---
- Reviewed HEAD SHA: `<reviewedHeadSha>`
```

### Verdict コメント投稿

Verdict コメントは `verdict: approve` のときだけ投稿する（判定基準は「Verdict」節）。`{OWL}:approve_pull_request` は呼ばない（GitHub native の APPROVE を自律実行しない）。投稿は `{OWL}:post_review_verdict` で行い、固定の 3 行（見出し・HEAD 行・Status 行）は tool が組み立てるので、skill 側では書かない。投稿の手順、`summary` の書き方、投稿前後の検証は、`references/verdict.md` を必ず読み、その規則に従う。読めない場合は、投稿前の検証ができないため Verdict を投稿せず、`VERDICT_FORMAT_INVALID` として停止する。

<!-- verdict-match-rule:begin -->
### Verdict 照合規則

reviewer-side の投稿前後の検証と reviewed-side のマージゲートは、この規則だけで Verdict コメントを照合する。この節は `thread-owl-pr-reviewer` と `review-raven-thread-owl-cycle` に同じ内容で置く。正本は `thread-owl-pr-reviewer` で、変更するときは両方を同時に更新する（Mcp-Docker の `go test ./...` が一致を検証する）。

1. 本文を `\n` で行に分割し、各行の末尾にある `\r` を 1 個だけ除去する。前後空白の trim、大文字小文字の同一視、Unicode 正規化は行わない。
2. 次の 3 つの正規表現（RE2 構文）を、それぞれ行全体に対して照合する。

   ```text
   ^## @thread-owl Review Verdict: APPROVED$
   ^- Reviewed HEAD SHA: `([0-9a-f]{40})`$
   ^- Status: `READY_TO_MERGE`$
   ```

3. 3 つの正規表現それぞれに一致する行が**ちょうど 1 行ずつ**あり、見出し行が他の 2 行より前にある場合だけ「書式一致」とする。バッククォートの省略、行頭 `- ` の省略、余分な空白、別の文言（`Review Verdict: READY_TO_MERGE`、`Reviewed HEAD:`、`判定:` など）はすべて不一致とする。
4. 書式一致の場合だけ、HEAD 行のキャプチャ（40 桁の小文字 hex）を照合対象の SHA と文字列全体で比較する。
5. 本文に部分文字列 `Review Verdict` を含むコメントを「Verdict 候補」と呼ぶ。Verdict 候補のうち手順 3 を満たさないものは「書式不一致」、手順 3 を満たすが手順 4 で一致しないものは「SHA 不一致」として区別する。
<!-- verdict-match-rule:end -->

### APPROVE 投稿とマージ判断について

`{OWL}:approve_pull_request` は、ユーザーがチャットで明示的に依頼した場合だけ実行する（O-13）。自動マージや自動デプロイがトリガーされるリスクがあるため、明示的な許可がない限り、自律的に `APPROVE` を送信してはならない。マージ処理自体は別ワークフローの責務であり、この skill では行わない。レビューの要約やコメントでは、「技術的・品質的にマージ可能な状態である（マージ推奨）」という評価を日本語で明確に報告する。

## Re-review

`re-review`（queue の `reason = re-review-requested` を含む）は、`references/re-review.md` の「Re-review」を必ず読み、その規則に従う。読めない場合は、投稿経路を推測せず、inline 投稿も thread 返信も行わずに `REFERENCE_UNREADABLE` として停止する。

## Thread Follow-up

`thread-follow-up` は、`references/re-review.md` の「Thread Follow-up」を必ず読み、その規則に従う。読めない場合は、何も投稿せず `REFERENCE_UNREADABLE` として停止する。

## Verdict

- `approve`: 新規 `blocking` 指摘と未回答の `[question]` がなく、既存 review thread がすべて resolved であり（分類を問わない。`non-blocking` / `question` の未解決も許容しない）、主要リスクのテストまたは説明があり、CI が成功し、CI の対象 SHA が `reviewedHeadSha` と一致している。「技術的・品質的にマージ可能な状態である（マージ推奨）」という判断結果であり、ユーザーへの報告で明記する。実装者が明示的な理由（Won't fix、スコープ外、仕様意図など）をもって resolve した指摘（`declined-by-implementer`）は新規 blocking とみなさず、残存リスクを完了サマリー（および Verdict の summary）に明記した上で `approve` を妨げない。`initial-review` / `re-review` でこの判定に至った場合は「Verdict コメント投稿」節に従って Verdict コメントを投稿する。明示的な許可（指示）がない限り、実際の `APPROVE` 投稿は行わない。
- `request changes`: blocking が残る。Thread Owl に REQUEST_CHANGES tool はないため、blocking comment と verdict の報告、および「レビュー完了サマリー」の投稿に留める。
- `comment only`: 判断材料が不足し、question が中心。question が未回答の間は、approve にせず `comment only` / `needs follow-up` の区別を維持する。
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
- posted: 新規inline N 件、thread 返信 N 件、summary N 件、verdict N 件、approve N 件
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
