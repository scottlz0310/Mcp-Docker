# レビュー対応サマリの template（Phase 7・R-19）

SKILL.md の「Phase 7: サマリコメント投稿」から移した template（内容は変更していない）。

`{GH}:add_issue_comment` で以下を PR に投稿する:

```markdown
## レビュー対応サマリ（thread-owl）

### 修正内容
- （概要を箇条書き）

### 採否判断
- accept: N 件
- reject: M 件
  - Thread <threadId> (PRRT_xxx): （理由）

### 先送り・スコープ外項目
- なし | <リスト: Thread <threadId> — Follow-up: #N>

### 検証
- CI: ...
- カバレッジ: <Codecov 要約: patch X%, project Y% (モード: gate / informative, 閾値: Z% | 未定義)> | 未確認（理由）
- 未解決指摘数: 0
- thread-owl Verdict: 確認済み (Reviewed HEAD SHA: `<SHA>`) | AWAITING_THREAD_OWL_VERDICT（VERDICT_NOT_POSTED | VERDICT_FORMAT_MISMATCH: comment <ID> | VERDICT_HEAD_MISMATCH: comment <ID>）
- サイクルステータス: <termination_status>
  - `ESCALATE — Unverified Fix` の場合: 理由・未検証コミット SHA・「マージ前に人間レビュー推奨」を明記
- 最終サイクル修正タイプ: blocking × N, non-blocking × N, suggestion × N, trivial × N
- 再レビュー: @thread-owl コメント投稿済み | 不要 | ESCALATE（最大サイクル超過）

### サイクル状態
- cycles_done: N
- max_cycles: 3
- expected_head: `<SHA>`
- handled_comments: ID1, ID2, ...
```

**`先送り・スコープ外項目` ルール**: `out-of-scope` / `deferred` / `follow-up` を理由とする全 reject をフォローアップ Issue 番号付きでリストしなければならない。「なし」は該当 reject が 0 件かつ Phase U5 ステップ 4 で未解決スレッドがない場合のみ許容。
