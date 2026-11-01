# 論理 alias の discovery と固定（R-00）

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

8. `{RAVEN}:read_pr_comments`は必須capability。入力schemaの`owner/repo/pr`を確認し、不在・不一致なら`BLOCKED_MCP_DISCOVERY`。成功応答とerror envelopeはR-01後の最初の本文readで`references/comment-reader.md`に従って検証する。R-00で本文を読むprobeはしない。

### Write route と投稿 identity の discovery

R-23が必要な場合は、同じRAVEN bindingの`get_pr_description` / `update_pr_description`も`pr-description.md`の入出力schemaで固定する。通常のレビューでは必須capabilityにしない。必要時の不在・不一致は`BLOCKED_MCP_DISCOVERY`で止まり、GH/ghへ切り替えない。

R-00で2つのwrite routeを固定する。候補のserver instance/route/opaque handle、input/output schema、repository対象、明示bindingを記録する。明示指定を優先し、無ければ必要capability/schemaを満たす一意の候補だけを採用する。曖昧・利用不能なら`BLOCKED_MCP_DISCOVERY`で停止する。

- R-10の汎用指摘返信は`{GH}`のissue-comment writeを`write_binding`へ固定。使用前だけ、R-10が明示する未使用primaryのfallbackを選べる。投稿後は切り替えない。
- R-14/R-19は同じ`{RAVEN}:post_review_cycle_comment`を`cycle_write_binding`へ固定する。入力owner/repo/pr/headSha/kind/body、出力commentId/url/author/headShaのschemaを確認。不在・不一致なら停止し、GHへ迂回しない。詳細は`references/cycle-comment.md`。
- `get_me`は診断補助で、失敗は停止条件にしない。probe投稿をせず、対象PRで実際に必要な最初のwrite後に返却comment IDで投稿者を観測する。token種別から推測しない。
- GHは同じPRのmetadataから`author.login`を取得して`write_author_login`へ保存する。RAVENは既存readerで本文/flat authorも照合し、別の`cycle_write_author_login`へ保存する。両identityを混同しない。
- いずれも正規化した実投稿者がcanonical allowlist内で、後続writeも観測済みidentityと一致すること。不一致/null/欠落/類似名は`WRITE_IDENTITY_UNCONFIRMED`。初回投稿自体の誤identityは事後検出となる。
- write開始後のtransport failure/受理不明/identity不一致では、別candidate/server/認証/ghへ切り替えず停止する。重複投稿しない。
