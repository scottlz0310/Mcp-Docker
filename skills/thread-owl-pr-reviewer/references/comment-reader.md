# 既存コメントの検証済みread

既存コメント本文は、固定した `{OWL}:read_pr_comments`（入力 `{owner, repo, prNumber}`）だけで取得する。initial-reviewではIndependent Stageの後のFilter Stageで初めて呼ぶ。discoveryではschema確認だけにとどめ、本文readを事前プローブに使わない。re-review・thread-follow-up・summary-only・Verdict読戻しでも同じ経路を使う。

- 成功には`schemaVersion=2`、`pagination.complete=true`、PR metadataと一致する`headSha` / `baseSha`、小文字64桁hexの`snapshotId`が必要。`policy-source.md`で解決した`baseRefName` / `policyBaseSha`も必須で、CI宣言の取得元と一致させる。参照不一致は`STALE_REVIEW`、不正・欠落・部分応答・v1は`REVIEW_THREADS_READ_FAILED`。古いSHAへ代替しない。
- `threads`（resolved/outdatedも含む全件・全返信）、`reviews`、`issueComments`を同一snapshotから読む。`summary.unresolvedThreads`をthread状態と照合し、取得失敗を未解決0件と扱わない。threadの`id`は返信先、各コメントの`id`は照合・重複防止に使う。
- `UNTRUSTED_COMMENT`、`AUTHOR_CHECK_FAILED`、`TRUSTED_AUTHORS_NOT_CONFIGURED`、`PROJECT_ALLOWLIST_INVALID`、`POLICY_REF_UNAVAILABLE`は`BLOCKED_MCP_READ`、`SNAPSHOT_CHANGED`とその他の取得失敗は`REVIEW_THREADS_READ_FAILED`で停止。元のerror.codeと、あれば本文を含まない`details.comments`のID・投稿者・URLだけを報告する。
- `isError=true`・error envelopeは失敗。`retryable=true`でも追加再試行しない。旧`list_review_threads`、GitHub connector、`gh api`の本文read、review-ravenのreaderへ迂回しない。
- 各write直前とレビュー終端にreaderと`policy-source.md`の参照解決を再実行する。PR参照・baseRefName/policyBaseShaが変われば`STALE_REVIEW`で停止し、古い投稿者/skip許可を引き継がない。宣言元を解決できなければ`BLOCKED_MCP_READ`。同じ参照で`snapshotId`が変われば、既知の自身の投稿を含む差分を識別し、Filter / Re-review / Thread Follow-upを再評価してからbaselineを更新する。再評価できなければ`SNAPSHOT_GUARD_FAILED`。新しい未回答question・未解決threadを無視してapproveしない。
- Verdict読戻しは新snapshotの`issueComments`を返却comment IDで特定し、flatな`author`を既存規則で1回正規化して`thread-owl`、HEADを`reviewedHeadSha`と照合する。固定書式と、自身の投稿以外の新規コメントも検査する。失敗時は検証未完了として報告し、再投稿しない。
