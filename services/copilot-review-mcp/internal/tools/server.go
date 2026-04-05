package tools

import (
	"net/http"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
	"github.com/scottlz0310/copilot-review-mcp/internal/middleware"
	"github.com/scottlz0310/copilot-review-mcp/internal/store"
)

var schemaCache = mcp.NewSchemaCache()

// BuildStreamableHandler returns an http.Handler that serves MCP over Streamable HTTP.
// getServer is called for each request (stateless mode) to produce a fresh *mcp.Server
// bound to the caller's GitHub access token.
func BuildStreamableHandler(db *store.DB, threshold time.Duration) http.Handler {
	getServer := func(r *http.Request) *mcp.Server {
		token := middleware.TokenFromContext(r.Context())
		if token == "" {
			return nil
		}
		gh := ghclient.NewClient(token, threshold)
		srv := mcp.NewServer(
			&mcp.Implementation{Name: "copilot-review-mcp", Version: "1.0.0"},
			&mcp.ServerOptions{SchemaCache: schemaCache},
		)
		RegisterStatusTool(srv, gh, db)
		RegisterWaitTool(srv, gh, db)
		RegisterRequestTool(srv, gh, db)
		return srv
	}
	return mcp.NewStreamableHTTPHandler(getServer, &mcp.StreamableHTTPOptions{
		Stateless: true,
		// Disable the built-in localhost DNS-rebinding protection because the
		// server may sit behind a reverse proxy or inside a Docker network.
		DisableLocalhostProtection: true,
	})
}
