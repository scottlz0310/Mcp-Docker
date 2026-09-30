# 完了記録とローカル契約検証（Phase 7.5）

SKILL.md の「Phase 7.5: 完了記録とローカル契約検証」から移した手順。

1. Phase 7 のサマリ投稿と投稿者確認が成功した直後に、最終スナップショットを取り直します。
   - `{GH}:get_pr` で現在のPR HEADを取得し、`final_head` として固定する。Phase 6.5 の `reviewedHeadSha` と異なる場合は、古いCI結果を破棄して Phase 6.5 からやり直す。
   - `{RAVEN}:get_review_threads` に `include_bodies=false` を明示して全ページを取得し、`pagination.complete=true` と `summary.unresolved=0` を確認する。未解決が残る場合は `REVIEW_INCOMPLETE` として停止する。
   - `all_replied=true` は、今回のサイクルで対象にした全スレッドの返信・resolve結果、および review body / PR comment の全 actionable 指摘に対する返信・処理済み記録を確認できた場合だけ設定する。未確認を `true` にしてはならない。
   - Phase 6.5 と同じCI read bindingで `final_head` の全ページを取得し、`sha`、各 `head_sha`、`pagination.complete` を再確認する。repository policyから確定した全 required check を `requiredChecks` に列挙し、すべて `status=completed` かつ `conclusion=success` であることを確認する。
2. 作業ツリー外の一時ファイルへ、次のJSONを1つだけ書き出します。`skillRevision` は Phase 0 で取得した埋め込みskillのrevision、`unresolved_count` は最終スナップショットの値、`ci.requiredChecks` はrequired checkだけを使います。

```json
{
  "contractVersion": 1,
  "repo": "owner/repository",
  "prNumber": 123,
  "headSha": "<final_head>",
  "skillId": "review-raven-thread-owl-cycle",
  "skillRevision": 18,
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

3. 次のコマンドを、最終PR HEADを再取得した値で実行します。`--record` は作業ツリー外の一時ファイルを指定し、記録をリポジトリへコミットしません。

```text
mcp-docker reviewgate validate --record <record-path> --repo <owner/repository> --pr <number> --head-sha <final_head>
```

4. `reviewgate: valid` の出力を得た場合だけ、完了記録のパス、対象HEAD、skill revision、required check数、検証結果を Phase 8 の証跡へ記録します。コマンドが見つからない、埋め込みskillを解決できない、revisionが一致しない場合は、それぞれ `REVIEW_GATE_UNAVAILABLE` または `SKILL_UNAVAILABLE` として停止します。完了記録の他の契約違反は返された停止コードのまま扱い、マージ準備完了とは報告しません。
