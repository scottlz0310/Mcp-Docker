# 指摘への返信とfollow-up Issue（R-10・R-11）

R-10・R-11は、専用App名義の`{RAVEN}`の`reply_to_pr_comment` / `create_follow_up_issue` / `get_follow_up_issue`だけを使う（review-raven v0.12.0以降。Issue用2 toolは`REVIEW_RAVEN_ENABLE_FOLLOW_UP_ISSUES=true`のときだけ公開される）。契約の正本はreview-ravenの`docs/follow-up-comments.md`。

## 入力

- 共通: `owner`・`repo`・`pr`、`expectedHeadSha`（R-08bで確認した現在のPR HEAD。40桁小文字）、`source`（`kind`と、readerが返した数字のID文字列`id`）。
- `source.kind`: R-10は`review_body` / `issue_comment`。inline threadの指摘への返信はR-09を使う。R-11はこれらに`review_thread_comment`（readerの`threadId`も必須）を加える。
- write: 直前の`read_pr_comments`の`snapshotId`を`expectedSnapshotId`に渡す。コメントが増えると（bot投稿でも）変わる。
- R-10は`body`。R-11は`title`・`body`・`reason`（`out-of-scope` / `deferred` / `follow-up`）・任意の`labels`（既存名）。本文に定型サイクル投稿・Review Verdict・再レビュー依頼のtrigger・固定footerを含めない。

## 手順

1. write直前にR-01を再実行し、`read_pr_comments`の`snapshotId`・head/baseを固定する（`comment-reader.md`）。
2. 同じ元指摘へのwriteは直列に1回だけ呼ぶ。
3. `status=created`かつ`matchesExpectedHead=true`なら、返却のID・URL・`author`（Bot型で`review-raven`、canonical allowlist内）を確認し、`read_pr_comments`（Issueは`get_follow_up_issue`）で読戻す。読戻し成功の後に、R-10は元指摘IDを`handled_comments`へ加え、R-11は返信（R-09またはR-10）へ`Follow-up: #番号`を記載する。
4. 失敗は`error.code`と`mayHaveChanged`で扱う。

| error.code | 扱い |
| --- | --- |
| `INVALID_INPUT` / `PRECONDITION_FAILED` / `APP_IDENTITY_FAILED`（`mayHaveChanged=false`） | POSTなし。原因（入力・snapshot変化・HEAD移動・identity）を確認する。snapshot変化は、投稿が0件であることを再読で確認した場合に限り、新しい`snapshotId`で1回だけ再実行できる |
| `ALREADY_REPLIED` / `FOLLOW_UP_EXISTS` | 既存の返信・Issueを読み、実際に指摘をカバーするかを判断する。再投稿しない |
| `WRITE_OUTCOME_UNKNOWN` / `POST_WRITE_MISMATCH`（`mayHaveChanged=true`） | 再投稿・別経路を行わない。返却された`createdResource`・候補をreadで確認して停止し、報告する（R-10は`COMMENT_WRITE_FAILED`、R-11は`FOLLOW_UP_UNTRACKED`） |
| `SNAPSHOT_CHANGED`・reader系 | `comment-reader.md`に従い停止する |

tool不在・Issue機能の無効・App権限不足のときは、`gh`や別routeへ迂回せず、R-10は`BLOCKED_MCP_DISCOVERY`、R-11は`FOLLOW_UP_UNTRACKED`で停止する（Issue機能の有効化は運用側の明示操作）。
