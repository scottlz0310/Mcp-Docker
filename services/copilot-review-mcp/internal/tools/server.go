package tools

import (
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
	"github.com/scottlz0310/copilot-review-mcp/internal/watch"
)

var schemaCache = mcp.NewSchemaCache()

const (
	defaultStreamableSessionTimeout = 30 * time.Minute
	mcpSessionIDHeader              = "Mcp-Session-Id"
)

// TokenInvalidator is implemented by auth.Handler to clear a token from the
// validation cache when a downstream GitHub API call returns HTTP 401.
type TokenInvalidator interface {
	InvalidateCachedToken(token string)
}

// StreamableHandler serves MCP over Streamable HTTP and owns shared background state.
type StreamableHandler struct {
	handler      http.Handler
	watchManager *watch.Manager
	server       *mcp.Server

	mu sync.Mutex

	sessionLogins map[string]string
}

// ServeHTTP proxies requests to the underlying MCP streamable handler.
func (h *StreamableHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	login := middleware.LoginFromContext(r.Context())
	sessionID := r.Header.Get(mcpSessionIDHeader)
	if sessionID != "" && login != "" && !h.authorizeSession(sessionID, login) {
		http.Error(w, "session user mismatch", http.StatusForbidden)
		return
	}

	rw := &statusCaptureResponseWriter{ResponseWriter: w, statusCode: http.StatusOK}
	h.handler.ServeHTTP(rw, r)

	if responseSessionID := rw.Header().Get(mcpSessionIDHeader); responseSessionID != "" &&
		login != "" &&
		rw.statusCode < http.StatusBadRequest {
		h.rememberSession(responseSessionID, login)
	}
	if r.Method == http.MethodDelete &&
		sessionID != "" &&
		rw.statusCode >= http.StatusOK &&
		rw.statusCode < http.StatusMultipleChoices {
		h.forgetSession(sessionID)
	}
}

// Close stops background review watches owned by this handler.
func (h *StreamableHandler) Close() {
	if h == nil {
		return
	}

	h.mu.Lock()
	server := h.server
	h.sessionLogins = make(map[string]string)
	h.mu.Unlock()

	if server != nil {
		for session := range server.Sessions() {
			session.Close()
		}
	}
	if h.watchManager != nil {
		h.watchManager.Close()
	}
}

// BuildStreamableHandler returns a handler that serves MCP over Streamable HTTP.
// getServer is called for new stateful MCP sessions and returns the shared
// long-lived *mcp.Server. GitHub clients are created per tool call from the
// authenticated request headers.
// inv is called to invalidate the cached token when GitHub returns HTTP 401.
func BuildStreamableHandler(db *store.DB, threshold time.Duration, inv TokenInvalidator) *StreamableHandler {
	var invalidate func(string)
	if inv != nil {
		invalidate = inv.InvalidateCachedToken
	}
	watchManager := watch.NewManager(db, watch.Options{
		Threshold:       threshold,
		InvalidateToken: invalidate,
	})

	clientProvider := newGitHubClientProvider(threshold, invalidate)
	srv := mcp.NewServer(
		&mcp.Implementation{Name: "copilot-review-mcp", Version: "1.0.0"},
		&mcp.ServerOptions{SchemaCache: schemaCache},
	)
	RegisterStatusTool(srv, clientProvider, db)
	RegisterWatchTools(srv, watchManager)
	RegisterWaitTool(srv, clientProvider, db)
	RegisterRequestTool(srv, clientProvider, db)
	RegisterThreadTools(srv, clientProvider)
	RegisterCycleTool(srv, clientProvider, db)

	streamableHandler := &StreamableHandler{
		watchManager:  watchManager,
		server:        srv,
		sessionLogins: make(map[string]string),
	}

	getServer := func(r *http.Request) *mcp.Server {
		if middleware.TokenFromContext(r.Context()) == "" {
			return nil
		}
		return srv
	}
	streamableHandler.handler = mcp.NewStreamableHTTPHandler(getServer, &mcp.StreamableHTTPOptions{
		EventStore:     mcp.NewMemoryEventStore(nil),
		SessionTimeout: defaultStreamableSessionTimeout,
		// DisableLocalhostProtection is opt-in via MCP_DISABLE_LOCALHOST_PROTECTION=true.
		// Enable when the server runs behind a reverse proxy or inside a Docker network.
		DisableLocalhostProtection: os.Getenv("MCP_DISABLE_LOCALHOST_PROTECTION") == "true",
	})
	return streamableHandler
}

func (h *StreamableHandler) rememberSession(sessionID, login string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.sessionLogins[sessionID] = login
}

func (h *StreamableHandler) forgetSession(sessionID string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	delete(h.sessionLogins, sessionID)
}

func (h *StreamableHandler) authorizeSession(sessionID, login string) bool {
	h.mu.Lock()
	defer h.mu.Unlock()

	expected, ok := h.sessionLogins[sessionID]
	return !ok || expected == login
}

type statusCaptureResponseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (w *statusCaptureResponseWriter) WriteHeader(statusCode int) {
	w.statusCode = statusCode
	w.ResponseWriter.WriteHeader(statusCode)
}

func (w *statusCaptureResponseWriter) Write(p []byte) (int, error) {
	if w.statusCode == 0 {
		w.WriteHeader(http.StatusOK)
	}
	return w.ResponseWriter.Write(p)
}

func (w *statusCaptureResponseWriter) Unwrap() http.ResponseWriter {
	return w.ResponseWriter
}
