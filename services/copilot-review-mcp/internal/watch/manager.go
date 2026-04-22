package watch

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/go-github/v72/github"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

const defaultPollInterval = 90 * time.Second
const defaultPollTimeout = 30 * time.Second
const defaultMaxWatchDuration = 2 * time.Hour

// Status is the lifecycle state of a background review watch.
type Status string

const (
	StatusWatching    Status = "WATCHING"
	StatusCompleted   Status = "COMPLETED"
	StatusBlocked     Status = "BLOCKED"
	StatusTimeout     Status = "TIMEOUT"
	StatusRateLimited Status = "RATE_LIMITED"
	StatusFailed      Status = "FAILED"
	StatusStale       Status = "STALE"
	StatusCancelled   Status = "CANCELLED"
)

// FailureReason describes why a watch entered FAILED.
type FailureReason string

const (
	FailureReasonAuthExpired FailureReason = "AUTH_EXPIRED"
	FailureReasonGitHubError FailureReason = "GITHUB_ERROR"
	FailureReasonInternal    FailureReason = "INTERNAL_ERROR"
)

// Snapshot is the externally visible state of a watch at a point in time.
type Snapshot struct {
	WatchID       string
	Login         string
	Owner         string
	Repo          string
	PR            int
	WatchStatus   Status
	ReviewStatus  *ghclient.ReviewStatus
	FailureReason *FailureReason
	Terminal      bool
	WorkerRunning bool
	PollsDone     int
	StartedAt     time.Time
	UpdatedAt     time.Time
	CompletedAt   *time.Time
	LastPolledAt  *time.Time
	LastError     *string
}

// StartInput identifies a PR watch owned by one authenticated GitHub user.
type StartInput struct {
	Login string
	Token string
	Owner string
	Repo  string
	PR    int
}

// ReviewDataFetcher fetches the GitHub snapshot needed to update watch state.
type ReviewDataFetcher interface {
	GetReviewData(ctx context.Context, owner, repo string, prNumber int) (*ghclient.ReviewData, error)
}

// Options configures the watch manager.
type Options struct {
	PollInterval     time.Duration
	PollTimeout      time.Duration
	MaxWatchDuration time.Duration
	Threshold        time.Duration
	InvalidateToken  func(string)
	ClientFactory    func(ctx context.Context, token string) ReviewDataFetcher
	Now              func() time.Time
}

// Manager owns background review-watch workers for the current server process.
type Manager struct {
	db               *store.DB
	threshold        time.Duration
	pollInterval     time.Duration
	pollTimeout      time.Duration
	maxWatchDuration time.Duration
	clientFactory    func(ctx context.Context, token string) ReviewDataFetcher
	now              func() time.Time
	ctx              context.Context
	cancel           context.CancelFunc
	idSeq            atomic.Uint64
	mu               sync.RWMutex
	watchesByID      map[string]*watchState
	activeByKey      map[watchKey]string
	latestByKey      map[watchKey]string
	closed           bool
}

type watchKey struct {
	login string
	owner string
	repo  string
	pr    int
}

type watchState struct {
	id            string
	key           watchKey
	token         string
	ctx           context.Context
	cancel        context.CancelFunc
	clientMu      sync.RWMutex
	client        ReviewDataFetcher
	status        Status
	reviewStatus  *ghclient.ReviewStatus
	failureReason *FailureReason
	terminal      bool
	workerRunning bool
	pollsDone     int
	startedAt     time.Time
	updatedAt     time.Time
	completedAt   *time.Time
	lastPolledAt  *time.Time
	lastError     *string
}

