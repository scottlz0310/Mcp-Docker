# Re-review と Thread Follow-up

SKILL.md の「Re-review」「Thread Follow-up」から移した手順。

## Re-review

1. queue 起点なら `reason = re-review-requested` と対象 PR を確認する。
2. 前回 thread と全返信、PR-level の question と作成者の後続コメント、現 head、前回レビュー後の差分を読む。回答は根拠として再評価し、未回答の同じ質問を再投稿しない。
3. 各 thread の `isResolved` / `isOutdated` 状態と、現 head での対応状況を確認する。
4. 未解決 thread と、対応差分が導入した重大な回帰だけを確認する。
5. CI の変化を確認する。
6. 次の投稿経路表に従って各 thread を処理する。

| 元 thread の状態 | 現 head での状態 | 投稿方法 |
| --- | --- | --- |
| unresolved | resolved in code | 元 thread へ簡潔に返信する。thread 自体は resolve しない |
| unresolved | partially resolved / not resolved / needs clarification | 元 thread へ残存再現条件を具体的に返信する。ただし未回答の `[question]` と同じ確認は再投稿しない |
| unresolved | declined-by-implementer | 元 thread へ実装者の判断を確認した旨と残存リスクを簡潔に返信する |
| resolved / outdated | resolved in code | 新規コメントを投稿しない。必要なら PR summary のみで解消を報告する |
| resolved / outdated | partially resolved / not resolved / needs clarification | current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 unresolved thread を作る |
| resolved / outdated | declined-by-implementer | 新規コメントを投稿しない。実装者による不対応判断と残存リスクを完了サマリー（`residual risk` 欄）および Verdict の summary に記録する |

実装者が返信で理由（Won't fix、仕様上の意図、別 Issue での対応方針など）を明示して thread を resolve している場合は、コード上の条件が残っていても `not resolved` と判定せず `declined-by-implementer` とする。同一論点の新規 thread を再作成してはならない（再掲ループ・デッドロックを防ぐため）。残存リスクは完了サマリー（`residual risk` 欄）および Verdict の summary に記録し、マージ判断を行う人間に明示する。

新規 inline comment には、以前の指摘の継続であることと、現 head に残る具体的な再現条件を記載する。元 thread への重複返信は行わない。

current diff 上に投稿可能な行がない場合は、無理に stale な位置へ投稿せず PR-level summary（「レビュー完了サマリー」節の 1 件）に blocking と残存条件を明示する。

新規 inline を投稿する前に Snapshot Guard を再実行し、現 head SHA と投稿可能行を確認する。

7. 初回レビューで出さなかった軽微な新規指摘を追加しない。
8. 新しい blocking がある場合だけ新規 inline comment を検討する。

## Thread Follow-up

1. 指定 thread と current head を特定する。
2. thread の `isResolved` / `isOutdated` 状態を確認する。
3. thread の root comment、全返信、対応差分だけを読む。question なら作成者の回答を根拠として再評価し、未回答の同じ質問を再投稿しない。
4. `resolved in code` / `partially resolved` / `not resolved` / `needs clarification` / `declined-by-implementer` を判断する。
5. 新しい独立論点を同じ thread に混ぜない。
6. Re-review の投稿経路表と同じルールを適用する。
   - thread が unresolved なら `{OWL}:reply_review_thread` で返信する。resolve は行わない。
   - thread が resolved / outdated で問題が残るなら、current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 thread を作る。元 thread への返信は行わない。
   - current diff 上に投稿可能な行がない場合は PR-level summary にする。
