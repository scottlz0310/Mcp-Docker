package register

import (
	"context"
	"errors"
	"testing"
)

type mockAgent struct {
	Agent
	callCount int
	entries   []Entry
	err       error
}

func (m *mockAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	m.callCount++
	return m.entries, m.err
}

func TestCachedAgent_ListEntries_CachesResult(t *testing.T) {
	expectedEntries := []Entry{
		{Name: "server1", URL: "http://127.0.0.1:8080/mcp/server1"},
	}
	mock := &mockAgent{
		entries: expectedEntries,
	}

	cached := NewCachedAgent(mock)

	// 1回目の呼び出し
	entries, err := cached.ListEntries(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 || entries[0].Name != "server1" {
		t.Errorf("unexpected entries: %v", entries)
	}

	// 2回目の呼び出し
	entries, err = cached.ListEntries(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 || entries[0].Name != "server1" {
		t.Errorf("unexpected entries: %v", entries)
	}

	// コール回数の検証
	if mock.callCount != 1 {
		t.Errorf("expected ListEntries to be called exactly once, but got %d", mock.callCount)
	}
}

func TestCachedAgent_ListEntries_CachesError(t *testing.T) {
	expectedErr := errors.New("list error")
	mock := &mockAgent{
		err: expectedErr,
	}

	cached := NewCachedAgent(mock)

	// 1回目の呼び出し
	_, err := cached.ListEntries(context.Background())
	if !errors.Is(err, expectedErr) {
		t.Fatalf("expected error %v, but got %v", expectedErr, err)
	}

	// 2回目の呼び出し
	_, err = cached.ListEntries(context.Background())
	if !errors.Is(err, expectedErr) {
		t.Fatalf("expected error %v, but got %v", expectedErr, err)
	}

	// コール回数の検証
	if mock.callCount != 1 {
		t.Errorf("expected ListEntries to be called exactly once, but got %d", mock.callCount)
	}
}