// NewManager creates a process-local, memory-only watch manager.
func NewManager(db *store.DB, opts Options) *Manager {
	pollInterval := opts.PollInterval
	if pollInterval <= 0 {
		pollInterval = defaultPollInterval
	}
	pollTimeout := opts.PollTimeout
	if pollTimeout <= 0 {
		pollTimeout = defaultPollTimeout
	}
	maxWatchDuration := opts.MaxWatchDuration
	if maxWatchDuration <= 0 {
		maxWatchDuration = defaultMaxWatchDuration
	}
	now := opts.Now
	if now == nil {
		now = time.Now
	}
	ctx, cancel := context.WithCancel(context.Background())
	clientFactory := opts.ClientFactory
	if clientFactory == nil {
		clientFactory = func(ctx context.Context, token string) ReviewDataFetcher {
			return ghclient.NewClient(ctx, token, opts.Threshold, opts.InvalidateToken)
		}
	}
	return &Manager{
		db:               db,
		threshold:        opts.Threshold,
		pollInterval:     pollInterval,
		pollTimeout:      pollTimeout,
		maxWatchDuration: maxWatchDuration,
		clientFactory:    clientFactory,
		now:              now,
		ctx:              ctx,
		cancel:           cancel,
		watchesByID:      make(map[string]*watchState),
		activeByKey:      make(map[watchKey]string),
		latestByKey:      make(map[watchKey]string),
	}
}

// Close cancels all active workers and marks them as STALE.
func (m *Manager) Close() {
	m.mu.Lock()
	if m.closed {
		m.mu.Unlock()
		return
	}
	m.closed = true
	now := m.now().UTC()
	watches := make([]*watchState, 0, len(m.activeByKey))
	for key, id := range m.activeByKey {
		w := m.watchesByID[id]
		if w == nil || w.terminal {
			delete(m.activeByKey, key)
			continue
		}
		w.status = StatusStale
		w.terminal = true
		w.workerRunning = false
		w.updatedAt = now
		w.completedAt = timePtr(now)
		w.token = ""
		w.clientMu.Lock()
		w.client = nil
		w.clientMu.Unlock()
		errText := "watch manager closed before the watch could finish"
		w.lastError = &errText
		watches = append(watches, w)
		delete(m.activeByKey, key)
	}
	m.mu.Unlock()

	for _, w := range watches {
		w.cancel()
	}
	m.cancel()
}

// Start begins a new background watch or reuses the current active watch for the same user/PR.
func (m *Manager) Start(in StartInput) (Snapshot, bool, error) {
	if in.Login == "" || in.Token == "" || in.Owner == "" || in.Repo == "" || in.PR <= 0 {
		return Snapshot{}, false, fmt.Errorf("login, token, owner, repo, and pr are required")
	}

	key := watchKey{
		login: in.Login,
		owner: in.Owner,
		repo:  in.Repo,
		pr:    in.PR,
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	if m.closed {
		return Snapshot{}, false, fmt.Errorf("watch manager is closed")
	}

	if id, ok := m.activeByKey[key]; ok {
		if existing := m.watchesByID[id]; existing != nil && !existing.terminal {
			if existing.token != in.Token {
				existing.token = in.Token
				existing.clientMu.Lock()
				existing.client = m.clientFactory(existing.ctx, in.Token)
				existing.clientMu.Unlock()
				existing.updatedAt = m.now().UTC()
			}
			return snapshotFromState(existing), true, nil
		}
		delete(m.activeByKey, key)
	}

	now := m.now().UTC()
	watchCtx, cancel := context.WithCancel(m.ctx)
	id := m.nextID()
	state := &watchState{
		id:            id,
		key:           key,
		token:         in.Token,
		ctx:           watchCtx,
		cancel:        cancel,
		client:        m.clientFactory(watchCtx, in.Token),
		status:        StatusWatching,
		workerRunning: true,
		startedAt:     now,
		updatedAt:     now,
	}
	m.watchesByID[id] = state
	m.activeByKey[key] = id
	m.latestByKey[key] = id

	go m.run(state)

	return snapshotFromState(state), false, nil
}

// GetByID returns the latest snapshot for a watch ID.
func (m *Manager) GetByID(watchID string) (Snapshot, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	w := m.watchesByID[watchID]
	if w == nil {
		return Snapshot{}, false
	}
	return snapshotFromState(w), true
}

// GetLatest returns the latest watch snapshot for a given user/PR key.
func (m *Manager) GetLatest(login, owner, repo string, pr int) (Snapshot, bool) {
	key := watchKey{login: login, owner: owner, repo: repo, pr: pr}
	m.mu.RLock()
	defer m.mu.RUnlock()

	id, ok := m.latestByKey[key]
	if !ok {
		return Snapshot{}, false
	}
	w := m.watchesByID[id]
	if w == nil {
		return Snapshot{}, false
	}
	return snapshotFromState(w), true
}

func (m *Manager) run(w *watchState) {
	defer func() {
		if r := recover(); r != nil {
			m.markStale(w.id, fmt.Sprintf("watch worker panicked: %v", r))
		}
	}()

	if m.pollOnce(w.id) {
		return
	}

	ticker := time.NewTicker(m.pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-w.ctx.Done():
			return
		case <-ticker.C:
			if m.pollOnce(w.id) {
				return
			}
		}
	}
}

