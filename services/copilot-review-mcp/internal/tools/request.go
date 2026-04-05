package tools

import (
	"context"
	"fmt"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
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
	ghClient *ghclient.Client,
	db *store.DB,
) func(context.Context, *mcp.CallToolRequest, RequestInput) (*mcp.CallToolResult, RequestOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in RequestInput) (*mcp.CallToolResult, RequestOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, RequestOutput{}, fmt.Errorf("owner, repo, and pr are required")
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
				Note:   "A Copilot review is already pending or in progress for this PR.",
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
				Note:   "Copilot is already listed as a requested reviewer for this PR.",
			}, nil
		}

		// Request the review via GitHub API.
		if err := ghClient.RequestCopilotReview(ctx, in.Owner, in.Repo, in.PR); err != nil {
			return nil, RequestOutput{}, err
		}

		// Record the MANUAL trigger. This must succeed so future HasPending
		// checks can prevent duplicate review requests.
		if _, err := db.Insert(in.Owner, in.Repo, in.PR, "MANUAL"); err != nil {
			return nil, RequestOutput{}, fmt.Errorf("copilot review requested successfully, but failed to record MANUAL trigger: %w", err)
		}

		return nil, RequestOutput{
			OK:      true,
			Trigger: "MANUAL",
			Note:    "Copilot review requested successfully.",
		}, nil
	}
}

// RegisterRequestTool adds request_copilot_review to the MCP server.
func RegisterRequestTool(server *mcp.Server, gh *ghclient.Client, db *store.DB) {
	mcp.AddTool(server, requestTool, requestHandler(gh, db))
}
