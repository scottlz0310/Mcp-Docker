package tools

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

// ─── Environment helpers ──────────────────────────────────────────────────────

const (
	defaultMaxCycles           = 3
	defaultNoCommentThresholdMin = 6
)

func envMaxCycles() int {
	if s := os.Getenv("MAX_REVIEW_CYCLES"); s != "" {
		if v, err := strconv.Atoi(s); err == nil && v > 0 {
			return v
		}
	}
	return defaultMaxCycles
}

func envNoCommentThreshold() int {
	if s := os.Getenv("NO_COMMENT_THRESHOLD_MIN"); s != "" {
		if v, err := strconv.Atoi(s); err == nil && v > 0 {
			return v
		}
	}
	return defaultNoCommentThresholdMin
}

// ─── Tool 8 Types ─────────────────────────────────────────────────────────────

// CycleStatusInput is the input schema for get_pr_review_cycle_status.
type CycleStatusInput struct {
	Owner         string  `json:"owner"`
	Repo          string  `json:"repo"`
	PR            int     `json:"pr"`
	CIAllSuccess  bool    `json:"ci_all_success"`
	LastCommentAt *string `json:"last_comment_at"` // ISO8601 | null
	CyclesDone    int     `json:"cycles_done"`
	MaxCycles     int     `json:"max_cycles"` // 0 → use env/default
	FixType       string  `json:"fix_type"`   // logic | spec_change | trivial | none
}

// MergeConditions holds the per-condition merge readiness check.
type MergeConditions struct {
	CIOK            bool `json:"ci_ok"`
	BlockingCount   int  `json:"blocking_count"`
	UnresolvedCount int  `json:"unresolved_count"`
	AllReplied      bool `json:"all_replied"`
}

// CycleClassificationSummary holds aggregate thread classification counts.
type CycleClassificationSummary struct {
	Blocking    int `json:"blocking"`
	NonBlocking int `json:"nonBlocking"`
	Suggestion  int `json:"suggestion"`
}

// CycleStatusOutput is the output schema for get_pr_review_cycle_status.
type CycleStatusOutput struct {
	CycleStatus           string                     `json:"cycle_status"`       // CONTINUE | TERMINATE
	RecommendedAction     string                     `json:"recommended_action"` // WAIT | APPLY_FIXES | REPLY_RESOLVE | REQUEST_REREVIEW | READY_TO_MERGE | ESCALATE
	RereviewRequired      bool                       `json:"rereview_required"`
	RereviewReason        *string                    `json:"rereview_reason"`
	CyclesDone            int                        `json:"cycles_done"`
	MaxCycles             int                        `json:"max_cycles"`
	MergeConditions       MergeConditions            `json:"merge_conditions"`
	ClassificationSummary CycleClassificationSummary `json:"classification_summary"`
	Notes                 []string                   `json:"notes"`
}

// ─── Tool 8: get_pr_review_cycle_status ──────────────────────────────────────

var cycleTool = &mcp.Tool{
	Name: "get_pr_review_cycle_status",
	Description: "PR レビューサイクルの現在状態を評価し、次の推奨アクション " +
		"(WAIT / APPLY_FIXES / REPLY_RESOLVE / REQUEST_REREVIEW / READY_TO_MERGE / ESCALATE) を返す。" +
		"ISSUE#25・ISSUE#26 のツール群を組み合わせた PR レビューサイクルのオーケストレーション用。",
}

