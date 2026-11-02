# 中断通知（O-02/O-04/O-10/O-12）

通常の指摘・Verdict・APPROVEを禁止することと、中断を知らせることを分ける。通常完了のsummary/Verdictは中断通知へ流用しない。中断後も`status = blocked`と元の停止コードを維持する。

## 開始時に固定する値

- O-00で同じOWL bindingの`post_review_stop`を任意capabilityとして記録する。入力はowner/repo/prNumber、delivery、attemptId、notificationId、reviewedHeadSha/currentHeadSha、code、facts/unverified/resumeConditions。応答はok/commentId/notification/statusUpdated/attemptId。未対応・schema不一致でも通常レビューは続行できるが、異常時は「通知未実施」として止める。途中の再discoveryや別経路への切替はしない。
- O-02の最初の成功したmetadataで`reviewedHeadSha`、PR identity、origin.allowed、binding、`notificationId`（run内で生成したUUID）を固定する。Squirrel/queue経由と確認できるrunは`reviewAttempt`のpending、UUIDのattemptId、PR HEADと同じheadShaも固定する。後のget_prでIDを取り直して紐付けない。
- 明示的なCLI直接起動では`delivery=comment-only`とし、既存pendingのattemptIdを借用しない。queue経路のreviewAttempt欠落/null/不一致、または起動経路不明は通知不可。旧サーバーの欠落から「直接起動」と推測しない。
- O-02以降のreadでattemptが変わったら古いrunを現在のattemptとして続けない。APIの開始時照合は最初のmetadata取得以降を守るもので、ランチャー起動とGitHub更新の原子性までは保証しない。

## 停止理由を区別する

| 観測 | 停止コード・再開条件 |
|---|---|
| PR head/base・宣言元の移動 | STALE_REVIEW。旧対象と現在値を分け、新runでsnapshotから取り直す |
| ローカルHEADの意図しない移動、実質的tracked内容の変更 | LOCAL_CONTENT_CHANGED。検証結果を採用せず、隔離環境を作り直す |
| checkout/生成処理による改行等の環境差異 | LOCAL_ENVIRONMENT_DIFFERENCE。差異の根拠と未検証範囲を示し、入力/属性を修正後に別runで検証する |
| 検証の途中中断により結果が確定しない | VERIFICATION_INTERRUPTED。中断事実と再実行に必要な条件を示す |

ローカル差異は`local-verification.md`の観測に従う。remote移動とローカル変更が両方あればSTALE_REVIEWを優先する。結果の出たテスト失敗は中断・未実施へ置き換えず、実際の指摘として評価する。環境を準備できない既存の`local verification: not performed`は、承認せずcomment only/needs follow-upで通常完了できる。すべての環境障害を中断へ変えない。

## 通知条件とwrite

1. 最初に元の停止コード、対象、mode、確認事実、未検証範囲、再開条件、実際のwrites performedを確定する。投稿未許可のsummary-onlyでは停止通知も行わない。通常完了writeを既に試行したrun、inline/返信等の投稿結果不明、許可外投稿者、origin/repo拒否、対象/binding不明、認証/read失敗では通知しない。失敗を隠すための追加writeはしない。
2. 通知可能コードは上表の4つとREPOSITORY_STATE_UNSAFE、INVALID_COMMENT_POSITION、VERDICT_TOOL_UNAVAILABLE、投稿前のVERDICT_FORMAT_INVALIDのみ。投稿後の書式不一致や結果不明では使わない。通知tool不在、参照文書の読取失敗、その他コードはチャットのみで「通知未実施」と理由を示す。
3. 同じOWL bindingでmetadataを再readし、PR identity/open状態・origin.allowed=true・現在HEADを確認する。policy-source.mdで現在の宣言元を解決し、readerで現在の投稿者を検証する。中断通知だけの検証では、この現在値を別のnotification snapshotへ固定してreaderのhead/base/baseRefName/policyBaseShaと照合する。元のreviewedHeadShaを上書きしない。移動で止まった場合も新しい宣言に対して検証し、古い許可を引き継がない。検証の成立を示すためだけの新snapshotで通常レビューを再開しない。read失敗や拒否を迂回しない。
4. queuedでは開始時attemptId/headShaが現在も同じpendingであることを確認する。通知直前に移動した場合は通知しない。comment-onlyはattemptIdを省略し、statusを変更しない。
5. `post_review_stop`を**高々1回**呼ぶ。codeは元の通知可能コード、currentHeadShaは再確認した現在値とし、HEADが異なる場合はSTALE_REVIEWだけを使う。詳細欄は各1〜4096文字、秘密や正常完了マーカーを含めない。サーバーが固定書式と識別マーカーを生成する。通常の指摘・Verdict・APPROVE、別connector/ghのwriteへ戻らない。
6. 成功応答は正のcommentId、notificationがposted/existing、同じattemptId（直接起動はnull）を確認する。queuedのstatusUpdated=falseは、投稿中の次enqueueや既存停止との照合等による可能性がある。現在statusを再readして確認し、通知完了と通常完了を混同しない。次attemptを上書きするため再送しない。
7. 成功した場合は、同bindingのreaderで返却IDの本文・App投稿者（正規化thread-owl）・PR・両HEAD・停止コード・通知識別子を確認する。未確認は未確認のまま報告する。通知は停止理由の記録であり、approve/reviewed/マージ可能ではない。

## 結果不明と限界

tool error、transport failure、STOP_NOTIFICATION_UNCERTAIN、STOP_NOTIFICATION_IN_PROGRESS、STOP_NOTIFICATION_CONFLICT、STOP_ATTEMPT_MISMATCH等は再送しない。同じbindingのreaderで**一度だけ**既存通知を照合する。見つからない場合もnotificationId/attemptIdを変えたり、再起動・再enqueue・別認証でやり直したりしない。read-backだけで不確実なwriteを成功に繰り上げず、確認できた事実と未確定範囲を報告する。

APIはPR単位のプロセス内排他とGitHub App ID/マーカー照合を行うが、GitHub投稿とstatus更新は非原子的。複数サーバー間のexactly-onceではない。通知toolに到達できないクラッシュや通知不可のrunはpendingのまま残り得るため、依頼側はSquirrelのfinishedと有限timeoutを維持する。過去runへの遡及投稿や再enqueueは行わない。
