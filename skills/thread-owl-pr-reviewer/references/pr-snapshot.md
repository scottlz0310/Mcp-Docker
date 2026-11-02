# 小さいmetadataと完全diffの取得（O-02/O-03）

`get_pr`は`includePatch: false`で呼ぶ。開始時だけでなくSnapshot Guard・CI・停止通知直前のmetadata再取得にも適用する。入力schemaにbooleanの`includePatch`がなければ`BLOCKED_MCP_DISCOVERY`で停止し、対応するthread-owl APIの先行配備を求める。patch付きの再取得へ切り替えない。

成功応答ではPR identity、`pr.head.sha`、`pr.base.sha`、`origin`、`reviewAttempt`に加え、`patchesOmitted: true`と`files`の各要素の`filename/status/additions/deletions`を検証する。`patch`は含まれない。欠落・不一致は`REMOTE_SNAPSHOT_READ_FAILED`。省略は明示的なmetadata取得の結果であり、空diffやレビュー済みを意味しない。最初の成功metadataでhead/base SHAと開始時attemptを固定する。

完全diffは`origin.allowed: true`の確認後、`local-verification.md`のO-04で用意した隔離環境から取得する。headだけでなく固定したbase SHAのcommitも取得し、両SHAの存在とHEAD一致を確認する。PRの比較は`git diff <baseSha>...<reviewedHeadSha>`（merge-baseからhead）とし、branch名や動いたbase branch先頭へ置き換えない。宣言用の`policyBaseSha`はdiffのbaseに使わない。

- 変更ファイル一覧、rename/deletion、統計、各fileの差分を読み、metadataのファイル一覧と照合する。rename前後のpathを混同しない。GitHubのpatchは大きな変更やbinaryで欠ける場合があり、`includePatch: true`も完全性の証明にはしない。
- 巨大diffは固定した同じSHA対をpath・hunkごとに分けて読む。出力上限・途中省略・欠落があれば取得範囲を分け、diff全体を確認した根拠を記録する。stat・ファイル名だけでレビューを終えない。
- binaryや生成物は形式に応じて変更内容・生成入力を検証し、未確認部分を隠さない。必要なdiffや投稿位置の完全性を確認できなければ`DIFF_SNAPSHOT_INCOMPLETE`で停止する。read-onlyのconnector/ghで補完する場合も、同じPR identityと固定SHA対を照合し、省略応答を完全diffとして扱わない。

inlineは固定diffのpath/lineを根拠にし、投稿直前に既存Snapshot Guardでcurrent HEAD/baseを再確認する。metadataの`patchesOmitted`を理由に位置を推測しない。これはMCP応答量の削減であり、GitHub APIの通信量を減らす保証ではない。
