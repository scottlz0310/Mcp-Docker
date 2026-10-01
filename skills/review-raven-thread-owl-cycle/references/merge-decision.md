# マージ判断（Phase 8）

SKILL.md の「Phase 8: マージ判断」から移した手順（内容は変更していない）。

## Phase 8: マージ判断

**自律的にマージしない。** ユーザーからの明示的な指示を待つ。

マージ条件（ユーザー指示時に満たすこと）:
- CI 全ジョブ SUCCESS
- 未解決の review 指摘 = 0 件
- 全スレッドに返信済み
- 未解決の `blocking` 項目なし
- `termination_status` が `READY_TO_MERGE` または `ESCALATE — Clean`
- Phase 7.5 の完了記録が `mcp-docker reviewgate validate` を通過していること。`reviewed` 通知、CIグリーン、未解決0件だけでは代用しない。
- **`termination_status = READY_TO_MERGE` の場合**: thread-owl の Verdict コメント（`normalize_login(author.login)` が canonical allowlist の `thread-owl` と一致し、Phase 7 の「Verdict 照合規則」で書式一致するもの）が存在し、その `Reviewed HEAD SHA` が現在の PR HEAD SHA と一致すること（Phase 7 で確認済みであること）。
  - 該当コメントが存在しない、または SHA が不一致の場合は `AWAITING_THREAD_OWL_VERDICT` としてマージ判断に進まず、Phase 7 の Verdict コメント確認へ戻ります。
- **`termination_status = ESCALATE — Clean` の場合**: Verdict コメント確認は対象外です（最大サイクル超過につき現在の HEAD に対する新しい Verdict が存在し得ないため。Phase U6「終了分類」参照）。マージには下記の `ESCALATE — Clean` 対応に従い、明示的な人間確認が必要です。

`termination_status = ESCALATE — Clean` の場合:
1. 無条件に「マージ準備完了」とは報告しない。
2. 最終修正サイクルが thread-owl に再レビューされていない旨（Verdict コメント確認は対象外である旨）を明記する。
3. ユーザーがそれでもマージを要求する場合は、thread-owl の最終再レビューなしでのマージを許容することを明示的に確認する。

`termination_status = ESCALATE — Unverified Fix` の場合:
1. CI グリーン・未解決 0 件でも **マージ準備完了とは報告しない**。
2. 未検証コミット SHA を付けて警告を明確に提示する。
3. ユーザーがそれでもマージを要求する場合は、未検証 blocking 修正を手動レビュー済みであることを明示的に確認してから進める。

**`ESCALATE — *` からのサイクル続行**: ユーザーが「続行」（レビューサイクルを継続する）と明示的に指示した場合に限り、指示された分だけ `max_cycles` を延長し、Phase U6 のステップ 3 に戻って `@thread-owl re-review requested` の投稿と起動モードに応じた queue 登録を行う。**エージェントの判断で延長して続行してはならない。** 延長が妥当と考える場合は、理由（未収束の根本原因・残る blocking など）を添えてユーザーに提案するにとどめ、指示を待つ。

`termination_status = AWAITING_THREAD_OWL_VERDICT`（Verdict コメント未確認・不一致）の場合:
1. マージ準備完了とは報告しない。
2. 理由を区別して報告する。「Verdict 未投稿」と「書式不一致」を同じ文言にまとめない。
   - `VERDICT_NOT_POSTED`: 「thread-owl の Verdict コメントが未投稿です。thread-owl 側のレビュー完了を待機してください。」
   - `VERDICT_FORMAT_MISMATCH`: 「thread-owl の Verdict コメント（comment <ID>）が照合規則に一致しません（不一致の行: …）。reviewer 側に固定書式での再投稿を依頼してください。」
   - `VERDICT_HEAD_MISMATCH`: 「thread-owl の Verdict コメント（comment <ID>）の Reviewed HEAD SHA が現在の PR HEAD と不一致です。現在の HEAD に対する再レビューを待機してください。」
3. thread-owl から新たな Verdict コメントが投稿され次第、Phase 7 の Verdict コメント確認からやり直す。

`termination_status = WAITING_FOR_REVIEW(thread-owl)`（`--webhook-mcp-http` で再レビューコメント投稿済み、または Phase W が停止した）の場合:
1. マージ準備完了とは報告しない。
2. 「thread-owl への再レビュー依頼済み。次の review cycle 待機中。」と報告する。
