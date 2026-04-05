// Package ghclient wraps the GitHub REST and GraphQL APIs for Copilot review operations.
package ghclient

import (
	"context"
	"fmt"
	"math"
	"time"

	"github.com/google/go-github/v72/github"
	"github.com/shurcooL/githubv4"
	"golang.org/x/oauth2"
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
	v4        *githubv4.Client
	threshold time.Duration // elapsed threshold for PENDING→IN_PROGRESS
}

// NewClient creates a new GitHub API client authenticated with the given token.
// threshold is the elapsed time after which PENDING becomes IN_PROGRESS.
func NewClient(token string, threshold time.Duration) *Client {
	src := oauth2.StaticTokenSource(&oauth2.Token{AccessToken: token})
	httpClient := oauth2.NewClient(context.Background(), src)
	return &Client{
		gh:        github.NewClient(httpClient),
		v4:        githubv4.NewClient(httpClient),
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

	// Short-circuit if rate limit is already low to avoid consuming the second call.
	if data.RateLimitRemaining < 10 {
		return data, nil
	}

	// Fetch submitted reviews across all pages.
	reviewOpts := &github.ListOptions{PerPage: 100}
	for {
		reviews, resp2, err := c.gh.PullRequests.ListReviews(ctx, owner, repo, prNumber, reviewOpts)
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
		if resp2 == nil || resp2.NextPage == 0 {
			break
		}
		reviewOpts.Page = resp2.NextPage
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
// It tries each known Copilot identity in order, returning nil on the first success.
func (c *Client) RequestCopilotReview(ctx context.Context, owner, repo string, prNumber int) error {
	var lastErr error
	for _, login := range copilotLogins {
		_, _, err := c.gh.PullRequests.RequestReviewers(ctx, owner, repo, prNumber,
			github.ReviewersRequest{Reviewers: []string{login}},
		)
		if err == nil {
			return nil
		}
		lastErr = err
	}
	return lastErr
}

// ─── GraphQL types for review thread operations ───────────────────────────────

// reviewThreadsPageQuery fetches one page of PR review threads via GraphQL.
type reviewThreadsPageQuery struct {
	Repository struct {
		PullRequest struct {
			ReviewThreads struct {
				Nodes    []reviewThreadNode
				PageInfo struct {
					HasNextPage githubv4.Boolean
					EndCursor   githubv4.String
				}
			} `graphql:"reviewThreads(first: 100, after: $cursor)"`
		} `graphql:"pullRequest(number: $pr)"`
	} `graphql:"repository(owner: $owner, name: $repo)"`
}

type reviewThreadNode struct {
	ID         githubv4.ID
	IsResolved githubv4.Boolean
	IsOutdated githubv4.Boolean
	Path       githubv4.String
	Line       *githubv4.Int
	StartLine  *githubv4.Int
	Comments   struct {
		Nodes []struct {
			Body      githubv4.String
			CreatedAt githubv4.DateTime
			Author    struct {
				Login githubv4.String
			}
		}
	} `graphql:"comments(first: 10)"`
}

// threadNodeQuery fetches a single thread's resolved status by global node ID.
type threadNodeQuery struct {
	Node struct {
		PullRequestReviewThread struct {
			IsResolved githubv4.Boolean
		} `graphql:"... on PullRequestReviewThread"`
	} `graphql:"node(id: $id)"`
}

// addReplyMutation is the GraphQL mutation for adding a reply to a review thread.
type addReplyMutation struct {
	AddPullRequestReviewCommentReply struct {
		Comment struct {
			ID        githubv4.ID
			CreatedAt githubv4.DateTime
		}
	} `graphql:"addPullRequestReviewCommentReply(input: $input)"`
}

// addPullRequestReviewCommentReplyInput is the input for addReplyMutation.
type addPullRequestReviewCommentReplyInput struct {
	PullRequestReviewThreadID githubv4.ID     `json:"pullRequestReviewThreadId"`
	Body                      githubv4.String `json:"body"`
}

// resolveThreadMutation is the GraphQL mutation for resolving a review thread.
type resolveThreadMutation struct {
	ResolveReviewThread struct {
		Thread struct {
			IsResolved githubv4.Boolean
		}
	} `graphql:"resolveReviewThread(input: $input)"`
}

// resolveReviewThreadInput is the input for resolveThreadMutation.
type resolveReviewThreadInput struct {
	ThreadID githubv4.ID `json:"threadId"`
}

// ─── Public review thread types ──────────────────────────────────────────────

// ThreadComment is a single comment within a review thread.
type ThreadComment struct {
	Author    string
	Body      string
	CreatedAt string
}

// ReviewThread is the parsed representation of a PR review thread.
type ReviewThread struct {
	ID         string
	IsResolved bool
	IsOutdated bool
	Path       string
	Line       *int32
	StartLine  *int32
	Comments   []ThreadComment
}

// ReplyResult holds the result of a reply-to-thread operation.
type ReplyResult struct {
	CommentID string
	CreatedAt string
}

// ─── GraphQL methods ──────────────────────────────────────────────────────────

// GetReviewThreads fetches all review threads for a PR using GraphQL (paginated).
func (c *Client) GetReviewThreads(ctx context.Context, owner, repo string, pr int) ([]ReviewThread, error) {
	if pr <= 0 || pr > math.MaxInt32 {
		return nil, fmt.Errorf("pr number out of valid range: %d", pr)
	}
	vars := map[string]interface{}{
		"owner":  githubv4.String(owner),
		"repo":   githubv4.String(repo),
		"pr":     githubv4.Int(int32(pr)), //nolint:gosec // range checked above
		"cursor": (*githubv4.String)(nil),
	}

	var allNodes []reviewThreadNode
	for {
		var q reviewThreadsPageQuery
		if err := c.v4.Query(ctx, &q, vars); err != nil {
			return nil, fmt.Errorf("graphql query failed: %w", err)
		}
		allNodes = append(allNodes, q.Repository.PullRequest.ReviewThreads.Nodes...)
		if !bool(q.Repository.PullRequest.ReviewThreads.PageInfo.HasNextPage) {
			break
		}
		cursor := q.Repository.PullRequest.ReviewThreads.PageInfo.EndCursor
		vars["cursor"] = &cursor
	}

	threads := make([]ReviewThread, 0, len(allNodes))
	for _, n := range allNodes {
		t := ReviewThread{
			ID:         fmt.Sprintf("%v", n.ID),
			IsResolved: bool(n.IsResolved),
			IsOutdated: bool(n.IsOutdated),
			Path:       string(n.Path),
		}
		if n.Line != nil {
			v := int32(*n.Line)
			t.Line = &v
		}
		if n.StartLine != nil {
			v := int32(*n.StartLine)
			t.StartLine = &v
		}
		for _, c := range n.Comments.Nodes {
			t.Comments = append(t.Comments, ThreadComment{
				Author:    string(c.Author.Login),
				Body:      string(c.Body),
				CreatedAt: c.CreatedAt.Format(time.RFC3339),
			})
		}
		threads = append(threads, t)
	}
	return threads, nil
}

// IsThreadResolved checks whether a review thread is already resolved.
// threadID must be a PRRT_xxx global node ID.
func (c *Client) IsThreadResolved(ctx context.Context, threadID string) (bool, error) {
	var q threadNodeQuery
	vars := map[string]interface{}{
		"id": githubv4.ID(threadID),
	}
	if err := c.v4.Query(ctx, &q, vars); err != nil {
		return false, fmt.Errorf("graphql query failed: %w", err)
	}
	return bool(q.Node.PullRequestReviewThread.IsResolved), nil
}

// ReplyToThread adds a reply comment to a review thread.
// Returns the new comment's ID and creation timestamp.
func (c *Client) ReplyToThread(ctx context.Context, threadID, body string) (ReplyResult, error) {
	var m addReplyMutation
	input := addPullRequestReviewCommentReplyInput{
		PullRequestReviewThreadID: githubv4.ID(threadID),
		Body:                      githubv4.String(body),
	}
	if err := c.v4.Mutate(ctx, &m, input, nil); err != nil {
		return ReplyResult{}, fmt.Errorf("graphql mutation failed: %w", err)
	}
	return ReplyResult{
		CommentID: fmt.Sprintf("%v", m.AddPullRequestReviewCommentReply.Comment.ID),
		CreatedAt: m.AddPullRequestReviewCommentReply.Comment.CreatedAt.Format(time.RFC3339),
	}, nil
}

// ResolveThread resolves a review thread. Returns true if it was already resolved before the call.
func (c *Client) ResolveThread(ctx context.Context, threadID string) (alreadyResolved bool, err error) {
	alreadyResolved, err = c.IsThreadResolved(ctx, threadID)
	if err != nil {
		return false, err
	}
	if alreadyResolved {
		return true, nil
	}
	var m resolveThreadMutation
	input := resolveReviewThreadInput{ThreadID: githubv4.ID(threadID)}
	if err := c.v4.Mutate(ctx, &m, input, nil); err != nil {
		return false, fmt.Errorf("graphql mutation failed: %w", err)
	}
	return false, nil
}
