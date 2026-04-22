package ghclient

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/google/go-github/v72/github"
	"github.com/shurcooL/githubv4"
)

// newReview creates a PullRequestReview with the given state and optional submittedAt.
func newReview(state string, submittedAt *time.Time) *github.PullRequestReview {
	r := &github.PullRequestReview{
		State: github.Ptr(state),
	}
	if submittedAt != nil {
		r.SubmittedAt = &github.Timestamp{Time: *submittedAt}
	}
	return r
}

// TestCopilotBotLoginValue guards against typos in the login constant.
// A wrong value here would cause a silent failure where GitHub accepts the mutation
// but Copilot is never actually added as a reviewer.
func TestCopilotBotLoginValue(t *testing.T) {
	const want = "copilot-pull-request-reviewer[bot]"
	if copilotBotLogin != want {
		t.Errorf("copilotBotLogin = %q, want %q", copilotBotLogin, want)
	}
}

// TestBuildCopilotReviewInput verifies the mutation input constructed by
// buildCopilotReviewInput satisfies the two critical invariants:
//
//  1. union must be true — preserves existing human reviewers.
//     union:false would replace the entire reviewer set with Copilot only.
//  2. botLogins[0] must equal copilotBotLogin — the exact identity GitHub expects.
func TestBuildCopilotReviewInput(t *testing.T) {
	testNodeID := githubv4.ID("PR_kwDOABCDEF12345")
	input := buildCopilotReviewInput(testNodeID)

	// Invariant 1: union must be true (additive, not replacing existing reviewers).
	if input.Union == nil || !bool(*input.Union) {
		t.Error("Union must be true to preserve existing human reviewers; false would remove them")
	}

	// Invariant 2: exactly one bot login with the correct value.
	if input.BotLogins == nil {
		t.Fatal("BotLogins must be set")
	}
	if len(*input.BotLogins) != 1 {
		t.Fatalf("BotLogins length = %d, want 1", len(*input.BotLogins))
	}
	if got := string((*input.BotLogins)[0]); got != copilotBotLogin {
		t.Errorf("BotLogins[0] = %q, want %q", got, copilotBotLogin)
	}

	// Sanity: userLogins and teamSlugs must be empty — we're only adding Copilot.
	if input.UserLogins == nil || len(*input.UserLogins) != 0 {
		t.Errorf("UserLogins must be empty, got %v", input.UserLogins)
	}
	if input.TeamSlugs == nil || len(*input.TeamSlugs) != 0 {
		t.Errorf("TeamSlugs must be empty, got %v", input.TeamSlugs)
	}

	// Sanity: PR node ID is passed through unchanged.
	if input.PullRequestID != testNodeID {
		t.Errorf("PullRequestID = %v, want %v", input.PullRequestID, testNodeID)
	}
}

