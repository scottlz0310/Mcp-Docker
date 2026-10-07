# Queue 待機（queue resource の subscription）

SKILL.md の O-00（queue 起点の待機）の手順（PR が明示されず queue 待機を依頼された場合）。

| Resource | 用途 |
| --- | --- |
| `queue://review/queue` | `opened` / `synchronized` / `re-review-requested` を含む通常レビュー起動 |
| `queue://review/re-review-requests` | `re-review-requested` だけを受ける reviewer-side handoff |

再レビュー待機では必ず `queue://review/re-review-requests` を使う。通常 queue では先行する `synchronized` 通知で待機が終了し、直後の再レビュー依頼を見逃す可能性がある。

native `subscriptions/listen` がなければ、Node >=26.10.0で `resource-bridge-cli` をシェル実行し、JSONを同じセッションで受け取る。MCP探索・登録の対象にしない。URLは `MCP_PROBE_URL` があれば--url省略、なければ `<MCP_GATEWAY_PUBLIC_URL>/mcp/thread-owl`。両方未設定は `QUEUE_WAIT_FAILED` で停止する。

```powershell
# MCP_PROBE_URL が設定済みの場合は --url 行を省く
bunx resource-bridge-cli `
  --url "$($env:MCP_GATEWAY_PUBLIC_URL.TrimEnd('/'))/mcp/thread-owl" `
  --uri queue://review/re-review-requests `
  --timeout-ms 900000 `
  --json
```

`json.route` が `"subscription"` または `"pre-completion"` であることを確認し、`json.finalText` をパースして `owner`、`repo`、`prNumber`、`reason` を取得する。`route` が `"timeout"` または `"failed"` の場合はレビュー完了として扱わない。
