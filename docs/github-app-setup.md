# GitHub App セットアップガイド（GitHub Web UI 作業）

mcp-gateway 経由で MCP サーバーに接続するために必要な GitHub App について、
**GitHub Web UI 側で行う作業**（新規登録・インストール・秘密鍵管理・TLS 切替時の URL 変更）を説明する。
`.env` への設定値は [README](../README.md) および `.env.template` のコメントを参照。

> 本書の画面遷移・ラベルは 2026-07 時点の GitHub Web UI（表示は英語）に基づく。
> UI が変更された場合は公式ドキュメント
> [Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) /
> [Modifying a GitHub App registration](https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration)
> を参照。

## 前提: ベース URL

以降 `<PUBLIC_URL>` と表記する URL は、gateway の公開 URL として実際に解決される値。
GitHub App に登録する URL は**必ずこの値と一致させる**。

解決順（`docker-compose.yml` と `mcp-docker register` で共通）:

1. `MCP_GATEWAY_PUBLIC_URL`（推奨。新規設定はこちらを使う）
2. `MCP_GATEWAY_BASE_URL`（旧名・後方互換エイリアス）
3. `http://127.0.0.1:<port>`（既定。port は `MCP_GATEWAY_PORT`、未設定時 `8080`）

| 構成 | `<PUBLIC_URL>` |
|---|---|
| デフォルト（HTTP、上記 1〜2 とも未設定） | `http://127.0.0.1:8080`（`MCP_GATEWAY_PORT` に追従） |
| 旧変数 `MCP_GATEWAY_BASE_URL` のみ設定済みの既存環境 | その設定値（既定値より優先される点に注意） |
| `make setup-tls` 実行後（HTTPS） | `https://localhost:8080`（setup-tls が `MCP_GATEWAY_PUBLIC_URL` を自動設定） |

## 1. GitHub App の新規登録

1. GitHub 右上のプロフィール画像 → **Settings** をクリック
2. 左サイドバー最下部の **Developer settings** をクリック
3. **GitHub Apps** → **New GitHub App** をクリック
4. 各フィールドを設定する:

   | フィールド / 項目 | 設定値 |
   |---|---|
   | **GitHub App name** | 任意の一意な名前（例: `mcp-docker-gateway-<user>`） |
   | **Homepage URL** | `<PUBLIC_URL>` |
   | **Callback URL** | `<PUBLIC_URL>/callback` を入力し、**Add Callback URL** をクリックして 2 本目に `<PUBLIC_URL>/device_callback` を追加（最大 10 本まで登録可能） |
   | **Expire user authorization tokens** | チェックしたまま（既定）を推奨。refresh_token が発行され、`MCP_GATEWAY_GITHUB_REFRESH_ENABLED=true` による自動ローテーションが機能する |
   | **Enable Device Flow** | チェック不要。`/device_callback` は mcp-gateway 自身が実装する Device Authorization Grant 用のエンドポイントであり、GitHub 側の device flow は使用しない |
   | **Webhook** の **Active** | チェックを**外す**（Webhook は使用しない。外すと Webhook URL の入力は不要になる） |

5. **Permissions** で以下を設定する（各権限は **No access** / **Read-only** / **Read & write** から選択）:

   | カテゴリ | Permission | Access |
   |---|---|---|
   | Repository permissions | Metadata | Read-only（自動選択） |
   | Repository permissions | Contents | Read-only |
   | Repository permissions | Issues | Read and write |
   | Repository permissions | Pull requests | Read and write |
   | Account permissions | Email addresses | Read-only |

6. **Where can this GitHub App be installed?** は、個人利用なら **Only on this account** を選択
7. **Create GitHub App** をクリック

## 2. Client ID / Client secret の取得

App 作成直後は App の settings ページ（General）に遷移する。あとから開く場合は
**Settings → Developer settings → GitHub Apps** で対象 App の右側の **Edit** をクリックする。

