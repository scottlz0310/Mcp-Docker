# review-raven専用Appへの切り替え

専用App認証に対応するreview-ravenイメージの配備後に、`docker-compose.review-raven-app.yml`を追加で読み込む。標準の`docker-compose.yml`だけなら従来のprovider token経路を維持する。専用Appの認証実装・V4検証条件は[review-ravenの手順書](https://github.com/scottlz0310/review-raven/blob/main/docs/github-app-auth.md)を参照。

## 資格情報

保管庫からdsxで次の環境変数を注入する。gateway・thread-owlの資格情報は変更しない。

| 名前 | 値 |
|---|---|
| `REVIEW_RAVEN_GITHUB_APP_ID` | `5184108` |
| `REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID` | `169443079` |
| `REVIEW_RAVEN_GITHUB_APP_OWNER` | `scottlz0310` |
| `REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64` | 専用AppのRSA PEM秘密鍵をbase64化した値 |

Client ID・Client secretは使わない。対象は組織`scottlz0310`のAll repositories。既存の`REVIEW_RAVEN_TRUSTED_COMMENT_AUTHORS`・`THREAD_OWL_ALLOWED_AUTHORS`に`review-raven`を含める。

## 切り替え

1. active watch・実行中のレビューがないことを確認する。専用AppモードではCopilot系・watchが非公開になる。
2. 対応済みのreview-ravenイメージを指定する。PR作成だけでは配備済みと判断しない。
3. Composeの読み込み対象を設定する。既存の`COMPOSE_FILE`がある場合は、その対象を保ったうえで専用Appファイルを末尾に追加する。PowerShellでの標準構成の例:

   ```powershell
   $env:COMPOSE_FILE = @('docker-compose.yml', 'docker-compose.review-raven-app.yml') -join [IO.Path]::PathSeparator
   docker compose config --quiet
   ```

   Linuxでは区切りは`:`、Windowsでは`;`になる。各PCの起動設定でも同じ読み込み対象を維持する。通常の`docker compose config`は注入済みの秘密鍵を表示するため使わず、`--quiet`を使う。必要な値が欠けるとCompose検証で失敗する。

4. `docker compose up -d --no-deps mcp-gateway review-raven`で反映する。gatewayのOAuth設定・鍵・GitHub MCP routeは維持する。routeから`upstream_provider_token=true`だけを外し、gateway Appのtokenは注入しない。
5. review-ravenの起動ログでApp・installation・組織・権限の照合成功を確認する。公開toolが6件でwatchが無いこと、許可リストの取得、各CLIの接続を確認する。
6. review-ravenの手順書に従い専用tokenでV4を実測する。gatewayのContents writeは維持し、専用tokenのresolve成功を確認した後に縮小を別作業で行う。

CLI登録は元のComposeに記載されたrouteから同じURLを読み取るため、専用Appの切り替えによるURL・alias変更はない。登録の削除や再登録は不要。

## 切り戻し

読み込み対象から`docker-compose.review-raven-app.yml`を外して、元のCompose設定で`mcp-gateway`・`review-raven`を再作成する。標準構成なら`COMPOSE_FILE=docker-compose.yml`に戻す。既存DB・許可リスト・専用botの投稿を維持する。gateway Contents縮小後は従来resolveへの切り戻しがそのまま成立するとは判断しない。