func cycleStatusHandler(
	gh *ghclient.Client,
	db *store.DB,
) func(context.Context, *mcp.CallToolRequest, CycleStatusInput) (*mcp.CallToolResult, CycleStatusOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in CycleStatusInput) (*mcp.CallToolResult, CycleStatusOutput, error) {
		// Input validation
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, CycleStatusOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}
		validFixTypes := map[string]bool{
			"logic": true, "spec_change": true, "trivial": true, "none": true,
		}
		if in.FixType != "" && !validFixTypes[in.FixType] {
			return nil, CycleStatusOutput{}, fmt.Errorf(
				"fix_type must be one of: logic, spec_change, trivial, none (got %q)", in.FixType,
			)
		}

		// Resolve max_cycles (input → env → default)
		maxCycles := in.MaxCycles
		if maxCycles <= 0 {
			maxCycles = envMaxCycles()
		}
		noCommentThreshold := envNoCommentThreshold()

		// Determine rereview_required from fix_type
		rereviewRequired := in.FixType == "logic" || in.FixType == "spec_change"
		var rereviewReason *string
		if rereviewRequired {
			reason := fmt.Sprintf("fix_type=%q は再レビューが必要です", in.FixType)
			rereviewReason = &reason
		}

		// ── Early exit: max cycles exceeded ────────────────────────────────
		if in.CyclesDone >= maxCycles {
			notes := []string{
				fmt.Sprintf("■ 最大サイクル数 %d 回に達しました。", maxCycles),
				fmt.Sprintf("■ PR: https://github.com/%s/%s/pull/%d", in.Owner, in.Repo, in.PR),
				"■ 人間によるレビューと判断が必要です。",
			}
			return nil, CycleStatusOutput{
				CycleStatus:       "TERMINATE",
				RecommendedAction: "ESCALATE",
				RereviewRequired:  rereviewRequired,
				RereviewReason:    rereviewReason,
				CyclesDone:        in.CyclesDone,
				MaxCycles:         maxCycles,
				Notes:             notes,
			}, nil
		}

		// ── Fetch review threads and classify ────────────────────────────────
		rawThreads, err := gh.GetReviewThreads(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, CycleStatusOutput{}, fmt.Errorf("failed to fetch review threads: %w", err)
		}

		blockingCount := 0
		nonBlockingCount := 0
		suggestionCount := 0
		unresolvedCount := 0
		allReplied := true // vacuously true when there are no threads

		for _, t := range rawThreads {
			cls, _ := classifyThread(t.Comments)
			switch cls {
			case "blocking":
				blockingCount++
			case "non-blocking":
				nonBlockingCount++
			default:
				suggestionCount++
			}
			if !t.IsResolved {
				unresolvedCount++
			}
			// A thread is "replied" when it has more than 1 comment
			// (original Copilot comment + at least one user reply).
			if len(t.Comments) <= 1 {
				allReplied = false
			}
		}

		classSummary := CycleClassificationSummary{
			Blocking:    blockingCount,
			NonBlocking: nonBlockingCount,
			Suggestion:  suggestionCount,
		}
		mergeConditions := MergeConditions{
			CIOK:            in.CIAllSuccess,
			BlockingCount:   blockingCount,
			UnresolvedCount: unresolvedCount,
			AllReplied:      allReplied,
		}

		// ── Fetch current review status ──────────────────────────────────────
		reviewData, err := gh.GetReviewData(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, CycleStatusOutput{}, fmt.Errorf("failed to fetch review data: %w", err)
		}

		entry, err := db.GetLatest(in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, CycleStatusOutput{}, fmt.Errorf("failed to fetch trigger log: %w", err)
		}

		var requestedAt *time.Time
		if entry != nil {
			requestedAt = &entry.RequestedAt
		}
		reviewStatus := gh.DeriveStatus(reviewData, requestedAt)

		// ── Elapsed time since last Copilot comment ───────────────────────────
		elapsedMinutes := 0
		if in.LastCommentAt != nil && *in.LastCommentAt != "" {
			lastAt, parseErr := time.Parse(time.RFC3339, *in.LastCommentAt)
			if parseErr == nil {
				elapsedMinutes = int(time.Since(lastAt).Minutes())
			}
		}

		// ── Determine cycle_status ────────────────────────────────────────────
		// Condition 1: all comments resolved, no blocking, CI OK.
		terminateCond1 := blockingCount == 0 && unresolvedCount == 0 && in.CIAllSuccess
		// Condition 2: no new Copilot comment for ≥ threshold minutes, CI OK, no blocking.
		terminateCond2 := elapsedMinutes >= noCommentThreshold && in.CIAllSuccess && blockingCount == 0

		cycleStatus := "CONTINUE"
		if terminateCond1 || terminateCond2 {
			cycleStatus = "TERMINATE"
		}

		// ── Determine recommended_action ──────────────────────────────────────
		var recommendedAction string

		switch {
		case reviewStatus == ghclient.StatusPending || reviewStatus == ghclient.StatusInProgress:
			recommendedAction = "WAIT"

		case blockingCount > 0:
			recommendedAction = "APPLY_FIXES"

		case unresolvedCount > 0:
			recommendedAction = "REPLY_RESOLVE"

		case rereviewRequired:
			// Guard: previous review must be COMPLETED or BLOCKED, and all threads replied.
			reviewDone := reviewStatus == ghclient.StatusCompleted || reviewStatus == ghclient.StatusBlocked
			if reviewDone && allReplied {
				recommendedAction = "REQUEST_REREVIEW"
			} else {
				// Guards not met; reply/resolve remaining threads first.
				recommendedAction = "REPLY_RESOLVE"
			}

		case cycleStatus == "TERMINATE":
			recommendedAction = "READY_TO_MERGE"

		default:
			// Remaining case: blocking==0, unresolved==0, rereview not required,
			// but cycle is still CONTINUE (e.g. CI not yet green).
			// WAIT is the most conservative choice until the next cycle.
			recommendedAction = "WAIT"
		}

		// ── Build notes ───────────────────────────────────────────────────────
		notes := []string{
			fmt.Sprintf("■ サイクル: %d/%d回目", in.CyclesDone+1, maxCycles),
			fmt.Sprintf("■ コメント分類: blocking=%d, non-blocking=%d, suggestion=%d",
				blockingCount, nonBlockingCount, suggestionCount),
		}
		if in.FixType != "" {
			fixNote := fmt.Sprintf("■ 修正種別: %s", in.FixType)
			if rereviewRequired {
				fixNote += " → 再レビュー必須"
			} else {
				fixNote += " → 再レビュー不要"
			}
			notes = append(notes, fixNote)
		}

		if cycleStatus == "TERMINATE" {
			switch {
			case terminateCond1:
				notes = append(notes, "■ サイクル終了条件: 達成（blocking=0, unresolved=0, CI=OK）")
			default:
				notes = append(notes, fmt.Sprintf(
					"■ サイクル終了条件: 達成（コメントなし %d分経過 ≥ %d分閾値 & CI=OK）",
					elapsedMinutes, noCommentThreshold,
				))
			}
		} else {
			var reasons []string
			if blockingCount > 0 {
				reasons = append(reasons, fmt.Sprintf("blocking=%d残存", blockingCount))
			}
			if unresolvedCount > 0 {
				reasons = append(reasons, fmt.Sprintf("unresolved=%d残存", unresolvedCount))
			}
			if !in.CIAllSuccess {
				reasons = append(reasons, "CI未達成")
			}
			if len(reasons) == 0 {
				reasons = append(reasons, "条件評価中")
			}
			notes = append(notes, fmt.Sprintf("■ サイクル終了条件: 未達成（%s）", strings.Join(reasons, ", ")))
		}
		notes = append(notes, fmt.Sprintf("■ 推奨アクション: %s", recommendedAction))

		return nil, CycleStatusOutput{
			CycleStatus:           cycleStatus,
			RecommendedAction:     recommendedAction,
			RereviewRequired:      rereviewRequired,
			RereviewReason:        rereviewReason,
			CyclesDone:            in.CyclesDone,
			MaxCycles:             maxCycles,
			MergeConditions:       mergeConditions,
			ClassificationSummary: classSummary,
			Notes:                 notes,
		}, nil
	}
}

// RegisterCycleTool adds get_pr_review_cycle_status to the MCP server.
func RegisterCycleTool(server *mcp.Server, gh *ghclient.Client, db *store.DB) {
	mcp.AddTool(server, cycleTool, cycleStatusHandler(gh, db))
}
