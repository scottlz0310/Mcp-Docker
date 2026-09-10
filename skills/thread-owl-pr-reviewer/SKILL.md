---
name: thread-owl-pr-reviewer
description: thread-owl MCP を使う reviewer-side GitHub Pull Request review。PR URL または Thread Owl queue を起点に、初回レビュー、再レビュー、thread follow-up、summary-only を実行し、既存レビューと重複しない高価値な日本語コメントを投稿する。failure path、回帰、security、CI、packaging、テスト不足を独立検出するときに使う。コード変更、resolve、merge は行わない。
---

# Thread Owl PR Reviewer

Thread Owl を reviewer-side の GitHub App として使い、PR を独立レビューして必要な指摘だけを投稿する。

## 責務境界

- コード変更、commit、push、branch 操作、merge を行わない。
- review thread を resolve / unresolve しない。修正側 workflow の責務とする。
- `@thread-owl re-review requested` の投稿と、それに伴う `enqueue_review(reason: "re-review-requested")` による review queue への登録は、いずれも修正側 workflow の責務とする。reviewer 側からは行わない。
- レビュー完了時に、実装 CLI へ渡す次アクションを**テキストとして提示する**（「ハンドオフ提示」節）。提示にとどめ、修正側 skill を自分で起動しない。
- レビュー判断、コメント生成、merge readiness 判定を行う。Thread Owl 自体に LLM があると仮定しない。
- レビュー本文、GitHub 投稿、ユーザー報告を日本語で書く。
- token、cookie、Authorization header、秘密鍵、環境変数値を出力しない。

## レビュー原則

- 推測を事実として断定しない。仕様意図や実行条件が不足する場合は `question` にする。
- style nit、既存コードだけに由来する問題、PR の目的外の大規模改善を投稿しない。
- 既存レビューへの同意、言い換え、根拠の弱い追従を投稿しない。
- 再レビューで、初回に出さなかった軽微な指摘を後出ししない。
- 指摘がない場合はコメントを作らない。ただし `initial-review` / `re-review` で `verdict: approve`（後述の「Verdict」節を参照）と判定した場合は例外とし、「Verdict コメント投稿」節に従ってレビュー観点サマリーを含む Verdict コメントを投稿する。
- 書き込み失敗が曖昧な場合は、同じ投稿を即時再実行せず thread を再取得して重複を確認する。

## Thread Owl 契約

Thread Owl の logical alias `{OWL}` を、実行中 client の discovery 結果から解決して読み取り・投稿の第一候補にする。skill 本文に client 固有の server 名・tool 名・namespace を書かず、未ロードなら client-native の tool / resource discovery を行う。

| 操作 | 契約 |
| --- | --- |
| `{OWL}:get_pr` | `owner`、`repo`、`prNumber` から `pr` と `files` を返す。`pr.head.sha`、`pr.base.sha`、各 file の `patch` を記録する |
| `{OWL}:list_review_threads` | resolved / outdated 状態とコメントを含む review thread 一覧を返す |
| `{OWL}:post_inline_comment` | `commitId`、`path`、`line`、`body` を指定して current diff に投稿する |
| `{OWL}:reply_review_thread` | `threadId` へ返信する。thread の所属 repository は server 側でも allowlist 照合される |
| `{OWL}:post_summary_comment` | PR conversation に issue comment として summary を投稿する。blocking 0件・全 review thread resolved 時の Verdict コメント投稿にも使う（「Verdict コメント投稿」節参照） |
| `{OWL}:approve_pull_request` | `expectedHeadSha` と現在の head が一致する場合だけ APPROVE review を送る |

`{OWL}:get_pr` は CI status、check logs、通常の issue comment 全文を返さない。必要な read-only の補完だけ GitHub connector または `gh` で行う。Thread Owl で提供されない書き込みを別経路へ迂回しない。

Thread Owl は `REQUEST_CHANGES`、resolve、unresolve、merge を提供しない。`request changes` は verdict と blocking comment で表現し、未実装操作を代替経路で送らない。

### CI read capability

