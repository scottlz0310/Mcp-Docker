package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/watch"
)

// StartReviewWatchInput is the input schema for start_copilot_review_watch.
type StartReviewWatchInput struct {
	Owner string `json:"owner"`
	Repo  string `json:"repo"`
	PR    int    `json:"pr"`
}

// StartReviewWatchOutput is the output schema for start_copilot_review_watch.
type StartReviewWatchOutput struct {
	WatchID       string  `json:"watch_id"`
	Reused        bool    `json:"reused"`
	WatchStatus   string  `json:"watch_status"`
	ReviewStatus  *string `json:"review_status,omitempty"`
	FailureReason *string `json:"failure_reason,omitempty"`
	Terminal      bool    `json:"terminal"`
	WorkerRunning bool    `json:"worker_running"`
	PollsDone     int     `json:"polls_done"`
	StartedAt     string  `json:"started_at"`
	UpdatedAt     string  `json:"updated_at"`
	LastPolledAt  *string `json:"last_polled_at,omitempty"`
	CompletedAt   *string `json:"completed_at,omitempty"`
	LastError     *string `json:"last_error,omitempty"`
	Note          string  `json:"note"`
}

// GetReviewWatchStatusInput is the input schema for get_copilot_review_watch_status.
type GetReviewWatchStatusInput struct {
	WatchID string `json:"watch_id,omitempty"`
	Owner   string `json:"owner,omitempty"`
	Repo    string `json:"repo,omitempty"`
	PR      int    `json:"pr,omitempty"`
}

// GetReviewWatchStatusOutput is the output schema for get_copilot_review_watch_status.
type GetReviewWatchStatusOutput struct {
	Found         bool    `json:"found"`
	WatchID       *string `json:"watch_id,omitempty"`
	WatchStatus   *string `json:"watch_status,omitempty"`
	ReviewStatus  *string `json:"review_status,omitempty"`
	FailureReason *string `json:"failure_reason,omitempty"`
	Terminal      bool    `json:"terminal"`
	WorkerRunning bool    `json:"worker_running"`
	PollsDone     int     `json:"polls_done"`
	StartedAt     *string `json:"started_at,omitempty"`
	UpdatedAt     *string `json:"updated_at,omitempty"`
	LastPolledAt  *string `json:"last_polled_at,omitempty"`
	CompletedAt   *string `json:"completed_at,omitempty"`
	LastError     *string `json:"last_error,omitempty"`
	Note          string  `json:"note"`
}

var startWatchTool = &mcp.Tool{
	Name:        "start_copilot_review_watch",
	Description: "Copilot review の background watch を開始し、即時 return する。同一ユーザー・同一 PR の active watch があればそれを再利用する。watch state は memory-only で、サーバー再起動後は維持されない。",
}

var getWatchStatusTool = &mcp.Tool{
	Name:        "get_copilot_review_watch_status",
	Description: "background watch の現在状態を memory-only state から返す。watch_id を優先し、watch_id が無い場合は owner/repo/pr から同一ユーザーの最新 watch を引く。",
}

func startWatchHandler(
	manager *watch.Manager,
) func(context.Context, *mcp.CallToolRequest, StartReviewWatchInput) (*mcp.CallToolResult, StartReviewWatchOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in StartReviewWatchInput) (*mcp.CallToolResult, StartReviewWatchOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, StartReviewWatchOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}

		login := middleware.LoginFromContext(ctx)
		token := middleware.TokenFromContext(ctx)
		if login == "" || token == "" {
			return nil, StartReviewWatchOutput{}, fmt.Errorf("authenticated GitHub login and token are required")
		}

		snapshot, reused, err := manager.Start(watch.StartInput{
			Login: login,
			Token: token,
			Owner: in.Owner,
			Repo:  in.Repo,
			PR:    in.PR,
		})
		if err != nil {
			return nil, StartReviewWatchOutput{}, err
		}

		out := buildStartWatchOutput(snapshot, reused)
		if reused {
			out.Note = "既存の active watch を再利用しました。"
		} else {
			out.Note = "background watch を開始しました。"
		}
		return nil, out, nil
	}
}

