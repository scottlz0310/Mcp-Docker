# `{OWL}` の discovery と固定（O-00）

この文書が、`thread-owl-pr-reviewer` における `{OWL}` の discovery と binding の固定の**唯一の定義**である（SKILL.md の O-00）。同じ規則を SKILL.md に書き足さない。initial-review、re-review、thread-follow-up、summary-only の全モードで共通に使う。

`{OWL}` の候補は、tool / resource の表示名や client 固有の namespace の文字列一致ではなく、Thread Owl の logical capability と input / output schema で判定する。候補の識別単位は server instance / route と opaque handle の組み合わせであり、同名の tool が別 route に存在しても一つにまとめない。

1. PR URL 起点では `owner`、`repo`、`prNumber` を確定してから候補を列挙する。queue 起点では、まず review queue resource を discovery し、resource read で candidate の `owner`、`repo`、`prNumber`、`reason` を取得する。
2. host / client の設定に `{OWL}` の明示 binding があれば優先する。なければ、必要な read / write capability と schema を満たす候補が一つだけの場合に限り採用する。複数候補が残った場合は discovery 順や表示名だけで選ばず、`BLOCKED_MCP_DISCOVERY` として停止する。
3. 採用候補で、PR URL 起点なら `{OWL}:get_pr`、queue 起点なら queue resource read と `{OWL}:get_pr` のうち対象を確認できる最小 read を **1 回成功** させる。成功とは tool / resource error がなく、PR identity・head SHA などの minimum output schema を満たすことをいう。server 一覧、`Connected` 表示、schema 取得だけでは成功とみなさない。
4. `{OWL}` から選択済み server / route / handle への binding を run の状態に固定し、以後の全 read / write で同じ binding を使う。後続の接続失敗、schema 不一致、allowlist 拒否を、別 candidate や GitHub connector / `gh` の write に切り替える理由にしてはならない。再 discovery による途中の候補切り替えも禁止する。

binding の確定後に、`{RAVEN}` の discovery と CI read の経路の固定を、`references/ci-check.md` の「1. 経路の固定」に従って行う。`{RAVEN}` の未解決は、レビューの停止条件にしない。

## 停止

候補を解決できない、未接続、schema 不一致、read 検証失敗、または複数候補を一意に選べない場合は、次の状態で停止する。

```text
termination_status = BLOCKED_MCP_DISCOVERY
status = blocked
```

次を報告する: 対象 PR（確定済みの場合）、logical alias `{OWL}`、必要 capability、候補数、失敗分類（unresolved / not connected / schema mismatch / read failed / ambiguous）、read 検証結果、`writes performed: 0`、再実行に必要な設定変更。token・Authorization header・秘密情報は報告しない。別の MCP candidate、GitHub connector、`gh` の write 経路へ進まず、レビューコメント・Verdict・APPROVE を投稿しない。
