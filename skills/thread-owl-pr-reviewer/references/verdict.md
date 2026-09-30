# Verdict コメントの投稿

SKILL.md の「Verdict コメント投稿」から移した手順（`verdict: approve` のとき）。後述の「Verdict 照合規則」は SKILL.md にある。

reviewed-side workflow は、マージ判断時に「thread-owl から現在の PR HEAD に対するレビュー完了の証拠が GitHub 上に存在するか」を確認する。指摘がなく沈黙すると、この証拠が残らずマージ判断が進まないデッドロックになる。これを避けるため、次の条件でだけ Verdict コメントを投稿する。

**トリガー条件**

`initial-review` または `re-review` において `verdict: approve` と判定した場合（判定基準は「Verdict」節を参照）。

**振る舞い**

- `{OWL}:approve_pull_request` は呼ばない。GitHub native の APPROVE 権限を自律実行する変更ではない。
- 代わりに `{OWL}:post_review_verdict` で Verdict コメントを、本節冒頭の投稿判断基準に従って投稿する。入力は `owner`、`repo`、`prNumber`、`headSha = reviewedHeadSha`、`summary` の 5 つである。
- **reviewed-side 連携の必須要件**: reviewed-side workflow（`review-raven`）は後述の「Verdict 照合規則」で見出し行・HEAD 行・Status 行を機械的に照合してマージゲートを判定する。一致しなければ reviewed-side cycle は `AWAITING_THREAD_OWL_VERDICT` で止まる。この 3 行は `{OWL}:post_review_verdict` が server 側で組み立てるので、**skill 側では書かない**。

**`summary` の書き方**

`summary` は server 側が見出しと `---` 区切り線の間に入れる自由記述部分であり、次を含める。

- 判定文: 技術的・品質的にマージ可能な状態である（マージ推奨）と判定したこと。
- 主な確認観点: Independent Stage や Synthesis Stage で実際に確認・評価した PR 固有の観点（境界値・異常系、後方互換性、テストによる仕様の固定、CI の成否と対象 SHA の一致など）。固定定型文の羅列で済ませない。
- 判定根拠: なぜ問題なし・マージ可能と判断したかの具体的要約。再レビューの場合は前回指摘事項の解消確認を含む。
- 実装者判断による不対応（declined-by-implementer）がある場合: 指摘内容と残存リスク（「実装者判断により不対応。残存リスクは〈内容〉」）を明記する。

見出しは `### レビューサマリー` など `##` 未満のレベルにする。変更が小さい PR（リリース準備、バージョン番号の更新だけ等）では短くしてよい。

`summary` に次を含めない。含めると tool が投稿せず error を返す。

- 部分文字列 `Review Verdict`（見出しに限らない）
- 「Verdict 照合規則」の 3 正規表現のいずれかに一致する行（`- Reviewed HEAD SHA: ` や `- Status: ` の行を自分で書かない）

**投稿前後の検証（必須）**

1. 投稿前: `summary` を上記 2 条件で検証する（行分割は「Verdict 照合規則」の手順 1 に従う）。満たさない場合は投稿せず `VERDICT_FORMAT_INVALID` として停止する。予約行を削って投稿し直すのではなく、停止して報告する。
2. 投稿: `{OWL}:post_review_verdict` を 1 回だけ呼ぶ。head 不一致の error は `STALE_REVIEW`、それ以外の error・結果不明は `VERDICT_POST_FAILED` として停止し、即時再実行しない。結果不明の場合は `gh api repos/<owner>/<repo>/issues/<pr>/comments --paginate` の read-only で重複を確認してから報告する。
3. 投稿後: 戻り値の `commentId` の本文を `gh api repos/<owner>/<repo>/issues/comments/<commentId>` の read-only で取得し、「Verdict 照合規則」で書式一致と HEAD 行のキャプチャが `reviewedHeadSha` と完全一致することを検証する。不一致なら `VERDICT_FORMAT_INVALID` として comment ID と不一致の行を報告し、停止する。重複 Verdict を作らないよう再投稿しない。
4. 投稿後の本文を read できない場合は `verdict post-verification: not performed` と記録して報告する。検証済みとは書かず、再投稿もしない。
5. comment ID、投稿前後の検証結果を evidence に残す。

- この Verdict コメント投稿自体は、上記の投稿判断基準（本節冒頭のリスト）にそのまま従う。承認不要の新たな自律アクションとして追加するものではない。
