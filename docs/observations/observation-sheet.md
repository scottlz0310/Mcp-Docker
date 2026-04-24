# 観測シート：Copilot Review 状態取得の前提条件検証

ISSUE #83 の観測結果をステートごとに記録する。

## 観測済み：PR #81（`release/v2.4.0`、マージ済み）

**条件**: MANUAL trigger、ドキュメント変更のみ、スレッド 0 件

### タイムライン実測（REST timeline + GraphQL）

| 時刻 (UTC) | イベント | actor | 補足 |
|---|---|---|---|
| 23:24:32Z | `review_requested` | scottlz0310-user | `ready_for_review` と同時発火 |
| 23:25:03Z | `copilot_work_started` | scottlz0310-user | 依頼から **31 秒後** に着手 |
| 23:26:57Z | `PullRequestReview` (COMMENTED) | copilot-pull-request-reviewer | 着手から **114 秒後** に完了 |

### 各 API エンドポイントの返り値

#### REST: requested_reviewers

| タイミング | copilot in reviewers? |
|---|---|
| 観測未実施（PR マージ済みのため取得不可） | — |

#### REST: reviews

```json
[{
  "id": "4166786012",
  "login": "copilot-pull-request-reviewer[bot]",
  "state": "COMMENTED",
  "submitted_at": "2026-04-23T23:26:57Z"
}]
```

**注**: REST では `login` に `[bot]` サフィックスあり。GraphQL `Bot.login` とは異なる（後述）。

#### REST: timeline events（review 関連のみ）

```json
[
  { "event": "review_requested",     "created_at": "2026-04-23T23:24:32Z", "actor": "scottlz0310-user", "reviewer": "Copilot" },
  { "event": "copilot_work_started", "created_at": "2026-04-23T23:25:03Z", "actor": "scottlz0310-user" },
  { "event": "reviewed",             "created_at": null }
]
```

**注**: `reviewed` の `created_at` は `null`（マージ後取得のため。GraphQL `submittedAt` は非 null）

#### GraphQL: timelineItems

```json
[
  {
    "type": "ReviewRequestedEvent",
    "createdAt": "2026-04-23T23:24:32Z",
    "actor": "scottlz0310-user",
    "reviewer": "copilot-pull-request-reviewer",
    "reviewerType": "Bot"
  },
  {
    "type": "PullRequestReview",
    "databaseId": "2419270726",
    "state": "COMMENTED",
    "createdAt": "2026-04-23T23:26:57Z",
    "submittedAt": "2026-04-23T23:26:57Z",
    "author": "copilot-pull-request-reviewer"
  }
]
```

**注**: GraphQL `Bot.login` は `"copilot-pull-request-reviewer"`（`[bot]` サフィックスなし）

#### MCP: get_copilot_review_status（23:27:xx 時点）

```json
{
  "status": "NOT_REQUESTED",
  "trigger": "MANUAL",
  "requested": false,
  "lastReviewAt": "2026-04-23T23:26:57Z",
  "elapsedSinceRequest": "1m59s"
}
```

#### 乖離サマリ

| 項目 | GitHub 実態 | MCP 返り値 | 乖離 |
|---|---|---|---|
| 状態 | `COMPLETED`（レビュー完了） | `NOT_REQUESTED` | ⚠ |
| `requested` | `false`（reviewer 除外済み） | `false` | ✅ |
| `lastReviewAt` | `23:26:57Z` | `23:26:57Z` | ✅ |
| `requestedAt`（内部） | `23:24:32Z`（GitHub 側） | `23:27:xx`（DB 記録） | ⚠ 2分以上ずれ |

**乖離の原因**:  
DB の `requested_at`（`23:27:xx`）が GitHub 側の依頼受付時刻（`23:24:32Z`）より後のため、  
`submittedAt(23:26:57) < requested_at(23:27:xx)` となりレビューが stale 判定されて無視された。

---

## 未観測ステート

以下は実際のPRで観測が必要。観測後にこのシートへ追記すること。

