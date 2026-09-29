# CI check runs の読み取りと判定

この文書が、`thread-owl-pr-reviewer` における CI 判定の**唯一の定義**である。SKILL.md の O-06、O-15、Snapshot Guard の手順 4 は、この規則に従う。同じ規則を SKILL.md に書き足さない。

## 1. 経路の固定

CI 判定に使う check runs は、**固定済みの `reviewedHeadSha` を入力**として、その commit の check run ごとの `name`、`status`、`conclusion`、対象 SHA（`head_sha`）、run ID、GitHub App を返す論理 read capability から取得する。

- **第一選択**: `{RAVEN}:list_check_runs_for_sha`。
- **fallback**: `{RAVEN}` の discovery 時点でこの capability が無い（review-raven v0.5.0 未満）、または schema が一致しない場合だけ、`gh api "repos/<owner>/<repo>/commits/<reviewedHeadSha>/check-runs?per_page=100" --paginate --jq '.check_runs[] | {id, name, head_sha, status, conclusion, app: .app.slug}'` を read-only で使う。
- **実行時の失敗で経路を切り替えない**: binding 後の tool error（認証系の構造化 error、入力検証 error のいずれも）、transport failure、schema 不一致は `CI: unknown` として停止する。`gh api` は実行ユーザーの token を使う別の認証経路なので、O-00 の「異なる認証経路を自動的に試さない」に反する。
- **PR 番号を入力とし、`head_sha` を返さない capability は CI 判定の根拠にしない**（公式 GitHub MCP の `pull_request_read` の `get_check_runs` など。PR の head が動くと対象が黙って変わるうえ、返却値で SHA を照合できない）。

`{RAVEN}` の discovery は、O-00 の `{OWL}` binding が成功した後に、次の手順で行う。

1. `owner`、`repo`、`sha`（40 桁の小文字 hex）を入力し、`sha`、`check_runs[].head_sha` / `name` / `status` / `conclusion` / `app`、`pagination.complete`、`deduplication.strategy` を返す候補を、表示名ではなく capability と input / output schema で列挙する。
2. host / client の設定に明示 binding があれば優先する。無ければ schema を満たす候補が一つだけの場合に限り採用する。複数候補が残る場合は `{RAVEN}` を未解決として扱う。
3. 採用候補で `reviewedHeadSha` を入力にした read を **1 回成功** させ、「3. 応答の検証」を満たすことを確認する。成功したら binding を run の状態に固定し、以後の CI read はすべて同じ binding を使う。
4. 候補が無い、複数候補を一意に選べない、schema 不一致、read 検証失敗の場合は、`{RAVEN}` を使わないことを run の状態に固定し、上記の `gh api` fallback へ切り替える。この場合も `BLOCKED_MCP_DISCOVERY` にはしない（`{RAVEN}` は任意 capability であり、`{OWL}` と違ってレビュー継続の必須条件ではない）。

どちらの経路を使うかは discovery 時点で決め、run の状態として固定する。

## 2. 読み取り

CI 判定の直前に固定済み `{OWL}:get_pr` を read し、現在の PR HEAD SHA を `reviewedHeadSha` として固定する。その直後に、「1. 経路の固定」で固定した経路を `reviewedHeadSha` で実行する。入力 `sha` には 40 桁の小文字 hex の `reviewedHeadSha` を渡す（branch 名や PR 番号は tool 側で拒否される）。

## 3. 応答の検証

第一選択の応答は次を検証してから使う。満たさない場合は `CI: unknown` とし、combined status や write 経路で代替しない。

- 出力の `sha` が入力の `reviewedHeadSha` と一致すること。
- `pagination.complete` が `true` であること。`false` または欠落は取得未完了として扱う。
- 各 run の `head_sha` が `reviewedHeadSha` と一致すること。対象 SHA を確認できない run は成功扱いにしない。
- 再実行 run の集約は tool 側で行われる（`deduplication.strategy = latest_id_per_app_and_name`）。skill 側で二重に集約しない。**「同じ GitHub App・同じ `name` の run は ID が最大のものだけを採用する」は `gh api` fallback を使うときだけの手順とする**。`gh api` には `pagination.complete` に相当する情報が無いため、`--paginate` が途中で失敗した場合も `CI: unknown` とする。
- `check_runs` が空配列でも正常な応答である（push 直後で CI が未開始の場合など）。required check が未返却のときの扱い（`CI: pending`）に従う。
- 未完了の run では `conclusion` が `null` になり得る。`status` と併せて `CI: pending` と判定する。
- tool は合否判定を行わない。required / optional の区別も出力に含まれないため、required の集合は「4. required checks の集合」で別途確定する。
- この応答に含まれるのは check runs だけで、commit status（Codecov など、一部の外部 CI が使う）は含まれない。required の context の照合では、個別の commit status を「4. required checks の集合」で別に読む。`combined status`（`commits/<sha>/status`）は使用禁止であり、その応答を「実行中」や成功の根拠にしてはならない。

## 4. required checks の集合

required の集合は、リポジトリの設定から確定する。`<base>` は PR の base ref（`{OWL}:get_pr` の `pr.base.ref`）。次の 2 つを、`gh api` の read-only で読み（MCP tool は提供していないため、CI read の経路にかかわらず常に `gh api`）、**和集合**をとる。

- ruleset（組織レベルとリポジトリの両方を含む）:

  ```text
  gh api "repos/<owner>/<repo>/rules/branches/<base>" --paginate --jq '.[] | select(.type == "required_status_checks" or .type == "workflows" or .type == "code_scanning") | {type, checks: (.parameters.required_status_checks // [] | map({context, integration_id}))}'
  ```