`get_check_runs` は client 固有の tool 名ではなく、PR 番号を入力として check run ごとの `status`、`conclusion`、対象 SHA（`head_sha` / `sha` または同等のフィールド）を返す論理 read capability として扱う。利用可能な client-native capability は schema で discovery し、候補が一つの場合だけこの run に binding する。候補が無い、複数候補を一意に選べない、または対象 SHA を返さない場合は `CI: unknown` とし、combined status や write 経路で代替しない。失敗ログ用の workflow run / job / log capability は任意の補助 capability であり、client ごとに有無が異なる。

### O-00: `{OWL}` の discovery と固定

`{OWL}` の候補は、tool / resource の表示名や client 固有の namespace の文字列一致ではなく、Thread Owl の logical capability と input / output schema で判定する。候補の識別単位は server instance / route と opaque handle の組み合わせであり、同名の tool が別 route に存在しても一つにまとめない。

1. PR URL 起点では `owner`、`repo`、`prNumber` を確定してから候補を列挙する。queue 起点では、まず review queue resource を discovery し、resource read で candidate の `owner`、`repo`、`prNumber`、`reason` を取得する。
2. host / client の設定に `{OWL}` の明示 binding があれば優先する。それがなければ、必要な read / write capability と schema を満たす候補が一つだけの場合に限り採用する。複数候補が残った場合は discovery 順や表示名だけで選ばず、`BLOCKED_MCP_DISCOVERY` として停止する。
3. 採用候補で、PR URL 起点なら `{OWL}:get_pr`、queue 起点なら queue resource read と `{OWL}:get_pr` のうち対象を確認できる最小 read を **1 回成功** させる。成功とは tool / resource error がなく、PR identity・head SHA などの minimum output schema を満たすことをいう。server 一覧、`Connected` 表示、schema 取得だけでは成功とみなさない。
4. `{OWL}` から選択済み server / route / handle への binding を run の状態に固定し、以後の全 read / write で同じ binding を使う。後続の接続失敗、schema 不一致、allowlist 拒否を別 candidate や GitHub connector / `gh` の write に切り替える理由にしてはならない。

候補を解決できない、未接続、schema 不一致、read 検証失敗、または複数候補を一意に選べない場合は、次の状態で停止する。

```text
termination_status = BLOCKED_MCP_DISCOVERY
status = blocked
```

対象 PR（確定済みの場合）、logical alias `{OWL}`、必要 capability、候補数、失敗分類（unresolved / not connected / schema mismatch / read failed / ambiguous）、read 検証結果、`writes performed: 0`、再実行に必要な設定変更を報告する。token・Authorization header・秘密情報は報告しない。別の MCP candidate、GitHub connector、`gh` write 経路へ進まず、レビューコメント・Verdict・APPROVEを投稿しない。

この binding は initial review、re-review、thread follow-up、summary-only の全モードで共通に使用する。再 discovery による途中の候補切り替えは禁止する。

## Queue 契約

PR が明示されず queue 待機を依頼された場合だけ subscription を使う。

| Resource | 用途 |
| --- | --- |
| `queue://review/queue` | `opened` / `synchronized` / `re-review-requested` を含む通常レビュー起動 |
| `queue://review/re-review-requests` | `re-review-requested` だけを受ける reviewer-side handoff |

再レビュー待機では必ず `queue://review/re-review-requests` を使う。通常 queue では先行する `synchronized` 通知で待機が終了し、直後の再レビュー依頼を見逃す可能性がある。

native `subscriptions/listen` が使えなければ、repository の運用ガイドに従って `mcp-resource-subscriber`（v0.6.0 以降）を使う。

```powershell
bunx mcp-resource-subscriber `
  --url $env:THREAD_OWL_MCP_URL `
  --uri queue://review/re-review-requests `
  --timeout-ms 900000 `
  --json
```

`json.route` が `"subscription"` または `"pre-completion"` であることを確認し、`json.finalText` をパースして `owner`、`repo`、`prNumber`、`reason` を取得する。`route` が `"timeout"` または `"failed"` の場合はレビュー完了として扱わない。