### `pending`（`review_requested` あり・`copilot_work_started` なし）

**観測方法**: `request_copilot_review` を呼んだ直後（31 秒以内）にスクリプトを実行。

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `review_requested` イベント | あり | — | — |
| `copilot_work_started` イベント | なし | — | — |
| `requested_reviewers` に copilot | あり（推測） | — | — |
| MCP `status` | `PENDING` | — | — |

### `in-progress`（`copilot_work_started` あり・`PullRequestReview` なし）

**観測方法**: `copilot_work_started` 後・レビュー完了前（着手から 2 分以内目安）にスクリプトを実行。

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `copilot_work_started` イベント | あり | — | — |
| `PullRequestReview` | なし | — | — |
| `requested_reviewers` に copilot | あり（推測） | — | — |
| MCP `status` | `IN_PROGRESS` | — | — |

### `completed`（`PullRequestReview` あり・reviewer 除外前）

**観測方法**: `reviewed` イベント発生直後にスクリプトを実行。

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `PullRequestReview` (COMMENTED) | あり | — | — |
| `requested_reviewers` に copilot | なし（推測・除外済み） | — | — |
| MCP `status` | `COMPLETED` | — | — |

### `auto-trigger`（automatic review settings による自動依頼）

**観測方法**: PR を push した際に GitHub の automatic review settings が発火するリポジトリで観測。

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `review_requested` の actor | システム or GitHub Actions | — | — |
| MCP `trigger` | `AUTO` | — | — |
| `copilot_work_started` イベント | あり | — | — |

### `rereview`（2 サイクル目以降）

**観測方法**: 修正コミット後に `request_copilot_review` を再度呼んだ後に観測。

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `review_requested` イベント | 複数あり | — | — |
| `copilot_work_started` イベント | 複数あり | — | — |
| 最新の `ReviewRequestedEvent.createdAt` | 再依頼時刻 | — | — |
| MCP `prevReviewID` の機能 | 旧レビューを stale 判定 | — | — |

### `blocked`（CHANGES_REQUESTED）

| 項目 | 期待値 | 実測値 | 一致? |
|---|---|---|---|
| `PullRequestReview.state` | `CHANGES_REQUESTED` | — | — |
| `reviewDecision` | `CHANGES_REQUESTED` | — | — |
| MCP `status` | `BLOCKED` | — | — |
| MCP `isBlocking` | `true` | — | — |

---

## Check Runs 観測結果

| PR | Copilot 関連 check runs | name | status | conclusion |
|---|---|---|---|---|
| #81 | **0 件**（スクリプト実測） | — | — | — |

Copilot レビューは Check Runs として登録されない（少なくともこの PR では）。

## `latestOpinionatedReviews` 観測結果

| PR | 結果 | 備考 |
|---|---|---|
| #81 | **空**（`[]`） | Copilot の `COMMENTED` は opinionated でないため含まれない |

Copilot が `APPROVED` / `CHANGES_REQUESTED` を出さない限り `latestOpinionatedReviews` には現れない。

## Bot login サフィックスの違い（実測確認済み）

| エンドポイント | login 値 |
|---|---|
| REST `GET /pulls/{pr}/reviews` | `copilot-pull-request-reviewer[bot]`（`[bot]` あり） |
| GraphQL `Bot { login }` | `copilot-pull-request-reviewer`（`[bot]` なし） |

現在の `copilotLogins` 定数は REST の `[bot]` あり形式に対応している。GraphQL で Bot を検出する場合は `[bot]` なし版での照合が必要。

---

## 知見・結論（観測完了後に記載）

- [ ] `copilot_work_started` は `PENDING` / `IN_PROGRESS` 境界として信頼できるか
- [ ] `threshold`（経過時間）を廃止してイベントベース判定に移行できるか
- [ ] `ReviewRequestedEvent.createdAt` を `requestedAt` として使えるか
- [ ] Bot login の `[bot]` サフィックス有無の正式ルール
- [ ] `reviewed` イベントの `created_at` が null になる条件
