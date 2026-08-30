# MCP 2026-07-28 conformance 検証

Mcp-Docker は実コンテナと mcp-gateway route を使い、MCP `2026-07-28` の横断契約を検証する。
対応 Issue は [#230](https://github.com/scottlz0310/Mcp-Docker/issues/230)、横断 tracker は
[thread-owl#165](https://github.com/scottlz0310/thread-owl/issues/165)。

## 方針

- modern path は `server/discover` から開始し、`2026-07-28` に固定する
- legacy stateful path は保持しない。`2025-06-18` の `initialize` が HTTP 400 / JSON-RPC `-32022` で拒否されることを負の対照にする
- gateway は discovery response、HTTP status、JSON-RPC body、SSE stream を合成しない
- `Mcp-Session-Id` を発行せず、連続する request を session affinity なしで処理する
- subscription の解除は `resources/unsubscribe` ではなく、client による SSE response body の close で行う
- Bearer token は環境変数からだけ読み、引数・ログ・結果へ出力しない

## 検証内容

| 対象 | 検証 |
|---|---|
| gateway 認証境界 | 未認証 request が `401` と Bearer `resource_metadata` challenge を返す |
| discovery | `server/discover` が成功し、`supportedVersions` に `2026-07-28` を含む |
| stateless | `Mcp-Session-Id` なしで `tools/list` を連続実行できる |
| legacy 負の対照 | `initialize` が `400` / `-32022`、`requested=2025-06-18` で拒否される |
| old session transport | MCP endpoint の GET / DELETE が `405` を返す |
| resource | `resources/list` で URI を確認し、`resources/read` が成功する |
| subscription | 最初の JSON-RPC message が `notifications/subscriptions/acknowledged` で、要求 URI と subscription ID が一致する |
| gateway long-lived SSE | `--require-no-buffering` 指定時に `X-Accel-Buffering: no`、任意で keep-alive comment の到達を確認する |
| update | 任意の trigger tool 後に `notifications/resources/updated` を受信し、resource を再 read する |

## 前提

- mcp-gateway v0.10.0 以降
- thread-owl v0.4.0 以降
- review-raven v0.3.0 以降
- protected route を呼び出せる gateway-issued Bearer token

token は `MCP_E2E_BEARER_TOKEN` に設定する。値を command line に渡してはならない。

```powershell
$env:MCP_E2E_BEARER_TOKEN = "<gateway-issued bearer token>"
make mcp-conformance
```

個別実行もできる。

```powershell
make mcp-conformance-thread-owl
make mcp-conformance-review-raven
```

既定では read-only 検証を行う。thread-owl では subscription ack を確認した直後に client 側から stream を閉じる。

## 通知を含む thread-owl E2E

通知発火には queue 更新が必要なため、対象 repository / PR を明示した場合だけ `enqueue_review` を呼び出す。
これは Thread Owl の外部状態を書き換える操作なので、実行前に対象がテスト用途として適切か確認する。

```powershell
bin/mcp-docker.exe conformance `
  --url "https://localhost:8080/mcp/thread-owl" `
  --token-env MCP_E2E_BEARER_TOKEN `
  --resource-uri "queue://review/queue" `
  --trigger-tool enqueue_review `
  --trigger-args '{"owner":"OWNER","repo":"REPO","prNumber":123,"reason":"opened"}' `
  --require-keepalive `
  --require-no-buffering `
  --timeout 15m
```

処理順は次のとおり。

```text
server/discover
  → resources/list
  → resources/read
  → subscriptions/listen
  → notifications/subscriptions/acknowledged
  → SSE keep-alive comment
  → tools/call enqueue_review
  → notifications/resources/updated
  → resources/read
  → client closes stream
```

自然発生する更新を待つ場合は `--trigger-tool` を省略して `--wait-for-update` を指定する。

## mcp-resource-subscriber / squirrel-notifier の受け入れ確認

protocol conformance client と実運用 client は別々に検証する。mcp-resource-subscriber v0.6.0 以降を先に起動し、
上記の `enqueue_review` E2E を実行すると、同じ更新が subscriber にも届く。

```powershell
$env:MCP_PROBE_AUTH_TOKEN = $env:MCP_E2E_BEARER_TOKEN
pnpm dlx mcp-resource-subscriber@0.6.1 `
  --url "https://localhost:8080/mcp/thread-owl" `
  --uri "queue://review/queue" `
  --timeout-ms 900000 `
  --json
```

成功条件は `listenAcknowledged=true`、`notificationReceived=true`、`closeReason=local`、
`errorCode=null` と、通知後の `finalText` 取得である。

squirrel-notifier v0.7.0 以降では、同じ resource を監視した状態で `enqueue_review` を実行し、
1本の long-lived stream からトースト通知が届くことを確認する。デスクトップ通知の表示確認は対話的な実機受け入れであり、CI には含めない。

## direct endpoint 比較

`--direct-url` を指定すると、gateway 経由と direct endpoint の `server/discover` result を JSON として比較する。
direct endpoint は通常ホストへ公開しないため、診断用の閉じたネットワークでのみ使用する。
review-raven の direct endpoint は gateway が注入する identity / provider token を前提とするため、
`--direct-token-env` には upstream が受け付ける専用 token、`--direct-authenticated-user` には検証用 identity を指定する。
direct endpoint を primary `--url` として単独診断する場合は、対応する `--token-env` と `--authenticated-user` を指定する。
`X-Accel-Buffering` は MCP protocol の要件ではないため、direct endpoint の単独診断では通常 `--require-no-buffering` を指定しない。
この option は mcp-gateway route の deployment contract を検証する場合だけ使用する。
これらの header を public gateway に対する認証回避として使ってはならない。gateway は client が送った identity header を除去する。

## CI と実機の境界

単体テストでは in-process HTTP/SSE server を使い、header、status、subscription ID、keep-alive、notification flow を固定する。
実 route の検証は gateway token と実コンテナを必要とするため、secret を持たない通常の Pull Request CI では実行しない。
リリース前または横断 migration の closeout 時に `make mcp-conformance` を実行し、結果を Issue / handoff に記録する。
