# 再依頼・対応サマリの専用App投稿（R-14/R-19）

R-14/R-19は固定した`{RAVEN}:post_review_cycle_comment`だけを使う。R-10のGH routeと投稿identityを分ける。

1. write直前にR-01・reader snapshot/current HEADを再確認し、新規指摘を再評価する。再依頼はmode/購読前提を先に満たす。
2. `owner/repo/pr`、現在の40桁小文字`headSha`、`kind`、固定templateの`body`を渡す。R-14は`re_review_request`、R-19は`cycle_summary`。見出し直後に空行、末尾にサイクル状態4キーを各1回置き、`expected_head`をheadShaと一致させる。処理済みIDは数値のカンマ+空白区切り、空なら`なし`。bodyに固定Verdict見出しや`Review Verdict`を混ぜず、サマリへ再依頼トリガーを書かない。
3. 1回だけ投稿する。tool error/isError/不完全応答/受理不明はR-14なら`REREVIEW_COMMENT_FAILED`、R-19なら`SUMMARY_COMMENT_FAILED`。自動再試行・GH connector/ghへの迂回・同一本文の再投稿をしない。投稿済みか不明ならreaderで照合するが、読戻し成功だけで不確実なwriteを成功へ繰り上げず停止・報告する。
4. 成功応答の正の数値文字列`commentId`、非空`url/author`、一致する`headSha`を確認し、`references/comment-reader.md`で同じPRを再取得する。返却IDのissueCommentがちょうど1件、head/baseが固定値と一致し、本文が送信本文（CRLFはLFに統一）と一致すること。新snapshot中の他のコメントも検査する。
5. 返却`author`とreaderのflatな`author`を既存規則で各1回正規化し、ともに`review-raven`かつcanonical allowlist内であること。最初の成功を`cycle_write_author_login`へ保存し、後続投稿も一致を要求する。不一致/未観測は`WRITE_IDENTITY_UNCONFIRMED`、読戻し失敗は該当write失敗として停止する。投稿後にHEADが動いたら`REVIEW_HEAD_MISMATCH`で停止する。
6. 再依頼は投稿と読戻しが成功してから既存のqueue/購読手順へ進む。tool自体はenqueueやreviewer起動を行わない。webhook構成は既存契約どおり二重enqueueしない。

対応サーバー配備→必要な実PRサマリで名義/読戻し確認→このrevision配布の順を守る。
