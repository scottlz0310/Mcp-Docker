# review-raven ⇔ thread-owl 内部連携の運用

review-raven（依頼側）と thread-owl（レビュー側）のサービス間連携を、標準`docker-compose.yml`で有効にするための手順。設計は[review-raven#144の設計文書](https://github.com/scottlz0310/review-raven/blob/main/docs/design/review-responsibility-boundaries.md)、契約は[review-raven `docs/design/contracts/`](https://github.com/scottlz0310/review-raven/tree/main/docs/design/contracts)を参照する。

**既定は無効**。`REVIEW_INTERNAL_LINK_ENABLED`が未設定の間は、内部ルート・内部面・台帳・配送のすべてが空になり、既存の挙動は変わらない。

## 構成

```
review-raven ──http(コンテナ内)──▶ mcp-gateway /mcp/thread-owl-internal ──▶ thread-owl /internal/mcp
thread-owl   ──http(コンテナ内)──▶ mcp-gateway /mcp/review-raven-internal ──▶ review-raven /internal/mcp
```

- 内部面は公開面（`/mcp`）とは別のMCPサーバーで、agent向けの`tools/list`に現れない。
- gatewayの内部ルートは、`required_audience`で通常のagent向けトークン（`aud: mcp-gateway`）と分け、upstreamへは内部面専用の共有Bearerを注入する。
- 内部ルート（名前が`_INTERNAL`で終わる`ROUTE_*`）は`mcp-docker register`の対象外。agentのMCP設定には載らない。
- 三層で守る: ①agent向けに登録しない、②audience分離、③アプリ層のサービス別ACL（subject→操作→repo）。gatewayにはルートごとの主体許可リストがないため、③が主体の絞り込みを担う。
- ホストへポートは公開しない。

## 有効にする変数

スイッチ以外は、有効のとき**必須**（欠ければ`docker compose config`が止まる）。値は保管庫からdsxで注入し、`.env`やリポジトリに置かない。

| 名前 | 内容 |
|---|---|
| `REVIEW_INTERNAL_LINK_ENABLED` | 任意の値で有効。未設定で無効 |
| `REVIEW_RAVEN_INTERNAL_PROXY_SECRET` | review-raven内部面の共有Bearer。32文字以上。`REVIEW_RAVEN_PROXY_SECRET`と別の値 |
| `THREAD_OWL_INTERNAL_PROXY_SECRET` | thread-owl内部面の共有Bearer。16文字以上（32文字以上を推奨） |
| `REVIEW_RAVEN_REQUEST_ACL` | 依頼を出せる利用者とrepoのJSON。例: `{"users":{"<login>":["scottlz0310/*"]},"operators":["<login>"]}` |
| `REVIEW_RAVEN_SERVICE_ACL` | review-ravenの内部面のサービス別ACL。例: `{"services":{"<owl主体のlogin>":{"actions":["ingest","publish_result"],"repos":["scottlz0310/*"]}}}` |
| `THREAD_OWL_SERVICE_ACL` | thread-owlの内部面のサービス別ACL。例: `{"services":{"<raven主体のlogin>":{"actions":["accept","cancel","get_result"],"repos":["scottlz0310/*"]}}}` |
| `REVIEW_RAVEN_OWL_INTERNAL_TOKEN` | review-ravenがthread-owlの内部ルートへ提示する資格情報（raven主体のgatewayトークン） |
| `THREAD_OWL_RAVEN_INTERNAL_TOKEN` | thread-owlがreview-ravenの内部ルートへ提示する資格情報（owl主体のgatewayトークン） |
| `THREAD_OWL_IMAGE` | 内部面・台帳・配送を含む thread-owl のイメージ。**有効時は明示が必須**（未指定なら`docker compose config`が止まる）。最新リリース（`:latest`、v0.7.0）にはまだ含まれないため、リリース前は`make pull-main`・`make restart-main`（`THREAD_OWL_MAIN_IMAGE`の`:main`を自動で渡す）を使う。対応済みのリリースが出たら、そのタグを指定してよい |
| `REVIEW_INTERNAL_LINK_GATEWAY_URL` | 任意。配送先gatewayのbase URL。既定は`http://mcp-gateway:${MCP_GATEWAY_PORT:-8080}` |

スイッチを有効にするとcomposeが次を設定する。

- review-raven: `REVIEW_RAVEN_REVIEW_REQUESTS=true`・`REVIEW_RAVEN_INTERNAL_SURFACE=true`・`REVIEW_RAVEN_OWL_INTERNAL_URL`（gatewayの`/mcp/thread-owl-internal`）・`REVIEW_RAVEN_OWL_INTERNAL_ALLOW_PLAIN_HTTP=true`
- thread-owl: `THREAD_OWL_LEDGER_PATH=/data/ledger.sqlite`・`THREAD_OWL_RAVEN_INTERNAL_URL`（gatewayの`/mcp/review-raven-internal`）・`THREAD_OWL_RAVEN_INTERNAL_ALLOW_PLAIN_HTTP=true`

`..._ALLOW_PLAIN_HTTP`は、コンテナのprivate networkでgatewayをサービス名で引くためのopt-in。資格情報はそのネットワーク上を平文で流れる。ホスト外のgatewayを引く場合は`REVIEW_INTERNAL_LINK_GATEWAY_URL`にhttpsを指定し、composeのopt-inは外す。

review-ravenの内部連携は、専用GitHub Appモード（[専用Appの運用](review-raven-app-auth.md)）が前提。

## サービス主体と資格情報

サービス主体は、**専用のGitHubアカウント（machine user）**として扱う。ACLのキーは、gatewayが付与する`X-Authenticated-User`（GitHub login）。利用者本人のアカウントを兼用しない。

| 主体 | 呼び出し先 | ACLの操作 |
|---|---|---|
| raven主体 | thread-owl内部面 | `accept` / `cancel` / `get_result`（`THREAD_OWL_SERVICE_ACL`） |
| owl主体 | review-raven内部面 | `ingest` / `publish_result`（`REVIEW_RAVEN_SERVICE_ACL`） |

トークンは、各主体のアカウントでgatewayのdevice flowを1回行って取得する。`resource`にはルート名（`ROUTE_`以降を小文字にした値）を渡し、内部audienceのトークンを得る。

```bash
# 例: owl主体のトークン（review-raven内部ルート向け）。raven主体は resource=thread_owl_internal
curl -s -X POST "$GATEWAY/device_authorization" -d "client_id=mcp-client" -d "scope=repo user" -d "resource=review_raven_internal"
# 表示されたURLをmachine userでログインしたブラウザで開いて承認し、device_codeで/tokenをポーリングする
curl -s -X POST "$GATEWAY/token" -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" -d "device_code=<device_code>" -d "client_id=mcp-client" -d "resource=review_raven_internal"
```

- 取得した`access_token`を`THREAD_OWL_RAVEN_INTERNAL_TOKEN`（owl主体）／`REVIEW_RAVEN_OWL_INTERNAL_TOKEN`（raven主体）として保管庫に格納する。値をログ・リポジトリ・チャットに出さない。
- 有効期間は`TOKEN_EXPIRES_IN_SEC`（既定90日）。**期限前にrotationする**: 同じ手順で再取得して保管庫を更新し、該当サービスだけ再作成する。
- 失効は`POST /revoke`（RFC 7009）。builtin modeではJWTが即時に失効する。漏えいの疑いがあれば失効→再取得→ACLの見直しの順で行う。
- 主体を増やす（Squirrelの`observe`など）ときは、アカウントを分け、該当サービスのACLに操作とrepoを最小で追加する。

## 有効化と切り戻し

1. 保管庫の値を注入したシェルで`REVIEW_INTERNAL_LINK_ENABLED=1`を設定し、`docker compose config -q`が通ることを確認する（必須の値が欠ければ、この段階で止まる）。
2. `make pull-main`→`make restart-main`で再作成する（review-raven・thread-owl・gateway。thread-owlは内部面を含む`:main`が必要）。標準の`make pull`・`make restart`を使う場合は、`THREAD_OWL_IMAGE`で内部面を含むイメージを指定する。
3. 下の確認チェックリストを実施する。
4. 切り戻し: `REVIEW_INTERNAL_LINK_ENABLED`を外して再作成する。内部ルート・内部面・配送が止まり、公開面は変わらない。台帳は`thread-owl-data`・`review-raven-data`に残る（削除は手動）。

## 永続データ

| volume | 中身 | 備考 |
|---|---|---|
| `review-raven-data` | 依頼台帳（既存の`/data/review-raven.db`と同じSQLite） | 既存のvolume |
| `thread-owl-data` | 候補・取消記録・結果索引・outbox（`/data/ledger.sqlite`） | 新規。無効の間もマウントのみ |

- どちらも保持期限で自動削除される（thread-owlは`THREAD_OWL_RETENTION_DAYS`、既定30）。
- バックアップは、サービスを止めてvolumeを退避する。稼働中のSQLiteファイルを直接コピーしない。
- `docker volume rm`は台帳（受付済みcycle・取消記録・冪等性キー）を失う。有効化後は、必要な場合を除いて実施しない。

## 確認チェックリスト（実環境）

このリポジトリのテストが確認するのは、composeの展開（無効時は空・有効時は必須値のfail-closed・内部ルートの登録除外・ポート非公開・volume）まで。以下は**実環境でしか確認できず、配備時に実施する**。

- [ ] 有効化後、review-raven・thread-owlが起動する（設定検証で止まらない）
- [ ] gatewayの起動ログに`/mcp/review-raven-internal`・`/mcp/thread-owl-internal`が出る
- [ ] 通常のagent向けトークン（`aud: mcp-gateway`）で内部ルートを呼ぶと拒否される
- [ ] raven主体のトークンでthread-owlの`accept_review_candidate`が成功し、同一内容の再送が`duplicate: true`になる
- [ ] owl主体のトークンでreview-ravenの`ingest_review_candidate`が成功する
- [ ] ACLにない操作・repoは`PERMISSION_DENIED`になる
- [ ] 再作成後も台帳（受付済みcycle）が残る
- [ ] `mcp-docker register`の出力に内部ルートが含まれない
- [ ] 契約の共有シナリオを、実raven・実owlに対して通して実行する（未実施。review-raven#147・thread-owl#279のクローズ条件）
