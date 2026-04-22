package tools

import (
	"net/http"
	"os"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
	"github.com/scottlz0310/copilot-review-mcp/internal/watch"
)

var schemaCache = mcp.NewSchemaCache()

// TokenInvalidator is implemented by auth.Handler to clear a token from the
// validation cache when a downstream GitHub API call returns HTTP 401.
type TokenInvalidator interface {
	InvalidateCachedToken(token string)
}

// StreamableHandler serves MCP over Streamable HTTP and owns shared background state.
type StreamableHandler struct {
	handler      http.Handler
	watchManager *watch.Manager
}

// ServeHTTP proxies requests to the underlying MCP streamable handler.
func (h *StreamableHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	h.handler.ServeHTTP(w, r)
}

// Close stops background review watches owned by this handler.
func (h *StreamableHandler) Close() {
	if h == nil || h.watchManager == nil {
		return
	}
	h.watchManager.Close()
}

// BuildStreamableHandler returns a handler that serves MCP over Streamable HTTP.
// getServer is called for each request (stateless mode) to produce a fresh *mcp.Server
// bound to the caller's GitHub access token.
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

	getServer := func(r *http.Request) *mcp.Server {
		token := middleware.TokenFromContext(r.Context())
		if token == "" {
			return nil
		}
		gh := ghclient.NewClient(r.Context(), token, threshold, invalidate)
		srv := mcp.NewServer(
			&mcp.Implementation{Name: "copilot-review-mcp", Version: "1.0.0"},
			&mcp.ServerOptions{SchemaCache: schemaCache},
		)
		RegisterStatusTool(srv, gh, db)
		RegisterWatchTools(srv, watchManager)
		RegisterWaitTool(srv, gh, db)
		RegisterRequestTool(srv, gh, db)
		RegisterThreadTools(srv, gh)
		RegisterCycleTool(srv, gh, db)
		return srv
	}
	return &StreamableHandler{
		handler: mcp.NewStreamableHTTPHandler(getServer, &mcp.StreamableHTTPOptions{
			Stateless: true,
			// DisableLocalhostProtection is opt-in via MCP_DISABLE_LOCALHOST_PROTECTION=true.
			// Enable when the server runs behind a reverse proxy or inside a Docker network.
			DisableLocalhostProtection: os.Getenv("MCP_DISABLE_LOCALHOST_PROTECTION") == "true",
		}),
		watchManager: watchManager,
	}
}
