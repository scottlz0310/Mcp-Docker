# 専用GitHub AppのV4実機検証

検証日: 2026-10-09。利用者が再作成したreview-ravenのrevisionは`13ca12288c908b9d51f79eb28e88c8196d2ea8bf`。

App ID `5184108`、Installation ID `169443079`、owner `scottlz0310`。起動時のApp/installation・全repo・権限照合成功をログで確認。専用App秘密鍵・proxy共有鍵の値は記録していない。

| 項目 | 観測した結果 |
|---|---|
| 認証経路 | `github-app`、gatewayの共有Bearer route、両サービスの共有鍵一致、ホストへのreview-ravenポート公開なし |
| tool公開 | 実際のdiscoveryでreviewed用6 toolのみ。resource capabilityなし、watch templateなし、`diagnose_github_token`はunknown tool |
| 利用者認証 | 無効Bearerでgateway経由の呼び出しが401 |
| proxy認証 | 同じ内部ネットワークから偽装identity/Bearerを付けた直接接続も401 |
| thread読み取り | metadataで本文不在・全ページ取得を確認し、許可リスト通過後に本文取得が成功 |
| 返信 | 成功。comment `4226184897`の投稿者が`review-raven[bot]` |
| resolve | 未解決threadのresolveが成功 |
| 返信後resolve | 両操作が成功。comment `4226185307`の投稿者が`review-raven[bot]` |
| 再取得 | 3 thread全件resolved、未解決0。専用botの返信が許可リストを通って読み戻せる |
| private checks | 組織内private repoの固定SHAでcheck runs全4件を取得。SHA一致・全ページ完了 |
| 公開情報 | 組織外公開repoのmetadataを取得できる。利用者がこの読み取りを許容し、installation権限だけを組織内に限定する方針を確認 |
| client | CodexのMCP経由とresource-bridge-cli/SDK経由の接続・呼び出しが成功 |

書き込みのfixtureは[review-raven#140](https://github.com/scottlz0310/review-raven/pull/140)（検証専用、マージ対象外）。対象HEADは`4282903493f57c2c3e8ad5e45554fc6a7c9ff7e9`。threadは`PRRT_kwDOSM7RP86qoP5W`、`PRRT_kwDOSM7RP86qoP6e`、`PRRT_kwDOSM7RP86qoP7O`。

期限前token更新は、署名・キャッシュ・並行取得・期限5分前更新・401無効化の自動テストが成功している。実機では新規tokenによる上記API成功を確認したが、稼働中tokenの期限越え更新はこの時点では未観測。Claude/Copilot/Antigravityでの実操作も未実施。これらを実測済みとは扱わない。

主要操作と認証境界に問題がなかったため、利用者が事前に指示した標準Compose/makeへの恒久対応を進める。gatewayのContents権限は変更していない。

## 恒久構成の配備確認（2026-10-09）

Mcp-Docker #386とreview-raven #141のマージ後、利用者が標準Composeでコンテナを再作成し、05:25 UTCの起動後に次を確認した。秘密値は記録していない。

- review-ravenは`:main`、revision `b69e2f39c45c835a8bc92c5ff744ab92a04d3f90`、`github-app`モードで稼働。
- App ID `5184108`、Installation ID `169443079`、owner `scottlz0310`、専用秘密鍵の注入を確認。
- gatewayのrouteは`upstream_bearer_token_env=REVIEW_RAVEN_PROXY_SECRET`。両サービスの共有Bearer一致、review-ravenの公開portなしを確認。
- SDK discoveryは公開6 tool、resource template 0件。
- MCP経由で許可リスト取得、PR #141のmetadata取得（全ページ完了・未解決0件）、上記固定SHAのChecks取得（全ページ完了・8件）が成功。

稼働tokenの期限越え更新・他クライアント実操作・gateway Contents権限縮小は、この配備確認の対象に含めていない。
