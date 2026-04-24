#!/usr/bin/env bash
# verify-review-status.sh
#
# Copilot review の状態を複数の GitHub API エンドポイントから同時取得し、
# get_copilot_review_status (MCP) との突き合わせ検証に使う観測スクリプト。
#
# 使い方:
#   ./scripts/verify-review-status.sh <owner> <repo> <pr>
#
# 出力: 標準出力（tee でファイルに保存することを推奨）
#   ./scripts/verify-review-status.sh owner repo 42 | tee docs/observations/pr-42-$(date -u +%Y%m%dT%H%M%SZ).log
#
# 依存: gh CLI（認証済み）

set -euo pipefail

OWNER="${1:?owner required}"
REPO="${2:?repo required}"
PR="${3:?pr number required}"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
HR="─────────────────────────────────────────────"

echo "$HR"
echo "verify-review-status  $OWNER/$REPO #$PR"
echo "timestamp: $TIMESTAMP"
echo "$HR"

# ─── REST: requested_reviewers ────────────────────────────────────────────────
echo ""
echo "## REST: requested_reviewers"
gh api "repos/$OWNER/$REPO/pulls/$PR/requested_reviewers" \
  --jq '{
    users: [.users[] | {login, type: .type}],
    teams: [.teams[].slug]
  }' 2>&1 || echo "(error)"

# ─── REST: reviews (Copilot のみ) ─────────────────────────────────────────────
echo ""
echo "## REST: reviews (copilot)"
gh api "repos/$OWNER/$REPO/pulls/$PR/reviews" \
  --jq '[.[] | select(.user.login | test("copilot|github-copilot"; "i"))
         | {id: (.id | tostring), login: .user.login, state, submitted_at}]' 2>&1 || echo "(error)"

# ─── REST: timeline events (review 関連) ──────────────────────────────────────
echo ""
echo "## REST: timeline events"
gh api "repos/$OWNER/$REPO/issues/$PR/timeline" \
  --paginate \
  --jq '[.[] | select(.event | IN(
      "review_requested",
      "review_request_removed",
      "copilot_work_started",
      "reviewed",
      "ready_for_review"
    ))
    | {
        event,
        created_at,
        actor:    (.actor.login    // null),
        reviewer: (.requested_reviewer.login // null),
        body_head: ((.body // "") | if length > 0 then .[:120] + "…" else null end)
      }]' 2>&1 || echo "(error)"

# ─── GraphQL: timelineItems (ReviewRequestedEvent + PullRequestReview) ────────
echo ""
echo "## GraphQL: timelineItems"
gh api graphql -f query='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        timelineItems(first:50, itemTypes:[REVIEW_REQUESTED_EVENT,PULL_REQUEST_REVIEW]) {
          nodes {
            __typename
            ... on ReviewRequestedEvent {
              createdAt
              actor { login }
              requestedReviewer {
                __typename
                ... on User     { login }
                ... on Bot      { login }
                ... on Mannequin{ login }
                ... on Team     { name }
              }
            }
            ... on PullRequestReview {
              databaseId
              state
              createdAt
              submittedAt
              author { login }
              bodyText
            }
          }
        }
      }
    }
  }' \
  -f owner="$OWNER" -f repo="$REPO" -F pr="$PR" \
  --jq '.data.repository.pullRequest.timelineItems.nodes
        | map(
            if .__typename == "ReviewRequestedEvent" then {
              type:       "ReviewRequestedEvent",
              createdAt,
              actor:      .actor.login,
              reviewer:   (.requestedReviewer | (.login // .name // null)),
              reviewerType: .requestedReviewer.__typename
            }
            elif .__typename == "PullRequestReview" then {
              type:        "PullRequestReview",
              databaseId:  (.databaseId | tostring),
              state,
              createdAt,
              submittedAt,
              author:      .author.login,
              body_head:   (if (.bodyText | length) > 0 then .bodyText[:120] + "…" else null end)
            }
            else . end
          )' 2>&1 || echo "(error)"

# ─── GraphQL: reviewDecision + latestOpinionatedReviews + reviewRequests ──────
echo ""
echo "## GraphQL: reviewDecision / latestOpinionatedReviews / reviewRequests"
gh api graphql -f query='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        reviewDecision
        latestOpinionatedReviews(first:5) {
          nodes { state submittedAt author { login } }
        }
        reviewRequests(first:10) {
          nodes {
            requestedReviewer {
              __typename
              ... on User     { login }
              ... on Bot      { login }
              ... on Team     { name }
            }
          }
        }
      }
    }
  }' \
  -f owner="$OWNER" -f repo="$REPO" -F pr="$PR" \
  --jq '.data.repository.pullRequest | {
    reviewDecision,
    latestOpinionatedReviews: .latestOpinionatedReviews.nodes,
    reviewRequests: [.reviewRequests.nodes[].requestedReviewer | {type: .__typename, name: (.login // .name)}]
  }' 2>&1 || echo "(error)"

# ─── Check Runs (Copilot 関連) ─────────────────────────────────────────────────
echo ""
echo "## Check Runs (copilot)"
SHA=$(gh api "repos/$OWNER/$REPO/pulls/$PR" --jq '.head.sha' 2>/dev/null || echo "")
if [ -n "$SHA" ]; then
  gh api "repos/$OWNER/$REPO/commits/$SHA/check-runs" \
    --jq '[.check_runs[] | select(.name | test("copilot"; "i"))
           | {name, status, conclusion, started_at, completed_at}]' 2>&1 || echo "(none or error)"
else
  echo "(could not resolve head SHA)"
fi

echo ""
echo "$HR"
echo "done. timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "$HR"
