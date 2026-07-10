# GitHub App セットアップガイド（GitHub Web UI 作業）

mcp-gateway 経由で MCP サーバーに接続するために必要な GitHub App について、
**GitHub Web UI 側で行う作業**（新規登録・TLS 切替時の URL 変更・Client secret 管理）を説明する。
`.env` への設定値は [README](../README.md) および `.env.template` のコメントを参照。

> 本書の画面遷移・ラベルは 2026-07 時点の GitHub Web UI（表示は英語）に基づく。
> UI が変更された場合は公式ドキュメント
> [Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) /
> [Modifying a GitHub App registration](https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration)
> を参照。

## 前提: ベース URL

以降 `<PUBLIC_URL>` と表記する URL は `.env` の `MCP_GATEWAY_PUBLIC_URL` の値。
GitHub App に登録する URL は**必ずこの値と一致させる**。

| 構成 | `<PUBLIC_URL>` |
|---|---|
| デフォルト（HTTP） | `http://127.0.0.1:8080`（`MCP_GATEWAY_PORT` に追従） |
| `make setup-tls` 実行後（HTTPS） | `https://localhost:8080`（setup-tls が `.env` に自動設定） |

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

1. settings ページ上部の **About** に表示される **Client ID**（`Iv23...` 形式）を控える
   （**App ID とは別物**である点に注意）
2. **Client secrets** セクションの **Generate a new client secret** をクリックし、
   表示された secret を控える（**この画面を離れると再表示できない**。紛失時は再生成する）
3. `.env` に設定する:

   ```bash
   OAUTH_CLIENT_ID=Iv23xxxxxxxxxxxxxxxx
   OAUTH_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## 3. TLS 切替時の変更（既存 App の URL 更新）

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

## 4. トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| 認可時に `redirect_uri` エラー（"The redirect_uri is not associated with this application." 等） | GitHub App の Callback URL が `<PUBLIC_URL>` と一致していない。scheme（http/https）・host（`127.0.0.1`/`localhost`）・port のいずれかの食い違いでも発生する。セクション 3 の手順で更新する |
| TLS 切替後にブラウザが証明書警告を出す | mkcert のローカル CA が信頼されていない。`make setup-tls` を再実行する（CA の生成・信頼登録は冪等） |
| Node.js 製 MCP クライアントが TLS 接続に失敗する | `NODE_EXTRA_CA_CERTS`（setup-tls が `.env` に自動設定）がクライアントのプロセス環境に渡っていない |
| 認可後に 401 が続く | Client secret の値違い・失効の可能性。セクション 2 の手順で再生成し `.env` を更新、`make restart-gateway` |

## 関連

- [README — GitHub App 登録](../README.md#github-app-登録)（最低限の要点）
- [mcp-gateway](https://github.com/scottlz0310/mcp-gateway) — `/callback` / `/device_callback` の実装元
- Mcp-Docker #202 / #207、mcp-gateway #201（ローカル TLS 終端）