## モード選択

依頼から次のモードを選ぶ。PR URL だけでレビューを依頼された場合は `initial-review` とする。

モードを決めた直後、queue 待機またはレビュー本文の取得に入る前に O-00 を実行する。`{OWL}` の binding と read 検証が成功するまで、Independent Stage、Filter Stage、各種コメント投稿、Verdict、APPROVEへ進まない。

### `initial-review`

PR 全体を初回レビューする。queue candidate の `reason` が `opened` または通常の `synchronized` の場合も使う。

### `re-review`

前回指摘への対応、未解決 thread、対応後の重大な回帰、CI の変化を確認する。candidate の `reason` が `re-review-requested` の場合はこのモードにする。

### `thread-follow-up`

指定 thread の文脈、実装者の返信、対応差分だけを確認して返信する。

### `summary-only`

インラインコメントを投稿せず、merge readiness と残存リスクをまとめる。ユーザーが投稿を明示していなければ draft のみ返す。

## Snapshot Guard & Repository State Guard

### 1. Remote Snapshot の原則
- レビュアーは現在のローカル作業ツリーをレビュー対象として信頼してはならない。GitHub から取得した PR HEAD SHA（`reviewedHeadSha`）を唯一のレビュー対象として固定する。
- PR metadata / diff / 変更ファイルは `{OWL}:get_pr` を第一候補にする。
- GitHub connector や `gh` で補完する場合も、必ず `reviewedHeadSha` を明示して取得する。branch 名だけを指定した読み取りは禁止する（レビュー中に branch が更新されて内容が変化し得るため、commit SHA を使用する）。

### 2. ローカル検証時の Repository State Guard
ローカル環境でコード参照、ビルド、テスト、静的解析等を行う場合は、開始前に以下を確認する。
1. `git status --porcelain --untracked-files=no` が空（tracked file に変更がない状態）であること
2. `git rev-parse HEAD` が `reviewedHeadSha` と一致すること
いずれかを満たさない場合、現在の worktree をレビュー根拠として使用してはならない。

- **dirty/mismatched な状態の扱い:**
  - 未 commit 変更を stash / discard してレビューを続行してはならない（実装担当の作業状態を破壊しないため）。
  - detached worktree または一時的な clone を作成し、`reviewedHeadSha` を checkout して検証する。
    - 推奨例:
      ```bash
      git fetch origin <reviewedHeadSha>
      git worktree add --detach <temporary-path> <reviewedHeadSha>
      # 検証完了後
      git worktree remove <temporary-path>
      ```
  - 隔離検証環境を作成できない場合は、ローカル検証を行わず `local verification: not performed` としてレビューを進行する。

### 3. 検証後の再確認ゲート
ビルドやテストが完了した後、かつ投稿処理（Snapshot Guard）の直前に、以下を再確認する。
1. 検証環境の `HEAD` が `reviewedHeadSha` のままであること
2. 検証環境の `git status --porcelain --untracked-files=no` が空であり、tracked file に変更がないこと
3. 現在の GitHub 上の PR HEAD SHA が `reviewedHeadSha` のままであること

次の場合は stale review として投稿（inline comment や APPROVE）を停止する。
- レビュー中に PR HEAD が変更された
- 検証処理によって tracked file が書き換えられた、または HEAD が意図せず移動した
（生成物などの untracked file は許容するが、tracked file の変更は厳禁とする）

