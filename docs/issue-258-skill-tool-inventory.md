---
issue: 258
repository: scottlz0310/Mcp-Docker
document_type: skill-tool-inventory
schema_version: 2
status: run-2
latest_run: 2026-09-10-claude-code-opus5
snapshot_at: 2026-09-10
repo_commit: 37c9eb9c4aadebd1e2cc9f7b56848568ab3213b9
scope:
  - skills/review-raven-thread-owl-cycle/SKILL.md
  - skills/thread-owl-pr-reviewer/SKILL.md
skill_revisions:
  review-raven-thread-owl-cycle: 3
  thread-owl-pr-reviewer: 1
redesign_targets:
  - skill execution contract
  - review-raven MCP
  - thread-owl MCP
  - mcp-resource-subscriber CLI
  - MCP client / gateway integration
---

# #258 skill のツール棚卸し

## 結論

この環境での推奨経路は次のとおりです。

- 投稿者ゲートの本文なし取得は、MCP の機能不足ではなく射影不足であり B。review-raven#124 の対象として切り出す。
- CI の確認は、GitHub MCP で代替できるが、現状は SHA 固定・run/job/log の複数取得になる。実運用で gh を選んだ理由は往復コストであり C。
- レビュー thread の取得・返信・resolve、Thread Owl のコメント投稿は対応する MCP がすでにある。gh を使った記録がある箇所は、機能不足ではなく運用上の C または理由未確認の D として再検証する。
- ローカルの編集・テスト・Git・Docker 設定確認は MCP へ寄せる対象ではなく A。CLI を使うことが正しい。
- queue の購読待機は Thread Owl の責務ではない。現環境では queue resource は存在するが native subscriptions/listen が利用可能なツール一覧にないため、mcp-resource-subscriber CLI を使う A。

本書は skill 本体や各サーバーを直接実装せず、現在の手順を固定 ID 付きの表に分解した調査記録である。加えて、別モデル・別クライアントでも同じ skill を遂行できるように、実装へ引き渡せる横断契約と受入れ条件を定義する。

## 再調査の方法

同じ調査を別モデルで繰り返す場合は、この文書を上書きせず、末尾に Run 2 以降を追記する。

1. 対象 commit、skill revision、MCP の実ツール名、実行モデルを Run 欄へ記録する。
2. R-xx / O-xx の行 ID を変えず、実際に呼んだ CLI・MCP と観測区分を更新する。
3. 実行したものは observed、手順から再現したものは simulated、推測を含むものは inferred と明記する。
4. 使わなかった理由は A〜D のうち主分類を 1 つ選ぶ。該当しないポリシー判断は not applicable とする。
5. CLI の完全な実行ログがない場合、コマンドを断定せず、Issue・PR timeline・skill 本文のどの記録に基づくかを書く。
6. API 応答を本文まで取得する手順では、投稿者ゲートを先に実行したかを必ず記録する。

### 分類

| 分類 | 意味 |
|---|---|
| A | MCP 側に該当機能がない。ローカル shell、Git、ビルド、テスト、購読 bridge など |
| B | MCP に機能はあるが、必要な射影・入力・出力・組み合わせができない |
| C | MCP で実行できるが、複数往復または複数ツールになるため gh の一括実行を選んだ |
| D | MCP で実行できるのに、選択理由が証跡から確認できない。習慣として扱い、次回に確認する |
| not applicable | 判断だけ、明示承認待ち、または skill の非目標で A〜D の比較対象ではない |

## Run 1

| 項目 | 値 |
|---|---|
| run_id | 2026-09-10-codex-gpt5 |
| 実行モデル | GPT-5 / Codex |
| 実行環境 | Windows、PowerShell、Asia/Tokyo |
| リポジトリ | scottlz0310/Mcp-Docker、main の v2.20.0 後、commit 37c9eb9 |
| 対象 skill | review-raven-thread-owl-cycle rev 3、thread-owl-pr-reviewer rev 1 |
| 実運用の観測範囲 | #248、#253、#255、#256、#257。Issue #258 の記載を主証跡とする |
| MCP の確認 | Thread Owl / review-raven / GitHub connector の read-only call、resource discovery |
| サーバー / CLI snapshot | review-raven: go.mod の go-sdk v1.7.0、thread-owl: v0.4.1 / MCP SDK v2.0.0、mcp-resource-subscriber: v0.6.1 / protocol `2026-07-28` |
| 制約 | GitHub の PR timeline は結果を残すが、過去の shell の完全な実行コマンドは保持しない |

## 観測対象

