package tools

import (
	"net/http"
	"os"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

var schemaCache = mcp.NewSchemaCache()

// TokenInvalidator is implemented by auth.Handler to clear a token from the
// validation cache when a downstream GitHub API call returns HTTP 401.
type TokenInvalidator interface {
	InvalidateCachedToken(token string)
}

// BuildStreamableHandler returns an http.Handler that serves MCP over Streamable HTTP.
// getServer is called for each request (stateless mode) to produce a fresh *mcp.Server
// bound to the caller's GitHub access token.
// inv is called to invalidate the cached token when GitHub returns HTTP 401.
func BuildStreamableHandler(db *store.DB, threshold time.Duration, inv TokenInvalidator) http.Handler {
	getServer := func(r *http.Request) *mcp.Server {
		token := middleware.TokenFromContext(r.Context())
		if token == "" {
			return nil
		}
		gh := ghclient.NewClient(r.Context(), token, threshold, inv.InvalidateCachedToken)
		srv := mcp.NewServer(
			&mcp.Implementation{Name: "copilot-review-mcp", Version: "1.0.0"},
			&mcp.ServerOptions{SchemaCache: schemaCache},
		)
		RegisterStatusTool(srv, gh, db)
		RegisterWaitTool(srv, gh, db)
		RegisterRequestTool(srv, gh, db)
		RegisterThreadTools(srv, gh)
		RegisterCycleTool(srv, gh, db)
		return srv
	}
	return mcp.NewStreamableHTTPHandler(getServer, &mcp.StreamableHTTPOptions{
		Stateless: true,
		// DisableLocalhostProtection is opt-in via MCP_DISABLE_LOCALHOST_PROTECTION=true.
		// Enable when the server runs behind a reverse proxy or inside a Docker network.
		DisableLocalhostProtection: os.Getenv("MCP_DISABLE_LOCALHOST_PROTECTION") == "true",
	})
}
