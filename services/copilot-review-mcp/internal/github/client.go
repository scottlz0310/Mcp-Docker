// Package ghclient wraps the GitHub REST API for Copilot review operations.
package ghclient

import (
	"context"
	"time"

	"github.com/google/go-github/v72/github"
)

// copilotLogins lists the known GitHub Copilot reviewer identities, checked in order.
var copilotLogins = []string{
	"github-copilot[bot]",
	"copilot-pull-request-reviewer[bot]",
	"github-copilot",
}

func isCopilot(login string) bool {
	for _, l := range copilotLogins {
		if login == l {
			return true
		}
	}
	return false
}

// ReviewStatus represents the Copilot review lifecycle state for a PR.
type ReviewStatus string

const (
	StatusNotRequested ReviewStatus = "NOT_REQUESTED"
	StatusPending      ReviewStatus = "PENDING"
	StatusInProgress   ReviewStatus = "IN_PROGRESS"
	StatusCompleted    ReviewStatus = "COMPLETED"
	StatusBlocked      ReviewStatus = "BLOCKED"
)

// ReviewData holds the raw review information fetched from GitHub.
type ReviewData struct {
	// IsCopilotInReviewers is true when Copilot is in the PR's requested reviewers list.
	IsCopilotInReviewers bool
	// LatestCopilotReview is the most recently submitted Copilot review, or nil.
	LatestCopilotReview *github.PullRequestReview
	// RateLimitRemaining is the number of remaining API calls in the current window.
	RateLimitRemaining int
	// RateLimitReset is when the rate limit window resets.
	RateLimitReset time.Time
}

// Client wraps the GitHub API for Copilot review operations.
type Client struct {
	gh        *github.Client
	threshold time.Duration // elapsed threshold for PENDING→IN_PROGRESS
}

// NewClient creates a new GitHub API client authenticated with the given token.
// threshold is the elapsed time after which PENDING becomes IN_PROGRESS.
func NewClient(token string, threshold time.Duration) *Client {
	return &Client{
		gh:        github.NewClient(nil).WithAuthToken(token),
		threshold: threshold,
	}
}

// GetReviewData fetches raw reviewer and review data for a PR from GitHub.
func (c *Client) GetReviewData(ctx context.Context, owner, repo string, prNumber int) (*ReviewData, error) {
	data := &ReviewData{}

	// Fetch current requested reviewers.
	reviewers, resp, err := c.gh.PullRequests.ListReviewers(ctx, owner, repo, prNumber, nil)
	if err != nil {
		return nil, err
	}
	if resp != nil {
		data.RateLimitRemaining = resp.Rate.Remaining
		data.RateLimitReset = resp.Rate.Reset.Time
	}
	for _, u := range reviewers.Users {
		if isCopilot(u.GetLogin()) {
			data.IsCopilotInReviewers = true
			break
		}
	}

	// Fetch submitted reviews.
	reviews, resp2, err := c.gh.PullRequests.ListReviews(ctx, owner, repo, prNumber, nil)
	if err != nil {
		return nil, err
	}
	if resp2 != nil {
		data.RateLimitRemaining = resp2.Rate.Remaining
		data.RateLimitReset = resp2.Rate.Reset.Time
	}
	for _, r := range reviews {
		if !isCopilot(r.GetUser().GetLogin()) {
			continue
		}
		if data.LatestCopilotReview == nil ||
			r.GetSubmittedAt().After(data.LatestCopilotReview.GetSubmittedAt().Time) {
			r2 := r // avoid loop-variable capture
			data.LatestCopilotReview = r2
		}
	}

	return data, nil
}

// DeriveStatus resolves the ReviewStatus from raw data and optional trigger_log requestedAt.
// requestedAt is nil when no trigger_log entry exists (AUTO trigger or not yet recorded).
func (c *Client) DeriveStatus(data *ReviewData, requestedAt *time.Time) ReviewStatus {
	if data.LatestCopilotReview != nil {
		if data.LatestCopilotReview.GetState() == "CHANGES_REQUESTED" {
			return StatusBlocked
		}
		return StatusCompleted
	}
	if data.IsCopilotInReviewers {
		if requestedAt != nil {
			elapsed := time.Since(*requestedAt)
			if elapsed >= c.threshold {
				return StatusInProgress
			}
			return StatusPending
		}
		// No trigger_log entry (AUTO trigger or unknown): assume IN_PROGRESS
		return StatusInProgress
	}
	return StatusNotRequested
}

// RequestCopilotReview sends a review request for the Copilot bot on the given PR.
func (c *Client) RequestCopilotReview(ctx context.Context, owner, repo string, prNumber int) error {
	_, _, err := c.gh.PullRequests.RequestReviewers(ctx, owner, repo, prNumber,
		github.ReviewersRequest{Reviewers: []string{"github-copilot"}},
	)
	return err
}
