package proxy

import (
	"crypto/sha256"
	"fmt"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/scottlz0310/github-oauth-proxy/internal/middleware"
)

// TokenInvalidator is implemented by auth.Handler.
type TokenInvalidator interface {
	InvalidateCachedToken(token string)
}

// NewHandler returns an HTTP handler that reverse-proxies authenticated requests
// to the upstream MCP server. It performs header sanitization, injects the
// verified GitHub login as X-GitHub-Login, and invalidates the token cache
// when the upstream returns HTTP 401.
func NewHandler(upstream *url.URL, inv TokenInvalidator) http.Handler {
	rp := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.SetURL(upstream)

			// Remove headers that clients must not be able to spoof.
			// With Rewrite, X-Forwarded-For is not added automatically,
			// but we delete it in case the client sends it directly.
			pr.Out.Header.Del("X-Forwarded-For")
			pr.Out.Header.Del("X-Real-Ip")
			pr.Out.Header.Del("X-GitHub-Login") // delete before setting to prevent spoofing
			pr.Out.Header.Del("X-Forwarded-Host")
			pr.Out.Header.Del("X-Forwarded-Proto")

			// Inject verified user context from auth middleware.
			if login := middleware.LoginFromContext(pr.In.Context()); login != "" {
				pr.Out.Header.Set("X-GitHub-Login", login)
			}

			// Log the outbound request for audit purposes.
			// Never log the raw token value — only a short hash for correlation.
			slog.Info("proxy request",
				"login", middleware.LoginFromContext(pr.In.Context()),
				"method", pr.Out.Method,
				"path", pr.Out.URL.Path,
				"token_hash", tokenHash(middleware.TokenFromContext(pr.In.Context())),
			)
		},

		ModifyResponse: func(resp *http.Response) error {
			// If the upstream rejected the token, invalidate the cache immediately
			// so the next request triggers a fresh GitHub API validation.
			if resp.StatusCode == http.StatusUnauthorized {
				if token := extractBearer(resp.Request); token != "" {
					inv.InvalidateCachedToken(token)
					slog.Warn("upstream rejected token; cache invalidated",
						"path", resp.Request.URL.Path,
						"token_hash", tokenHash(token),
					)
				}
			}
			slog.Info("proxy response",
				"upstream_status", resp.StatusCode,
				"path", resp.Request.URL.Path,
			)
			return nil
		},
	}

	return rp
}

func extractBearer(req *http.Request) string {
	h := req.Header.Get("Authorization")
	if strings.HasPrefix(h, "Bearer ") {
		return strings.TrimPrefix(h, "Bearer ")
	}
	return ""
}

// tokenHash returns the first 8 hex characters of SHA-256(token) for log
// correlation. The raw token value must never appear in logs.
func tokenHash(token string) string {
	if token == "" {
		return ""
	}
	sum := sha256.Sum256([]byte(token))
	return fmt.Sprintf("%x", sum[:4])
}
