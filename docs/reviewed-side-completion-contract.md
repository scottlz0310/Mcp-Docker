# reviewed-side 完了記録契約

この文書は、`review://status/<owner>/<repo>/<prNumber>` が `status=reviewed` になった後に、実装側エージェントが merge 判定へ進むための証跡契約を定義する。これは Mcp-Docker#305 の完了記録・ローカル検証スライスであり、外部通知と最終merge gateの再取得は後続の変更で行う。

## 正本と配置

- 正本 skill: `skills/review-raven-thread-owl-cycle/SKILL.md`（手順の詳細は、同じ skill の `references/` にある。完了記録の作成と検証は `references/completion-record.md`、停止コードの定義は SKILL.md の「停止コード」の表）
- カタログ: `skills/catalog.json`
- バイナリへの埋め込み: `SkillsFS` (`skills.go`)
- 配置コマンド: `mcp-docker skill install`
- 配置状態の確認: `mcp-docker skill status`
- 完了記録の検証: `mcp-docker reviewgate validate --record <path> --repo <owner/repository> --pr <number> --head-sha <sha>`
- reviewed-side skill の revision: `skills/catalog.json` の `review-raven-thread-owl-cycle` の `revision`（この文書に値を書かない。手書きの値は更新を忘れて乖離する）

配置先は次の4種類であり、skill 本体を各クライアントへ二重管理しない。

| エージェント | 配置先 |
|---|---|
| Claude | `~/.claude/skills/` |
| Copilot | `~/.copilot/skills/` |
| Codex | `~/.codex/skills/` |
| Antigravity | `~/.gemini/config/skills/` |

各配置先には `.mcp-docker-skill.json` を置き、`content_hash` と `revision` で正本との差分・方向を確認する。手動コピーや別リポジトリからの読み込みは、正本解決の経路として扱わない。

## 完了記録

完了記録は JSON で、次の項目を必須とする。

```json
{
  "contractVersion": 1,
  "repo": "owner/repository",
  "prNumber": 123,
  "headSha": "0123456789abcdef0123456789abcdef01234567",
  "skillId": "review-raven-thread-owl-cycle",
  "skillRevision": <skills/catalog.json の revision（整数）>,
  "skillCompleted": true,
  "all_replied": true,
  "unresolved_count": 0,
  "ci": {
    "headSha": "0123456789abcdef0123456789abcdef01234567",
    "complete": true,
    "requiredChecks": [
      {
        "name": "Go CLI チェック",
        "headSha": "0123456789abcdef0123456789abcdef01234567",
        "status": "completed",
        "conclusion": "success"
      }
    ]
  }
}
```

必須 check が repository に定義されていない場合は、`ci` を次の形にする。`requiredChecks` が空であること自体は「未定義」を意味しない。読み取りに成功して未定義と確認できたときだけ、`requiredChecksPolicy` を `undefined` にして、固定 HEAD で観測した全 check run を `observedChecks` に列挙する。必須 check を判定できなかった場合（読み取り失敗など）は、完了記録を作らず `CI: unknown` で停止する。

```json
  "ci": {
    "headSha": "0123456789abcdef0123456789abcdef01234567",
    "complete": true,
    "requiredChecksPolicy": "undefined",
    "requiredChecks": [],
    "observedChecks": [
      {
        "name": "Go CLI チェック",
        "appId": 15368,
        "headSha": "0123456789abcdef0123456789abcdef01234567",
        "status": "completed",
        "conclusion": "success"
      }
    ]
  }
```

`requiredChecksPolicy` は省略可能で、省略は `defined` と同じ（`contractVersion` は 1 のまま）。`observedChecks` は `undefined` のときだけ指定できる。CI の read は (GitHub App の ID, name) ごとに再実行を集約するため、別の App が同名の check を報告すると同名の run が複数残る。`observedChecks` の各要素には、報告した App の ID を `appId`（1 以上）として必ず付け、`(appId, name)` の重複だけを拒否する。`requiredChecks` の `appId` は省略でき（指定する場合は 0 以上）、必須 check は context 単位なので、同名は App が違っても重複として拒否する。

`internal/reviewgate.CompletionRecord.Validate` と `mcp-docker reviewgate validate` は次を fail-closed で検証する。

- `contractVersion`、repository、PR番号、40桁小文字 SHA が有効であること
- `skillId` が `review-raven-thread-owl-cycle` で、revision が記録されていること
- skill 実行済み、全返信済み、未解決スレッド数が0件であること
- CI の HEAD と完了記録の HEAD が一致すること
- 必須 check run が1件以上あり、すべて同一 HEAD 上で `completed / success` であること。`requiredChecksPolicy` が `undefined` のときは、`requiredChecks` が空で、`observedChecks`（固定 HEAD で観測した全 check run）が1件以上あり、すべて同一 HEAD 上で `completed / success` であること（`observedChecks` は `appId` を持ち、`(appId, name)` が重複しないこと）
- `requiredChecksPolicy` が `defined`（省略を含む）のときに `observedChecks` を持たないこと、未対応の値でないこと
- `skipped` の扱い（下の「skipped の許可」）。`success` 以外の結論は、`ci.skipPolicy` で許可した名前の `skipped` に `policyAllowedSkip` を付けたものを除き、`neutral` を含めてすべて `CI_NOT_GREEN` とすること。`success` の check が1件も無い記録は拒否すること
- 未知の JSON フィールド、同一オブジェクト内の重複キー、連結された複数 JSON、重複した check 名を拒否すること

