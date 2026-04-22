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
	if out.Watch == nil {
		t.Fatal("Watch = nil, want payload")
	}
	if out.Watch.WatchID != started.WatchID {
		t.Fatalf("Watch.WatchID = %q, want %q", out.Watch.WatchID, started.WatchID)
	}
	if out.Watch.RecommendedNextAction != nextActionPollAfter {
		t.Fatalf("Watch.RecommendedNextAction = %q, want %q", out.Watch.RecommendedNextAction, nextActionPollAfter)
	}
	if out.Watch.NextPollSeconds == nil || *out.Watch.NextPollSeconds != 1 {
		t.Fatalf("Watch.NextPollSeconds = %v, want initial delay 1s", out.Watch.NextPollSeconds)
	}
	if out.Watch.ResourceURI == nil || *out.Watch.ResourceURI == "" {
		t.Fatalf("Watch.ResourceURI = %v, want populated URI", out.Watch.ResourceURI)
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
	if out.Cancelled == nil || !*out.Cancelled {
		t.Fatalf("Cancelled = %v, want true", out.Cancelled)
	}
	if out.Watch == nil {
		t.Fatal("Watch = nil, want payload")
	}
	if out.Watch.WatchStatus != string(watch.StatusCancelled) {
		t.Fatalf("Watch.WatchStatus = %q, want %q", out.Watch.WatchStatus, watch.StatusCancelled)
	}
	if out.Watch.RecommendedNextAction != nextActionStartNewWatch {
		t.Fatalf("Watch.RecommendedNextAction = %q, want %q", out.Watch.RecommendedNextAction, nextActionStartNewWatch)
	}
}

func TestGetWatchStatusHandlerNotFoundOmitsWatchPayload(t *testing.T) {
	db := openWatchToolsTestDB(t)
	manager := watch.NewManager(db, watch.Options{Threshold: 30 * time.Second})
	t.Cleanup(manager.Close)

	handler := getWatchStatusHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "owner-user")

	_, out, err := handler(ctx, nil, GetReviewWatchStatusInput{Owner: "scottlz0310", Repo: "Mcp-Docker", PR: 999})
	if err != nil {
		t.Fatalf("getWatchStatusHandler() error = %v", err)
	}
	if out.Found {
		t.Fatal("Found = true, want false")
	}
	if out.Watch != nil {
		t.Fatalf("Watch = %+v, want nil", out.Watch)
	}
}

func TestCancelWatchHandlerNotFoundOmitsWatchPayload(t *testing.T) {
	db := openWatchToolsTestDB(t)
	manager := watch.NewManager(db, watch.Options{Threshold: 30 * time.Second})
	t.Cleanup(manager.Close)

	handler := cancelWatchHandler(manager)
	ctx := context.WithValue(context.Background(), middleware.ContextKeyLogin, "owner-user")

	_, out, err := handler(ctx, nil, CancelReviewWatchInput{Owner: "scottlz0310", Repo: "Mcp-Docker", PR: 999})
	if err != nil {
		t.Fatalf("cancelWatchHandler() error = %v", err)
	}
	if out.Found {
		t.Fatal("Found = true, want false")
	}
	if out.Watch != nil {
		t.Fatalf("Watch = %+v, want nil", out.Watch)
	}
	if out.Cancelled != nil {
		t.Fatalf("Cancelled = %v, want nil", out.Cancelled)
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