### 4. CI 検証の SHA 固定
- **状態集約**: CI 判定の直前に固定済み `{OWL}:get_pr` を read し、現在の PR HEAD SHA を `reviewedHeadSha` として固定する。その直後に check-runs read capability の `get_check_runs` を PR 番号で **1 call** 実行する。`get_check_runs` は SHA を受け取らないため、返却された各 check run の `head_sha` / `sha`（または同等の対象 SHA）が `reviewedHeadSha` と一致することを確認する。対象 SHA を確認できない応答は `CI: unknown` とし、成功扱いにしない。
- `CI: success` は、`reviewedHeadSha` に対するすべての required checks が `status: completed` かつ `conclusion: success` の場合だけにする。required check が未返却、または `queued` / `in_progress` / `pending` の場合は `CI: pending`、required check に `failure` / `cancelled` / `timed_out` / `action_required` / `startup_failure` / `skipped`（リポジトリ方針で明示的に許可されていない場合）などの結論があれば `CI: failure` とする。optional check の結果は別途記録する。`combined status` は使用禁止であり、その応答を「実行中」や成功の根拠にしてはならない。
- **失敗ログ**: `CI: failure` の場合、現在の client に workflow run / job / log の read capability があれば、その capability で失敗 job のログを取得する。client にその capability がなければ `gh run view <run-id> --log-failed` を read-only のフォールバックとして使う。失敗ログ取得の可否は client 依存であり、いずれの経路も利用できない場合は `CI: unknown` として記録し、Verdict / APPROVE を投稿せず停止する。
- 最終的な verdict（判定）の根拠とした CI の対象 SHA を確認・記録する。
- **HEAD 移動時の再確認**: 検証結果の採用または APPROVE 投稿の直前に、`{OWL}:get_pr` を再度 read して PR HEAD が `reviewedHeadSha` のままであることを確認する。HEAD が動いた場合は、以前の check runs 結果を破棄し、新しい current head を固定して `get_check_runs` を再実行する。再取得または SHA 照合ができない場合は `CI: unknown` とし、Verdict / APPROVE を停止する。

### 5. 再レビュー依頼の期待 HEAD 照合
- candidate queue などの再レビュー依頼に `expected_head` が含まれる場合、開始時に `candidate.expected_head` と、固定済み `{OWL}` binding の `get_pr(...).pr.head.sha` を比較する。
- 不一致の場合は古い再レビュー依頼とみなし、そのまま APPROVE せず、最新の HEAD を新しいレビュー対象としてレビューをやり直すか、明示的に処理を停止する。

### 6. 既存 Snapshot Guard の維持
- `{OWL}:post_inline_comment.commitId` と `{OWL}:approve_pull_request.expectedHeadSha` には、最終確認済みの同じ head SHA (`reviewedHeadSha`) を使う。
- inline の `path` と `line` が current diff 上の投稿可能な位置であることを確認する。確実でなければ PR-level summary にする。

## Initial Review

初回レビューは次の順序を守る。Independent Stage が終わるまで、既存 review comment、review thread、review summary の本文を読まない。

### 1. Independent Stage

1. PR の owner、repo、番号、title、description、base/head、head SHA を確認する。
2. diff、変更ファイル、関連実装、テスト差分を読む。
3. CI は Snapshot Guard の check-runs 契約（current head SHA を先に固定し、`get_check_runs` の対象 SHA を照合する）で確認する。failed/skipped checks、packaging、docs、release への影響も確認し、確認経路がなければ `CI: unknown` と記録する。
4. 既存レビューを参照せず、独立した懸念候補を作る。
5. 次の非主要パスを横断確認する。
   - 空、null、不正値、境界値、巨大入力、重複入力
   - 初回実行、再実行、二重実行、キャンセル、部分成功、失敗後リトライ
   - timeout、fallback、例外変換、権限不足、secret 欠落、token 失効
   - 既存設定、既存データ、旧バージョン、migration、後方互換性
   - Windows / Linux / macOS、local / CI、開発 / 配布環境の差
   - UI / domain / infrastructure / persistence / CLI / CI の責務境界
   - エラーメッセージ、ログ、通知、復旧導線
6. テストが実装詳細ではなく、PR が壊してはならない仕様を固定しているか確認する。

この段階では候補を投稿しない。

### 2. Filter Stage

1. `{OWL}:list_review_threads` と必要な GitHub 読み取り経路で、既存 review、thread、実装者返信を初めて読む。
2. 既存レビューが扱った行、条件、リスク種別、edge case、修正方針を整理する。
3. Independent Stage の候補から次を削除する。
   - 同じ条件、結論、修正方針を繰り返すもの
   - 新しい再現条件や影響範囲を加えないもの
   - resolved、outdated、または現 head で対応済みのもの
   - 同意、言い換え、根拠の弱い追従