### skipped の許可

`if` 条件で設計どおりに `skipped` になる job（PR では実行しない job など）は、GitHub では成功として扱われ、必須チェックでもマージを妨げない。一方で、本来動くべき実質的な check（テストなど）が、`if` やパスフィルタの誤りで黙って `skipped` になった場合と、結論からは区別できない。そのため、`skipped` を一律には許さず、リポジトリが**名前を明示して許可した check に限り**成功として扱う。

- 宣言: 対象リポジトリの `.review-raven/ci-policy.json` に `{"version": 1, "allowedSkippedChecks": ["<check run の name>", ...]}` を置く。ファイルが無ければ、許可は 0 件である。
- 信頼境界: 宣言は、PR の HEAD ではなく **base ref のファイルだけ**を読む。PR 自身が、自分の skip を許可できないようにするためで、投稿者の許可リスト（`.review-raven/trusted-comment-authors.json`）と同じ規則である。宣言を読めない・形式が不正な場合は、許可を推測せず `CI: unknown` で止まる（reviewed-side skill の `references/ci-check.md` 手順 2a）。
- 完了記録: 宣言を読んだ base ref の SHA と名前を `ci.skipPolicy`（`baseSha`、`allowedSkippedChecks`）に記録し、許可に基づいて成功として扱った check に `policyAllowedSkip: true` を付ける（`conclusion` は `skipped` のまま）。`ci.skipPolicy` は `requiredChecksPolicy` が `defined` / `undefined` のどちらでも指定できる。許可を使わないときは省略する。
- 検証: `mcp-docker reviewgate validate` は、`conclusion` が `skipped` で、名前が `allowedSkippedChecks` にあり、`policyAllowedSkip` が付いた check だけを成功として受け入れる。`policyAllowedSkip` を `skipped` 以外の check に付ける、宣言に無い名前に付ける、`baseSha` が 40 桁の小文字 hexadecimal でない、`allowedSkippedChecks` が空・空白を含む・重複する、の記録は `COMPLETION_RECORD_INVALID` とする。許可した `skipped` 以外の check が1件でも成功でなければ、許可があっても `CI_NOT_GREEN` である。
- 限界: この検証器は、記録内の整合しか確認できない。宣言が base ref から読まれたこと、および `baseSha` が実際の base ref であることは、記録を作る skill の手順（`ci-check.md` 手順 2a）に依存する。この記録は自己申告可能な証跡であり、後続の gate が現在の状態を再取得して照合する、という前提は変わらない。

```json
  "ci": {
    "headSha": "0123456789abcdef0123456789abcdef01234567",
    "complete": true,
    "requiredChecksPolicy": "undefined",
    "requiredChecks": [],
    "skipPolicy": {
      "baseSha": "89abcdef0123456789abcdef0123456789abcdef",
      "allowedSkippedChecks": ["report"]
    },
    "observedChecks": [
      { "name": "update", "appId": 15368, "headSha": "0123456789abcdef0123456789abcdef01234567", "status": "completed", "conclusion": "success" },
      { "name": "report", "appId": 15368, "headSha": "0123456789abcdef0123456789abcdef01234567", "status": "completed", "conclusion": "skipped", "policyAllowedSkip": true }
    ]
  }
```

この記録自体は自己申告可能な証跡であり、merge の唯一の根拠ではない。`mcp-docker reviewgate validate` は JSON の契約、直前に固定した repository・PR・HEAD、および実行中バイナリに埋め込まれた reviewed-side skill の revision を照合する。後続の gate は、現在の PR HEAD、購読 URI、review thread、GitHub の required checks を再取得し、同一値であることを確認する。

## 停止コード

| コード | 停止条件 |
|---|---|
| `SKILL_UNAVAILABLE` | 正本 skill の解決・読み込み・revision 確認に失敗 |
| `COMPLETION_RECORD_INVALID` | JSON または完了記録の契約違反 |
| `REVIEW_STATUS_MISMATCH` | `reviewed` 通知の URI・PR・status が一致しない |
| `HEAD_MISMATCH` | PR、完了記録、review thread、CI の HEAD が不一致 |
| `REVIEW_INCOMPLETE` | skill 未完了、未返信、または未解決 thread が残存 |
| `CI_NOT_GREEN` | 固定 HEAD の必須 CI が未完了または失敗 |
| `REVIEW_GATE_UNAVAILABLE` | 完了記録のローカル検証コマンドを実行できない |

いずれかの停止条件に該当した場合、手動継続・別認証経路への切り替え・merge 操作へ進んではならない。停止理由と再実行条件を報告する。

## 責務境界

- **Mcp-Docker**: skill 正本・配置・完了記録契約・`reviewgate validate`・後続の merge gate
- **review-raven**: thread の取得・返信・resolve、固定 SHA CI の read capability
- **mcp-resource-subscriber**: `reviewed` 通知、URI、PR、`headSha` の伝達
- **squirrel-notifier**: 必要な場合に起動エージェントへ skill 識別子を渡す通知連携

このスライスでは既存の skill 配布動作と、reviewer-side skill の起動契約を変更しない。
