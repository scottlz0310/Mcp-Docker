# 現在のbase branchから宣言を読む

PR比較用の`baseSha`（`baseRefOid`）と、宣言元の`policyBaseSha`を分ける。author allowlistとci-policyは、同じ`baseRefName` / `policyBaseSha`のファイルだけから読む。PR HEAD・作業ツリー・既定branch・古い比較元SHAへ代替しない。branchの保護設定や認証・権限を変更する手順ではない。

## 解決と固定

1. metadata bindingのdiscoveryと最小readが成功した後、次の`gh api graphql`をread-only補完として使う。reviewerは先にPR作成元の許可判定も通す。拒否されたreadを迂回しない。この経路を宣言元解決に固定し、失敗後に別認証へ切り替えない。owner/repo/PR番号は確定済み対象を渡す。queryとowner/repoは`-f`、PR番号は整数の`-F pr=<番号>`で渡す。コメント本文は選択しない。

   ```graphql
   query($owner: String!, $repo: String!, $pr: Int!) {
     repository(owner: $owner, name: $repo) {
       pullRequest(number: $pr) {
         headRefOid baseRefOid baseRefName
         baseRef { name prefix target { __typename oid } }
       }
     }
   }
   ```

2. PRのhead/baseが固定metadataと一致し、`baseRefName`が非空で`baseRef.name`と一致、prefixが`refs/heads/`、targetが`Commit`、oidが40桁小文字hexの場合だけ、branch名とoidを宣言元として固定する。null・削除・不一致・取得失敗は呼出し元のauthor gate / CI / readerの停止分類に従い、宣言なしへ補完しない。
3. reviewedのfile readは固定したGH binding、reviewerのCI宣言はread-only補完の`gh api repos/<owner>/<repo>/contents/.review-raven/ci-policy.json?ref=<policyBaseSha>`に固定する。REST応答はtype=file / encoding=base64を確認し、contentを復号して宣言JSONを検証する。reviewerのauthor宣言はOWL reader自身が同じSHAで検証する。reviewedも両ファイルへ`policyBaseSha`を明示する。ファイル取得の404だけを不在とし、他の失敗や不正JSONを空の許可へ代替しない。ファイル取得後にも同じqueryを実行し、head/base/branch名/宣言SHAの一致を確認する。変化した場合は古い宣言を使わず停止する。再開時は宣言取得と投稿者検証から新しく実行する。

## 書込み前と終端

各外部write直前、reader取得後、サイクル終端、完了記録の作成直前にも宣言元を解決し直す。reader v2の`baseRefName` / `policyBaseSha`と、両宣言の取得元が同じであることを確認する。取消・branch変更・進行を検出したら、以前の投稿者検証やskip許可を持ち越さず停止する。skillで自動再試行しない。reader内部の最大3試行と、外部writeの再実行を混同しない。

`baseRefName`、PR比較用`baseSha`、宣言用`policyBaseSha`、取得時点と照合結果を証跡に分けて記録する。`ci.skipPolicy.baseSha`は既存JSON名を保ち、実際にci-policyを読んだ`policyBaseSha`を入れる。最後の観測後の変更を原子的に防ぐ保証はなく、reviewgateもGitHubの現在値を検証しない。
