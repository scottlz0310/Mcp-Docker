package watch

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
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

type watchStore interface {
	GetLatest(owner, repo string, pr int) (*store.TriggerEntry, error)
	UpdateCompletedAt(id int64) error
	GetReviewWatchByID(id string) (*store.ReviewWatchEntry, error)
	GetLatestReviewWatch(login, owner, repo string, pr int) (*store.ReviewWatchEntry, error)
	UpsertReviewWatch(entry store.ReviewWatchEntry) error
}

// Manager owns background review-watch workers for the current server process.
type Manager struct {
	db               watchStore
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
	id               string
	key              watchKey
	triggerLogID     *int64
	resourceURI      *string
	token            string
	ctx              context.Context
	cancel           context.CancelFunc
	clientMu         sync.RWMutex
	client           ReviewDataFetcher
	status           Status
	reviewStatus     *ghclient.ReviewStatus
	failureReason    *FailureReason
	terminal         bool
	workerRunning    bool
	pollsDone        int
	startedAt        time.Time
	updatedAt        time.Time
	completedAt      *time.Time
	staleAt          *time.Time
	lastPolledAt     *time.Time
	lastError        *string
	rateLimitResetAt *time.Time
}

// NewManager creates a process-local, memory-only watch manager.
func NewManager(db watchStore, opts Options) *Manager {
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
		w.staleAt = timePtr(now)
		w.token = ""
		w.clientMu.Lock()
		w.client = nil
		w.clientMu.Unlock()
		errText := "watch manager closed before the watch could finish"
		w.lastError = &errText
		_ = m.persistOrDegradeLocked(w, StatusStale, now)
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

	var triggerLogID *int64
	if m.db != nil {
		entry, err := m.db.GetLatest(in.Owner, in.Repo, in.PR)
		if err != nil {
			return Snapshot{}, false, fmt.Errorf("failed to read trigger_log: %w", err)
		}
		if entry != nil {
			id := entry.ID
			triggerLogID = &id
		}
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
			tokenChanged := existing.token != in.Token
			triggerLinked := existing.triggerLogID == nil && triggerLogID != nil
			if tokenChanged {
				existing.token = in.Token
				existing.clientMu.Lock()
				existing.client = m.clientFactory(existing.ctx, in.Token)
				existing.clientMu.Unlock()
				existing.updatedAt = m.now().UTC()
			}
			if triggerLinked {
				existing.triggerLogID = cloneInt64Ptr(triggerLogID)
			}
			if tokenChanged || triggerLinked {
				if err := m.persistLocked(existing); err != nil {
					return Snapshot{}, false, fmt.Errorf("failed to persist review_watch: %w", err)
				}
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
		triggerLogID:  cloneInt64Ptr(triggerLogID),
		token:         in.Token,
		ctx:           watchCtx,
		cancel:        cancel,
		client:        m.clientFactory(watchCtx, in.Token),
		status:        StatusWatching,
		workerRunning: true,
		startedAt:     now,
		updatedAt:     now,
	}
	if err := m.persistLocked(state); err != nil {
		cancel()
		return Snapshot{}, false, fmt.Errorf("failed to persist review_watch: %w", err)
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
	w := m.watchesByID[watchID]
	if w != nil {
		snapshot := snapshotFromState(w)
		m.mu.RUnlock()
		return snapshot, true
	}
	m.mu.RUnlock()

	if m.db == nil {
		return Snapshot{}, false
	}
	entry, err := m.db.GetReviewWatchByID(watchID)
	if err != nil || entry == nil {
		return Snapshot{}, false
	}
	return snapshotFromReviewWatchEntry(entry), true
}

// GetLatest returns the latest watch snapshot for a given user/PR key.
func (m *Manager) GetLatest(login, owner, repo string, pr int) (Snapshot, bool) {
	key := watchKey{login: login, owner: owner, repo: repo, pr: pr}
	m.mu.RLock()
	id, ok := m.latestByKey[key]
	if ok {
		w := m.watchesByID[id]
		if w != nil {
			snapshot := snapshotFromState(w)
			m.mu.RUnlock()
			return snapshot, true
		}
	}
	m.mu.RUnlock()

	if m.db == nil {
		return Snapshot{}, false
	}
	entry, err := m.db.GetLatestReviewWatch(login, owner, repo, pr)
	if err != nil || entry == nil {
		return Snapshot{}, false
	}
	return snapshotFromReviewWatchEntry(entry), true
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
		m.finishStatusWithoutPoll(w.id, now, StatusTimeout, nil, fmt.Sprintf("watch exceeded max duration of %s", m.maxWatchDuration))
		return true
	}

	w.clientMu.RLock()
	client := w.client
	w.clientMu.RUnlock()
	if client == nil {
		m.finishFailureWithoutPoll(w.id, now, FailureReasonInternal, "watch client is unavailable")
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
			m.finishFailureWithPoll(w.id, now, FailureReasonGitHubError, fmt.Sprintf("github poll timed out after %s", m.pollTimeout))
			return true
		}
		if IsRateLimitHTTPError(err) {
			m.finishStatusWithPoll(w.id, now, StatusRateLimited, nil, err.Error())
			return true
		}
		reason := FailureReasonGitHubError
		if ghclient.IsAuthError(err) {
			reason = FailureReasonAuthExpired
		}
		m.finishFailureWithPoll(w.id, now, reason, err.Error())
		return true
	}

	var entry *store.TriggerEntry
	if m.db != nil {
		var err error
		entry, err = m.db.GetLatest(w.key.owner, w.key.repo, w.key.pr)
		if err != nil {
			m.finishFailureWithPoll(w.id, now, FailureReasonInternal, fmt.Sprintf("failed to read trigger_log: %v", err))
			return true
		}
	}

	var requestedAt *time.Time
	if entry != nil {
		requestedAt = &entry.RequestedAt
	}
	reviewStatus := ghclient.DeriveStatusWithThreshold(m.threshold, data, requestedAt)

	if data.RateLimitRemaining < 10 {
		m.mu.Lock()
		current := m.watchesByID[watchID]
		if current == nil || current.terminal {
			m.mu.Unlock()
			return true
		}
		m.markPollLocked(current, now)
		current.reviewStatus = reviewStatusPtr(reviewStatus)
		current.lastError = nil
		if data.RateLimitReset.IsZero() {
			current.rateLimitResetAt = nil
		} else {
			current.rateLimitResetAt = cloneTimePtr(&data.RateLimitReset)
		}
		m.finishLocked(current, StatusRateLimited, nil, now, formatRateLimitMessage(data.RateLimitRemaining, data.RateLimitReset))
		m.mu.Unlock()
		return true
	}

	terminalStatus, terminal := watchStatusForReview(reviewStatus)
	if terminal {
		if m.db != nil && entry != nil && entry.CompletedAt == nil {
			if err := m.db.UpdateCompletedAt(entry.ID); err != nil {
				m.finishFailureWithPoll(w.id, now, FailureReasonInternal, fmt.Sprintf("failed to update trigger_log completed_at: %v", err))
				return true
			}
		}
		m.mu.Lock()
		current := m.watchesByID[watchID]
		if current == nil || current.terminal {
			m.mu.Unlock()
			return true
		}
		m.markPollLocked(current, now)
		current.reviewStatus = reviewStatusPtr(reviewStatus)
		current.lastError = nil
		current.rateLimitResetAt = nil
		if current.triggerLogID == nil && entry != nil {
			id := entry.ID
			current.triggerLogID = &id
		}
		m.finishLocked(current, terminalStatus, nil, now, "")
		m.mu.Unlock()
		return true
	}

	m.mu.Lock()
	current := m.watchesByID[watchID]
	if current == nil || current.terminal {
		m.mu.Unlock()
		return true
	}
	m.markPollLocked(current, now)
	current.reviewStatus = reviewStatusPtr(reviewStatus)
	current.lastError = nil
	current.rateLimitResetAt = nil
	if current.triggerLogID == nil && entry != nil {
		id := entry.ID
		current.triggerLogID = &id
	}
	current.status = StatusWatching
	current.workerRunning = true
	if err := m.persistOrDegradeLocked(current, StatusWatching, now); err != nil {
		m.mu.Unlock()
		return true
	}
	m.mu.Unlock()
	return false
}