4. 次だけを残す。
   - 未指摘の failure path、edge case、integration point
   - より具体的な再現条件、影響範囲、テスト観点を示せるもの
   - 同じファイルでも別責務、別経路、別ユースケースの問題
   - マージ後に発覚すると手戻りが大きい問題

既存レビューはレビュー範囲の上限ではなく、重複投稿を防ぐマスクとして扱う。

### 3. Synthesis Stage

各候補について、根拠、重大度、投稿位置、対応可能性を確認する。

1. `blocking` / `non-blocking` / `question` / `note` / `praise` に分類する。
2. 特定 diff 行に直接対応する指摘だけ inline にする。
3. 複数ファイルにまたがる設計、運用、CI、packaging、release の問題は PR-level summary にする。
4. 再現条件、影響、期待する次の行動を短く書く。
5. 根拠が弱い、差分価値が薄い、対応方法が不明、コメント過多を招く候補を削除する。
6. Snapshot Guard を再確認してから投稿する。

## コメント分類

- `blocking`: correctness、security、privacy、data loss、主要ユースケース、CI、packaging、release の明確な問題。
- `non-blocking`: merge を止めない保守性、テスト、UX、DX 改善。後続対応可能であることを明記する。
- `question`: 仕様意図や既存仕様を確認しないと断定できない論点。
- `note`: docs、release note、follow-up issue で追う価値がある論点。
- `praise`: 回帰リスク低減、責務分離、テスト容易性など明確な価値がある判断。過剰に投稿しない。

投稿本文は簡潔にする。

```markdown
[blocking] XXX の条件では YYY となり、ZZZ が失敗します。
AAA のケースをテストで固定し、BBB の処理を見直してください。
```

```markdown
[question] この分岐は AAA も対象にする意図でしょうか？
既存仕様では BBB と読めるため、期待する挙動を確認したいです。
```

## 投稿判断

PR URL を示してレビューと投稿を依頼された場合、根拠が固い inline comment と通常の review comment は投稿まで行う。次は投稿前にユーザーへ確認する。

- PR 全体方針を覆す大きな指摘
- blocking 判定が微妙
- release / operation の意思決定を含む
- 既存コメントとの重複が疑わしい
- コメント候補が 5 件を超える
- 投稿対象 PR、head、line、thread を確実に特定できない
- `summary-only` の summary 投稿を明示されていない

### Verdict コメント投稿

reviewed-side workflow は、マージ判断時に「thread-owl から現在の PR HEAD に対するレビュー完了の証拠が GitHub 上に存在するか」を確認する。指摘がなく沈黙すると、この証拠が残らずマージ判断が進まないデッドロックになる。これを避けるため、次の条件でだけ Verdict コメントを投稿する。

**トリガー条件**

`initial-review` または `re-review` において `verdict: approve` と判定した場合（判定基準は「Verdict」節を参照）。

**振る舞い**

- `{OWL}:approve_pull_request` は呼ばない。GitHub native の APPROVE 権限を自律実行する変更ではない。
- 代わりに `{OWL}:post_summary_comment` でレビュー観点・検証結果のサマリーを含む Verdict コメントを、本節冒頭の投稿判断基準に従って投稿する。
- **reviewed-side 連携の必須要件**: reviewed-side workflow（`review-raven`）は `## @thread-owl Review Verdict: APPROVED`、`Reviewed HEAD SHA`、`Status: READY_TO_MERGE` を機械的に検出してマージゲートを判定する。そのため、**見出し行および末尾のメタデータ行の形式・文言は変更せず、その間にレビューサマリーを記述する**こと。