1. settings ページ上部の **About** に表示される **App ID**（数字）と **Client ID**（`Iv23...` 形式）を控える
   （App ID はinstallation認証、Client IDはユーザー認可に使用する）
2. **Client secrets** セクションの **Generate a new client secret** をクリックし、
   表示された secret を控える（**この画面を離れると再表示できない**。紛失時は再生成する）
3. 環境変数に設定する（推奨。`.env` には書かない。[資格情報の置き場](#資格情報の置き場) を参照）:

   ```bash
   OAUTH_CLIENT_ID=Iv23xxxxxxxxxxxxxxxx
   OAUTH_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## 3. Installation ID / 秘密鍵の取得

1. settings ページ左側の **Install App** をクリックし、対象 owner へ App をインストールする
2. インストール後の URL `https://github.com/settings/installations/<ID>` の末尾を Installation ID として控える
3. App の **General** ページへ戻り、**Private keys** の **Generate a private key** をクリックする
4. ダウンロードした PEM は、Bitwarden など、リポジトリの外の保管庫に保管する。リポジトリへ置いたり、gateway へマウントしたりしない。`make github-app-key-b64 PEM=<path>` で単一行の base64 にして、環境変数 `GITHUB_APP_PRIVATE_KEY_B64` で渡す（[資格情報の置き場](#資格情報の置き場) を参照）
5. 環境変数に設定する（推奨。`.env` には書かない）:

   ```bash
   GITHUB_APP_ID=123456
   GITHUB_APP_INSTALLATION_ID=12345678
   MCP_GATEWAY_INTERNAL_SECRET=<32文字以上のランダム値>
   ```

秘密鍵は、gateway コンテナだけに、環境変数 `GITHUB_APP_PRIVATE_KEY_B64` で渡す。gateway は、初回起動時に暗号化して `config.yaml` へ保存し、以後は保存済みの値を優先する。`github-mcp` と `review-raven` には秘密鍵も installation token も環境変数として渡さない。

### 資格情報の置き場

`OAUTH_CLIENT_ID`・`OAUTH_CLIENT_SECRET`・`GITHUB_APP_ID`・`GITHUB_APP_INSTALLATION_ID`・`MCP_GATEWAY_INTERNAL_SECRET` は、`.env` ではなく**環境変数**で渡すことを推奨する。

- 環境変数は `.env` より優先される（Makefile の `?=`。Docker Compose の既定の優先順位も同じ）。`.env` は、環境変数が無いときのフォールバックである。
- `.env` に値があると、環境変数が入っていない実行（`dsx-env` の忘れなど）で、`.env` の**旧い値が黙って使われる**。GitHub App を切り替えたときに、旧い Client ID が残って、認証が失敗する原因になる。
- 例: Bitwarden に `env:<変数名>` の項目（カスタムフィールド `value` に値）を作り、[dsx](https://github.com/scottlz0310/dsx) の `dsx-env` で、シェルへ注入する。値の変更は、`bw sync` → `dsx-env` の順で反映する。
- `.env` は、秘密を含まない PC 固有の設定（`LOG_LEVEL`・`MCP_GATEWAY_PUBLIC_URL`・TLS 証明書のパスなど）に使う。環境変数を使わない場合に限り、同じ変数名で `.env` に書いてもよい。
- **秘密鍵（PEM）は、単一行の base64 にして `GITHUB_APP_PRIVATE_KEY_B64` で渡す。この変数だけは、`.env` から読まない**（秘密を `.env` に置かないため。未設定なら `make start-gateway` が止まる）。複数行の PEM は、dsx が改行入りの値を警告してスキップするため、そのままでは注入できない。
  1. `make github-app-key-b64 PEM=<path>` を実行する。単一行の base64 が、クリップボードへ入る（画面には表示しない）。
  2. Bitwarden に Secure Note `env:GITHUB_APP_PRIVATE_KEY_B64` を作り、カスタムフィールド `value`（非表示）へ貼り付ける。
  3. `bw sync` → `dsx-env` で、シェルへ注入する。
  4. `make verify-github-app-key PEM=<path>` が「一致しました」を返せば、注入できている（鍵の値は表示しない）。

### 旧運用（PEM のファイルを手動配置）からの移行

以前は、PEM を `config/github-app/private-key.pem` に置き、`docker-compose.yml` が gateway へ read-only でマウントしていた。この運用は廃止した。

1. 上の手順で、`GITHUB_APP_PRIVATE_KEY_B64` を Bitwarden へ登録し、`dsx-env` で注入して、`make verify-github-app-key` で確認する。
2. `make start-gateway` で起動する（`GITHUB_APP_PRIVATE_KEY_B64` が未設定なら、止まる）。
3. 稼働中の gateway は、`config.yaml` に暗号化して保存済みの鍵を優先するので、この変更だけでは動作は変わらない。鍵を差し替えるときは、`make rotate-secret` を実行する（全サービスを停止し、`config.yaml` を削除して、起動し直す。`tokens.db` は保持される）。
4. 不要になった `config/github-app/private-key.pem` は、Bitwarden に PEM の控えがあることを確認してから、削除してよい（`.gitignore` の対象なので、誤ってコミットはされない）。

## 4. TLS 切替時の変更（既存 App の URL 更新）

`make setup-tls` は `.env` の `MCP_GATEWAY_PUBLIC_URL` を `https://localhost:<port>` に
書き換えるが、**GitHub App 側の URL は自動では変わらない**。以下を手動で行う。

1. **Settings → Developer settings → GitHub Apps** で対象 App の **Edit** をクリック
2. General ページで以下を変更する:
   - **Basic information** の **Homepage URL** → `https://localhost:<port>`
   - **Identifying and authorizing users** の **Callback URL** 2 本:
     - `https://localhost:<port>/callback`
     - `https://localhost:<port>/device_callback`
3. **Save changes** をクリック
4. サービスを再起動し、CLI の登録 URL を更新する:

   ```bash
   make restart-gateway
   make register-all
   ```

> **旧 URL を残す場合**: Callback URL は最大 10 本登録できるため、HTTP へ戻す可能性が
> あるなら旧 `http://127.0.0.1:<port>/...` の 2 本を残したまま https の 2 本を追加してもよい。
> ただし認可リクエストの `redirect_uri` を省略した場合は**先頭の Callback URL** が使われるため、
> 並び順には注意する。

## 5. トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| 認可時に `redirect_uri` エラー（"The redirect_uri is not associated with this application." 等） | GitHub App の Callback URL が `<PUBLIC_URL>` と一致していない。scheme（http/https）・host（`127.0.0.1`/`localhost`）・port のいずれかの食い違いでも発生する。セクション 4 の手順で更新する |
| TLS 切替後にブラウザが証明書警告を出す | mkcert のローカル CA が信頼されていない。`make setup-tls` を再実行する（CA の生成・信頼登録は冪等） |
| Node.js 製 MCP クライアントが TLS 接続に失敗する | `NODE_EXTRA_CA_CERTS`（setup-tls が `.env` に自動設定）がクライアントのプロセス環境に渡っていない |
| 認可後に 401 が続く | Client secret の値違い・失効の可能性。セクション 2 の手順で再生成し、環境変数（Bitwarden の項目）を更新して、`make rotate-secret`。gateway は、初回に保存した暗号化済みの secret を、環境変数より優先するので、`make restart-gateway` だけでは反映されない |
| `--with-api` の資格情報診断が失敗する | App ID / Installation ID / 秘密鍵の組み合わせ、App のインストール先、権限を確認する。`docker compose logs mcp-gateway` には秘密値を出さず失敗原因が記録される |

## 関連

- [README — GitHub App 登録](../README.md#github-app-登録)（最低限の要点）
- [mcp-gateway](https://github.com/scottlz0310/mcp-gateway) — `/callback` / `/device_callback` の実装元
- Mcp-Docker #202 / #207、mcp-gateway #201（ローカル TLS 終端）