func (m *Manager) finishFailureWithPoll(watchID string, now time.Time, reason FailureReason, errText string) {
	reasonCopy := reason
	m.finishState(watchID, now, StatusFailed, &reasonCopy, errText, true)
}

func (m *Manager) finishFailureWithoutPoll(watchID string, now time.Time, reason FailureReason, errText string) {
	reasonCopy := reason
	m.finishState(watchID, now, StatusFailed, &reasonCopy, errText, false)
}

func (m *Manager) finishStatusWithPoll(watchID string, now time.Time, status Status, reason *FailureReason, errText string) {
	m.finishState(watchID, now, status, reason, errText, true)
}

func (m *Manager) finishStatusWithoutPoll(watchID string, now time.Time, status Status, reason *FailureReason, errText string) {
	m.finishState(watchID, now, status, reason, errText, false)
}

func (m *Manager) finishState(watchID string, now time.Time, status Status, reason *FailureReason, errText string, countedPoll bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	w := m.watchesByID[watchID]
	if w == nil || w.terminal {
		return
	}

	if countedPoll {
		m.markPollLocked(w, now)
	} else {
		w.updatedAt = now
	}
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

func (m *Manager) markPollLocked(w *watchState, now time.Time) {
	w.pollsDone++
	w.updatedAt = now
	w.lastPolledAt = timePtr(now)
}

func (m *Manager) finishLocked(w *watchState, status Status, reason *FailureReason, now time.Time, errText string) {
	w.status = status
	w.failureReason = reason
	w.terminal = true
	w.workerRunning = false
	w.updatedAt = now
	w.completedAt = timePtr(now)
	if status == StatusStale {
		w.staleAt = timePtr(now)
	}
	w.token = ""
	w.clientMu.Lock()
	w.client = nil
	w.clientMu.Unlock()
	if errText != "" {
		w.lastError = &errText
	}
	delete(m.activeByKey, w.key)
	_ = m.persistOrDegradeLocked(w, status, now)
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
		ReviewStatus:  cloneReviewStatusPtr(w.reviewStatus),
		FailureReason: cloneFailureReasonPtr(w.failureReason),
		Terminal:      w.terminal,
		WorkerRunning: w.workerRunning,
		PollsDone:     w.pollsDone,
		StartedAt:     w.startedAt,
		UpdatedAt:     w.updatedAt,
		CompletedAt:   cloneTimePtr(w.completedAt),
		LastPolledAt:  cloneTimePtr(w.lastPolledAt),
		LastError:     cloneStringPtr(w.lastError),
	}
}

