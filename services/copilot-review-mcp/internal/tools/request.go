package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

// RequestInput is the input schema for request_copilot_review.
type RequestInput struct {
	Owner string `json:"owner"`
	Repo  string `json:"repo"`
	PR    int    `json:"pr"`
}

// RequestOutput is the output schema for request_copilot_review.
type RequestOutput struct {
	OK      bool   `json:"ok"`
	Trigger string `json:"trigger,omitempty"`
	Reason  string `json:"reason,omitempty"`
	Note    string `json:"note"`
}

// requestTool is the MCP tool definition for request_copilot_review.
var requestTool = &mcp.Tool{
	Name:        "request_copilot_review",
	Description: "Copilot にプルリクエストのレビューをリクエストする。既にレビュー進行中の場合は拒否する（REVIEW_IN_PROGRESS）。",
}

// requestHandler handles a single request_copilot_review call.
func requestHandler(
	clientProvider githubClientProvider,
	db *store.DB,
) func(context.Context, *mcp.CallToolRequest, RequestInput) (*mcp.CallToolResult, RequestOutput, error) {
	return func(ctx context.Context, req *mcp.CallToolRequest, in RequestInput) (*mcp.CallToolResult, RequestOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, RequestOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}
		ghClient, err := clientProvider(ctx, req)
		if err != nil {
			return nil, RequestOutput{}, err
		}

		// Guard: check for an in-progress trigger_log entry.
		pending, err := db.HasPending(in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, RequestOutput{}, err
		}
		if pending {
			return nil, RequestOutput{
				OK:     false,
				Reason: "REVIEW_IN_PROGRESS",
				Note:   "この PR の Copilot レビューは既に保留中または進行中です。",
			}, nil
		}

		// Guard: also check the live GitHub reviewer list.
		data, err := ghClient.GetReviewData(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, RequestOutput{}, err
		}

		// If Copilot is already in the requested-reviewers list, reject.
		if data.IsCopilotInReviewers {
			return nil, RequestOutput{
				OK:     false,
				Reason: "REVIEW_IN_PROGRESS",
				Note:   "Copilot は既にこの PR のレビュアーとして登録されています。",
			}, nil
		}

		// Request the review via GitHub API.
		if err := ghClient.RequestCopilotReview(ctx, in.Owner, in.Repo, in.PR); err != nil {
			return nil, RequestOutput{}, err
		}

		// Record the MANUAL trigger. This must succeed so future HasPending
		// checks can prevent duplicate review requests.
		//
		// If a Copilot review was already submitted before this call (e.g. due to
		// GitHub REST API propagation delay causing get_copilot_review_status to
		// return NOT_REQUESTED for a completed review), set requested_at to just
		// before the review's SubmittedAt. This prevents the stale-guard in
		// DeriveStatusWithThreshold from treating the existing review as stale
		// (relevant = !SubmittedAt.Before(requestedAt) would otherwise be false).
		var insertErr error
		if data.LatestCopilotReview != nil {
			sat := data.LatestCopilotReview.GetSubmittedAt().Time
			if !sat.IsZero() {
				_, insertErr = db.InsertWithTime(in.Owner, in.Repo, in.PR, "MANUAL", sat.Add(-time.Nanosecond))
			} else {
				_, insertErr = db.Insert(in.Owner, in.Repo, in.PR, "MANUAL")
			}
		} else {
			_, insertErr = db.Insert(in.Owner, in.Repo, in.PR, "MANUAL")
		}
		if insertErr != nil {
			return nil, RequestOutput{}, fmt.Errorf("copilot review requested successfully, but failed to record MANUAL trigger: %w", insertErr)
		}

		return nil, RequestOutput{
			OK:      true,
			Trigger: "MANUAL",
			Note:    "Copilot レビューをリクエストしました。",
		}, nil
	}
}

// RegisterRequestTool adds request_copilot_review to the MCP server.
func RegisterRequestTool(server *mcp.Server, clientProvider githubClientProvider, db *store.DB) {
	mcp.AddTool(server, requestTool, requestHandler(clientProvider, db))
}