```markdown
## @thread-owl Review Verdict: APPROVED

すべての対象コードの検証が完了しました。技術的・品質的にマージ可能な状態である（マージ推奨）と判定しました。

### レビューサマリー
- **主な確認観点**:
  - （例: 境界値・異常系入力に対する堅牢性、エラーハンドリング）
  - （例: 既存仕様・設定との後方互換性やマイグレーション影響）
  - （例: 型安全性、テストコードによる仕様の固定状況）
  - （例: CI（build, test, lint, coverage）の成否と実行対象 SHA の一致）
- **判定根拠**: （なぜ問題なし・マージ可能と判断したかの具体的要約。再レビューの場合は前回指摘事項の解消確認を含む）

---
- Reviewed HEAD SHA: `<reviewedHeadSha>`
- Status: `READY_TO_MERGE`
```

- サマリー内容は固定定型文の羅列で済ませず、Independent Stage や Synthesis Stage で実際に確認・評価した PR 固有の観点・根拠を反映すること。
- `<reviewedHeadSha>` は Snapshot Guard で確認済みの `reviewedHeadSha` と一致させる。
- この Verdict コメント投稿自体は、上記の投稿判断基準（本節冒頭のリスト）にそのまま従う。承認不要の新たな自律アクションとして追加するものではない。

### APPROVE 投稿とマージ判断について

`{OWL}:approve_pull_request` はユーザーが明示的に APPROVE 投稿を依頼した場合だけ実行する。実行直前に `{OWL}:get_pr` で head SHA と CI を再確認する。CI が unknown、blocking が残る、または head が変わった場合は実行しない。

安全性の観点（自動マージや自動デプロイがトリガーされるリスク等）から、明示的な許可（指示）がない限り、自律的に `APPROVE` を送信してはならない。

マージ判断の伝わりやすさを担保するため、以下の運用ルールを適用する。
- **レビュー結果の明記:** レビューの要約やコメントにおいて、「技術的・品質的にマージ可能な状態である（マージ推奨）」という評価自体は日本語で明確に報告する。
- **ユーザーの指示による実行:** ユーザーから「APPROVEを投稿してください」という明示的な許可（指示）をチャット上でいただいた段階で、エージェントが実際の `approve_pull_request` 送信を実行する（マージ処理自体は別ワークフローの責務であり、本スキルでは行わない）。

## Re-review

1. queue 起点なら `reason = re-review-requested` と対象 PR を確認する。
2. 前回 thread、実装者返信、現 head、前回レビュー後の差分を読む。
3. 各 thread の `isResolved` / `isOutdated` 状態と、現 head での対応状況を確認する。
4. 未解決 thread と、対応差分が導入した重大な回帰だけを確認する。
5. CI の変化を確認する。
6. 次の投稿経路表に従って各 thread を処理する。

| 元 thread の状態 | 現 head での状態 | 投稿方法 |
| --- | --- | --- |
| unresolved | resolved in code | 元 thread へ簡潔に返信する。thread 自体は resolve しない |
| unresolved | partially resolved / not resolved / needs clarification | 元 thread へ残存再現条件を具体的に返信する |
| resolved / outdated | resolved in code | 新規コメントを投稿しない。必要なら PR summary のみで解消を報告する |
| resolved / outdated | partially resolved / not resolved / needs clarification | current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 unresolved thread を作る |

新規 inline comment には、以前の指摘の継続であることと、現 head に残る具体的な再現条件を記載する。元 thread への重複返信は行わない。

current diff 上に投稿可能な行がない場合は、無理に stale な位置へ投稿せず PR-level summary に blocking と残存条件を明示する。

新規 inline を投稿する前に Snapshot Guard を再実行し、現 head SHA と投稿可能行を確認する。

7. 初回レビューで出さなかった軽微な新規指摘を追加しない。
8. 新しい blocking がある場合だけ新規 inline comment を検討する。

## Thread Follow-up

1. 指定 thread と current head を特定する。
2. thread の `isResolved` / `isOutdated` 状態を確認する。
3. thread の root comment、全返信、対応差分だけを読む。
4. `resolved in code` / `partially resolved` / `not resolved` / `needs clarification` を判断する。
5. 新しい独立論点を同じ thread に混ぜない。
6. Re-review の投稿経路表と同じルールを適用する。
   - thread が unresolved なら `{OWL}:reply_review_thread` で返信する。resolve は行わない。
   - thread が resolved / outdated で問題が残るなら、current diff 上の関連行へ `{OWL}:post_inline_comment` で新規 thread を作る。元 thread への返信は行わない。
   - current diff 上に投稿可能な行がない場合は PR-level summary にする。