func snapshotFromReviewWatchEntry(entry *store.ReviewWatchEntry) Snapshot {
	var reviewStatus *ghclient.ReviewStatus
	if entry.ReviewStatus != nil {
		status := ghclient.ReviewStatus(*entry.ReviewStatus)
		reviewStatus = &status
	}
	var failureReason *FailureReason
	if entry.FailureReason != nil {
		reason := FailureReason(*entry.FailureReason)
		failureReason = &reason
	}
	return Snapshot{
		WatchID:       entry.ID,
		Login:         entry.GitHubLogin,
		Owner:         entry.Owner,
		Repo:          entry.Repo,
		PR:            entry.PR,
		WatchStatus:   Status(entry.WatchStatus),
		ReviewStatus:  reviewStatus,
		FailureReason: failureReason,
		Terminal:      !entry.IsActive,
		WorkerRunning: false,
		PollsDone:     0,
		StartedAt:     entry.StartedAt,
		UpdatedAt:     entry.UpdatedAt,
		CompletedAt:   cloneTimePtr(entry.CompletedAt),
		LastPolledAt:  nil,
		LastError:     cloneStringPtr(entry.LastError),
	}
}

func (m *Manager) persistLocked(w *watchState) error {
	if m.db == nil {
		return nil
	}
	reviewWatch := store.ReviewWatchEntry{
		ID:               w.id,
		GitHubLogin:      w.key.login,
		Owner:            w.key.owner,
		Repo:             w.key.repo,
		PR:               w.key.pr,
		TriggerLogID:     cloneInt64Ptr(w.triggerLogID),
		ResourceURI:      cloneStringPtr(w.resourceURI),
		WatchStatus:      string(w.status),
		ReviewStatus:     reviewStatusStringPtr(w.reviewStatus),
		FailureReason:    failureReasonStringPtr(w.failureReason),
		IsActive:         !w.terminal,
		StartedAt:        w.startedAt,
		UpdatedAt:        w.updatedAt,
		CompletedAt:      cloneTimePtr(w.completedAt),
		StaleAt:          cloneTimePtr(w.staleAt),
		LastError:        cloneStringPtr(w.lastError),
		RateLimitResetAt: cloneTimePtr(w.rateLimitResetAt),
	}
	return m.db.UpsertReviewWatch(reviewWatch)
}