func TestRequestCopilotReviewUsesRequestReviewsByLoginInput(t *testing.T) {
	const (
		owner    = "owner"
		repo     = "repo"
		pr       = 123
		prNodeID = "PR_kwDOABCDEF12345"
	)

	var sawNodeIDQuery atomic.Bool
	var sawRequestMutation atomic.Bool
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Errorf("ReadAll() error = %v", err)
			http.Error(w, "failed to read body", http.StatusInternalServerError)
			return
		}

		var req struct {
			Query     string                     `json:"query"`
			Variables map[string]json.RawMessage `json:"variables"`
		}
		if err := json.Unmarshal(body, &req); err != nil {
			t.Errorf("json.Unmarshal() error = %v", err)
			http.Error(w, "invalid JSON", http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		normalizedQuery := strings.Join(strings.Fields(req.Query), "")

		switch {
		case strings.Contains(normalizedQuery, "pullRequest(number:$pr){id}"):
			sawNodeIDQuery.Store(true)
			fmt.Fprintf(w, `{"data":{"repository":{"pullRequest":{"id":%q}}}}`, prNodeID)
		case strings.Contains(normalizedQuery, "requestReviewsByLogin(input:$input)"):
			sawRequestMutation.Store(true)
			if !strings.Contains(normalizedQuery, "$input:RequestReviewsByLoginInput!") {
				t.Errorf("mutation query = %q, want RequestReviewsByLoginInput", req.Query)
			}
			if strings.Contains(normalizedQuery, "$input:requestReviewsByLoginInput!") {
				t.Errorf("mutation query = %q, unexpected lower-camel input type", req.Query)
			}

			var input struct {
				PullRequestID string   `json:"pullRequestId"`
				BotLogins     []string `json:"botLogins"`
				UserLogins    []string `json:"userLogins"`
				TeamSlugs     []string `json:"teamSlugs"`
				Union         bool     `json:"union"`
			}
			if err := json.Unmarshal(req.Variables["input"], &input); err != nil {
				t.Errorf("json.Unmarshal(input) error = %v", err)
				http.Error(w, "invalid input payload", http.StatusBadRequest)
				return
			}
			if input.PullRequestID != prNodeID {
				t.Errorf("input.pullRequestId = %q, want %q", input.PullRequestID, prNodeID)
			}
			if len(input.BotLogins) != 1 || input.BotLogins[0] != copilotBotLogin {
				t.Errorf("input.botLogins = %v, want [%q]", input.BotLogins, copilotBotLogin)
			}
			if len(input.UserLogins) != 0 {
				t.Errorf("input.userLogins = %v, want empty", input.UserLogins)
			}
			if len(input.TeamSlugs) != 0 {
				t.Errorf("input.teamSlugs = %v, want empty", input.TeamSlugs)
			}
			if !input.Union {
				t.Error("input.union = false, want true")
			}

			fmt.Fprint(w, `{"data":{"requestReviewsByLogin":{"clientMutationId":""}}}`)
		default:
			fmt.Fprint(w, `{"data":{}}`)
		}
	}))
	defer srv.Close()

	c := &Client{
		v4: githubv4.NewEnterpriseClient(srv.URL, srv.Client()),
	}

	if err := c.RequestCopilotReview(context.Background(), owner, repo, pr); err != nil {
		t.Fatalf("RequestCopilotReview() error = %v", err)
	}
	if !sawNodeIDQuery.Load() {
		t.Fatal("did not observe PR node ID query")
	}
	if !sawRequestMutation.Load() {
		t.Fatal("did not observe requestReviewsByLogin mutation")
	}
}

