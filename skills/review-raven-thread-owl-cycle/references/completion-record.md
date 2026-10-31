# 完了記録とローカル契約検証（Phase 7.5）

SKILL.md の「Phase 7.5: 完了記録とローカル契約検証」から移した手順。

1. Phase 7 のサマリ投稿と投稿者確認が成功した直後に、最終スナップショットを取り直します。
   - `{GH}:get_pr` で現在のPR HEADを取得し、`final_head` として固定する。Phase 6.5 の `reviewedHeadSha` と異なる場合は、古いCI結果を破棄して Phase 6.5 からやり直す。
   - `references/comment-reader.md`に従って`{RAVEN}:read_pr_comments`を再取得し、`pagination.complete=true`と`summary.unresolvedThreads=0`を全thread状態と照合する。snapshotIdの変化と新規actionable指摘も確認する。未解決が残る場合は `REVIEW_INCOMPLETE` として停止する。
   - `all_replied=true` は、今回のサイクルで対象にした全スレッドの返信・resolve結果、および review body / PR comment の全 actionable 指摘に対する返信・処理済み記録を確認できた場合だけ設定する。未確認を `true` にしてはならない。
   - Phase 6.5 と同じCI read bindingで `final_head` の全ページを取得し、`sha`、各 `head_sha`、`pagination.complete` を再確認する。`references/ci-check.md` の手順 2 で確定した required の集合に従い、次のとおり扱う。記録する check は、すべて `status=completed` かつ `conclusion=success`（または `ci-check.md` の手順 2a で許可した `skipped`）であることを確認する。
   - **required を確定できた**: 全 required check を `requiredChecks` に列挙する（`requiredChecksPolicy` は省略するか `defined`）。
   - **required を読み取って未定義と確認できた**: `requiredChecksPolicy` を `undefined` にし、`requiredChecks` は空にして、`final_head` で観測した全 check run（1 件以上）を、省略せず `observedChecks` に列挙する。各 run に報告した GitHub App の ID（`app.id`）を `appId` として必ず付ける（別の App が同名の check を報告すると、同名の run が複数残るため。`appId` が違えば同名でも別の run として記録する）。
   - **required を確定できなかった**（読み取り失敗、判定できない rule など）: `CI: unknown` であり、完了記録を作らず停止する。`requiredChecks` を空にして記録してはならない（空配列は「未定義」を意味しない）。
   - **許可された skipped がある**（`ci-check.md` の手順 2a。`defined` / `undefined` のどちらでも）: `ci.skipPolicy` に `{"baseSha": "<宣言を読んだ base ref の SHA>", "allowedSkippedChecks": [<宣言の名前>]}` を記録し、許可に基づいて成功として扱った check に `"policyAllowedSkip": true` を付ける（`conclusion` は `skipped` のまま）。許可の宣言が無い、または宣言が無い名前の skipped は、記録に入れず、`CI: failure` として扱う。`mcp-docker reviewgate validate` は、宣言した名前の skipped だけを成功として受け入れ、`success` の check が 1 件も無い記録を拒否する。記録を除外して検証を通してはならない。
2. 作業ツリー外の一時ファイルへ、次のJSONを1つだけ書き出します。`skillRevision` は Phase 0 で取得した埋め込みskillのrevision、`unresolved_count` は最終スナップショットの値、`ci.requiredChecks` はrequired checkだけを使います。

```json
{
  "contractVersion": 1,
  "repo": "owner/repository",
  "prNumber": 123,
  "headSha": "<final_head>",
  "skillId": "review-raven-thread-owl-cycle",
  "skillRevision": <Phase 0 で取得した埋め込み skill の revision（整数）>,
  "skillCompleted": true,
  "all_replied": true,
  "unresolved_count": 0,
  "ci": {
    "headSha": "<final_head>",
    "complete": true,
    "requiredChecks": [
      {
        "name": "<required check name>",
        "headSha": "<final_head>",
        "status": "completed",
        "conclusion": "success"
      }
    ]
  }
}
```

required が未定義の場合は、`ci` を次の形にします。

```json
  "ci": {
    "headSha": "<final_head>",
    "complete": true,
    "requiredChecksPolicy": "undefined",
    "requiredChecks": [],
    "observedChecks": [
      {
        "name": "<observed check name>",
        "appId": <報告した GitHub App の ID（整数）>,
        "headSha": "<final_head>",
        "status": "completed",
        "conclusion": "success"
      }
    ]
  }
```

3. 次のコマンドを、最終PR HEADを再取得した値で実行します。`--record` は作業ツリー外の一時ファイルを指定し、記録をリポジトリへコミットしません。

```text
mcp-docker reviewgate validate --record <record-path> --repo <owner/repository> --pr <number> --head-sha <final_head>
```

4. `reviewgate: valid` の出力を得た場合だけ、完了記録のパス、対象HEAD、skill revision、required check数（未定義の場合はその旨と観測した check 数）、検証結果を Phase 8 の証跡へ記録します。コマンドが見つからない、埋め込みskillを解決できない、revisionが一致しない場合は、それぞれ `REVIEW_GATE_UNAVAILABLE` または `SKILL_UNAVAILABLE` として停止します。完了記録の他の契約違反は返された停止コードのまま扱い、マージ準備完了とは報告しません。
