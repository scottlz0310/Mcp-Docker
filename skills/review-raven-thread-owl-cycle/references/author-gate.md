# プロジェクト固有の追加許可リスト（必須コメント投稿者ゲート）

SKILL.md の「必須コメント投稿者ゲート」にある「プロジェクト固有の追加許可リスト」から移した手順（内容は変更していない）。

### プロジェクト固有の追加許可リスト

プロジェクト固有の CI/CD 通知 bot は、skill 本体の canonical allowlist へ追加せず、対象リポジトリのルートにある `.review-raven/trusted-comment-authors.json` で追加する。このファイルは client に依存しないリポジトリ設定として、プロジェクトの git 履歴に残す。

ファイルのスキーマは次のとおりとする。

```json
{
  "version": 1,
  "additional_logins": [
    "cloudflare-workers-and-pages"
  ]
}
```

1. R-00 で対象 PR の base ref SHA（`baseRefOid`）を先に固定し、その SHA のファイルだけを固定済みの `{GH}` binding で読む。作業ツリー、PR HEAD、PR の変更ファイルから読んではならない。
2. ファイルが存在しない場合は追加項目なしとして、base allowlist だけを使う。存在する場合は JSON object、`version: 1`、文字列だけの `additional_logins` 配列、未知のキーがないことを検証する。
3. 各 login には既存の `normalize_login` を適用し、base allowlist との union を canonical allowlist とする。wildcard、正規表現、Organization 所属、`author_association`、App の権限による暗黙の追加は認めない。配列内の正規化後重複、null、空文字、非文字列、類似名は不正とする。
4. このファイルを変更できる主体が新しい信頼境界になるため、保護された base branch へ取り込む変更はリポジトリ管理者がレビューする。PR 側で追加された設定は、base branch に反映されるまで信頼源にしない。
5. ファイルの読み取り・JSON・schema 検証に失敗した場合は `termination_status = PROJECT_ALLOWLIST_INVALID` として fail-closed に停止し、本文取得、修正、返信、resolve、コメント、enqueue、merge を行わない。
