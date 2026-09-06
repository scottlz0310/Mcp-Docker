# agy 向け過渡期アダプタ

対応 Issue: [#240](https://github.com/scottlz0310/Mcp-Docker/issues/240)。MCP `2026-07-28` 未対応の agy から modern upstream を利用する間だけ、gateway の互換層を有効化する。

## 前提と制限

- [mcp-gateway PR #234](https://github.com/scottlz0310/mcp-gateway/pull/234) を含むイメージを使用する。マージ済みであることだけでは、利用イメージへの収録を保証しない。公開イメージのリリース内容を確認して `GITHUB_MCP_GATEWAY_IMAGE` を選ぶ。
- 登録には `agy mcp` 対応の Antigravity CLI v1.1.16 以降が必要。
- 設定は全 proxy route に適用される。github-mcp / playwright-mcp を含め、legacy upstream が混在する構成では有効化しない。agy の登録対象を絞っても適用範囲は変わらない。
- 旧式の resource subscription、GET SSE、sampling / elicitation などの callback は変換対象外。詳細は [gateway の仕様](https://github.com/scottlz0310/mcp-gateway/blob/main/docs/legacy-adapter.md) を参照。

### 有効化前の upstream 判定

この PR では github-mcp / playwright-mcp の MCP `2026-07-28` 対応を確認していない。両 route を含む既定構成を、そのまま有効化可能と判断しない。

マージ後、アダプタ無効の状態で gateway の全有効 route（Compose の `ROUTE_*` と gateway 設定ファイルの route を含む）を列挙し、各 upstream の使用イメージの仕様と `server/discover` の成功応答を確認する。`supportedVersions` に `2026-07-28` が含まれることを確認し、認証失敗・通信失敗・未対応応答は対応確認済みと扱わない。既存 conformance suite が検証するのは thread-owl / review-raven だけで、github-mcp / playwright-mcp の確認を代替しない。

未対応または未確認の route が残る場合は無効を維持する。thread-owl / review-raven だけで先に利用する場合は、未確認の `ROUTE_GITHUB` / `ROUTE_PLAYWRIGHT` などを Compose の環境変数定義から除外し、gateway 設定ファイルにも同じ route が残っていない構成を用意する。コンテナ停止や agy の登録対象の限定だけでは route の除外にならない。全有効 route の対応確認後に、次の有効化手順へ進む。

## 有効化と登録

以下はマージ後の運用手順。実構成 E2E は未実施。

1. `.env` に `GATEWAY_LEGACY_ADAPTER_ENABLED=true` を設定する。
2. 対応イメージを取得し、環境変数を反映するため gateway コンテナを再作成する。

   ```sh
   docker compose pull mcp-gateway
   docker compose up -d --no-deps --force-recreate mcp-gateway
   ```

3. 再作成した gateway の今回の起動ログで `legacy_adapter_enabled=true`（JSON 形式なら `"legacy_adapter_enabled":true`）を確認する。ログは `docker compose logs --since 5m --no-log-prefix mcp-gateway` でローカル確認し、共有する証跡は該当フィールドと値だけにする。フィールドがない、または `false` の場合は E2E に進まず、使用イメージと設定を確認する。コンテナ内に環境変数が存在するだけでは、アダプタ対応イメージであることを証明できない。
4. 対象を確認して agy に登録する。既存の gateway URL と OAuth 認証を使用する。

   ```sh
   make register-antigravity REGISTER_FLAGS="--server thread-owl,review-raven --dry-run"
   make register-antigravity REGISTER_FLAGS="--server thread-owl,review-raven --yes"
   agy mcp list
   ```

Compose は未設定・空文字・`false` の場合に `false` を渡す。これは gateway の YAML の `legacy_adapter_enabled: true` より優先される。無効化は `.env` を `false` に戻してコンテナを再作成する。`docker compose restart` だけでは環境変数は更新されない。シェルに同名の環境変数がある場合は `.env` より優先されるため、その値も確認する。

運用では `true` / `false` を使用する。gateway は Go の `strconv.ParseBool` で解釈し、`yes` / `on` / `enabled` などの不正値は起動エラーになる。Compose は不正値を補正せず、`restart: unless-stopped` により再起動を繰り返すため、値を修正してコンテナを再作成する。無効化後も今回の起動ログの `legacy_adapter_enabled=false` を確認してから conformance を実行する。

## マージ後の実構成 E2E

イメージの tag / digest、agy のバージョン、設定値、対象 route と結果を記録する。トークンや環境変数全体をログへ出力しない。

- 有効時: agy で thread-owl / review-raven の initialize、tools/list、読み取り専用 tools/call を確認する。resources を提供する upstream では resources/list と resources/read も確認する。
- 有効時: modern client でも同じ route の discovery、tool / resource read が成功することを確認する。
- 無効時: [conformance 検証](mcp-2026-07-28-conformance.md) を実行し、modern 通信と legacy initialize 拒否を確認する。

有効時に conformance suite 全体を実行すると、legacy initialize 拒否の項目が失敗する。これは有効時の合否判定には使用しない。E2E 完了までは #240 の実接続に関する完了条件を未完了として扱う。

## 撤去

agy が MCP `2026-07-28` に対応した後、`false` で再作成し、両 upstream への agy 接続を確認する。その後 Compose のマッピング、`.env.template` と運用 `.env` の設定、本書と README / conformance 文書の案内を撤去する。gateway 内のアダプタ撤去は gateway 側で行う。
