# review-raven専用GitHub Appの運用

専用App設定は標準`docker-compose.yml`に組み込まれている。追加Composeや`COMPOSE_FILE`の手動設定は不要。認証実装は[review-ravenの手順書](https://github.com/scottlz0310/review-raven/blob/main/docs/github-app-auth.md)、実機検証結果は[V4検証記録](review-raven-app-v4.md)を参照する。

## 資格情報

保管庫からdsxで次の環境変数を注入する。gateway・thread-owlの既存資格情報も維持する。

| 名前 | 値 |
|---|---|
| `REVIEW_RAVEN_GITHUB_APP_ID` | `5184108` |
| `REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID` | `169443079` |
| `REVIEW_RAVEN_GITHUB_APP_OWNER` | `scottlz0310` |
| `REVIEW_RAVEN_PROXY_SECRET` | 32文字以上のランダムな専用共有シークレット |
| `REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64` | 専用AppのRSA PEM秘密鍵をbase64化した値 |

Bitwardenの項目名は`env:<変数名>`、カスタムフィールドは非表示の`value`。専用App秘密鍵とproxy共有鍵は環境変数で渡し、`.env`からはmakeへ読み込まない。Client ID・Client secretは専用Appでは使わない。

Appは組織`scottlz0310`のAll repositoriesへインストールする。GitHubが許可する組織外の公開情報の読み取りは許容する。installation権限の対象を限定する方針であり、MCPに組織外の読み取りを一律拒否する制限は追加しない。`REVIEW_RAVEN_TRUSTED_COMMENT_AUTHORS`・`THREAD_OWL_ALLOWED_AUTHORS`に`review-raven`を含める。

## 起動・再起動

鍵を登録した後は、同じシェルで次を実行する。他PCも同じ手順でよい。

```powershell
cd ~/src/Mcp-Docker
bw sync
dsx-env
make pull
make restart
```

gateway・thread-owlもmain版を使う場合は`make pull-main`・`make restart-main`を使う。review-ravenの既定イメージは専用App対応を公開済みの`:main`。別の`REVIEW_RAVEN_IMAGE`を指定する場合は、`github-app`モードと共有Bearer検証に対応するイメージを選ぶ。

makeは`COMPOSE_FILE=docker-compose.yml`を子プロセスへ渡す。シェルに検証時の古い`COMPOSE_FILE`が残っていても、廃止した追加Composeを読み込まない。独自の追加Composeを使う場合だけ、`make COMPOSE_FILE=<読み込み対象> ...`として明示する。Docker Composeを直接実行するときは、makeの設定は適用されないため`docker compose -f docker-compose.yml ...`を使う。

pull・start・restartは、資格情報と`docker compose config --quiet`を先に検証する。restartは検証成功後にstop→startを順番に実行するため、不正な設定で稼働中コンテナを停止しない。設定検証だけなら`make check-compose-config`を使う。通常の`docker compose config`は秘密値を表示するので使用しない。

gatewayは利用者を認証し、`upstream_bearer_token_env=REVIEW_RAVEN_PROXY_SECRET`で専用共有Bearerを注入する。review-ravenは共有Bearerを照合した後に専用App tokenを使う。ホストへreview-ravenのポートは公開しない。内部HTTPを保護し、共有鍵を他サービスへ渡さない。

## 共有鍵の更新と切り戻し

共有鍵を保管庫で更新し、`bw sync`→`dsx-env`→`make restart(-main)`でgatewayとreview-ravenへ同時に反映する。実行中のレビューがない時間に行い、起動ログと6 tool公開を確認する。

旧provider tokenモードへ戻す場合は、切り替え前のrepo構成とイメージへ戻して再作成する。標準Composeの設定を混在させない。専用botが投稿したコメントを読めるよう、許可リストの`review-raven`は維持する。gateway Contents縮小後は、旧resolve経路がそのまま使えると仮定しない。

gatewayのContents縮小は、専用App移行とは別の後続作業である。
