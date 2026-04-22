package watch

import (
	"context"
	"errors"
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

func TestManagerStartPersistsActiveWatch(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(db, Options{
		PollInterval: time.Hour,
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

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    41,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	persisted, err := db.GetReviewWatchByID(started.WatchID)
	if err != nil {
		t.Fatalf("GetReviewWatchByID() error = %v", err)
	}
	if persisted == nil {
		t.Fatal("GetReviewWatchByID() = nil, want persisted watch")
	}
	if persisted.WatchStatus != string(StatusWatching) {
		t.Fatalf("WatchStatus = %q, want %q", persisted.WatchStatus, StatusWatching)
	}
	if !persisted.IsActive {
		t.Fatal("IsActive = false, want true")
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

	persisted, err := db.GetReviewWatchByID(started.WatchID)
	if err != nil {
		t.Fatalf("GetReviewWatchByID() error = %v", err)
	}
	if persisted == nil {
		t.Fatal("GetReviewWatchByID() = nil, want persisted watch")
	}
	if persisted.WatchStatus != string(StatusStale) {
		t.Fatalf("persisted WatchStatus = %q, want %q", persisted.WatchStatus, StatusStale)
	}
	if persisted.IsActive {
		t.Fatal("persisted IsActive = true, want false")
	}
	if persisted.StaleAt == nil {
		t.Fatal("persisted StaleAt = nil, want timestamp")
	}
}

func TestManagerPersistFailureDuringPollingFailsWatch(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(&persistFailDB{
		DB:        db,
		failAfter: 1,
		err:       errors.New("forced persist failure"),
	}, Options{
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

	started, _, err := manager.Start(StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    124,
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
	if snapshot.FailureReason == nil || *snapshot.FailureReason != FailureReasonInternal {
		t.Fatalf("FailureReason = %v, want %q", snapshot.FailureReason, FailureReasonInternal)
	}
	if snapshot.LastError == nil || !strings.Contains(*snapshot.LastError, "failed to persist review_watch while recording WATCHING") {
		t.Fatalf("LastError = %v, want persist failure detail", snapshot.LastError)
	}
}

func TestManagerPersistFailureDuringTerminalTransitionFailsWatch(t *testing.T) {
	db := openTestDB(t)
	reviewTime := time.Now().Add(time.Minute)
	manager := NewManager(&persistFailDB{
		DB:        db,
		failAfter: 1,
		err:       errors.New("forced persist failure"),
	}, Options{
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
		PR:    125,
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
	if snapshot.ReviewStatus == nil || *snapshot.ReviewStatus != ghclient.StatusCompleted {
		t.Fatalf("ReviewStatus = %v, want %q", snapshot.ReviewStatus, ghclient.StatusCompleted)
	}
	if snapshot.FailureReason == nil || *snapshot.FailureReason != FailureReasonInternal {
		t.Fatalf("FailureReason = %v, want %q", snapshot.FailureReason, FailureReasonInternal)
	}
	if snapshot.LastError == nil || !strings.Contains(*snapshot.LastError, "failed to persist review_watch while recording COMPLETED") {
		t.Fatalf("LastError = %v, want persist failure detail", snapshot.LastError)
	}
}

func TestManagerCloseKeepsStaleStatusWhenPersistenceFails(t *testing.T) {
	db := openTestDB(t)
	manager := NewManager(&persistFailDB{
		DB:        db,
		failAfter: 1,
		err:       errors.New("forced persist failure"),
	}, Options{
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
		PR:    126,
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
	if snapshot.LastError == nil || !strings.Contains(*snapshot.LastError, "failed to persist review_watch while recording STALE") {
		t.Fatalf("LastError = %v, want persist failure detail", snapshot.LastError)
	}
}

func TestManagerGetLatestFallsBackToPersistedWatch(t *testing.T) {
	db := openTestDB(t)
	if _, err := db.Insert("octo", "demo", 55, "MANUAL"); err != nil {
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
		PR:    55,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}
	waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool { return s.Terminal })

	restarted := NewManager(db, Options{Threshold: 30 * time.Second})
	t.Cleanup(restarted.Close)

	snapshot, ok := restarted.GetLatest("alice", "octo", "demo", 55)
	if !ok {
		t.Fatal("GetLatest() = not found, want persisted watch")
	}
	if snapshot.WatchID != started.WatchID {
		t.Fatalf("GetLatest().WatchID = %q, want %q", snapshot.WatchID, started.WatchID)
	}
	if snapshot.WatchStatus != StatusCompleted {
		t.Fatalf("GetLatest().WatchStatus = %q, want %q", snapshot.WatchStatus, StatusCompleted)
	}
	if snapshot.WorkerRunning {
		t.Fatal("GetLatest().WorkerRunning = true, want false for DB fallback")
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
	base := time.Now().UTC()
	nowValues := []time.Time{
		base,
		base,
		base.Add(2 * time.Millisecond),
	}
	var nowMu sync.Mutex
	nowIndex := 0
	nowFn := func() time.Time {
		nowMu.Lock()
		defer nowMu.Unlock()
		if nowIndex >= len(nowValues) {
			return nowValues[len(nowValues)-1]
		}
		value := nowValues[nowIndex]
		nowIndex++
		return value
	}
	fetcher := &fakeFetcher{
		results: []fetchResult{
			{data: &ghclient.ReviewData{IsCopilotInReviewers: true, RateLimitRemaining: 100}},
		},
	}
	manager := NewManager(db, Options{
		PollInterval:     1 * time.Millisecond,
		MaxWatchDuration: 1 * time.Millisecond,
		Threshold:        30 * time.Second,
		Now:              nowFn,
		ClientFactory:    func(_ context.Context, _ string) ReviewDataFetcher { return fetcher },
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
	if snapshot.PollsDone != 0 {
		t.Fatalf("PollsDone = %d, want 0 when timeout occurs before polling", snapshot.PollsDone)
	}
	if snapshot.LastPolledAt != nil {
		t.Fatalf("LastPolledAt = %v, want nil when timeout occurs before polling", snapshot.LastPolledAt)
	}
	if fetcher.calls != 0 {
		t.Fatalf("GetReviewData() calls = %d, want 0", fetcher.calls)
	}
}

func TestManagerLowRateLimitIncludesRetryDetail(t *testing.T) {
	db := openTestDB(t)
	reset := time.Now().UTC().Add(5 * time.Minute).Truncate(time.Second)
	manager := NewManager(db, Options{
		PollInterval: 5 * time.Millisecond,
		Threshold:    30 * time.Second,
		ClientFactory: func(_ context.Context, _ string) ReviewDataFetcher {
			return &fakeFetcher{
				results: []fetchResult{
					{
						data: &ghclient.ReviewData{
							IsCopilotInReviewers: true,
							RateLimitRemaining:   5,
							RateLimitReset:       reset,
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
		PR:    202,
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}

	snapshot := waitForWatch(t, manager, started.WatchID, func(s Snapshot) bool {
		return s.Terminal
	})
	if snapshot.WatchStatus != StatusRateLimited {
		t.Fatalf("WatchStatus = %q, want %q", snapshot.WatchStatus, StatusRateLimited)
	}
	if snapshot.LastError == nil {
		t.Fatal("LastError = nil, want rate-limit detail")
	}
	if !strings.Contains(*snapshot.LastError, "remaining=5") {
		t.Fatalf("LastError = %q, want remaining count", *snapshot.LastError)
	}
	if !strings.Contains(*snapshot.LastError, reset.Format(time.RFC3339)) {
		t.Fatalf("LastError = %q, want reset time %q", *snapshot.LastError, reset.Format(time.RFC3339))
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

func TestSnapshotFromStateClonesPointerFields(t *testing.T) {
	reviewStatus := ghclient.StatusCompleted
	failureReason := FailureReasonGitHubError
	startedAt := time.Now().UTC()
	updatedAt := startedAt.Add(time.Minute)
	completedAt := updatedAt.Add(time.Minute)
	lastPolledAt := updatedAt
	lastError := "original error"

	state := &watchState{
		id:            "cw_test",
		key:           watchKey{login: "alice", owner: "octo", repo: "demo", pr: 42},
		status:        StatusFailed,
		reviewStatus:  &reviewStatus,
		failureReason: &failureReason,
		terminal:      true,
		startedAt:     startedAt,
		updatedAt:     updatedAt,
		completedAt:   &completedAt,
		lastPolledAt:  &lastPolledAt,
		lastError:     &lastError,
	}

	snapshot := snapshotFromState(state)
	if snapshot.ReviewStatus == state.reviewStatus {
		t.Fatal("ReviewStatus pointer aliases internal state")
	}
	if snapshot.FailureReason == state.failureReason {
		t.Fatal("FailureReason pointer aliases internal state")
	}
	if snapshot.CompletedAt == state.completedAt {
		t.Fatal("CompletedAt pointer aliases internal state")
	}
	if snapshot.LastPolledAt == state.lastPolledAt {
		t.Fatal("LastPolledAt pointer aliases internal state")
	}
	if snapshot.LastError == state.lastError {
		t.Fatal("LastError pointer aliases internal state")
	}

	*snapshot.ReviewStatus = ghclient.StatusBlocked
	*snapshot.FailureReason = FailureReasonInternal
	*snapshot.CompletedAt = snapshot.CompletedAt.Add(time.Hour)
	*snapshot.LastPolledAt = snapshot.LastPolledAt.Add(time.Hour)
	*snapshot.LastError = "mutated error"

	if *state.reviewStatus != ghclient.StatusCompleted {
		t.Fatalf("internal ReviewStatus = %q, want %q", *state.reviewStatus, ghclient.StatusCompleted)
	}
	if *state.failureReason != FailureReasonGitHubError {
		t.Fatalf("internal FailureReason = %q, want %q", *state.failureReason, FailureReasonGitHubError)
	}
	if !state.completedAt.Equal(completedAt) {
		t.Fatalf("internal CompletedAt = %v, want %v", state.completedAt, completedAt)
	}
	if !state.lastPolledAt.Equal(lastPolledAt) {
		t.Fatalf("internal LastPolledAt = %v, want %v", state.lastPolledAt, lastPolledAt)
	}
	if *state.lastError != "original error" {
		t.Fatalf("internal LastError = %q, want %q", *state.lastError, "original error")
	}
}

func TestFinishFailureWithPollCountsExactlyOnce(t *testing.T) {
	manager := &Manager{
		watchesByID: make(map[string]*watchState),
		activeByKey: make(map[watchKey]string),
		latestByKey: make(map[watchKey]string),
	}
	key := watchKey{login: "alice", owner: "octo", repo: "demo", pr: 77}
	now := time.Now().UTC()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	state := &watchState{
		id:     "cw_test_failure",
		key:    key,
		ctx:    ctx,
		cancel: cancel,
		status: StatusWatching,
	}
	manager.watchesByID[state.id] = state
	manager.activeByKey[key] = state.id
	manager.latestByKey[key] = state.id

	manager.finishFailureWithPoll(state.id, now, FailureReasonInternal, "failed to update trigger_log completed_at")

	if state.pollsDone != 1 {
		t.Fatalf("PollsDone = %d, want 1", state.pollsDone)
	}
	if state.lastPolledAt == nil {
		t.Fatal("LastPolledAt = nil, want poll timestamp")
	}
	if state.status != StatusFailed {
		t.Fatalf("status = %q, want %q", state.status, StatusFailed)
	}
	if state.failureReason == nil || *state.failureReason != FailureReasonInternal {
		t.Fatalf("FailureReason = %v, want %q", state.failureReason, FailureReasonInternal)
	}
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

type persistFailDB struct {
	*store.DB
	failAfter int
	upserts   int
	err       error
}

func (d *persistFailDB) UpsertReviewWatch(entry store.ReviewWatchEntry) error {
	d.upserts++
	if d.upserts > d.failAfter {
		return d.err
	}
	return d.DB.UpsertReviewWatch(entry)
}

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
