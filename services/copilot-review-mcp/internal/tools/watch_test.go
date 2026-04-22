package tools

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
	"github.com/scottlz0310/copilot-review-mcp/internal/watch"
)

func TestGetWatchStatusHandlerScopesWatchIDByLogin(t *testing.T) {
	db := openWatchToolsTestDB(t)

	manager := watch.NewManager(db, watch.Options{
		PollInterval: time.Hour,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) watch.ReviewDataFetcher {
			return testStaticFetcher{}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(watch.StartInput{
		Login: "owner-user",
		Token: "token-a",
		Owner: "scottlz0310",
		Repo:  "Mcp-Docker",
		PR:    71,
	})
	if err != nil {
		t.Fatalf("manager.Start() error = %v", err)
	}

	handler := getWatchStatusHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "different-user")

	_, out, err := handler(ctx, nil, GetReviewWatchStatusInput{WatchID: started.WatchID})
	if err != nil {
		t.Fatalf("getWatchStatusHandler() error = %v", err)
	}
	if out.Found {
		t.Fatalf("Found = %v, want false", out.Found)
	}
}

func TestGetWatchStatusHandlerReturnsLLMHints(t *testing.T) {
	db := openWatchToolsTestDB(t)

	manager := watch.NewManager(db, watch.Options{
		PollInterval: time.Hour,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) watch.ReviewDataFetcher {
			return testStaticFetcher{}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(watch.StartInput{
		Login: "owner-user",
		Token: "token-a",
		Owner: "scottlz0310",
		Repo:  "Mcp-Docker",
		PR:    72,
	})
	if err != nil {
		t.Fatalf("manager.Start() error = %v", err)
	}

	handler := getWatchStatusHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "owner-user")

	_, out, err := handler(ctx, nil, GetReviewWatchStatusInput{Owner: "scottlz0310", Repo: "Mcp-Docker", PR: 72})
	if err != nil {
		t.Fatalf("getWatchStatusHandler() error = %v", err)
	}
	if !out.Found {
		t.Fatal("Found = false, want true")
	}
	if out.WatchID != started.WatchID {
		t.Fatalf("WatchID = %q, want %q", out.WatchID, started.WatchID)
	}
	if out.RecommendedNextAction != nextActionPollAfter {
		t.Fatalf("RecommendedNextAction = %q, want %q", out.RecommendedNextAction, nextActionPollAfter)
	}
	if out.NextPollSeconds == nil || *out.NextPollSeconds <= 0 {
		t.Fatalf("NextPollSeconds = %v, want positive poll hint", out.NextPollSeconds)
	}
	if out.ResourceURI == nil || *out.ResourceURI == "" {
		t.Fatalf("ResourceURI = %v, want populated URI", out.ResourceURI)
	}
}

func TestListWatchesHandlerReturnsSortedViews(t *testing.T) {
	db := openWatchToolsTestDB(t)
	base := time.Now().UTC().Truncate(time.Second)
	manager := watch.NewManager(db, watch.Options{
		PollInterval: time.Hour,
		Threshold:    30 * time.Second,
		Now: func() time.Time {
			return base
		},
		ClientFactory: func(_ context.Context, _ string) watch.ReviewDataFetcher {
			return testStaticFetcher{}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(watch.StartInput{
		Login: "owner-user",
		Token: "token-a",
		Owner: "scottlz0310",
		Repo:  "Mcp-Docker",
		PR:    73,
	})
	if err != nil {
		t.Fatalf("manager.Start() error = %v", err)
	}

	reviewStatus := "COMPLETED"
	if err := db.UpsertReviewWatch(store.ReviewWatchEntry{
		ID:           "cw_terminal",
		GitHubLogin:  "owner-user",
		Owner:        "scottlz0310",
		Repo:         "Mcp-Docker",
		PR:           74,
		WatchStatus:  "COMPLETED",
		ReviewStatus: &reviewStatus,
		IsActive:     false,
		StartedAt:    base.Add(-time.Hour),
		UpdatedAt:    base.Add(-time.Minute),
	}); err != nil {
		t.Fatalf("UpsertReviewWatch() error = %v", err)
	}

	handler := listWatchesHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "owner-user")

	_, out, err := handler(ctx, nil, ListReviewWatchesInput{Owner: "scottlz0310", Repo: "Mcp-Docker", Limit: 10})
	if err != nil {
		t.Fatalf("listWatchesHandler() error = %v", err)
	}
	if out.Count != 2 {
		t.Fatalf("Count = %d, want 2", out.Count)
	}
	if out.Watches[0].WatchID != started.WatchID {
		t.Fatalf("Watches[0].WatchID = %q, want active watch %q", out.Watches[0].WatchID, started.WatchID)
	}
	if out.Watches[0].RecommendedNextAction != nextActionPollAfter {
		t.Fatalf("Watches[0].RecommendedNextAction = %q, want %q", out.Watches[0].RecommendedNextAction, nextActionPollAfter)
	}
	if out.Watches[1].WatchID != "cw_terminal" {
		t.Fatalf("Watches[1].WatchID = %q, want %q", out.Watches[1].WatchID, "cw_terminal")
	}
	if out.Watches[1].RecommendedNextAction != nextActionReadReviewThreads {
		t.Fatalf("Watches[1].RecommendedNextAction = %q, want %q", out.Watches[1].RecommendedNextAction, nextActionReadReviewThreads)
	}
}

func TestCancelWatchHandlerCancelsByPRKey(t *testing.T) {
	db := openWatchToolsTestDB(t)

	manager := watch.NewManager(db, watch.Options{
		PollInterval: time.Hour,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) watch.ReviewDataFetcher {
			return testStaticFetcher{}
		},
	})
	t.Cleanup(manager.Close)

	_, _, err := manager.Start(watch.StartInput{
		Login: "owner-user",
		Token: "token-a",
		Owner: "scottlz0310",
		Repo:  "Mcp-Docker",
		PR:    75,
	})
	if err != nil {
		t.Fatalf("manager.Start() error = %v", err)
	}

	handler := cancelWatchHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "owner-user")

	_, out, err := handler(ctx, nil, CancelReviewWatchInput{Owner: "scottlz0310", Repo: "Mcp-Docker", PR: 75})
	if err != nil {
		t.Fatalf("cancelWatchHandler() error = %v", err)
	}
	if !out.Found {
		t.Fatal("Found = false, want true")
	}
	if !out.Cancelled {
		t.Fatal("Cancelled = false, want true")
	}
	if out.WatchStatus != string(watch.StatusCancelled) {
		t.Fatalf("WatchStatus = %q, want %q", out.WatchStatus, watch.StatusCancelled)
	}
	if out.RecommendedNextAction != nextActionStartNewWatch {
		t.Fatalf("RecommendedNextAction = %q, want %q", out.RecommendedNextAction, nextActionStartNewWatch)
	}
}

func openWatchToolsTestDB(t *testing.T) *store.DB {
	t.Helper()

	db, err := store.Open(filepath.Join(t.TempDir(), "watch-tools.db"))
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Fatalf("db.Close() error = %v", err)
		}
	})
	return db
}

type testStaticFetcher struct{}

func (testStaticFetcher) GetReviewData(context.Context, string, string, int) (*ghclient.ReviewData, error) {
	return &ghclient.ReviewData{
		IsCopilotInReviewers: true,
		RateLimitRemaining:   100,
	}, nil
}