func TestDeriveStatus(t *testing.T) {
	// threshold=30s.
	// recentRequest: 1s elapsed → PENDING (29s slack vs threshold, safe on slow CI).
	// longAgoRequest: 2min elapsed → IN_PROGRESS.
	c := &Client{threshold: 30 * time.Second}

	now := time.Now()
	recentRequest := now.Add(-time.Second)      // 1s ago — safely within 30s threshold
	longAgoRequest := now.Add(-2 * time.Minute) // 2min ago — safely past threshold
	threeMinAgo := now.Add(-3 * time.Minute)
	oneMinAgo := now.Add(-1 * time.Minute)
	oneMinLater := now.Add(1 * time.Minute)

	tests := []struct {
		name        string
		data        *ReviewData
		requestedAt *time.Time
		want        ReviewStatus
	}{
		// ── no review ────────────────────────────────────────────────────────────
		{
			name: "no review, no reviewers → NOT_REQUESTED",
			data: &ReviewData{},
			want: StatusNotRequested,
		},
		{
			name:        "no review, copilot in reviewers, within threshold → PENDING",
			data:        &ReviewData{IsCopilotInReviewers: true},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "no review, copilot in reviewers, threshold elapsed → IN_PROGRESS",
			data:        &ReviewData{IsCopilotInReviewers: true},
			requestedAt: &longAgoRequest,
			want:        StatusInProgress,
		},
		{
			name: "no review, copilot in reviewers, no requestedAt → IN_PROGRESS (AUTO)",
			data: &ReviewData{IsCopilotInReviewers: true},
			want: StatusInProgress,
		},

		// ── review exists, requestedAt nil (backward compat) ─────────────────────
		{
			name: "APPROVED review, no requestedAt → COMPLETED",
			data: &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			want: StatusCompleted,
		},
		{
			name: "CHANGES_REQUESTED review, no requestedAt → BLOCKED",
			data: &ReviewData{LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinAgo)},
			want: StatusBlocked,
		},

		// ── review submitted AFTER requestedAt ───────────────────────────────────
		{
			name:        "APPROVED review after requestedAt → COMPLETED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinLater)},
			requestedAt: &now,
			want:        StatusCompleted,
		},
		{
			name:        "CHANGES_REQUESTED review after requestedAt → BLOCKED",
			data:        &ReviewData{LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinLater)},
			requestedAt: &now,
			want:        StatusBlocked,
		},

		// ── review submitted at EXACTLY requestedAt (same-second inclusive) ───────
		{
			name:        "APPROVED review at exact requestedAt → COMPLETED (same-second inclusive)",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &now)},
			requestedAt: &now,
			want:        StatusCompleted,
		},

		// ── stale review (submitted BEFORE requestedAt) ───────────────────────────
		{
			// review (1min ago) is older than recentRequest (1s ago) → stale,
			// then elapsed since request = 1s < 30s threshold → PENDING.
			name:        "stale APPROVED review, copilot in reviewers, within threshold → PENDING",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "stale CHANGES_REQUESTED review, copilot in reviewers, within threshold → PENDING (not BLOCKED)",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("CHANGES_REQUESTED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusPending,
		},
		{
			name:        "stale review, copilot NOT in reviewers → NOT_REQUESTED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", &oneMinAgo)},
			requestedAt: &recentRequest,
			want:        StatusNotRequested,
		},
		{
			// review (3min ago) is older than longAgoRequest (2min ago) → stale,
			// then elapsed since request = 2min > 30s threshold → IN_PROGRESS.
			name:        "stale review, copilot in reviewers, threshold elapsed → IN_PROGRESS",
			data:        &ReviewData{IsCopilotInReviewers: true, LatestCopilotReview: newReview("APPROVED", &threeMinAgo)},
			requestedAt: &longAgoRequest,
			want:        StatusInProgress,
		},

		// ── nil submittedAt on review ─────────────────────────────────────────────
		{
			name:        "review with nil submittedAt, requestedAt set → treat as stale → NOT_REQUESTED",
			data:        &ReviewData{LatestCopilotReview: newReview("APPROVED", nil)},
			requestedAt: &now,
			want:        StatusNotRequested,
		},
		{
			name: "review with nil submittedAt, no requestedAt → COMPLETED (backward compat)",
			data: &ReviewData{LatestCopilotReview: newReview("APPROVED", nil)},
			want: StatusCompleted,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := c.DeriveStatus(tt.data, tt.requestedAt)
			if got != tt.want {
				t.Errorf("DeriveStatus() = %q, want %q", got, tt.want)
			}
		})
	}
}

// newTestGHClient creates a Client backed by a test HTTP server.
// The caller must call teardown() when done.
func newTestGHClient(mux *http.ServeMux) (*Client, func()) {
	srv := httptest.NewServer(mux)
	gh := github.NewClient(nil)
	u, _ := url.Parse(srv.URL + "/")
	gh.BaseURL = u
	gh.UploadURL = u
	return &Client{gh: gh}, srv.Close
}

