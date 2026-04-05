package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

// WaitInput is the input schema for wait_for_copilot_review.
type WaitInput struct {
	Owner               string `json:"owner"`
	Repo                string `json:"repo"`
	PR                  int    `json:"pr"`
	PollIntervalSeconds int    `json:"poll_interval_seconds"`
	MaxPolls            int    `json:"max_polls"`
}

// WaitOutput is the output schema for wait_for_copilot_review.
type WaitOutput struct {
	Status        string           `json:"status"`
	ReviewStatus  *GetStatusOutput `json:"review_status"`
	PollsDone     int              `json:"polls_done"`
	WaitedSeconds int              `json:"waited_seconds"`
}

// waitTool is the MCP tool definition for wait_for_copilot_review.
var waitTool = &mcp.Tool{
	Name:        "wait_for_copilot_review",
	Description: "Copilot のレビューが COMPLETED または BLOCKED になるまで定期的にポーリングして待機する。タイムアウト時は TIMEOUT を返す。レート制限時は RATE_LIMITED を返す。",
}

// waitHandler handles a single wait_for_copilot_review call.
func waitHandler(
	ghClient *ghclient.Client,
	db *store.DB,
) func(context.Context, *mcp.CallToolRequest, WaitInput) (*mcp.CallToolResult, WaitOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in WaitInput) (*mcp.CallToolResult, WaitOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, WaitOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}
		// Apply defaults.
		if in.PollIntervalSeconds <= 0 {
			in.PollIntervalSeconds = 120
		}
		if in.MaxPolls <= 0 {
			in.MaxPolls = 5
		}
		// Enforce upper bounds to prevent goroutine pinning / DoS.
		const maxPollIntervalSeconds = 3600
		const maxMaxPolls = 100
		if in.PollIntervalSeconds > maxPollIntervalSeconds {
			return nil, WaitOutput{}, fmt.Errorf("poll_interval_seconds must not exceed %d", maxPollIntervalSeconds)
		}
		if in.MaxPolls > maxMaxPolls {
			return nil, WaitOutput{}, fmt.Errorf("max_polls must not exceed %d", maxMaxPolls)
		}
		// Enforce a total-wait ceiling to cap goroutine occupancy.
		const maxTotalWait = 30 * time.Minute
		totalWait := time.Duration(in.PollIntervalSeconds) * time.Duration(in.MaxPolls-1) * time.Second
		if totalWait > maxTotalWait {
			return nil, WaitOutput{}, fmt.Errorf(
				"total wait time must not exceed %d seconds (poll_interval_seconds\u00d7(max_polls−1) = %d)",
				int(maxTotalWait.Seconds()), int(totalWait.Seconds()),
			)
		}

		pollInterval := time.Duration(in.PollIntervalSeconds) * time.Second
		start := time.Now()

		for poll := 0; poll < in.MaxPolls; poll++ {
			// Wait between polls (skip on first iteration).
			if poll > 0 {
				timer := time.NewTimer(pollInterval)
				select {
				case <-ctx.Done():
					if !timer.Stop() {
						select {
						case <-timer.C:
						default:
						}
					}
					return nil, WaitOutput{}, ctx.Err()
				case <-timer.C:
				}
			}

			data, err := ghClient.GetReviewData(ctx, in.Owner, in.Repo, in.PR)
			if err != nil {
				return nil, WaitOutput{}, err
			}

			// Check rate limit before proceeding.
			if data.RateLimitRemaining < 10 {
				entry, err := db.GetLatest(in.Owner, in.Repo, in.PR)
				if err != nil {
					return nil, WaitOutput{}, fmt.Errorf("failed to get latest entry (RATE_LIMITED): %w", err)
				}
				var reqAt *time.Time
				if entry != nil {
					reqAt = &entry.RequestedAt
				}
				partialStatus := ghClient.DeriveStatus(data, reqAt)
				rs := buildStatusOutput(data, entry, partialStatus)
				return nil, WaitOutput{
					Status:        "RATE_LIMITED",
					ReviewStatus:  &rs,
					PollsDone:     poll + 1,
					WaitedSeconds: int(time.Since(start).Seconds()),
				}, nil
			}

			entry, err := db.GetLatest(in.Owner, in.Repo, in.PR)
			if err != nil {
				return nil, WaitOutput{}, err
			}

			var requestedAt *time.Time
			if entry != nil {
				requestedAt = &entry.RequestedAt
			}

			status := ghClient.DeriveStatus(data, requestedAt)

			// Auto-update completed_at.
			if (status == ghclient.StatusCompleted || status == ghclient.StatusBlocked) &&
				entry != nil && entry.CompletedAt == nil {
				if err := db.UpdateCompletedAt(entry.ID); err != nil {
					return nil, WaitOutput{}, fmt.Errorf("failed to update completed_at: %w", err)
				}
			}

			if status == ghclient.StatusCompleted || status == ghclient.StatusBlocked {
				rs := buildStatusOutput(data, entry, status)
				return nil, WaitOutput{
					Status:        string(status),
					ReviewStatus:  &rs,
					PollsDone:     poll + 1,
					WaitedSeconds: int(time.Since(start).Seconds()),
				}, nil
			}
		}

		// All polls exhausted.
		data, err := ghClient.GetReviewData(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, WaitOutput{}, fmt.Errorf("final review data fetch failed after %d polls: %w", in.MaxPolls, err)
		}
		entry, err := db.GetLatest(in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, WaitOutput{}, fmt.Errorf("failed to get latest entry (TIMEOUT): %w", err)
		}
		var requestedAt *time.Time
		if entry != nil {
			requestedAt = &entry.RequestedAt
		}
		status := ghClient.DeriveStatus(data, requestedAt)
		rs := buildStatusOutput(data, entry, status)
		return nil, WaitOutput{
			Status:        "TIMEOUT",
			ReviewStatus:  &rs,
			PollsDone:     in.MaxPolls,
			WaitedSeconds: int(time.Since(start).Seconds()),
		}, nil
	}
}

// buildStatusOutput assembles a GetStatusOutput from already-fetched data.
func buildStatusOutput(data *ghclient.ReviewData, entry *store.TriggerEntry, status ghclient.ReviewStatus) GetStatusOutput {
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
	return out
}

// RegisterWaitTool adds wait_for_copilot_review to the MCP server.
func RegisterWaitTool(server *mcp.Server, gh *ghclient.Client, db *store.DB) {
	mcp.AddTool(server, waitTool, waitHandler(gh, db))
}
