# ユーザー管理 instruction source

## 目的

CLI エージェントごとの instruction 本文をリポジトリへコピーせず、ユーザーが管理する 1 つの source of truth を各 CLI のユーザー単位の入口から参照する。

`Mcp-Docker` が管理するのは source のパス、配置方式、リンク状態である。source の本文・トークン・個人環境の絶対パスは、リポジトリの設定やログへ保存しない。

## 対応する入口

| エージェント | ユーザー単位の instruction 入口 |
|---|---|
| Claude CLI | `~/.claude/CLAUDE.md` |
| GitHub Copilot CLI | `~/.copilot/copilot-instructions.md` |
| Codex CLI | `~/.codex/AGENTS.md` |
| Antigravity / Gemini CLI | `~/.gemini/GEMINI.md` |

## 設定と配置

source は明示的な絶対パスで設定する。`configure` は source の存在を検証し、本文を読み込まずにユーザー設定へパスと `symlink` 方式だけを保存する。

```text
mcp-docker instruction configure --source "C:\path\to\user-instructions.md"
mcp-docker instruction status
mcp-docker instruction link --dry-run
mcp-docker instruction link --yes
```

設定済み source を変更せずに一時的な source を使う場合は、`link` / `status` / `repair` に `--source` を指定できる。

```text
mcp-docker instruction link --agent codex --source "C:\path\to\user-instructions.md" --dry-run
mcp-docker instruction repair --agent claude,copilot --yes
```

ユーザー設定ファイルの既定位置は、Windows では `%AppData%\mcp-docker\instructions.json`、その他の OS では Go の `os.UserConfigDir()` 配下の `mcp-docker/instructions.json` である。テスト・隔離環境では `MCP_DOCKER_INSTRUCTION_CONFIG` と `MCP_DOCKER_INSTRUCTION_HOME` で差し替えられる。

現在の配置方式は `symlink` のみである。symlink 作成に失敗した場合、通常ファイルのコピーへフォールバックしない。Windows では symlink 作成に必要な権限または Developer Mode が必要になる場合がある。

## 既存配置の保護

- source と同じリンクが既にある場合は、何も変更しない。
- `link` は、異なる symlink、壊れた symlink、通常ファイルを、確認後に同一ディレクトリへバックアップし、配置先を一時 symlink で原子的に置き換える。
- `repair` は壊れた symlink または別 source への symlink だけを修復し、通常ファイルや未配置の入口を保護する。
- バックアップ名は `<配置先>.mcp-docker-backup-<UTC timestamp>` である。
- `--dry-run` はディレクトリ作成・バックアップ・リンク作成を行わない。
- 配置先がディレクトリ、または未対応のファイル種別の場合は自動置換せず停止する。置換直前にも配置先を再検証し、検証後にディレクトリへ変化した場合も、ディレクトリをバックアップへ移動せず停止する。
- source と配置先が symlink やハードリンク経由で同じ実体を指す場合は、循環や source 消失を防ぐため拒否する。

したがって、既存ファイルがある場合にバックアップを取るのは正しいが、未確認の通常ファイルを黙って上書きすることはしない。既存の symlink はリンク先を追跡せず、symlink のリンク値をバックアップする。通常ファイルは hard link によるバックアップを作成し、配置先のディレクトリを移動する操作は行わない。

`status` は source の存在検証で停止せず、source が移動・削除された場合も `[見つかりません]` と配置先の link type / target を表示する。一方、`link` と `repair` は source が存在する通常ファイルであることを必須とし、fail-closed で停止する。

## instruction source に追加するレビュー待機ルール

次の差分を、ユーザー管理の source に一度だけ追加する。これは `Mcp-Docker` のリポジトリへコピーするものではなく、各 CLI が同じ source を読むことで共有される。

```diff
--- a/<user-managed-instruction-source>
+++ b/<user-managed-instruction-source>
@@
 ### PR レビューサイクル
+
+### PR 作成・更新後のレビュー完了待機
+
+実装依頼の入口は Issue（`#xxx`）の実装、またはハンドオフの受け渡しとする。実装開始時に reviewed-side のレビュー対応 skill を呼び出さない。
+
+PR を作成または更新した実装側エージェントは、同じセッションで次を行う。
+
+1. `--mcp-http` 構成では thread-owl の `enqueue_review` を、PR作成時は `reason: opened`、既存PRへのpush後は `reason: synchronized`、修正対応後の再レビューは `reason: re-review-requested` で呼ぶ。
+2. enqueue の直後に `mcp-resource-subscriber` で、owner / repo を小文字にした `review://status/<owner>/<repo>/<prNumber>` を購読する。
+3. `listenAcknowledged`、要求URIの受理、対象PR、最終 `status`（`reviewed` または `approved`）、`headSha` と待機開始時のPR HEAD一致を確認してからレビュー結果を取得する。
+4. timeout、resource消失、URI不一致、HEAD不一致、認証・URL解決失敗は完了扱いにせず、原因と再実行条件を報告して停止する。
+5. webhook構成では自動enqueueとの二重登録を行わない。queue登録は reviewer の起動ではなく、マージも自律実行しない。
+6. レビュー完了後は status だけで指摘なしと判断せず、未解決スレッドを取得してから、明示されたレビュー対応手順またはハンドオフへ進む。
+
+レビュー開始は Squirrel Notifier の「レビューする」ボタン、または別 CLI エージェントへの reviewer 起動指示で行う。購読はレビュー完了を待つためのものであり、登録・購読だけでレビュー開始済みとは扱わない。
+
+購読の接続設定や CLI への配布は `mcp-resource-subscriber` / Mcp-Docker 側の責務とし、review-raven の reviewed-side skill はレビューコメント受信後の修正・返信・resolve にのみ使う。
```

購読 URL や gateway の認証情報は source 本文へ固定値で書かず、各 CLI の実行環境・MCP 設定から解決する。購読が利用できない場合は、待機を完了扱いにせず原因と復旧方法を報告する。

## 責務境界

| 責務 | 担当 |
|---|---|
| instruction source の本文 | ユーザー管理ファイル |
| source パス、symlink、状態確認、バックアップ | Mcp-Docker |
| review queue への登録 | thread-owl の `enqueue_review` |
| review 完了イベントの購読 | mcp-resource-subscriber |
| レビューエージェントの起動 | Squirrel Notifier または別 CLI エージェント |
| コメント対応、返信、resolve | review-raven / reviewed-side skill |

関連 Issue: [Mcp-Docker #302](https://github.com/scottlz0310/Mcp-Docker/issues/302)、[squirrel-notifier #87](https://github.com/scottlz0310/squirrel-notifier/issues/87)