func TestGetCIStatus(t *testing.T) {
	const (
		owner = "owner"
		repo  = "repo"
		pr    = 1
		sha   = "abc123def456"
	)

	prJSON := fmt.Sprintf(`{"number":%d,"head":{"sha":%q}}`, pr, sha)

	makeChecksJSON := func(runs ...string) string {
		return fmt.Sprintf(`{"total_count":%d,"check_runs":[%s]}`, len(runs), join(runs, ","))
	}
	makeRun := func(status, conclusion string) string {
		return fmt.Sprintf(`{"id":1,"status":%q,"conclusion":%q}`, status, conclusion)
	}

	tests := []struct {
		name       string
		checksJSON string
		want       bool
	}{
		{
			name:       "zero check runs → true (CI not configured)",
			checksJSON: makeChecksJSON(),
			want:       true,
		},
		{
			name:       "all success → true",
			checksJSON: makeChecksJSON(makeRun("completed", "success")),
			want:       true,
		},
		{
			name:       "skipped → true",
			checksJSON: makeChecksJSON(makeRun("completed", "skipped")),
			want:       true,
		},
		{
			name:       "neutral → true",
			checksJSON: makeChecksJSON(makeRun("completed", "neutral")),
			want:       true,
		},
		{
			name:       "in_progress (not completed) → false",
			checksJSON: makeChecksJSON(makeRun("in_progress", "")),
			want:       false,
		},
		{
			name:       "failure → false",
			checksJSON: makeChecksJSON(makeRun("completed", "failure")),
			want:       false,
		},
		{
			name: "mixed success and failure → false",
			checksJSON: makeChecksJSON(
				makeRun("completed", "success"),
				makeRun("completed", "failure"),
			),
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mux := http.NewServeMux()
			mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/pulls/%d", owner, repo, pr), func(w http.ResponseWriter, _ *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				fmt.Fprint(w, prJSON)
			})
			mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/commits/%s/check-runs", owner, repo, sha), func(w http.ResponseWriter, _ *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				fmt.Fprint(w, tt.checksJSON)
			})

			c, teardown := newTestGHClient(mux)
			defer teardown()

			got, err := c.GetCIStatus(context.Background(), owner, repo, pr)
			if err != nil {
				t.Fatalf("GetCIStatus() error = %v", err)
			}
			if got != tt.want {
				t.Errorf("GetCIStatus() = %v, want %v", got, tt.want)
			}
		})
	}

	t.Run("returns false when a later check-runs page contains failure", func(t *testing.T) {
		mux := http.NewServeMux()
		pagesSeen := []string{}

		mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/pulls/%d", owner, repo, pr), func(w http.ResponseWriter, _ *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, prJSON)
		})
		mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/commits/%s/check-runs", owner, repo, sha), func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			page := r.URL.Query().Get("page")
			if page == "" {
				page = "1"
			}
			pagesSeen = append(pagesSeen, page)
			if page == "1" {
				w.Header().Set("Link", fmt.Sprintf(`<http://%s/repos/%s/%s/commits/%s/check-runs?page=2>; rel="next"`, r.Host, owner, repo, sha))
				fmt.Fprint(w, `{"total_count":2,"check_runs":[{"id":1,"status":"completed","conclusion":"success"}]}`)
				return
			}
			fmt.Fprint(w, `{"total_count":2,"check_runs":[{"id":2,"status":"completed","conclusion":"failure"}]}`)
		})

		c, teardown := newTestGHClient(mux)
		defer teardown()

		got, err := c.GetCIStatus(context.Background(), owner, repo, pr)
		if err != nil {
			t.Fatalf("GetCIStatus() error = %v", err)
		}
		if got {
			t.Fatalf("GetCIStatus() = %v, want false", got)
		}
		if join(pagesSeen, ",") != "1,2" {
			t.Fatalf("GetCIStatus() did not request all pages, got pages %q, want %q", join(pagesSeen, ","), "1,2")
		}
	})

	t.Run("returns true when all check-runs across later pages succeed", func(t *testing.T) {
		mux := http.NewServeMux()
		pagesSeen := []string{}

		mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/pulls/%d", owner, repo, pr), func(w http.ResponseWriter, _ *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, prJSON)
		})
		mux.HandleFunc(fmt.Sprintf("/repos/%s/%s/commits/%s/check-runs", owner, repo, sha), func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			page := r.URL.Query().Get("page")
			if page == "" {
				page = "1"
			}
			pagesSeen = append(pagesSeen, page)
			if page == "1" {
				w.Header().Set("Link", fmt.Sprintf(`<http://%s/repos/%s/%s/commits/%s/check-runs?page=2>; rel="next"`, r.Host, owner, repo, sha))
				fmt.Fprint(w, `{"total_count":2,"check_runs":[{"id":1,"status":"completed","conclusion":"success"}]}`)
				return
			}
			fmt.Fprint(w, `{"total_count":2,"check_runs":[{"id":2,"status":"completed","conclusion":"success"}]}`)
		})

		c, teardown := newTestGHClient(mux)
		defer teardown()

		got, err := c.GetCIStatus(context.Background(), owner, repo, pr)
		if err != nil {
			t.Fatalf("GetCIStatus() error = %v", err)
		}
		if !got {
			t.Fatalf("GetCIStatus() = %v, want true", got)
		}
		if join(pagesSeen, ",") != "1,2" {
			t.Fatalf("GetCIStatus() did not request all pages, got pages %q, want %q", join(pagesSeen, ","), "1,2")
		}
	})
}

// join concatenates strings with a separator (avoids importing strings in test file).
func join(ss []string, sep string) string {
	if len(ss) == 0 {
		return ""
	}
	result := ss[0]
	for _, s := range ss[1:] {
		result += sep + s
	}
	return result
}
