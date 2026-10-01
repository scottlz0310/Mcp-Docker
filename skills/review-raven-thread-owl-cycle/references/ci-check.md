# CI 確認（Phase 6.5・R-16）

SKILL.md の「Phase 6.5: CI 確認」から移した手順（内容は変更していない）。

## Phase 6.5: CI 確認

R-16 の CI 判定は、状態集約・SHA 固定・失敗ログ取得を分けて実行する。

1. **状態集約**: CI 判定の直前に `{GH}:get_pr` を read し、現在の PR HEAD SHA を `reviewedHeadSha` として固定する。その直後に、R-00 で固定した CI read 経路で `reviewedHeadSha` の check runs を取得する。対象 SHA を確認できない応答は `CI: unknown` とし、成功扱いにしない。
   - **第一選択**: `{RAVEN}:list_check_runs_for_sha`（`owner`、`repo`、40 桁小文字 hex の `sha` を入力する。branch 名や PR 番号は tool 側で拒否される）。次を検証してから使い、満たさない場合は `CI: unknown` とする。
     - 応答の `sha` が入力の `reviewedHeadSha` と一致すること
     - `pagination.complete` が `true` であること（`false` や欠落は取得未完了とする）
     - 各 check run の `head_sha` が `reviewedHeadSha` と一致すること
     - 再実行 run の集約は tool 側で行われる（`deduplication.strategy = latest_id_per_app_and_name`）。**skill 側で二重に集約しない**
     - `check_runs` が空配列でも正常な応答である（push 直後で CI が未開始の場合など）。required check が未返却のときの扱い（手順 2 の `CI: pending`）に従う
     - tool は合否判定を行わず、required / optional の区別も出力に含まれない。required checks の特定はリポジトリ方針（branch protection / repository policy）から別途行う
     - 取得対象は check runs だけで、Status API の commit status（一部の外部 CI が使う）は含まれない
   - **fallback**: R-00 の時点で `{RAVEN}:list_check_runs_for_sha` が無い（review-raven v0.5.0 未満）か schema が一致しない場合だけ、`gh api "repos/<owner>/<repo>/commits/<reviewedHeadSha>/check-runs?per_page=100" --paginate --jq '.check_runs[] | {id, name, head_sha, status, conclusion, app: .app.slug}'` を read-only で使う。この経路では**同じ GitHub App・同じ `name` の run が複数ある場合（再実行）は ID が最大のものだけを採用する**。`pagination.complete` に相当する情報が無いため、`--paginate` が途中で失敗した場合は `CI: unknown` とする。
   - **実行時の失敗で経路を切り替えない**: binding 後の tool error（認証系の構造化 error、入力検証 error のいずれも）、transport failure、schema 不一致は `CI: unknown` として扱い、`gh api` へ迂回しない。
   - **`{GH}:get_check_runs`（公式 GitHub MCP の `pull_request_read`）は PR 番号を入力とし `head_sha` を返さないので、CI 判定の根拠にしない。**
2. `CI: success` は、`reviewedHeadSha` に対するすべての required check が `status: completed` かつ `conclusion: success` の場合だけにする。required check が未返却（`check_runs` が空配列の場合を含む）、または `queued` / `in_progress` / `pending`（未完了 run の `conclusion` は `null` になり得る）の場合は `CI: pending`、required check に `failure` / `cancelled` / `timed_out` / `action_required` / `startup_failure` / `skipped`（リポジトリ方針で明示的に許可されていない場合）などの結論があれば `CI: failure` とする。optional check の結果は別途記録する。`combined status` は使用禁止であり、その応答を「実行中」や成功の根拠にしてはならない。
3. **失敗ログ**: `CI: failure` の場合、現在の client に workflow run / job / log の read capability があれば、その capability で失敗 job のログを取得する。client にその capability がなければ `gh run view <run-id> --log-failed` を read-only のフォールバックとして使う。失敗ログ取得の可否は client 依存であり、いずれの経路も利用できない場合は `CI: unknown` としてユーザーに報告し、修正可能なら Phase 4、修正困難なら停止する。
4. **HEAD 移動時の再確認**: Phase 6.6 または Phase 7 へ進む前に `{GH}:get_pr` を再度 read して PR HEAD が `reviewedHeadSha` のままであることを確認する。HEAD が動いた場合は、以前の check runs 結果を破棄し、新しい current head を固定して同じ経路で手順 1 から再実行する。再取得または SHA 照合ができない場合は `CI: unknown` として停止する。
