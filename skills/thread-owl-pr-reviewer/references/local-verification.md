# ローカル検証の隔離手順（Repository State Guard）

SKILL.md の O-04 と「Snapshot Guard」の手順 2 の手順（worktree が dirty または `reviewedHeadSha` と不一致の場合）。

**前提**: O-02 の `origin.allowed` が `true` であること。この手順に入る時点で確認済みであり、許可外の作成者・fork の PR のコードは、ローカルで実行しない（`BLOCKED_PR_ORIGIN`）。

- **dirty/mismatched な状態の扱い:**
  - 未 commit 変更を stash / discard してレビューを続行してはならない（実装担当の作業状態を破壊しないため）。
  - detached worktree または一時的な clone を作成し、`reviewedHeadSha` を checkout して検証する。
  - **一時領域（スクラッチディレクトリ）の解決**:
    - 環境変数 `SQUIRREL_REVIEW_SCRATCH_DIR` が設定されている場合：
      - パスが**絶対パス**であり、かつ**実在するディレクトリ**であることを確認する。
      - 有効な場合、隔離 worktree / clone、およびビルド成果物やテストログ等の一時ファイルをすべてその配下に作成する（例: `$SQUIRREL_REVIEW_SCRATCH_DIR/<reviewedHeadSha>-worktree`）。
      - 相対パス、存在しないパス、ファイルパスなど不正な値の場合は、**既定パスへフォールバックしてはならない**（不正な指定を黙って無視しないため）。この場合は隔離環境を作成せず、`local verification: not performed` としてレビューを進行する。
    - 環境変数 `SQUIRREL_REVIEW_SCRATCH_DIR` が未設定または空の場合：
      - 従来どおり既定の一時パス（OS の一時ディレクトリなど）を使用する（CLI 直接起動の互換性を維持）。
  - **片付け（クリーンアップ）の責務境界**:
    - 一時領域の削除・片付けはランチャー（Squirrel Notifier 等）の責務とする。
    - skill は検証完了後に `git worktree remove <temporary-path>` などの片付けをベストエフォートで行ってよいが、失敗や未実施であってもレビュー失敗としない。
    - 推奨例:
      ```bash
      git fetch origin <reviewedHeadSha>
      git worktree add --detach <temporary-path> <reviewedHeadSha>
      # 検証完了後（ベストエフォートで実行。片付けの担保はランチャーが行う）
      git worktree remove <temporary-path> || true
      ```
  - 隔離検証環境を作成できない場合は、ローカル検証を行わず `local verification: not performed` としてレビューを進行する。
  - **証跡**: evidence やユーザー報告の `worktree path` に、使用した一時領域の出所を記録する（例: `<path> (env: SQUIRREL_REVIEW_SCRATCH_DIR)` または `<path> (default)`）。
