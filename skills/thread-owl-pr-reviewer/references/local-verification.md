# ローカル検証の隔離手順（Repository State Guard）

SKILL.md の O-04 と「Snapshot Guard」の手順 2 の手順。Squirrelのreviewer作業場所は意図的に非Gitであり、それだけを理由に検証を省かない。

**前提**: O-02 の `origin.allowed` が `true` であること。この手順に入る時点で確認済みであり、許可外の作成者・fork の PR のコードは、ローカルで実行しない（`BLOCKED_PR_ORIGIN`）。

- **検証環境の選択**:
  - 最初に `git rev-parse --is-inside-work-tree` で作業場所がGit作業ツリーか確認する。
  - Git作業ツリーであり、tracked fileがclean・HEADが `reviewedHeadSha` と一致する場合だけ、その場所で検証してよい。
  - 非Gitの作業場所では、scratch配下の `c-<SHA先頭12文字>` にcloneする。既存の実装担当checkoutを流用しない。短縮SHAはフォルダ名だけに使い、取得・checkout・HEAD照合は完全なSHAを使う。
  - dirty/mismatchedなGit作業ツリーでは、隔離worktreeまたはcloneを使用する。
- **隔離環境の作成**:
  - 未 commit 変更を stash / discard してレビューを続行してはならない（実装担当の作業状態を破壊しないため）。
  - detached worktree または一時的な clone を作成し、`reviewedHeadSha` を checkout して検証する。
  - **一時領域（スクラッチディレクトリ）の解決**:
    - 環境変数 `SQUIRREL_REVIEW_SCRATCH_DIR` が設定されている場合：
      - パスが**絶対パス**であり、かつ**実在するディレクトリ**であることを確認する。
      - 有効な場合、隔離 worktree / clone と検証の一時ファイルをすべてその配下に作成する（worktree名は `w-<SHA先頭12文字>`）。
      - 相対パス、存在しないパス、ファイルパスなど不正な値の場合は、**既定パスへフォールバックしてはならない**（不正な指定を黙って無視しないため）。この場合は隔離環境を作成せず、`local verification: not performed` としてレビューを進行する。
    - 環境変数 `SQUIRREL_REVIEW_SCRATCH_DIR` が未設定または空の場合：
      - 従来どおり既定の一時パス（OS の一時ディレクトリなど）を使用する（CLI 直接起動の互換性を維持）。
  - **片付け（クリーンアップ）の責務境界**:
    - 一時領域の削除・片付けはランチャー（Squirrel Notifier 等）の責務とする。
    - skill は検証完了後に `git worktree remove <temporary-path>` などの片付けをベストエフォートで行ってよいが、失敗や未実施であってもレビュー失敗としない。
    - Git作業ツリー内での例:
      ```bash
      git fetch origin <reviewedHeadSha>
      git worktree add --detach <temporary-path> <reviewedHeadSha>
      # 検証完了後（ベストエフォートで実行。片付けの担保はランチャーが行う）
      git worktree remove <temporary-path>
      ```
  - **非Gitの作業場所での手順**:
    1. O-02で取得したowner/repoと固定SHAからrepositoryとclone先を決める。private repoの認証は実行環境の `gh` に委ね、tokenを引数やログに出さない。
    2. 次の例の各コマンドの終了コードを確認する。失敗したら後続コマンドを実行せず、検証不能の理由を報告する。別token・別checkoutへ自動切替しない。
       ```powershell
       $repository = "$owner/$repo"
       $clonePath = Join-Path $scratchRoot ("c-" + $reviewedHeadSha.Substring(0, 12))
       gh repo clone $repository $clonePath -- --no-checkout
       git -C $clonePath fetch origin $reviewedHeadSha
       git -C $clonePath checkout --detach $reviewedHeadSha
       git -C $clonePath rev-parse HEAD
       git -C $clonePath status --porcelain --untracked-files=no
       ```
    3. HEADが固定SHAと文字列全体で一致し、tracked fileがcleanであることを確認してから、そのcloneで必要なbuild/testを実行する。検証後もSnapshot Guardの手順3で再確認する。
  - clone不能、認証/ネットワーク障害、不正scratch、検証コマンドを実行できない等の場合は、`local verification: not performed` とし、理由・試した操作・未検証範囲を完了サマリーとユーザー報告へ記録する。cloneできたのに検証を省いた場合も未実施として報告する。未実施時のVerdictはSKILL.mdの「Verdict」に従い、CI成功でも承認しない。検証を実行して失敗した場合は未実施ではなく、その失敗を記録する。
  - **証跡**: evidence やユーザー報告の `worktree path` に、使用した一時領域の出所を記録する（例: `<path> (env: SQUIRREL_REVIEW_SCRATCH_DIR)` または `<path> (default)`）。