- classic の branch protection の要約:

  ```text
  gh api "repos/<owner>/<repo>/branches/<base>" --jq 'if .protection.enabled then .protection.required_status_checks else null end | {contexts: (.contexts // []), checks: (.checks // [] | map({context, app_id}))}'
  ```

**admin 権限が要る `branches/<base>/protection` は使わない**。保護がなければ 404、権限がなければ 403 になり、「未定義」と「取得不能」を区別できなくなる。

required の要素は、ruleset の `required_status_checks` の `checks[]`（`context`、`integration_id`）と、classic の `checks[]`（`context`、`app_id`）と `contexts[]`（`context` のみ）である。同じ `context` はまとめる。次のいずれかに当たる場合は、**この規則では判定できないため `CI: unknown`** とする。

- どちらかの読み取りに失敗した（403 などの失敗）。
- ruleset に `workflows`（required workflow）または `code_scanning` の rule がある。必須の結果を、この規則では判定できない。
- required の要素に、**App が指定されたもの**がある（`integration_id` / `app_id` が、`null` でも `-1` でもない）。run の App の照合には対応しない。`null` と `-1` は「どの App でもよい」を表す。

上記に当たらず、和集合が**空**なら **required 未定義**とする。報告済みの check run をすべて required とみなし、「5. 判定」の規則をその集合に適用する。**check run が 1 件も報告されていなければ `CI: pending`**。この場合、commit status は対象にしない。

和集合が空でなければ、required の各 `context` を、check run と commit status の**両方**で照合する。

- check run: 名前が一致する run（再実行は集約した後）。
- commit status: 個別の status の一覧を読み、同じ `context` のうち最新のもの（新しい順に返るため、最初に現れるもの）。

  ```text
  gh api "repos/<owner>/<repo>/commits/<reviewedHeadSha>/statuses" --paginate --jq '.[] | {context, state}'
  ```

  `combined status` は使わない。
- どちらにも該当がない: 未返却として `CI: pending`。
- 該当のうち 1 つでも失敗（check run の失敗系の結論、status の `failure` / `error`）: その `context` は失敗。
- 未完了（check run の `queued` / `in_progress`、status の `pending`）: その `context` は未完了。
- すべて成功（check run は `completed` かつ `success`、status は `success`）の場合だけ、その `context` は成功。**同名の check run と commit status が併存する場合は、両方が成功のときだけ**成功とする。

required 未定義のときは、まだ報告されていない check（後から現れる check）を検知できず、commit status も見ない。すべて成功に見えても、後から現れた check が赤になり得る。この限界を、完了サマリー（approve の場合は Verdict の `summary`）の残存リスクに書く（例: 「required checks が未定義のため、報告済みの check run すべてを対象にした。後から現れる check と commit status は検知できない」）。

## 5. 判定

- `CI: success`: `reviewedHeadSha` に対するすべての required checks が、「4」の照合で成功の場合だけ（check run は `status: completed` かつ `conclusion: success`、commit status は `state: success`）。required 未定義のときは、報告済みの check run すべてが成功の場合だけ。
- `CI: pending`: required check が未返却（`check_runs` が空配列の場合を含む）、または `queued` / `in_progress` / `pending`（未完了 run の `conclusion` は `null` になり得る。commit status は `pending`）の場合。
- `CI: failure`: required check に `failure` / `cancelled` / `timed_out` / `action_required` / `startup_failure` / `skipped`（リポジトリ方針で明示的に許可されていない場合）などの結論がある場合、または required の commit status が `failure` / `error` の場合。
- `CI: unknown`: 上記のいずれにも当てはめられない場合。取得できない、対象 SHA を確認できない、`pagination.complete` が `true` でない、tool error、required の集合を確定できない（「4」。App 指定、`workflows` / `code_scanning` の rule を含む）、結果不明を含む。

optional check の結果は別途記録する。`CI: unknown` のまま Verdict / APPROVE を投稿しない。

## 6. 失敗ログ

`CI: failure` の場合、現在の client に workflow run / job / log の read capability があれば、その capability で失敗 job のログを取得する。client にその capability がなければ `gh run view <run-id> --log-failed` を read-only のフォールバックとして使う。どちらも同じ SHA を確認する。失敗ログ取得の可否は client 依存であり、いずれの経路も利用できない場合は `CI: unknown` として記録し、Verdict / APPROVE を投稿せず停止する。

## 7. HEAD 移動時の再確認

検証結果の採用または APPROVE 投稿の直前に、`{OWL}:get_pr` を再度 read して PR HEAD が `reviewedHeadSha` のままであることを確認する。HEAD が動いた場合は、以前の check runs 結果を破棄し、新しい current head を固定して同じ経路で「2. 読み取り」から再実行する。再取得または SHA 照合ができない場合は `CI: unknown` とし、Verdict / APPROVE を停止する。

re-review（O-15）では、current head を固定し直して、この文書の手順で CI を再確認する。

## 8. 記録

evidence に次を記録する（`observed`）: `reviewedHeadSha`、CI read 経路（`{RAVEN}` / `gh api`）と `{RAVEN}` の解決可否、応答の `sha`、全 check run、status / conclusion、`pagination.complete`、`deduplication`、SHA 比較、required の集合とその由来（ruleset / classic / 未定義）、失敗ログ経路、最終 head 再確認。最終的な verdict の根拠とした CI の対象 SHA を確認・記録する。