func (m *Manager) pollOnce(watchID string) bool {
	m.mu.RLock()
	w := m.watchesByID[watchID]
	m.mu.RUnlock()
	if w == nil {
		return true
	}
	now := m.now().UTC()
	if now.Sub(w.startedAt) >= m.maxWatchDuration {
		m.finishStatus(w.id, now, StatusTimeout, nil, fmt.Sprintf("watch exceeded max duration of %s", m.maxWatchDuration))
		return true
	}

	w.clientMu.RLock()
	client := w.client
	w.clientMu.RUnlock()
	if client == nil {
		m.finishFailure(w.id, now, FailureReasonInternal, "watch client is unavailable")
		return true
	}

	callCtx, cancel := context.WithTimeout(w.ctx, m.pollTimeout)
	defer cancel()

	data, err := client.GetReviewData(callCtx, w.key.owner, w.key.repo, w.key.pr)
	now = m.now().UTC()

	if err != nil {
		if errors.Is(err, context.Canceled) && w.ctx.Err() != nil {
			return true
		}
		if errors.Is(err, context.DeadlineExceeded) {
			if w.ctx.Err() != nil {
				return true
			}
			m.finishFailure(w.id, now, FailureReasonGitHubError, fmt.Sprintf("github poll timed out after %s", m.pollTimeout))
			return true
		}
		if IsRateLimitHTTPError(err) {
			m.finishStatus(w.id, now, StatusRateLimited, nil, err.Error())
			return true
		}
		reason := FailureReasonGitHubError
		if ghclient.IsAuthError(err) {
			reason = FailureReasonAuthExpired
		}
		m.finishFailure(w.id, now, reason, err.Error())
		return true
	}

	entry, err := m.db.GetLatest(w.key.owner, w.key.repo, w.key.pr)
	if err != nil {
		m.finishFailure(w.id, now, FailureReasonInternal, fmt.Sprintf("failed to read trigger_log: %v", err))
		return true
	}

	var requestedAt *time.Time
	if entry != nil {
		requestedAt = &entry.RequestedAt
	}
	reviewStatus := ghclient.DeriveStatusWithThreshold(m.threshold, data, requestedAt)

	m.mu.Lock()
	current := m.watchesByID[watchID]
	if current == nil || current.terminal {
		m.mu.Unlock()
		return true
	}

	current.pollsDone++
	current.updatedAt = now
	current.lastPolledAt = timePtr(now)
	current.reviewStatus = reviewStatusPtr(reviewStatus)
	current.lastError = nil

	if data.RateLimitRemaining < 10 {
		m.finishLocked(current, StatusRateLimited, nil, now, formatRateLimitMessage(data.RateLimitRemaining, data.RateLimitReset))
		m.mu.Unlock()
		return true
	}

	terminalStatus, terminal := watchStatusForReview(reviewStatus)
	if terminal {
		m.mu.Unlock()
		if entry != nil && entry.CompletedAt == nil {
			if err := m.db.UpdateCompletedAt(entry.ID); err != nil {
				m.finishFailure(w.id, now, FailureReasonInternal, fmt.Sprintf("failed to update trigger_log completed_at: %v", err))
				return true
			}
		}
		m.mu.Lock()
		current = m.watchesByID[watchID]
		if current == nil || current.terminal {
			m.mu.Unlock()
			return true
		}
		m.finishLocked(current, terminalStatus, nil, now, "")
		m.mu.Unlock()
		return true
	}

	current.status = StatusWatching
	current.workerRunning = true
	m.mu.Unlock()
	return false
}

