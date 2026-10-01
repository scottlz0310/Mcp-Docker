# Queue 待機（queue resource の subscription）

SKILL.md の O-00（queue 起点の待機）の手順（PR が明示されず queue 待機を依頼された場合）。

| Resource | 用途 |
| --- | --- |
| `queue://review/queue` | `opened` / `synchronized` / `re-review-requested` を含む通常レビュー起動 |
| `queue://review/re-review-requests` | `re-review-requested` だけを受ける reviewer-side handoff |

再レビュー待機では必ず `queue://review/re-review-requests` を使う。通常 queue では先行する `synchronized` 通知で待機が終了し、直後の再レビュー依頼を見逃す可能性がある。

native `subscriptions/listen` が使えなければ、repository の運用ガイドに従って `mcp-resource-subscriber`（v0.6.0 以降）を使う。thread-owl の MCP URL は、環境変数 `MCP_PROBE_URL` があればそれを使って `--url` を省略する。なければ `<MCP_GATEWAY_PUBLIC_URL>/mcp/thread-owl` を渡す。どちらも未設定なら推測せず `QUEUE_WAIT_FAILED` として停止する。

```powershell
# MCP_PROBE_URL が設定済みの場合は --url 行を省く
bunx mcp-resource-subscriber `
  --url "$($env:MCP_GATEWAY_PUBLIC_URL.TrimEnd('/'))/mcp/thread-owl" `
  --uri queue://review/re-review-requests `
  --timeout-ms 900000 `
  --json
```

`json.route` が `"subscription"` または `"pre-completion"` であることを確認し、`json.finalText` をパースして `owner`、`repo`、`prNumber`、`reason` を取得する。`route` が `"timeout"` または `"failed"` の場合はレビュー完了として扱わない。
