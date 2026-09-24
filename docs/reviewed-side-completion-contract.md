# reviewed-side 完了記録契約

この文書は、`review://status/<owner>/<repo>/<prNumber>` が `status=reviewed` になった後に、実装側エージェントが merge 判定へ進むための証跡契約を定義する。これは Mcp-Docker#305 の完了記録・ローカル検証スライスであり、外部通知と最終merge gateの再取得は後続の変更で行う。

## 正本と配置

- 正本 skill: `skills/review-raven-thread-owl-cycle/SKILL.md`
- カタログ: `skills/catalog.json`
- バイナリへの埋め込み: `SkillsFS` (`skills.go`)
- 配置コマンド: `mcp-docker skill install`
- 配置状態の確認: `mcp-docker skill status`
- 完了記録の検証: `mcp-docker reviewgate validate --record <path> --repo <owner/repository> --pr <number> --head-sha <sha>`
- 現在の reviewed-side skill revision: `18`

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
  "skillRevision": 18,
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

`internal/reviewgate.CompletionRecord.Validate` と `mcp-docker reviewgate validate` は次を fail-closed で検証する。

- `contractVersion`、repository、PR番号、40桁小文字 SHA が有効であること
- `skillId` が `review-raven-thread-owl-cycle` で、revision が記録されていること
- skill 実行済み、全返信済み、未解決スレッド数が0件であること
- CI の HEAD と完了記録の HEAD が一致すること
- 必須 check run が1件以上あり、すべて同一 HEAD 上で `completed / success` であること
- 未知の JSON フィールド、同一オブジェクト内の重複キー、連結された複数 JSON、重複した check 名を拒否すること

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
