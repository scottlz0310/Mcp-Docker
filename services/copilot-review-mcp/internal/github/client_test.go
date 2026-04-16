package ghclient

import (
	"testing"
	"time"

	"github.com/google/go-github/v72/github"
	"github.com/shurcooL/githubv4"
)

// newReview creates a PullRequestReview with the given state and optional submittedAt.
func newReview(state string, submittedAt *time.Time) *github.PullRequestReview {
	r := &github.PullRequestReview{
		State: github.Ptr(state),
	}
	if submittedAt != nil {
		r.SubmittedAt = &github.Timestamp{Time: *submittedAt}
	}
	return r
}

// TestCopilotBotLoginValue guards against typos in the login constant.
// A wrong value here would cause a silent failure where GitHub accepts the mutation
// but Copilot is never actually added as a reviewer.
func TestCopilotBotLoginValue(t *testing.T) {
	const want = "copilot-pull-request-reviewer[bot]"
	if copilotBotLogin != want {
		t.Errorf("copilotBotLogin = %q, want %q", copilotBotLogin, want)
	}
}

// TestBuildCopilotReviewInput verifies the mutation input constructed by
// buildCopilotReviewInput satisfies the two critical invariants:
//
//  1. union must be true — preserves existing human reviewers.
//     union:false would replace the entire reviewer set with Copilot only.
//  2. botLogins[0] must equal copilotBotLogin — the exact identity GitHub expects.
func TestBuildCopilotReviewInput(t *testing.T) {
	testNodeID := githubv4.ID("PR_kwDOABCDEF12345")
	input := buildCopilotReviewInput(testNodeID)

	// Invariant 1: union must be true (additive, not replacing existing reviewers).
	if !bool(input.Union) {
		t.Error("Union must be true to preserve existing human reviewers; false would remove them")
	}

	// Invariant 2: exactly one bot login with the correct value.
	if len(input.BotLogins) != 1 {
		t.Fatalf("BotLogins length = %d, want 1", len(input.BotLogins))
	}
	if got := string(input.BotLogins[0]); got != copilotBotLogin {
		t.Errorf("BotLogins[0] = %q, want %q", got, copilotBotLogin)
	}

	// Sanity: userLogins and teamSlugs must be empty — we're only adding Copilot.
	if len(input.UserLogins) != 0 {
		t.Errorf("UserLogins must be empty, got %v", input.UserLogins)
	}
	if len(input.TeamSlugs) != 0 {
		t.Errorf("TeamSlugs must be empty, got %v", input.TeamSlugs)
	}

	// Sanity: PR node ID is passed through unchanged.
	if input.PullRequestID != testNodeID {
		t.Errorf("PullRequestID = %v, want %v", input.PullRequestID, testNodeID)
	}
}

func TestDeriveStatus(t *testing.T) {
	// threshold=30s.
	// recentRequest: 1s elapsed → PENDING (29s slack vs threshold, safe on slow CI).
	// longAgoRequest: 2min elapsed → IN_PROGRESS.
	c := &Client{threshold: 30 * time.Second}

	now := time.Now()
	recentRequest := now.Add(-time.Second)   // 1s ago — safely within 30s threshold
	longAgoRequest := now.Add(-2 * time.Minute) // 2min ago — safely past threshold
	threeMinAgo := now.Add(-3 * time.Minute)
	oneMinAgo := now.Add(-1 * time.Minute)
	oneMinLater := now.Add(1 * time.Minute)

	tests := []struct {
		name        string
		data        *ReviewData
		requestedAt *time.Time
		want        ReviewStatus
	}{
		// ── no review ────────────────────────────────────────────────────────────
		{
			name: "no review, no reviewers → NOT_REQUESTED",
			data: &ReviewData{},
			want: StatusNotRequested,
		},
		{
			name:        "no review, copilot in reviewers, within threshold → PENDING",
			data:        &ReviewData{IsCopilotInReviewers: true},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "no review, copilot in reviewers, threshold elapsed → IN_PROGRESS",
			data:        &ReviewData{IsCopilotInReviewers: true},
			requestedAt: &longAgoRequest,
			want:        StatusInProgress,
		},
		{
			name: "no review, copilot in reviewers, no requestedAt → IN_PROGRESS (AUTO)",
			data: &ReviewData{IsCopilotInReviewers: true},
			want: StatusInProgress,
		},

		// ── review exists, requestedAt nil (backward compat) ─────────────────────
		{
			name: "APPROVED review, no requestedAt → COMPLETED",
			data: &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			want: StatusCompleted,
		},
		{
			name: "CHANGES_REQUESTED review, no requestedAt → BLOCKED",
			data: &ReviewData{LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinAgo)},
			want: StatusBlocked,
		},

		// ── review submitted AFTER requestedAt ───────────────────────────────────
		{
			name:        "APPROVED review after requestedAt → COMPLETED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinLater)},
			requestedAt: &now,
			want:        StatusCompleted,
		},
		{
			name:        "CHANGES_REQUESTED review after requestedAt → BLOCKED",
			data:        &ReviewData{LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinLater)},
			requestedAt: &now,
			want:        StatusBlocked,
		},

		// ── review submitted at EXACTLY requestedAt (same-second inclusive) ───────
		{
			name:        "APPROVED review at exact requestedAt → COMPLETED (same-second inclusive)",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &now)},
			requestedAt: &now,
			want:        StatusCompleted,
		},

		// ── stale review (submitted BEFORE requestedAt) ───────────────────────────
		{
			// review (1min ago) is older than recentRequest (1s ago) → stale,
			// then elapsed since request = 1s < 30s threshold → PENDING.
			name:        "stale APPROVED review, copilot in reviewers, within threshold → PENDING",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "stale CHANGES_REQUESTED review, copilot in reviewers, within threshold → PENDING (not BLOCKED)",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "stale review, copilot NOT in reviewers → NOT_REQUESTED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusNotRequested,
		},
		{
			// review (3min ago) is older than longAgoRequest (2min ago) → stale,
			// then elapsed since request = 2min > 30s threshold → IN_PROGRESS.
			name:        "stale review, copilot in reviewers, threshold elapsed → IN_PROGRESS",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("APPROVED", &threeMinAgo)},
			requestedAt: &longAgoRequest,
			want:        StatusInProgress,
		},

		// ── nil submittedAt on review ─────────────────────────────────────────────
		{
			name:        "review with nil submittedAt, requestedAt set → treat as stale → NOT_REQUESTED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", nil)},
			requestedAt: &now,
			want:        StatusNotRequested,
		},
		{
			name: "review with nil submittedAt, no requestedAt → COMPLETED (backward compat)",
			data: &ReviewData{LatestCopilotReview: newReview("APPROVED", nil)},
			want: StatusCompleted,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := c.DeriveStatus(tt.data, tt.requestedAt)
			if got != tt.want {
				t.Errorf("DeriveStatus() = %q, want %q", got, tt.want)
			}
		})
	}
}
