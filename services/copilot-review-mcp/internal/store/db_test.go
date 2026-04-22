package store

import (
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestReviewWatchActiveUniqueConstraint(t *testing.T) {
	db := openTestDB(t, filepath.Join(t.TempDir(), "review-watch-unique.db"))

	startedAt := time.Now().UTC().Truncate(time.Second)
	first := ReviewWatchEntry{
		ID:          "cw_first",
		GitHubLogin: "alice",
		Owner:       "octo",
		Repo:        "demo",
		PR:          42,
		WatchStatus: "WATCHING",
		IsActive:    true,
		StartedAt:   startedAt,
		UpdatedAt:   startedAt,
	}
	if err := db.UpsertReviewWatch(first); err != nil {
		t.Fatalf("UpsertReviewWatch(first) error = %v", err)
	}

	second := first
	second.ID = "cw_second"
	second.UpdatedAt = startedAt.Add(time.Minute)
	if err := db.UpsertReviewWatch(second); err == nil {
		t.Fatal("UpsertReviewWatch(second) = nil error, want unique constraint failure")
	}

	first.IsActive = false
	first.WatchStatus = "COMPLETED"
	completedAt := startedAt.Add(2 * time.Minute)
	first.CompletedAt = &completedAt
	first.UpdatedAt = completedAt
	if err := db.UpsertReviewWatch(first); err != nil {
		t.Fatalf("UpsertReviewWatch(first inactive) error = %v", err)
	}
	if err := db.UpsertReviewWatch(second); err != nil {
		t.Fatalf("UpsertReviewWatch(second after deactivation) error = %v", err)
	}
}

func TestGetLatestReviewWatchReturnsNewestSnapshot(t *testing.T) {
	db := openTestDB(t, filepath.Join(t.TempDir(), "review-watch-latest.db"))

	base := time.Now().UTC().Truncate(time.Second)
	first := ReviewWatchEntry{
		ID:          "cw_old",
		GitHubLogin: "alice",
		Owner:       "octo",
		Repo:        "demo",
		PR:          7,
		WatchStatus: "COMPLETED",
		IsActive:    false,
		StartedAt:   base,
		UpdatedAt:   base,
	}
	if err := db.UpsertReviewWatch(first); err != nil {
		t.Fatalf("UpsertReviewWatch(first) error = %v", err)
	}

	lastError := "auth expired"
	reviewStatus := "PENDING"
	failureReason := "AUTH_EXPIRED"
	second := ReviewWatchEntry{
		ID:            "cw_new",
		GitHubLogin:   "alice",
		Owner:         "octo",
		Repo:          "demo",
		PR:            7,
		WatchStatus:   "FAILED",
		ReviewStatus:  &reviewStatus,
		FailureReason: &failureReason,
		IsActive:      false,
		StartedAt:     base.Add(time.Minute),
		UpdatedAt:     base.Add(2 * time.Minute),
		LastError:     &lastError,
	}
	if err := db.UpsertReviewWatch(second); err != nil {
		t.Fatalf("UpsertReviewWatch(second) error = %v", err)
	}

	got, err := db.GetLatestReviewWatch("alice", "octo", "demo", 7)
	if err != nil {
		t.Fatalf("GetLatestReviewWatch() error = %v", err)
	}
	if got == nil {
		t.Fatal("GetLatestReviewWatch() = nil, want entry")
	}
	if got.ID != second.ID {
		t.Fatalf("GetLatestReviewWatch().ID = %q, want %q", got.ID, second.ID)
	}
	if got.LastError == nil || *got.LastError != lastError {
		t.Fatalf("GetLatestReviewWatch().LastError = %v, want %q", got.LastError, lastError)
	}
}

func TestOpenMarksActiveReviewWatchesStale(t *testing.T) {
	path := filepath.Join(t.TempDir(), "review-watch-open.db")
	db := openTestDB(t, path)

	startedAt := time.Now().UTC().Truncate(time.Second)
	entry := ReviewWatchEntry{
		ID:          "cw_active",
		GitHubLogin: "alice",
		Owner:       "octo",
		Repo:        "demo",
		PR:          99,
		WatchStatus: "WATCHING",
		IsActive:    true,
		StartedAt:   startedAt,
		UpdatedAt:   startedAt,
	}
	if err := db.UpsertReviewWatch(entry); err != nil {
		t.Fatalf("UpsertReviewWatch() error = %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatalf("db.Close() error = %v", err)
	}

	reopened, err := Open(path)
	if err != nil {
		t.Fatalf("store.Open(reopen) error = %v", err)
	}
	defer reopened.Close()

	got, err := reopened.GetReviewWatchByID(entry.ID)
	if err != nil {
		t.Fatalf("GetReviewWatchByID() error = %v", err)
	}
	if got == nil {
		t.Fatal("GetReviewWatchByID() = nil, want entry")
	}
	if got.WatchStatus != "STALE" {
		t.Fatalf("WatchStatus = %q, want %q", got.WatchStatus, "STALE")
	}
	if got.IsActive {
		t.Fatal("IsActive = true, want false")
	}
	if got.StaleAt == nil {
		t.Fatal("StaleAt = nil, want timestamp")
	}
	if got.CompletedAt == nil {
		t.Fatal("CompletedAt = nil, want timestamp")
	}
	if got.LastError == nil || !strings.Contains(*got.LastError, staleOnOpenMessage) {
		t.Fatalf("LastError = %v, want message containing %q", got.LastError, staleOnOpenMessage)
	}
}

func openTestDB(t *testing.T, path string) *DB {
	t.Helper()

	db, err := Open(path)
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() {
		_ = db.Close()
	})
	return db
}