func (m *Manager) persistOrDegradeLocked(w *watchState, intended Status, now time.Time) error {
	err := m.persistLocked(w)
	if err == nil {
		return nil
	}

	msg := fmt.Sprintf("failed to persist review_watch while recording %s: %v", intended, err)
	slog.Error(
		"failed to persist review_watch",
		"watch_id", w.id,
		"login", w.key.login,
		"owner", w.key.owner,
		"repo", w.key.repo,
		"pr", w.key.pr,
		"intended_status", intended,
		"err", err,
	)

	w.updatedAt = now
	if w.completedAt == nil {
		w.completedAt = timePtr(now)
	}
	w.lastError = &msg
	w.terminal = true
	w.workerRunning = false
	w.token = ""
	w.clientMu.Lock()
	w.client = nil
	w.clientMu.Unlock()
	delete(m.activeByKey, w.key)

	if intended == StatusStale {
		w.status = StatusStale
		w.failureReason = nil
		if w.staleAt == nil {
			w.staleAt = timePtr(now)
		}
	} else {
		reason := FailureReasonInternal
		w.status = StatusFailed
		w.failureReason = &reason
	}

	w.cancel()
	return err
}

func reviewStatusPtr(status ghclient.ReviewStatus) *ghclient.ReviewStatus {
	s := status
	return &s
}

func reviewStatusStringPtr(status *ghclient.ReviewStatus) *string {
	if status == nil {
		return nil
	}
	value := string(*status)
	return &value
}

func failureReasonStringPtr(reason *FailureReason) *string {
	if reason == nil {
		return nil
	}
	value := string(*reason)
	return &value
}

func cloneReviewStatusPtr(status *ghclient.ReviewStatus) *ghclient.ReviewStatus {
	if status == nil {
		return nil
	}
	s := *status
	return &s
}

func cloneFailureReasonPtr(reason *FailureReason) *FailureReason {
	if reason == nil {
		return nil
	}
	r := *reason
	return &r
}

func cloneTimePtr(t *time.Time) *time.Time {
	if t == nil {
		return nil
	}
	v := *t
	return &v
}

func cloneStringPtr(s *string) *string {
	if s == nil {
		return nil
	}
	v := *s
	return &v
}

func cloneInt64Ptr(v *int64) *int64 {
	if v == nil {
		return nil
	}
	value := *v
	return &value
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