func getWatchStatusHandler(
	manager *watch.Manager,
) func(context.Context, *mcp.CallToolRequest, GetReviewWatchStatusInput) (*mcp.CallToolResult, GetReviewWatchStatusOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in GetReviewWatchStatusInput) (*mcp.CallToolResult, GetReviewWatchStatusOutput, error) {
		var (
			snapshot watch.Snapshot
			ok       bool
		)

		switch {
		case in.WatchID != "":
			snapshot, ok = manager.GetByID(in.WatchID)
		case in.Owner != "" && in.Repo != "" && in.PR > 0:
			login := middleware.LoginFromContext(ctx)
			if login == "" {
				return nil, GetReviewWatchStatusOutput{}, fmt.Errorf("authenticated GitHub login is required")
			}
			snapshot, ok = manager.GetLatest(login, in.Owner, in.Repo, in.PR)
		default:
			return nil, GetReviewWatchStatusOutput{}, fmt.Errorf("watch_id or owner, repo, and pr are required")
		}

		if !ok {
			return nil, GetReviewWatchStatusOutput{
				Found: false,
				Note:  "watch が見つかりませんでした。",
			}, nil
		}

		return nil, buildGetWatchStatusOutput(snapshot), nil
	}
}

// RegisterWatchTools adds the async review watch tools to the MCP server.
func RegisterWatchTools(server *mcp.Server, manager *watch.Manager) {
	mcp.AddTool(server, startWatchTool, startWatchHandler(manager))
	mcp.AddTool(server, getWatchStatusTool, getWatchStatusHandler(manager))
}

func buildStartWatchOutput(snapshot watch.Snapshot, reused bool) StartReviewWatchOutput {
	out := StartReviewWatchOutput{
		WatchID:       snapshot.WatchID,
		Reused:        reused,
		WatchStatus:   string(snapshot.WatchStatus),
		Terminal:      snapshot.Terminal,
		WorkerRunning: snapshot.WorkerRunning,
		PollsDone:     snapshot.PollsDone,
		StartedAt:     snapshot.StartedAt.UTC().Format(time.RFC3339),
		UpdatedAt:     snapshot.UpdatedAt.UTC().Format(time.RFC3339),
		LastError:     snapshot.LastError,
	}
	if snapshot.ReviewStatus != nil {
		status := string(*snapshot.ReviewStatus)
		out.ReviewStatus = &status
	}
	if snapshot.FailureReason != nil {
		reason := string(*snapshot.FailureReason)
		out.FailureReason = &reason
	}
	if snapshot.LastPolledAt != nil {
		ts := snapshot.LastPolledAt.UTC().Format(time.RFC3339)
		out.LastPolledAt = &ts
	}
	if snapshot.CompletedAt != nil {
		ts := snapshot.CompletedAt.UTC().Format(time.RFC3339)
		out.CompletedAt = &ts
	}
	return out
}

func buildGetWatchStatusOutput(snapshot watch.Snapshot) GetReviewWatchStatusOutput {
	watchID := snapshot.WatchID
	watchStatus := string(snapshot.WatchStatus)
	startedAt := snapshot.StartedAt.UTC().Format(time.RFC3339)
	updatedAt := snapshot.UpdatedAt.UTC().Format(time.RFC3339)

	out := GetReviewWatchStatusOutput{
		Found:         true,
		WatchID:       &watchID,
		WatchStatus:   &watchStatus,
		Terminal:      snapshot.Terminal,
		WorkerRunning: snapshot.WorkerRunning,
		PollsDone:     snapshot.PollsDone,
		StartedAt:     &startedAt,
		UpdatedAt:     &updatedAt,
		LastError:     snapshot.LastError,
		Note:          "watch の現在状態です。",
	}
	if snapshot.ReviewStatus != nil {
		status := string(*snapshot.ReviewStatus)
		out.ReviewStatus = &status
	}
	if snapshot.FailureReason != nil {
		reason := string(*snapshot.FailureReason)
		out.FailureReason = &reason
	}
	if snapshot.LastPolledAt != nil {
		ts := snapshot.LastPolledAt.UTC().Format(time.RFC3339)
		out.LastPolledAt = &ts
	}
	if snapshot.CompletedAt != nil {
		ts := snapshot.CompletedAt.UTC().Format(time.RFC3339)
		out.CompletedAt = &ts
	}
	return out
}