| PR | HEAD SHA | timeline から確認できたこと | 調査上の用途 |
|---|---|---|---|
| [#248](https://github.com/scottlz0310/Mcp-Docker/pull/248) | 48788778d3f8e01cf2eb223787939f0fffbd7e74 | Codecov と thread-owl Verdict | 初回レビュー後に blocking がない経路 |
| [#253](https://github.com/scottlz0310/Mcp-Docker/pull/253) | f84e44378c764c7991351f6fb7a069564884f63d | Codecov と thread-owl Verdict | skill カタログ変更の経路 |
| [#255](https://github.com/scottlz0310/Mcp-Docker/pull/255) | b4239c93ccd996cc034592da7cf8e4b8db019d8a | thread-owl の blocking inline、実装者返信、再レビュー依頼、Verdict、対応サマリ | 1 回の再レビューを含む代表ケース |
| [#256](https://github.com/scottlz0310/Mcp-Docker/pull/256) | 80f0bbda66de1e971bd68bd12d0506846b2b9057 | thread-owl Verdict、Codecov、対応サマリ | 対応なし・サマリのみの経路 |
| [#257](https://github.com/scottlz0310/Mcp-Docker/pull/257) | 4a5871d33f7c16a404fe56a16295b5c77f1993f7 | Codecov、thread-owl Verdict、対応サマリ | リリース PR の最終ゲート |

PR #255 の issue timeline は GitHub connector の github_fetch_issue_comments でも 4 件を返し、#257 の同一 HEAD に対する workflow run は 4 件を返した。一方、combined status は空配列だった。この差から、CI は 1 つの status API だけでなく workflow run と job の追跡が必要になる。

## この環境の実ツール名

skill 本文の {GH} / {RAVEN} / {OWL} は論理名である。今回の実行環境では次の名前に解決された。

| 論理名 | 実ツール | 棚卸しで使う主な操作・代表引数 |
|---|---|---|
| {GH} | mcp__codex_apps__github_* | PR/Issue コメント、Issue、PR metadata、レビュー、CI。repository_full_name と pr_number |
| {RAVEN} | mcp__review_raven__* | reviewed-side の thread 取得、返信、resolve。owner / repo / pr、threadId |
| {OWL} | mcp__thread_owl__* | queue 登録、reviewer-side の PR/thread 読み取り、コメント投稿。owner / repo / prNumber |
| queue bridge | mcp-resource-subscriber CLI | resources/subscribe、通知待機、resources/read、JSON 化。MCP URL / resource URI |

今回確認した Thread Owl resource は queue://review/queue と queue://review/re-review-requests である。native subscriptions/listen はこの環境の利用可能ツール一覧には現れなかったため、queue を読む処理は mcp-resource-subscriber を選ぶ。

行列中の github_*、review_raven_*、thread_owl_* は、上表の実ツール名から共通 prefix を省略した表記である。Run では、実際に呼んだ完全な tool name と引数を記録する。

### Run 1 の完全な tool registry

次の一覧は「利用可能だった tool」と「各行での第一候補」を区別するための registry である。別クライアントでは namespace が変わり得るため、再調査時は同じ論理名に解決できたかを記録する。

| 論理対象 | 完全な tool / command | 対象行 | read / write |
|---|---|---|---|
| GitHub review threads | `mcp__codex_apps__github_list_pull_request_review_threads` | R-01 / R-03 / R-12 / O-08 | read |
| GitHub reviews | `mcp__codex_apps__github_list_pull_request_reviews` | R-01 / R-04 / R-12 / O-08 | read |
| GitHub issue comments | `mcp__codex_apps__github_fetch_issue_comments` | R-01 / R-05 / R-17 / R-18 | read |
| GitHub PR timeline | `mcp__codex_apps__github_fetch_pr_comments` | R-02 / R-05 / R-12 | read |
| GitHub PR metadata | `mcp__codex_apps__github_get_pr_info` | R-02 / R-08b / R-18b / O-02 | read |
| GitHub CI runs/jobs/logs | `mcp__codex_apps__github_fetch_commit_workflow_runs`、`mcp__codex_apps__github_fetch_workflow_run_jobs`、`mcp__codex_apps__github_fetch_workflow_job_logs` | R-16 / O-06 | read |
| GitHub comment | `mcp__codex_apps__github_add_comment_to_issue` | R-10 / R-14 / R-19 | write |
| GitHub follow-up Issue | `mcp__codex_apps__github_create_issue` | R-11 | write |
| reviewed-side thread | `mcp__review_raven__get_review_threads` | R-03 / R-12 | read |
| reviewed-side reply | `mcp__review_raven__reply_to_review_thread` | R-09 | write |
| reviewed-side resolve | `mcp__review_raven__resolve_review_thread` | R-09 | write |
| reviewed-side reply + resolve | `mcp__review_raven__reply_and_resolve_review_thread` | R-09 | write |
| reviewer-side PR snapshot | `mcp__thread_owl__get_pr` | O-02 / O-03 / O-10 / O-14 / O-15 | read |
| reviewer-side threads | `mcp__thread_owl__list_review_threads` | O-08 / O-15 / O-19 | read |
| reviewer-side inline | `mcp__thread_owl__post_inline_comment` | O-11 / O-17 | write |
| reviewer-side summary | `mcp__thread_owl__post_summary_comment` | O-12 / O-18 / O-20 | write |
| reviewer-side reply | `mcp__thread_owl__reply_review_thread` | O-16 / O-19 | write |
| reviewer-side approve | `mcp__thread_owl__approve_pull_request` | O-13 | write（明示承認後のみ） |
| review queue enqueue | `mcp__thread_owl__enqueue_review` | R-15 | write |
| queue subscribe/read | `mcp-resource-subscriber --url <url> --uri <resource-uri> --timeout-ms <ms> --json` | O-00 / O-14 | read / wait |
| generic MCP call | `mcp-resource-subscriber call --url <url> --tool <name> --args <json> --json` | 将来の CLI fallback | tool 依存 |

## review-raven-thread-owl-cycle の棚卸し

| ID / 箇所 | 実際に使った CLI・操作 | 対応する MCP ツール | 使わなかった理由 / 分類 | 寄せられるか・推奨 |
|---|---|---|---|---|
| R-00 セットアップ | MCP server/tool discovery。CLI 操作なし。 | mcp__codex_apps__github_*、mcp__review_raven__*、mcp__thread_owl__* | not applicable | 開始時に 3 server の実名と利用可否を固定する。未ロードなら discovery する。 |
| R-01 必須コメント投稿者ゲート | observed（#258 / review-raven#124）: gh api graphql で body を選ばない reviewThreads query、gh api .../pulls/{pr}/reviews --paginate --jq、gh api .../issues/{pr}/comments --paginate --jq。 | github_list_pull_request_review_threads、github_list_pull_request_reviews、github_fetch_issue_comments、github_fetch_pr_comments は本文を含む。review_raven get_review_threads も本文を含む。 | B。本文を含めない射影がない。本文を先に取得してから LLM 側で捨てる方法はゲートを満たさない。 | そのままでは寄せられない。review-raven#124 の include_bodies:false または metadata 専用 tool が必要。 |
| R-02 Phase 0: owner/repo/pr と状態復元 | simulated: gh api .../issues/{pr}/comments --paginate で最新のサイクル状態を読む。gh pr view {pr} --json headRefOid --jq .headRefOid で HEAD を読む。 | github_fetch_issue_comments、github_get_pr_info、thread_owl get_pr | C。MCP でも読めるが、既存の gh 呼び出し群に一括しやすい。 | full body の復元は github_fetch_issue_comments、HEAD は get_pr_info を推奨。R-01 は別の B のまま。 |
| R-03 Phase U2: inline thread 取得 | observed/simulated: gh api graphql の reviewThreads query。 | review_raven get_review_threads | C。Issue の実運用では複数操作を gh にまとめた。 | 寄せられる。thread ID、resolved、本文を返す review-raven MCP を第一選択にする。 |
| R-04 Phase U2: review body 取得 | observed/simulated: gh api .../pulls/{pr}/reviews --paginate --jq。 | github_list_pull_request_reviews。必要なら github_fetch_pr_comments で timeline を取得。 | C。MCP は取得できるが、CLI の paginate と jq を 1 回にまとめた。 | 寄せられる。本文取得は R-01 通過後に限る。 |
| R-05 Phase U2: PR issue comment 取得 | observed/simulated: gh api .../issues/{pr}/comments --paginate --jq。 | github_fetch_issue_comments（全ページ）、github_fetch_pr_comments | C。MCP は取得できるが、既存の CLI projection と一括実行が速い。 | 寄せられる。#255 で 4 件を返すことを実測済み。 |
| R-06 Phase 3: 分類・採否 | LLM の判断と Phase 3 テーブル作成。外部操作なし。 | なし | not applicable | ツール移行対象ではない。reject が out-of-scope / deferred の場合は Issue 作成まで含めて判断する。 |
| R-07 Phase 4: 編集・build/test・commit | git status、ローカル編集、リポジトリの build/test、git commit。 | なし。GitHub の create_commit はローカル worktree の代替ではない。 | A。MCP の責務外。 | CLI / ローカル実行を維持する。未 commit の状態を隠さない。 |
| R-08a Phase 4: push/fetch/state | git status、git push、git fetch origin、git rev-parse HEAD。 | なし。 | A。ローカル repository state を操作する MCP がない。 | CLI を使う。stash/discard による実装者状態の破壊は行わない。 |
| R-08b Phase 4: remote HEAD 同期 | observed/simulated: gh pr view {pr} --json headRefOid --jq .headRefOid。 | github_get_pr_info、thread_owl get_pr | C。単独なら MCP へ寄せやすいが、同期ゲートの CLI 群へまとめられた。 | 寄せられる。ローカル HEAD と MCP の pr.head.sha を比較する。 |
| R-09 Phase U5: inline 返信＋resolve | fallback path: gh の REST reply と gh api graphql mutation。 | review_raven reply_and_resolve_review_thread、reply_to_review_thread、resolve_review_thread | C。MCP に一回で実行できる複合 tool がある。 | 寄せる。reply 成功前に resolve しない契約も MCP 側で扱う。 |
| R-10 Phase U5: review body / issue comment への返信 | observed/simulated: gh pr comment または gh api .../issues/{pr}/comments。#255 の再レビュー依頼・対応サマリは実装者 identity で残る。 | github_add_comment_to_issue | C。PR comment を他の gh 操作と同一 shell にまとめた。経路の完全な command log はない。 | 寄せられる。投稿 identity の差を記録し、本文取得は次のゲート後に行う。 |
| R-11 Phase U5: follow-up Issue | 今回の 5 PR では未発生。skill の fallback は gh issue create 相当。 | github_create_issue | not applicable（未発生） | 寄せられる。Issue URL/番号を返信・Phase 3・Phase 7 に記録する。 |
| R-12 Phase U6: 再取得 | R-01、R-03〜R-05 を再実行。 | 同じ MCP 群 | B（投稿者 metadata）＋ C（本文取得）。ゲートを省略してはいけない。 | R-01 は review-raven#124 解決まで残る。その他は MCP を第一選択にする。 |
| R-13 Phase U6: Thread Owl 起動モード判定 | docker compose config または docker-compose.yml の thread-owl command を確認。現 repo は command: [--mcp-http]。 | なし | A。ローカル Compose 設定の確認。 | CLI / ファイル確認を維持する。queue の観測結果から推測しない。 |
| R-14 Phase U6: 再レビュー依頼コメント | observed/simulated: gh pr comment {pr} --body、本文は @thread-owl re-review requested とサイクル状態。 | github_add_comment_to_issue | C。コメント投稿を既存 gh 操作にまとめた。明確な速度証跡がない場合は次回 D 候補。 | 寄せられる。{GH} を使い、本文の固定見出し・4 状態キーを守る。 |
| R-15 Phase U6: queue 登録 | observed: 関連運用では thread-owl enqueue_review を使用。CLI の queue 登録はない。 | thread_owl enqueue_review | not applicable。MCP 専用契約で、gh fallback は存在しない。 | {OWL}:enqueue_review を使う。--mcp-http は必須、--webhook-mcp-http は二重登録防止のため呼ばない。 |
| R-16 Phase 6.5: CI と失敗ログ | observed/simulated: gh pr checks {pr}、失敗時 gh run view {run-id} --log-failed。 | github_get_commit_combined_status、github_fetch_commit_workflow_runs、github_fetch_workflow_run_jobs、github_fetch_workflow_job_logs | C。MCP では SHA → run → job → log の複数往復になる。combined status だけでは #257 のように空になり得る。 | 条件付きで寄せられる。required checks、対象 SHA、skipped/failed をまとめて返す MCP が将来の改善候補。 |
| R-17 Phase 6.6: Codecov | observed: PR issue comment に Codecov report。CLI では gh api .../issues/{pr}/comments --paginate が取得経路。 | github_fetch_issue_comments | C。本文を含む comment collection は MCP で取得できるが、既存のコメント取得へまとめた。 | 寄せられる。Codecov 専用 tool は不要で、信頼済み投稿者ゲート後に comment を読む。 |
| R-18a Phase 7: Verdict 投稿者 metadata | observed/simulated: gh api .../issues/{pr}/comments --paginate --jq で author.login 等だけを取得。 | github_fetch_issue_comments は本文を含む。 | B。R-01 と同じ本文なし射影不足。 | review-raven#124 または GitHub connector の metadata projection が必要。 |
| R-18b Phase 7: Verdict 本文・Status・SHA | gh api .../issues/{pr}/comments --paginate、gh pr view {pr} --json headRefOid。 | github_fetch_issue_comments、github_get_pr_info / thread_owl get_pr | C（全文取得・SHA照合）。metadata 部分は B。 | R-18a 通過後は MCP へ寄せられる。thread-owl login、見出し、Status、HEAD SHA をすべて検証する。 |
| R-19 Phase 7: サマリ投稿 | observed/simulated: gh pr comment {pr} --body。#255〜#257 に対応サマリが残る。 | github_add_comment_to_issue | C。既存の gh comment flow にまとめた。 | 寄せられる。サイクル状態ブロックを同じ本文に含める。 |
| R-20 Phase 8: merge | skill は自律 merge を禁止。gh pr merge は #258 の観測にあるが skill の実行手順ではない。 | github_merge_pull_request は存在するが本 skill では呼ばない。 | not applicable。明示承認待ちで、#258 の対象外。 | merge は人の明示操作へ委ねる。 |
| R-21 ユーザー報告 | Markdown テキストを出力。外部操作なし。 | なし | not applicable | 固定フォーマットで termination_status、Verdict、SHA、残存リスクを報告する。 |

## thread-owl-pr-reviewer の棚卸し

| ID / 箇所 | 実際に使った CLI・操作 | 対応する MCP ツール | 未使用理由 / 分類 | 寄せられるか・推奨 |
|---|---|---|---|---|
| O-00 queue 起点の待機 | skill 記載の bunx mcp-resource-subscriber --url $env:THREAD_OWL_MCP_URL --uri queue://review/re-review-requests --timeout-ms 900000 --json。 | queue resource は存在するが、native subscriptions/listen は今回の tool set にない。 | A。subscribe する側は mcp-resource-subscriber の責務。 | CLI bridge を使う。route が subscription または pre-completion であることを確認し、timeout/failed は完了扱いにしない。 |
| O-01 モード選択 | PR URL、queue reason、依頼文の読み取り。外部操作なし。 | なし | not applicable | opened/synchronized は initial-review、re-review-requested は re-review とする。 |
| O-02 Remote Snapshot: PR metadata | observed/simulated: gh pr view {pr} --json title,body,baseRefName,headRefName,headRefOid。 | thread_owl get_pr（pr と files、head/base SHA、patch を返す）、github_get_pr_info | C。実運用では CLI の metadata 取得を他の CLI とまとめた。 | 寄せる。Thread Owl get_pr を第一候補にし、reviewedHeadSha を固定する。 |
| O-03 Remote Snapshot: diff/files | simulated: gh pr diff {pr} または gh api の changed files。 | thread_owl get_pr、github_get_pr_diff、github_list_pr_changed_filenames、github_fetch_pr_file_patch | C。MCP は取得できるが、必要な patch の量に応じた複数 call になる。 | 寄せる。まず get_pr、巨大差分だけ GitHub connector で補う。 |
| O-04 Repository State Guard | git status --porcelain --untracked-files=no、git rev-parse HEAD、必要なら git fetch origin と git worktree add --detach。 | なし | A。ローカル worktree の責務。 | CLI を使う。dirty/mismatched なら作業ツリーを破壊せず隔離 worktree を使う。 |
| O-05 Independent Stage: 実装・テスト確認 | git/rg によるローカル参照、build/test/static analysis。 | Remote 部分は thread_owl get_pr、ローカル部分はなし。 | A（ローカル確認）。 | ローカル検証は reviewedHeadSha 固定の隔離環境で行う。 |
| O-06 Independent Stage: CI | observed/simulated: gh pr checks、失敗時 gh run view --log-failed。 | github_get_commit_combined_status、github_fetch_commit_workflow_runs、github_fetch_workflow_run_jobs、github_fetch_workflow_job_logs | C。MCP で可能だが、run/job/log の複数往復になる。 | 条件付きで寄せる。CI の対象 SHA を必ず記録し、unknown を success にしない。 |
| O-07 Independent Stage: 候補生成 | LLM の独立評価。投稿なし。 | なし | not applicable | 既存レビュー本文を Independent Stage の終了まで読まない。 |
| O-08 Filter Stage: 既存 review/thread | observed/simulated: gh の PR timeline/GraphQL、または Thread Owl の読み取り。 | thread_owl list_review_threads、github_list_pull_request_review_threads、github_list_pull_request_reviews | C。既存の CLI 読み取りを他の取得とまとめた場合。 | Thread Owl list_review_threads を第一選択にする。review 内容を読んだ後に重複候補を落とす。 |
| O-09 Synthesis Stage | LLM の分類、投稿位置、再現条件の判断。 | なし | not applicable | inline は diff 行に直接対応するものだけ、横断論点は summary にする。 |
| O-10 投稿前 Snapshot Guard | thread_owl get_pr、必要なら git status と remote HEAD 再確認。 | thread_owl get_pr | not applicable | post_inline_comment の commitId と approve の expectedHeadSha に同じ reviewedHeadSha を使う。 |
| O-11 Initial Review: inline | 5 PR の公開 timeline では thread-owl のレビュー投稿を確認できるが、投稿コマンド自体は記録されない。 | thread_owl post_inline_comment | not applicable。Thread Owl の第一選択がそのまま適切。 | 寄せる。GitHub connector の add_review_to_pr は存在するが、Thread Owl の allowlist・契約を迂回しない。 |
| O-12 Initial/Re-review: summary/Verdict | observed: thread-owl[bot] の Verdict コメント。 | thread_owl post_summary_comment | not applicable | 寄せる。initial-review/re-review の approve 時だけ固定見出し、Reviewed HEAD SHA、Status を投稿する。 |
| O-13 APPROVE | 今回は自律 APPROVE を実行しない。 | thread_owl approve_pull_request。GitHub add_review_to_pr の APPROVE も存在する。 | not applicable。ユーザーの明示指示が必要。 | 明示指示後にのみ Thread Owl tool を使い、直前に get_pr と CI SHA を再確認する。 |
| O-14 Re-review: queue candidate と前回差分 | O-00 の subscriber 出力を JSON として読む。PR URL 起点なら queue 待機なし。 | queue resource、thread_owl get_pr | A（購読）＋ not applicable（JSON parsing） | candidate reason と expected_head を current pr.head.sha と照合する。 |
| O-15 Re-review: thread 状態・CI再確認 | gh の読み取り、または Thread Owl/GitHub read tools。 | thread_owl get_pr、thread_owl list_review_threads、GitHub CI tools | C（gh の一括読み取りを選んだ場合）。 | resolved/outdated と current diff を MCP で確認する。 |
| O-16 Re-review: unresolved thread への返信 | CLI 記録なし。 | thread_owl reply_review_thread | not applicable | 元 thread が unresolved なら返信のみ。resolve は reviewed-side の別 workflow に任せる。 |
| O-17 Re-review: resolved/outdated だが問題が残る | CLI 記録なし。 | thread_owl post_inline_comment | not applicable | current diff の有効行へ新規 thread を投稿する。位置がない場合は O-18。 |
| O-18 Re-review/Follow-up: current diff に位置がない | CLI 記録なし。 | thread_owl post_summary_comment | not applicable | stale な行へ投稿せず PR-level summary にする。 |
| O-19 Thread Follow-up | 指定 thread、current head、対応差分の読み取り。 | thread_owl list_review_threads、get_pr、reply_review_thread、post_inline_comment、post_summary_comment | not applicable | Re-review の投稿経路表を再利用し、独立論点を同じ thread に混ぜない。 |
| O-20 Verdict 判定 | LLM の判断。merge はしない。 | なし。approve 時の投稿だけ thread_owl post_summary_comment。 | not applicable | blocking なし、全 thread resolved、主要リスクの検証あり、CI success の全条件を満たす場合だけ approve。 |
| O-21 ユーザー報告・ハンドオフ | Markdown テキストを出力。外部操作なし。 | なし | not applicable | reviewed head、CI head、verdict、投稿数、残存リスク、queue route を固定フォーマットで報告する。 |

## 推奨シミュレーション順序

### reviewed-side

1. R-00 で server/tool 名を確定する。
2. R-01 の本文なし投稿者ゲートを先に実行する。現状は MCP だけで完結しないため、gh の metadata projection を使用する。
3. ゲート通過後に R-02〜R-05 を実行し、R-06 で分類する。
4. 修正がある場合は R-07〜R-10、不要な場合は R-12 へ進む。
5. 再レビューが必要なら R-13 → R-14 → R-15 の順で完了する。
6. R-16〜R-19 で CI、Codecov、Verdict、サマリを処理する。
7. R-20 は人の明示操作へ引き渡し、R-21 を報告する。

### reviewer-side

1. PR URL 起点なら O-02、queue 起点なら O-00 → O-01 → O-02 の順で対象を固定する。
2. O-03〜O-07 で reviewedHeadSha に対する独立レビューを完了する。
3. O-08〜O-10 で既存レビューをフィルタし、Snapshot Guard を再確認する。
4. O-11〜O-13 または O-16〜O-18 で、Thread Owl MCP の契約に従って投稿する。
5. O-20 で verdict を決め、O-21 で固定フォーマットの結果とハンドオフを出力する。

## 再設計スコープ（今回追加）

元の #258 は `gh` と MCP の利用実態を分類する調査としては十分だが、複数の LLM クライアントで skill を再実行するための「実行契約」までは定義していなかった。本件の成果物には、次回以降の実装・再監査へそのまま渡せる以下の範囲を含める。

### 1. LLM 非依存の実行契約

skill 内の `{GH}` / `{RAVEN}` / `{OWL}` は論理名として維持し、クライアントごとに異なる MCP namespace や tool 名を実行時の discovery で解決する。tool 名を推測できない、server が未接続、schema が不一致のときは、LLM が勝手に別の write 経路へ進まず、`blocked` として停止・報告できる契約にする。

R-xx / O-xx の各行について、将来の実装仕様として次の項目を埋める。

| 契約項目 | 必須内容 |
|---|---|
| precondition | 入力 PR、current head、認証、allowlist、作業ツリーなどの前提 |
| primary tool | 実際の完全な tool 名、または解決した論理 alias と schema version |
| input / output | 必須引数、型、ページ境界、成功時に次の step が読むフィールド |
| side effect | read / comment / reply / resolve / approve / enqueue の別、外部変更の有無 |
| guard | 投稿者ゲート、current head SHA、位置の有効性、重複投稿防止など |
| fallback | primary が使えない場合に許される代替と、代替を使う条件 |
| failure / stop | timeout、auth、schema 不一致、partial failure ごとの停止状態と報告 |
| evidence | 実行順、tool/command、引数の秘匿化ログ、応答要約、observed/simulated/inferred |

この契約により、「MCP 第一選択」という宣言だけでなく、各 step がどの tool を使い、何を確認したら次へ進めるかをモデル間で比較できるようにする。

### 2. コンポーネント別の追加対象

| 対象 | #258 で固定すべき再設計要件 | 現行実装との接続 |
|---|---|---|
| 2つの skill | entry / phase / termination の状態機械、論理 alias の解決、read-before-write、失敗時の fail-closed、固定された最終報告 schema、skill revision の記録 | R-00〜R-21 / O-00〜O-21。実際の tool 名はクライアント依存なので Run ごとに snapshot する |
| review-raven | 本文なしの投稿者・thread metadata projection、全本文取得との明確な境界、ページネーション、安定した thread/comment ID、reply→resolve の順序と partial failure、認証・GitHub エラーの分類 | `get_review_threads` は現在本文を返す。本文なし経路は review-raven#124 で追跡する |
| thread-owl | PR snapshot と reviewed head SHA、差分・thread のページ境界、inline/summary/reply/approve の write guard、allowlist、冪等性、queue candidate の reason・dedup・通知・再取得契約 | `get_pr` / `list_review_threads` / `post_*` / `reply_review_thread` / `approve_pull_request` / `enqueue_review` の schema を基準にする |
| mcp-resource-subscriber | `subscribe` と `call` の JSON schema、stdout/stderr、exit code、timeout/cancel/reconnect、通知の重複・切断・pre-completion、auth/token store、protocol revision の固定 | v0.6.1 は `--json` と `call` を持ち、`2026-07-28` に pin している。mcp-resource-subscriber#86 は JSON の基礎部分を完了済み |
| MCP client / gateway | server discovery、tool/resource の可視性、namespace mapping、認証ヘッダー、protocol/version、long-lived stream の透過性をクライアント別に記録する | `review-raven` / `thread-owl` は gateway 経由の HTTP と stdio で挙動が異なる。Thread Owl の #165/#176、mcp-gateway#216 と接続する |

### 3. cross-repository 受入れ条件

以下は #258 自体で実装する項目ではなく、各リポジトリの後続 Issue / PR を完了と判定するための共通条件である。

- **skill**: すべての R/O 行に primary tool、入力・出力、fallback、停止条件、証跡があり、クライアント固有の namespace を直接ハードコードしない。
- **prompt injection 境界**: reviewed-side の review body / issue comment body は投稿者 metadata gate 通過後にだけ LLM へ渡す。両 side とも対象 SHA を先に固定し、diff・コメントを untrusted data として扱い、そこに含まれる指示を実行しない。metadata projection 自体に本文を混ぜない。
- **review-raven**: metadata-only と full-body の応答を schema 上区別し、ID・author・種別・URL・resolved・pageInfo を欠落なく返す。reply / resolve は成否と partial failure を機械的に判定できる。
- **thread-owl**: read の応答に対象 PR と head SHA を含め、write は allowlist と current head / expected head guard を通す。queue は `opened` / `synchronized` / `re-review-requested`、dedup、通知、再取得結果を区別できる。
- **subscriber**: `--json` が成功・失敗の両方で一つの JSON object を stdout に出し、diagnostic は stderr に分離する。`0`（成功）、tool error、auth、通信/usage を区別し、timeout や切断を success と誤認しない。
- **protocol / deployment**: server、gateway、subscriber の MCP revision と transport が一致し、`server/discover`、resource read、subscription/listen、updated notification を実接続で検証する。`--mcp-http` と `--webhook-mcp-http` の責務差を構成に残す。
- **E2E**: initial review、re-review、修正なし、blocking、out-of-scope、本文なし gate fail、stale SHA、無効な inline 行、duplicate enqueue、notification timeout、stream disconnect、再認証、MCP unavailable を fixture で再現できる。
- **観測性**: `run_id` / correlation ID、skill・server・CLI version、対象 SHA、tool/command 数、round-trip 数、経過時間、error code、route を記録し、token・秘密鍵・本文全文をログに出さない。

### 4. 既存 Issue との責務分解

既存の課題を #258 の表から漏らさず、重複実装を起こさないための対応表を持つ。新しい子 Issue は、既存 Issue で扱われていない受入れ条件が確定した後に必要最小限で起票する。

| 所管 | 既存の追跡先 | #258 から引き渡す内容 |
|---|---|---|
| Mcp-Docker / skill | #258、#250 | 固定 ID 行列、LLM 実行契約、allowlist の信頼境界、Run 比較フォーマット |
| review-raven | [#124](https://github.com/scottlz0310/review-raven/issues/124)、[#109](https://github.com/scottlz0310/review-raven/issues/109) | metadata projection、本文取得境界、protocol/SDK 前提、partial failure の受入れ条件 |
| thread-owl | [#165](https://github.com/scottlz0310/thread-owl/issues/165)、[#176](https://github.com/scottlz0310/thread-owl/issues/176)、[#117](https://github.com/scottlz0310/thread-owl/issues/117) | `2026-07-28`、queue/listen、dedup、stream lifecycle、PR/write guard の E2E 条件 |
| mcp-resource-subscriber | [#86](https://github.com/scottlz0310/mcp-resource-subscriber/issues/86)、[#162](https://github.com/scottlz0310/mcp-resource-subscriber/issues/162) | 完了済み JSON の残差（exit/error/route/timeout/切断）とクライアント別検証 |
| gateway / 通知基盤 | mcp-gateway#216、squirrel-notifier の関連検証 | gateway 透過性、認証、long-lived stream、実運用の再接続と観測性 |

### 5. 次回 Run で追加計測するもの

従来の A〜D は「なぜ gh を選んだか」を表す分類であり、再設計の完了度やモデル間の実行品質を測れない。各 Run で次も記録する。

| 計測 | 目的 |
|---|---|
| client / model / skill revision / server・CLI version | モデル変更と環境変更を混同しない |
| discovery で見えた server・tool・resource と実際の namespace | tool 名の推測・未接続を検出する |
| step ごとの primary / fallback、read/write、call 数、shell 数、round-trip 数 | C と D を区別し、粒度改善の効果を測る |
| elapsed time、timeout、route、exit code、error code | 「速い」という印象を再現可能な値にする |
| 入力 PR / reviewed head SHA / queue reason / fixture | 同じ対象・同じ状態で比較する |
| body gate 通過時刻と本文取得時刻 | prompt injection 境界の順序違反を検出する |
| 出力 schema 検証結果と最終 termination status | LLM が異なる表現で成功を報告する問題を防ぐ |

## MCP 側の改善候補

この PR では各 MCP / CLI の機能実装は行わない。上の受入れ条件を MCP 側の別 Issue / PR に切り出す候補として、責務境界に沿って記録する。skill 本体の変更も #258 の直接実装には含めないが、契約を消費するために必要な変更は後続 PR の受入れ条件として扱う。

| 優先度 | 候補 | 所管 | 根拠 |
|---|---|---|---|
| 高 | 本文なしの review thread / review body / issue comment metadata projection | review-raven または GitHub connector | R-01、R-18a。prompt injection 防御の前提であり、review-raven#124 が既存の切り出し先 |
| 中 | reviewedHeadSha をキーに required checks、workflow runs、failed/skipped、job logs をまとめる read tool | GitHub connector 側 | R-16、O-06。C の往復コストを下げる |
| 中 | queue subscribe/read の native client tool | host / subscriber 側 | O-00。ただし architecture 上、Thread Owl に subscriber を内蔵しない |
| 低 | review-raven の全 review body / issue comment を含む取得結果のページ境界・projection の明示 | review-raven / GitHub connector | R-04、R-05。モデル間の再現差を減らす |

## スキル記述と実運用の差分

現在の skill 本文は、review thread の取得・返信・resolveを MCP 第一選択として記述している。したがって、gh が使われた事実だけを理由に skill 本体を直すのは不十分である。

- B は MCP の API 契約を改善する問題であり、review-raven#124 に委ねる。
- C は一括取得の速度・粒度の問題であり、CI 集約 tool の設計論点として扱う。
- D は command log がないため今回の事実とは断定せず、次回 Run で「単独操作だったか」「一括実行だったか」を記録する。
- A はローカル環境の責務であり、MCP 化しない。

また、gh pr merge、gh release edit、タグ push は #258 の背景で観測されたリリース操作だが、両 skill の手順ではない。Phase 8 は自律 merge を禁止しているため、今回の skill 行列には移行候補として混ぜない。`gh` の一律禁止、MCP への subscriber 内蔵、ユーザー承認なしの merge も再設計スコープには含めない。

## Run 2 以降の追記テンプレート

以下をコピーして末尾へ追加する。既存 Run と行 ID を変更しない。

### Run N

| 項目 | 値 |
|---|---|
| run_id | YYYY-MM-DD-<agent>-<model> |
| 実行モデル |  |
| 実行環境 |  |
| 対象 commit / skill revision |  |
| server / CLI version・MCP protocol |  |
| 対象 PR |  |
| MCP tool snapshot |  |
| client namespace / discovery 結果 |  |
| observed / simulated / inferred の境界 |  |
| 失敗・未確認事項 |  |
| call 数 / shell 数 / round-trip 数 / elapsed_ms |  |
| queue reason / reviewed head SHA / fixture |  |
| body gate 時刻 / 本文取得時刻 / output schema 検証 |  |

#### 変更された判定

| 行 ID | 前回分類 | 今回分類 | 変更理由 | 証跡 |
|---|---|---|---|---|
| R-xx / O-xx |  |  |  |  |

#### 今回の実行 tool log

| 順序 | 行 ID | tool / command | read/write | 結果 | elapsed_ms | error / route | observed / simulated |
|---|---|---|---|---|---:|---|---|
| 1 |  |  |  |  |  |  |  |

#### 今回の提案差分

- 既存の B / C / D 判定から変わったもの:
- 新規 MCP tool の必要性:
- skill 本体を変更しない理由または変更候補:
- 次回に再確認する仮説:

## Run 2

| 項目 | 値 |
|---|---|
| run_id | 2026-09-10-claude-code-opus5 |
| 実行モデル | Claude Opus 5（claude-opus-5）/ Claude Code |
| 実行環境 | Windows 11、PowerShell + Git Bash、Asia/Tokyo |
| 対象 commit / skill revision | 2d19064（`docs/258-skill-tool-inventory`）。review-raven-thread-owl-cycle rev 3、thread-owl-pr-reviewer rev 1（Run 1 と同一） |
| server / CLI version・MCP protocol | thread-owl `ghcr.io/scottlz0310/thread-owl:main` rev 51145c4、review-raven `:main` rev 5b5c834、mcp-gateway `:main` rev b19e00a、github-mcp `ghcr.io/github/github-mcp-server:main`、mcp-resource-subscriber v0.6.1。protocol pin `2026-07-28` |
| 対象 PR | #255（代表ケース）、#256（get_pr サンプル）、#257（CI ゲート）、#259（本 PR） |
| MCP tool snapshot | Run 1 の registry とは tool 名・namespace の両方が異なる。下記「Run 2 の client namespace」を参照 |
| client namespace / discovery 結果 | `claude mcp list` で 11 server。`github` / `review-raven` / `thread-owl` はいずれも mcp-gateway 経由の HTTP（`https://localhost:8080/mcp/*`）。tool 名は `mcp__github__*` / `mcp__review-raven__*` / `mcp__thread-owl__*`（Run 1 は `mcp__codex_apps__github_*` / `mcp__review_raven__*` / `mcp__thread_owl__*`） |
| observed / simulated / inferred の境界 | 本 Run の MCP 呼び出しはすべて read-only で observed。PR への投稿・resolve・approve・enqueue（write 系）は一切実行していないため inferred。skill の phase 遷移自体は実行していないので simulated ですらなく、tool 契約の実測に限定する |
| 失敗・未確認事項 | `mcp__github__get_me` が 403（下記）。`desktop-commander` は `claude mcp list` では Connected だが本セッションでは CONNECT_TIMEOUT。write 経路の投稿 identity は未実測 |
| call 数 / shell 数 / round-trip 数 / elapsed_ms | MCP call 11（うち失敗 1）、shell 6、ToolSearch 3。elapsed_ms は計測なし（この client は tool 単位の所要時間を返さないため、印象値を書かない） |
| queue reason / reviewed head SHA / fixture | queue 待機なし（PR URL 起点）。参照 head SHA: #255 `b4239c93ccd996cc034592da7cf8e4b8db019d8a`、#256 `80f0bbda66de1e971bd68bd12d0506846b2b9057`、#257 `4a5871d33f7c16a404fe56a16295b5c77f1993f7`。fixture なし（本番 PR の read-only 参照） |
| body gate 時刻 / 本文取得時刻 / output schema 検証 | 本 Run は skill 実行ではなく tool 契約の実測のため、投稿者ゲートを先行させていない。本文取得を先に行った事実をここに明記する。output schema 検証は各 tool の応答構造の目視確認まで |

### Run 2 の client namespace

Run 1 の registry は論理名の解決結果であって、別 client では tool 名そのものが変わる。本 Run は同じ論理名が次へ解決された。

| 論理名 | Run 1 の解決結果 | Run 2 の解決結果 | 差分 |
|---|---|---|---|
| {GH} | `mcp__codex_apps__github_*`（操作ごとに 1 tool） | `mcp__github__*`（公式 GitHub MCP Server。`pull_request_read` / `issue_read` の method 引数で操作を切り替える） | tool 名も呼び出し形も非互換。skill が tool 名を固定できない実例 |
| {RAVEN} | `mcp__review_raven__*` | `mcp__review-raven__*` | 区切り文字が `_` から `-` へ。文字列一致でハードコードすると解決に失敗する |
| {OWL} | `mcp__thread_owl__*` | `mcp__thread-owl__*` | 同上 |
| queue bridge | mcp-resource-subscriber CLI | `ListMcpResourcesTool` / `ReadMcpResourceTool`（client ネイティブ）＋ 待機は引き続き subscriber CLI | read はネイティブ化。待機だけが CLI の責務として残る |

本 Run では GitHub 系 server が 2 つ見えた（gateway 経由の `mcp__github__*` と claude.ai connector の `mcp__claude_ai_github__*`）。どちらも公式 GitHub MCP Server 系の tool 名で、同名 tool が異なる認証で 2 経路存在する。skill は「どちらを使うか」を discovery 時に固定しないと、投稿 identity が Run ごとに変わる。

### 変更された判定

| 行 ID | 前回分類 | 今回分類 | 変更理由 | 証跡 |
|---|---|---|---|---|
| R-01 / R-12 / R-18a | B | B（維持・強化） | 本文なし射影は Run 2 の 3 経路すべてに存在しない。`pull_request_read:get_review_comments`、`issue_read:get_comments`、`review-raven:get_review_threads` はいずれも `body` を必ず含み、除外する引数を持たない。server instructions が言及する `minimal_output` はこれらの tool の schema に存在しない | observed（tool schema と #255 の応答） |
| R-16 / O-06（状態集約） | C（SHA → run → job → log の複数往復） | C から改善。1 call で状態集約が可能 | `pull_request_read:get_check_runs` が #257 の 13 check run を conclusion 付きで 1 回で返した。Run 1 が「中優先度の改善候補」とした CI 集約 read tool は、公式 GitHub MCP Server にすでに存在する | observed（#257、total_count 13、全 success） |
| R-16 / O-06（失敗ログ） | C | A（client 依存） | 本 Run の GitHub MCP には workflow run / job / log を取得する tool が 1 つも存在しない（`mcp__github__*` / `mcp__claude_ai_github__*` の両方を検索して不在を確認）。Run 1 の client には `github_fetch_workflow_job_logs` があった。失敗ログは `gh run view --log-failed` に戻る | observed（tool 検索結果） |
| R-16 / O-06（combined status） | C | 使用禁止に格上げ | #257 の `get_status` は `total_count: 0` かつ `state: "pending"`。全 check が success の merged PR に対して pending を返す。unknown を success にしないだけでは不十分で、pending を「実行中」と解釈しても誤りになる。CI 判定は check runs のみを根拠にする | observed（#257） |
| R-02 / R-08b（HEAD 取得） | C | MCP 単独で完結（寄せ済みを実測） | `thread-owl:get_pr` が `pr.head.sha` / `pr.base.sha` / `state` / `htmlUrl` を 1 call で返した。gh を併用する理由が本 Run では発生しない | observed（#256） |
| O-02 / O-03 | C | MCP 単独で完結（寄せ済みを実測） | 同じ `get_pr` 応答に `files[]`（filename / status / additions / deletions / patch）が同梱された。metadata と diff で call を分ける必要がない | observed（#256、5 ファイル・patch 込み） |
| O-00 / O-14（queue read） | A（subscriber の責務） | A（待機のみ）＋ ネイティブ read | この client は `ReadMcpResourceTool` を持ち、`queue://review/re-review-requests` を直接読めた（`[]`）。購読して待つ部分だけが subscriber CLI の責務として残る | observed（resource 一覧 2 件、read 成功） |
| R-13 | A | A（維持・observed へ昇格） | Run 1 は skill 手順からの再現だったが、本 Run は `docker-compose.yml:203` の `command: ["--mcp-http"]` を直接確認した | observed |

### 今回の実行 tool log

| 順序 | 行 ID | tool / command | read/write | 結果 | elapsed_ms | error / route | observed / simulated |
|---|---|---|---|---|---:|---|---|
| 1 | R-00 / O-00 | `claude mcp list` | read | server 11 件。github / review-raven / thread-owl は gateway HTTP | 未計測 | — | observed |
| 2 | R-13 | `grep -n -A25 'thread-owl' docker-compose.yml` | read | `command: ["--mcp-http"]`、`ROUTE_THREAD_OWL=/mcp/thread-owl` | 未計測 | — | observed |
| 3 | 環境 | `docker compose ps` / `docker inspect` | read | thread-owl rev 51145c4、review-raven rev 5b5c834、mcp-gateway rev b19e00a | 未計測 | — | observed |
| 4 | O-00 | `bunx mcp-resource-subscriber --version` | read | `v0.6.1`、exit 0 | 未計測 | — | observed |
| 5 | R-00 / O-00 | `ToolSearch select:...`（3 回） | read | tool schema 取得。namespace が Run 1 と非互換であることを確認 | 未計測 | — | observed |
| 6 | R-02 | `mcp__github__get_me` | read | 失敗。`403 Resource not accessible by integration` | 未計測 | gateway `ROUTE_GITHUB` は `upstream_github_app=true`。App installation token に `/user` はない | observed |
| 7 | O-02 / O-03 | `mcp__thread-owl__get_pr`（#256） | read | pr + head.sha + files[].patch を 1 call で取得 | 未計測 | gateway `/mcp/thread-owl` | observed |
| 8 | R-03 / O-08 | `mcp__thread-owl__list_review_threads`（#255） | read | thread 1 件、`isResolved: true`、comment に id と url あり。pageInfo なし | 未計測 | 同上 | observed |
| 9 | R-03 | `mcp__review-raven__get_review_threads`（#255） | read | `summary{total:1, unresolved:0}` + thread 1 件。comment に id / url なし、pageInfo なし | 未計測 | gateway `/mcp/review-raven`、`upstream_provider_token=true` | observed |
| 10 | R-01 / R-12 | `mcp__github__pull_request_read:get_review_comments`（#255） | read | body 必須。pageInfo（cursor 付き）あり。`is_outdated` / `original_line` を返す | 未計測 | — | observed |
| 11 | R-16 / O-06 | `mcp__github__pull_request_read:get_status`（#257） | read | `state: pending`、`total_count: 0`、`statuses: []` | 未計測 | — | observed |
| 12 | R-16 / O-06 | `mcp__github__pull_request_read:get_check_runs`（#257） | read | 13 件すべて `conclusion: success`。job 単位の URL 付き | 未計測 | — | observed |
| 13 | R-05 / R-17 / R-18b | `mcp__github__issue_read:get_comments`（#255） | read | 4 件（Codecov / 再レビュー依頼 / Verdict / 対応サマリ）。Run 1 の 4 件と一致。`author_association` を含む | 未計測 | — | observed |
| 14 | O-00 / O-14 | `ListMcpResourcesTool(server=thread-owl)` | read | `queue://review/queue` と `queue://review/re-review-requests` の 2 件。Run 1 と同一 | 未計測 | — | observed |
| 15 | O-14 | `ReadMcpResourceTool(queue://review/re-review-requests)` | read | `[]`（空 queue）。client ネイティブで read 成功 | 未計測 | — | observed |
| 16 | 認証 | `mcp__review-raven__diagnose_github_token` | read | `login: scottlz0310-user`、`scopes: []` | 未計測 | provider token 経路 | observed |

### Run 2 で新たに判明した事項

#### 1. 同一 gateway 上で identity が 2 つに割れている

| route | gateway 設定 | 実測した identity |
|---|---|---|
| `/mcp/github` | `upstream_github_app=true` | GitHub App installation token。`get_me` が 403 で login を取得できない |
| `/mcp/review-raven` | `upstream_provider_token=true` | `scottlz0310-user`、`scopes: []`（fine-grained PAT / App token のため header なし） |

公式 GitHub MCP Server の instructions は「まず `get_me` を呼べ」と指示するが、この deployment では常に失敗する。skill が identity を前提に分岐する場合、`get_me` に依存してはならない。write を伴う R-10 / R-14 / R-19 は、どの route で投稿したかによって PR 上の投稿者が変わる（本 Run では write 未実行のため inferred）。

#### 2. 投稿者 login の表記が経路によって揺れる

同じ thread-owl の発言が、経路ごとに次の login で返った。

| 経路 | author |
|---|---|
| `thread-owl:list_review_threads` / `review-raven:get_review_threads` | `thread-owl` |
| `github:issue_read:get_comments`（Verdict コメント） | `thread-owl[bot]` |

投稿者ゲートを login の完全一致で実装すると、経路を替えた時点で信頼判定が静かに壊れる。`[bot]` サフィックスの正規化規則を、review-raven#124 の metadata projection と thread-owl 側の応答契約の両方に含める必要がある。あわせて、`author_association` は thread-owl[bot] / codecov[bot] のいずれも `NONE` を返すため、信頼シグナルとして使えないことを実測した。

#### 3. ページ境界の実装差

| 経路 | pageInfo |
|---|---|
| `github:pull_request_read:get_review_comments` | あり（`hasNextPage` / `endCursor`、`after` 引数で継続） |
| `thread-owl:list_review_threads` | なし |
| `review-raven:get_review_threads` | なし（`summary.total` はあるが継続手段がない） |

再設計スコープの「ページ境界」要件は、GitHub connector 側では満たされ、自作 2 server では未達である。thread が多い PR で thread-owl / review-raven を第一選択にすると、取りこぼしを検出できない。

#### 4. Run 1 の registry に無かった review-raven tool

本環境の review-raven は `get_pr_review_cycle_status`、`diagnose_github_token`、Copilot watch 系（`start_copilot_review_watch` 等）も公開している。`get_pr_review_cycle_status` は reviewed-side のサイクル判定（WAIT / REPLY_RESOLVE / REQUEST_REREVIEW / READY_TO_MERGE / ESCALATE）を返すが、現行の review-raven-thread-owl-cycle skill の R-xx 行はこの tool を使っていない。Copilot watch 系は #256 で廃止した `pr-review-cycle` 向けであり、本 skill の対象外である。

#### 5. discovery と実接続の乖離

`claude mcp list` は `desktop-commander` を Connected と表示したが、本セッションでは CONNECT_TIMEOUT で利用できなかった。health 一覧の Connected 表示は、そのセッションで tool が呼べることを保証しない。skill の R-00 / O-00 は「一覧に出たか」ではなく「実際に 1 回 read できたか」を discovery の完了条件にする必要がある。

### 今回の提案差分

- 既存の B / C / D 判定から変わったもの:
  - R-16 / O-06 を 3 つに分解する。状態集約は `get_check_runs` で 1 call（改善候補は実装済み）、combined status は使用禁止、失敗ログは client 依存で `gh run view --log-failed` に残る。
  - R-02 / R-08b / O-02 / O-03 は `thread-owl:get_pr` 単独で完結することを実測した。C の根拠だった「往復コスト」は本 client では成立しない。
  - O-00 / O-14 の queue read はネイティブ tool へ寄せられる。subscriber CLI に残る責務は購読と待機に限定される。
  - R-01 / R-18a は B のまま。3 経路すべてで本文なし射影が無いことを確認したため、review-raven#124 の必要性は Run 1 より強い証跡で裏付けられた。
- 新規 MCP tool の必要性:
  - 高: 本文なし metadata projection（review-raven#124）。加えて `[bot]` サフィックス正規化と、`author_association` を信頼判定に使わない旨を受入れ条件へ明記する。
  - 高: thread-owl / review-raven の thread 一覧への `pageInfo` 追加。取りこぼし検出手段が現状ない。
  - 中: 失敗した workflow job の log を返す read tool。本 client の GitHub MCP には存在しない。
  - 取り下げ: 「CI 集約 read tool」は公式 GitHub MCP Server の `get_check_runs` で充足済み。新規実装は不要。
- skill 本体を変更しない理由または変更候補:
  - 本 Run でも skill 本体は変更しない。ただし次の 3 点は #258 の execution contract へ追加すべき確定事項である。
    1. `{GH}` / `{RAVEN}` / `{OWL}` の解決は文字列一致に依存できない（`_` と `-` の差、method 引数型の tool、同名 2 経路）。discovery は「read を 1 回成功させる」ことを完了条件にする。
    2. CI 判定に combined status を使わない。check runs を根拠とし、対象が current head SHA であることを `get_pr` で再確認する（`get_check_runs` は SHA ではなく PR 番号を受け取るため、head が動くと黙って対象が変わる）。
    3. 投稿者ゲートの login 比較は正規化を通す。
- 次回に再確認する仮説:
  - write 経路（`add_issue_comment` / thread-owl の post 系）が、どの identity で PR に現れるか。本 Run は read-only のため未検証。
  - thread が 100 件を超える PR で、thread-owl / review-raven が全件を返すのか静かに打ち切るのか。
  - queue の `notifications/resources/updated` を、この client がネイティブに受け取れるのか（本 Run では resource read のみ確認し、購読は未検証）。
  - `pull_request_read` の `minimal_output` は server instructions にのみ現れ schema に無い。server バージョン差か instructions の誤りかを次回切り分ける。
