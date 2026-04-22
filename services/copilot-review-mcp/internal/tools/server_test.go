package tools

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/scottlz0310/copilot-review-mcp/internal/store"
	"github.com/scottlz0310/copilot-review-mcp/internal/watch"
)

func TestStreamableHandlerCloseClosesWatchManager(t *testing.T) {
	db, err := store.Open(filepath.Join(t.TempDir(), "server-test.db"))
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Fatalf("db.Close() error = %v", err)
		}
	})

	handler := BuildStreamableHandler(db, 30*time.Second, nil)
	handler.Close()
	handler.Close()

	_, _, err = handler.watchManager.Start(watch.StartInput{
		Login: "alice",
		Token: "token-a",
		Owner: "octo",
		Repo:  "demo",
		PR:    1,
	})
	if err == nil {
		t.Fatal("Start() after Close() = nil error, want watch manager is closed")
	}
	if err.Error() != "watch manager is closed" {
		t.Fatalf("Start() after Close() error = %q, want %q", err.Error(), "watch manager is closed")
	}
}
