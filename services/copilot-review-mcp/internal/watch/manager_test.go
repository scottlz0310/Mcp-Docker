package watch

import (
	"context"
	"fmt"
	"net/http"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/google/go-github/v72/github"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

func TestManagerStartReusesActiveWatch(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval: 5 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{data: &ghclient.ReviewData{IsCopilotInReviewers: true, RateLimitRemaining: 100}},
				},
			}
		},
	})
	t.Cleanup(manager.Close)

	first, reused, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    42,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}
	if reused {
		t.Fatalf("Start() reused = %v, want false", reused)
	}

	second, reused, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-b",
		Owner: "octo",
		Repo:  "demo",
		PR:    42,
	})
	if err != nil {
		t.Fatalf("Start() second call error = %v", err)
	}
	if !reused {
		t.Fatalf("second Start() reused = %v, want true", reused)
	}
	if second.WatchID != first.WatchID {
		t.Fatalf("second Start() returned watch %q, want %q", second.WatchID, first.WatchID)
	}
}

func TestManagerMarksCompletedAndClearsActiveKey(t *testing.T) {
	db := openTestDB(t)
	if _, err := db.Insert("octo", "demo", 7, "MANUAL"); err != nil {
		t.Fatalf("Insert() error = %v", err)
	}
	reviewTime := time.Now().Add(time.Minute)
	manager := NewManager(db, Options{
		PollInterval: 5 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{
						data: &ghclient.ReviewData{
							LatestCopilotReview: newReview("APPROVED", &reviewTime),
							RateLimitRemaining:  100,
						},
					},
				},
			}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    7,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusCompleted {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusCompleted)
	}
	if snapshot.ReviewStatus == nil || *snapshot.ReviewStatus != ghclient.StatusCompleted {
		t.Fatalf("ReviewStatus = %v, want %q", snapshot.ReviewStatus, ghclient.StatusCompleted)
	}
	manager.mu.RLock()
	client := manager.watchesByID[started.WatchID].client
	manager.mu.RUnlock()
	if client != nil {
		t.Fatal("completed watch retained client, want nil")
	}
	if _, ok := manager.GetLatest("alice", "octo", "demo", 7); !ok {
		t.Fatal("GetLatest() after completion = not found, want last terminal watch")
	}

	next, reused, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    7,
	})
	if err != nil {
		t.Fatalf("Start() after completion error = %v", err)
	}
	if reused {
		t.Fatalf("Start() after completion reused = %v, want false", reused)
	}
	if next.WatchID == started.WatchID {
		t.Fatalf("Start() after completion reused old watch ID %q", next.WatchID)
	}
}

func TestManagerAuthExpiredFailsWatch(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval: 5 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{err: &github.ErrorResponse{Response: &http.Response{StatusCode: http.StatusUnauthorized}}},
				},
			}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "expired-token",
		Owner: "octo",
		Repo:  "demo",
		PR:    99,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusFailed {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusFailed)
	}
	if snapshot.FailureReason == nil || *snapshot.FailureReason != FailureReasonAuthExpired {
		t.Fatalf("FailureReason = %v, want %q", snapshot.FailureReason, FailureReasonAuthExpired)
	}
}

func TestManagerCloseMarksActiveWatchStale(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval: 50 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{data: &ghclient.ReviewData{IsCopilotInReviewers: true, RateLimitRemaining: 100}},
				},
			}
		},
	})

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    123,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	manager.Close()
	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusStale {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusStale)
	}
	if snapshot.WorkerRunning {
		t.Fatal("WorkerRunning = true, want false")
	}
}

func TestManagerPollTimeoutFailsWatch(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval: 5 * time.Millisecond,
		PollTimeout:  10 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return blockingFetcher{}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    200,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusFailed {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusFailed)
	}
	if snapshot.FailureReason == nil || *snapshot.FailureReason != FailureReasonGitHubError {
		t.Fatalf("FailureReason = %v, want %q", snapshot.FailureReason, FailureReasonGitHubError)
	}
	if snapshot.LastError == nil || !strings.Contains(*snapshot.LastError, "timed out") {
		t.Fatalf("LastError = %v, want timeout detail", snapshot.LastError)
	}
}

func TestManagerMaxWatchDurationTransitionsToTimeout(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval:     1 * time.Millisecond,
		MaxWatchDuration: 1 * time.Millisecond,
		Threshold:        30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{data: &ghclient.ReviewData{IsCopilotInReviewers: true, RateLimitRemaining: 100}},
				},
			}
		},
	})
	t.Cleanup(manager.Close)

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    201,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusTimeout {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusTimeout)
	}
}

func TestIsRateLimitHTTPError(t *testing.T) {
	t.Run("matches typed rate limit errors", func(t *testing.T) {
		if !IsRateLimitHTTPError(&github.RateLimitError{Rate: github.Rate{Remaining: 0}}) {
			t.Fatal("RateLimitError should be classified as rate limited")
		}
		if !IsRateLimitHTTPError(&github.AbuseRateLimitError{Response: &http.Response{StatusCode: http.StatusForbidden}}) {
			t.Fatal("AbuseRateLimitError should be classified as rate limited")
		}
	})

	t.Run("does not treat generic forbidden as rate limited", func(t *testing.T) {
		err := &github.ErrorResponse{Response: &http.Response{StatusCode: http.StatusForbidden}}
		if IsRateLimitHTTPError(err) {
			t.Fatal("generic HTTP 403 should not be classified as rate limited")
		}
	})
}

type fetchResult struct {
	data *ghclient.ReviewData
	err  error
}

type fakeFetcher struct {
	mu      sync.Mutex
	results []fetchResult
	calls   int
}

type blockingFetcher struct{}

func (f *fakeFetcher) GetReviewData(_ context.Context, _, _ string, _ int) (*ghclient.ReviewData, error) {
	f.mu.Lock()
	defer f.mu.Unlock()

	if len(f.results) == 0 {
		return nil, fmt.Errorf("no fake results configured")
	}
	index := f.calls
	if index >= len(f.results) {
		index = len(f.results) - 1
	}
	f.calls++
	result := f.results[index]
	return result.data, result.err
}

func (blockingFetcher) GetReviewData(ctx context.Context, _, _ string, _ int) (*ghclient.ReviewData, error) {
	<-ctx.Done()
	return nil, ctx.Err()
}

func waitForWatch(t *testing.T, manager *Manager, watchID string, done func(Snapshot) bool) Snapshot {
	t.Helper()

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		snapshot, ok := manager.GetByID(watchID)
		if ok && done(snapshot) {
			return snapshot
		}
		time.Sleep(10 * time.Millisecond)
	}

	snapshot, _ := manager.GetByID(watchID)
	t.Fatalf("watch %q did not reach expected state before timeout; last snapshot=%+v", watchID, snapshot)
	return Snapshot{}
}

func openTestDB(t *testing.T) *store.DB {
	t.Helper()

	db, err := store.Open(filepath.Join(t.TempDir(), "watch-test.db"))
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

func newReview(state string, submittedAt *time.Time) *github.PullRequestReview {
	review := &github.PullRequestReview{
		State: github.Ptr(state),
	}
	if submittedAt != nil {
		review.SubmittedAt = &github.Timestamp{Time: *submittedAt}
	}
	return review
}