## Verdict

- `approve`: 新規 `blocking` 指摘がなく、既存 review thread がすべて resolved であり（分類を問わない。`non-blocking` / `question` の未解決も許容しない）、主要リスクのテストまたは説明があり、CI が成功している。「技術的・品質的にマージ可能な状態である（マージ推奨）」という判断結果であり、ユーザーへの報告で明記する。明示的な許可（指示）がない限り、実際の `APPROVE` 投稿は行わない。`initial-review` / `re-review` でこの判定に至った場合は「Verdict コメント投稿」節に従って Verdict コメントを投稿する。
- `request changes`: blocking が残る。Thread Owl に REQUEST_CHANGES tool はないため、blocking comment と verdict の報告に留める。
- `comment only`: 判断材料が不足し、question が中心。
- `needs follow-up`: merge 可能だが、別 issue または後続 PR で追う論点がある。

## ユーザー報告

```markdown
## Review result

- PR: ...
- mode: initial-review | re-review | thread-follow-up | summary-only
- reviewed head: <SHA>
- source of truth: remote PR snapshot
- local verification: isolated worktree | clean matching worktree | not performed
- local verification head: <SHA | n/a>
- CI head: <SHA | unknown>
- verdict: approve | request changes | comment only | needs follow-up
- CI: success | failure | unknown
- posted: 新規inline N 件、thread 返信 N 件、summary N 件、approve N 件
- blocking: N 件（新規inline N 件 / thread 返信 N 件）
- residual risk: ...

## Independent review delta

- 既存レビューで扱われていた範囲: ...
- 今回追加で確認した死角: ...
- 投稿を見送った重複候補: ...
```

queue を使った場合は resource URI、candidate reason、subscription route も報告する。指摘がない場合は、レビュー済み範囲と残存リスクだけを報告する。

## ハンドオフ提示

`initial-review` / `re-review` を終えたら、ユーザー報告の**最後に**次アクションを提示する。レビュー指摘への対応は、その PR を実装した CLI エージェントが同一セッションで引き受けるのが最良であり（実装時の設計意図・トレードオフ・棄却案がコンテキストに残っており、リポジトリとスレッドの再調査が要らない）、reviewer 側がここで停止して実装側へ渡すのが正しい。`thread-follow-up` / `summary-only` では提示しない。

verdict によって提示内容を分ける。

### 対応が必要な場合（`request changes` / `comment only` / `needs follow-up`）

そのまま実装 CLI へ貼り付けられる 1 行を、**コードブロックに単独で**出力する。前後に説明を混ぜず、コピーしてそのまま使える形にする。

```
/review-raven-thread-owl-cycle <owner>/<repo>#<pr> のレビュー指摘に対応してください
```

続けて 1 行で、投稿した blocking 件数と未解決 thread 数を添える。

### サイクル終了とみなせる場合（`verdict: approve`）

対応プロンプトは出さない。新規 `blocking` がなく全 thread が resolved でありサイクルが終了したことを示し、次アクションが**人によるマージ判断**であることを述べる。

```
レビューサイクル完了: <owner>/<repo>#<pr>（Verdict: APPROVED / Reviewed HEAD SHA: <SHA>）
```

### 制約

- 提示はテキスト出力に限る。**このスキルは実装側 skill を自分で起動しない。** reviewer と reviewed は別セッションで動かす。
- `<owner>` / `<repo>` / `<pr>` / `<SHA>` は実際の値に展開する。プレースホルダーのまま出力しない。
- コードブロックにはプロンプト 1 行だけを入れる。ここは機械的に読み取られる前提の出力である（Squirrel Notifier のハンドオフポップアップがこの行をコピー対象として扱う）。
- 実際にマージするかどうかは判断しない。マージは常に人の明示的な操作を挟む。