func (m *Manager) finishFailure(watchID string, now time.Time, reason FailureReason, errText string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	w := m.watchesByID[watchID]
	if w == nil || w.terminal {
		return
	}

	w.pollsDone++
	w.updatedAt = now
	w.lastPolledAt = timePtr(now)
	m.finishLocked(w, StatusFailed, &reason, now, errText)
}

func (m *Manager) finishStatus(watchID string, now time.Time, status Status, reason *FailureReason, errText string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	w := m.watchesByID[watchID]
	if w == nil || w.terminal {
		return
	}

	w.pollsDone++
	w.updatedAt = now
	w.lastPolledAt = timePtr(now)
	m.finishLocked(w, status, reason, now, errText)
}

func (m *Manager) markStale(watchID, errText string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	w := m.watchesByID[watchID]
	if w == nil || w.terminal {
		return
	}

	now := m.now().UTC()
	m.finishLocked(w, StatusStale, nil, now, errText)
}

func (m *Manager) finishLocked(w *watchState, status Status, reason *FailureReason, now time.Time, errText string) {
	w.status = status
	w.failureReason = reason
	w.terminal = true
	w.workerRunning = false
	w.updatedAt = now
	w.completedAt = timePtr(now)
	w.token = ""
	w.clientMu.Lock()
	w.client = nil
	w.clientMu.Unlock()
	if errText != "" {
		w.lastError = &errText
	}
	delete(m.activeByKey, w.key)
	w.cancel()
}

func (m *Manager) nextID() string {
	seq := m.idSeq.Add(1)
	return fmt.Sprintf("cw_%d_%d", m.now().UTC().UnixNano(), seq)
}

func snapshotFromState(w *watchState) Snapshot {
	return Snapshot{
		WatchID:       w.id,
		Login:         w.key.login,
		Owner:         w.key.owner,
		Repo:          w.key.repo,
		PR:            w.key.pr,
		WatchStatus:   w.status,
		ReviewStatus:  w.reviewStatus,
		FailureReason: w.failureReason,
		Terminal:      w.terminal,
		WorkerRunning: w.workerRunning,
		PollsDone:     w.pollsDone,
		StartedAt:     w.startedAt,
		UpdatedAt:     w.updatedAt,
		CompletedAt:   w.completedAt,
		LastPolledAt:  w.lastPolledAt,
		LastError:     w.lastError,
	}
}

func reviewStatusPtr(status ghclient.ReviewStatus) *ghclient.ReviewStatus {
	s := status
	return &s
}

func timePtr(t time.Time) *time.Time {
	return &t
}

func formatRateLimitMessage(remaining int, reset time.Time) string {
	resetText := "unknown"
	if !reset.IsZero() {
		resetText = reset.UTC().Format(time.RFC3339)
	}
	return fmt.Sprintf(
		"GitHub API rate limit is low (remaining=%d, reset=%s); poll again after the reset time",
		remaining,
		resetText,
	)
}

// IsRateLimitHTTPError reports whether err is a GitHub rate-limit HTTP failure.
func IsRateLimitHTTPError(err error) bool {
	var rateErr *github.RateLimitError
	if errors.As(err, &rateErr) {
		return true
	}
	var abuseErr *github.AbuseRateLimitError
	if errors.As(err, &abuseErr) {
		return true
	}
	return false
}

func watchStatusForReview(status ghclient.ReviewStatus) (Status, bool) {
	switch status {
	case ghclient.StatusCompleted:
		return StatusCompleted, true
	case ghclient.StatusBlocked:
		return StatusBlocked, true
	default:
		return "", false
	}
}
