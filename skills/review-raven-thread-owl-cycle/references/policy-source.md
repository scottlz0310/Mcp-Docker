# 現在のbase branchから宣言を読む

PR比較用の`baseSha`（`baseRefOid`）と、宣言元の`policyBaseSha`を分ける。author allowlistとci-policyは、同じ`baseRefName` / `policyBaseSha`のファイルだけから読む。PR HEAD・作業ツリー・既定branch・古い比較元SHAへ代替しない。branchの保護設定や認証・権限を変更する手順ではない。

## 解決と固定

1. metadata bindingのdiscoveryと最小readが成功した後、`{RAVEN}:get_pr_context`の`baseRefName` / `policyBaseSha`（現在のbase branch先頭Commit。PR比較元の`baseSha`とは別）を宣言元として固定する。取得は1回で、失敗後に別認証・別経路へ切り替えない。branch名・SHAの形式、PR head/baseとの整合はtool側で検証される。

2. author宣言は既存readerが同じ`policyBaseSha`で検証する。許可リスト本体は`author-gate.md`の手順で`gh api`のread-only、CI宣言は`get_pr_context`の`ciPolicy`から取得する。`found=false`だけを不在（空の許可）とし、他の失敗や不正JSON（schema不一致）を空の許可へ代替しない。取得後にも`get_pr_context`を再取得し、head/base/branch名/`policyBaseSha`の一致を確認する。変化した場合は古い宣言を使わず停止する。再開時は宣言取得と投稿者検証から新しく実行する。

## 書込み前と終端

各外部write直前、reader取得後、サイクル終端、完了記録の作成直前にも宣言元を解決し直す。reader v2の`baseRefName` / `policyBaseSha`と、両宣言の取得元が同じであることを確認する。取消・branch変更・進行を検出したら、以前の投稿者検証やskip許可を持ち越さず停止する。skillで自動再試行しない。reader内部の最大3試行と、外部writeの再実行を混同しない。

`baseRefName`、PR比較用`baseSha`、宣言用`policyBaseSha`、取得時点と照合結果を証跡に分けて記録する。`ci.skipPolicy.baseSha`は既存JSON名を保ち、実際にci-policyを読んだ`policyBaseSha`を入れる。最後の観測後の変更を原子的に防ぐ保証はなく、reviewgateもGitHubの現在値を検証しない。
