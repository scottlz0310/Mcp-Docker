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
	db, err := store.Open(filepath.Join(t.TempDir(), "watch-tools.db"))
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Fatalf("db.Close() error = %v", err)
		}
	})

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

type testStaticFetcher struct{}

func (testStaticFetcher) GetReviewData(context.Context, string, string, int) (*ghclient.ReviewData, error) {
	return &ghclient.ReviewData{
		IsCopilotInReviewers: true,
		RateLimitRemaining:   100,
	}, nil
}
