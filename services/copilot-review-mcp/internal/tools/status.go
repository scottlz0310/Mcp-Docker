// Package tools registers the three Copilot-review MCP tools and builds the MCP server.
package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

// GetStatusInput is the input schema for get_copilot_review_status.
type GetStatusInput struct {
	Owner string `json:"owner"`
	Repo  string `json:"repo"`
	PR    int    `json:"pr"`
}

// GetStatusOutput is the output schema for get_copilot_review_status.
type GetStatusOutput struct {
	Requested           bool    `json:"requested"`
	Status              string  `json:"status"`
	Trigger             *string `json:"trigger"`
	IsBlocking          bool    `json:"isBlocking"`
	BlockingThreadCount int     `json:"blockingThreadCount"`
	LastReviewAt        *string `json:"lastReviewAt"`
	ElapsedSinceRequest *string `json:"elapsedSinceRequest"`
}

// statusTool is the MCP tool definition for get_copilot_review_status.
var statusTool = &mcp.Tool{
	Name:        "get_copilot_review_status",
	Description: "Copilot が PR をレビューしているかどうかの現在のステータスを返す。ステータスは NOT_REQUESTED / PENDING / IN_PROGRESS / COMPLETED / BLOCKED のいずれか。",
}

// statusHandler handles a single get_copilot_review_status call.
func statusHandler(
	ghClient *ghclient.Client,
	db *store.DB,
) func(context.Context, *mcp.CallToolRequest, GetStatusInput) (*mcp.CallToolResult, GetStatusOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in GetStatusInput) (*mcp.CallToolResult, GetStatusOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, GetStatusOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}

		data, err := ghClient.GetReviewData(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, GetStatusOutput{}, err
		}

		entry, err := db.GetLatest(in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, GetStatusOutput{}, err
		}

		var requestedAt *time.Time
		if entry != nil {
			requestedAt = &entry.RequestedAt
		}

		status := ghClient.DeriveStatus(data, requestedAt)

		// Auto-update completed_at when the review is done.
		if (status == ghclient.StatusCompleted || status == ghclient.StatusBlocked) &&
			entry != nil && entry.CompletedAt == nil {
			if err := db.UpdateCompletedAt(entry.ID); err != nil {
				return nil, GetStatusOutput{}, fmt.Errorf("failed to update completed_at: %w", err)
			}
		}

		out := GetStatusOutput{
			Requested:  data.IsCopilotInReviewers || data.LatestCopilotReview != nil,
			Status:     string(status),
			IsBlocking: status == ghclient.StatusBlocked,
		}

		if data.LatestCopilotReview != nil {
			s := data.LatestCopilotReview.GetSubmittedAt().UTC().Format(time.RFC3339)
			out.LastReviewAt = &s
		}

		if entry != nil {
			elapsed := time.Since(entry.RequestedAt)
			s := fmtDuration(elapsed)
			out.ElapsedSinceRequest = &s
			t := entry.Trigger
			out.Trigger = &t
		}

		return nil, out, nil
	}
}

// RegisterStatusTool adds get_copilot_review_status to the MCP server.
func RegisterStatusTool(server *mcp.Server, gh *ghclient.Client, db *store.DB) {
	mcp.AddTool(server, statusTool, statusHandler(gh, db))
}

// fmtDuration formats a duration as a human-readable string.
func fmtDuration(d time.Duration) string {
	d = d.Round(time.Second)
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	if h > 0 {
		return fmt.Sprintf("%dh%dm%ds", h, m, s)
	}
	if m > 0 {
		return fmt.Sprintf("%dm%ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}
