# 論理 alias の discovery と固定（R-00）

SKILL.md の「R-00: 論理 alias の discovery と固定」と「Write route と投稿 identity の discovery」から移した手順（内容は変更していない）。

### R-00: 論理 alias の discovery と固定

`{GH}` / `{RAVEN}` / `{OWL}` は論理 alias であり、MCP client が割り当てた server 名・tool 名・namespace を skill 本文に書かない。各 alias の実体は、対象 PR と起動モードが確定した時点で、実行中の client の discovery 結果から解決する。

1. client-native の server / tool / resource discovery を実行し、候補ごとに server の識別情報、transport / route、tool または resource の opaque handle、input / output schema を記録する。server 一覧の `Connected` 表示や tool 名の存在だけでは、利用可能と判定しない。
2. 候補は文字列の prefix / namespace ではなく、論理 alias に必要な capability と schema で分類する。method 引数で操作を切り替える tool と操作ごとに分かれた tool は、schema が契約を満たす限り同じ論理候補として扱う。
3. 選択規則は次のとおりとする。
   - host / client の設定で alias に明示的な server binding が指定されている場合は、それを優先する。
   - 明示指定がない場合は、必要な capability・input schema・minimum output schema を満たす候補が一つだけのときに限り採用する。同一 server 内の操作別 tool は、その server binding に属する操作候補として扱う。
   - 複数の server / route が残る場合、discovery 順や表示名だけで選ばず、`BLOCKED_MCP_DISCOVERY` として停止する。異なる認証経路を自動的に試してはならない。
4. 採用した各 binding について、write ではない最小の read を **1 回成功** させる。成功とは transport が応答しただけでなく、tool error がなく、論理契約の minimum output schema を満たすことをいう。server 一覧、schema の取得、resource の存在確認だけでは read 成功とみなさない。`{RAVEN}` の minimum read は `get_review_threads` に `include_bodies=false` を明示した metadata-only 呼び出しとし、`include_bodies` の入力 schema、本文を含まない出力、`pagination.complete=true` を検証する。本文ありの read は必須コメント投稿者ゲートが成功するまで実行しない。
5. alias から選択済み binding への対応表と、各論理操作に使う tool / resource handle をこの run の状態として固定する。以後は同じ binding を使い、途中の再 discovery、候補の切り替え、失敗した write の別経路への迂回を行わない。後続の transport failure は新しい候補を探す理由にせず、停止・報告する。
6. `{RAVEN}` の `list_check_runs_for_sha`（R-16 / Phase 6.5 の CI read）は**任意 capability**として扱う。採用した `{RAVEN}` binding にこの tool があり、input（`owner` / `repo` / 40 桁小文字 hex の `sha`）と output（`sha`、`check_runs[].head_sha` / `name` / `status` / `conclusion` / `app`、`pagination.complete`、`deduplication.strategy`）の schema が一致する場合に CI read の第一選択として固定する。無い（review-raven v0.5.0 未満）または schema 不一致の場合だけ、Phase 6.5 の `gh api` fallback を CI read 経路として固定する。**この任意 capability の不在を `BLOCKED_MCP_DISCOVERY` にしない。**どちらの経路を使うかは discovery 時点で決め、実行時の tool error や transport failure から切り替えない。
7. `{RAVEN}` の `get_trusted_comment_authors` は**必須 capability**である（入力なし。出力は `logins`＝文字列の配列）。R-00 では呼ばない（R-01 の入口で 1 回だけ呼んで、run の状態へ固定する）。採用した `{RAVEN}` binding にこの tool が無い、または schema が一致しない場合は、`BLOCKED_MCP_DISCOVERY` ではなく、`TRUSTED_AUTHORS_UNAVAILABLE` で停止する。

候補を解決できない、未接続、schema 不一致、read 検証失敗、または複数候補を一意に選べない場合は、次の状態で停止する。

```text
termination_status = BLOCKED_MCP_DISCOVERY
status = blocked
```

この場合は、対象 PR（確定済みの場合）、logical alias、必要 capability、候補数、失敗分類（unresolved / not connected / schema mismatch / read failed / ambiguous）、read 検証の結果、`writes performed: 0`、再実行に必要な設定変更を報告する。token・Authorization header・秘密情報は報告しない。`gh` CLI、別の MCP candidate、別の write 経路へ進まず、Phase 3 以降の変更・返信・resolve・コメント投稿・enqueue を実行しない。

### Write route と投稿 identity の discovery

R-00 では read binding だけでなく、R-10、R-14、R-19 が使う GitHub write binding も固定する。投稿 identity は route / server instance / 認証経路に依存して変わり得るため、`get_me` の成功や token 種別から推測しない。

1. `{GH}` の issue-comment write capability について、server instance / route / opaque handle、input / output schema、想定される fallback を候補ごとに列挙する。
2. 明示 binding があれば優先し、なければ capability・schema・repository 対象が一意な候補だけを `write_binding` として採用する。R-00 完了後は R-10、R-14、R-19 の全 write で同じ binding を使う。
3. `get_me` は診断補助にとどめ、失敗しても停止条件にしない。
4. 投稿 identity の確認は、対象 PR に対して実際に必要なコメント（R-10 返信、R-14 再レビュー依頼、R-19 サマリ）を投稿した直後に、返却された comment ID を使って同じ PR の issue-comment metadata を再取得し、実際の `author.login` を `write_author_login` として観測・検証する。分離された probe PR への事前プローブ投稿は要求しない。
5. 観測した `write_author_login` を run の状態へ保存し、canonical allowlist に含まれることを確認する。allowlist にない投稿者、null、欠落、類似名の場合は `WRITE_IDENTITY_UNCONFIRMED` として停止する。fallback route を使う場合も、最初の write 直後に同様に観測・固定する。
6. write 開始後の transport failure、受理結果不明、identity 不一致では別 route、別認証、`gh` CLI へ切り替えない。同じコメントの重複投稿を避け、停止して報告する。
