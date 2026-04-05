package middleware

import (
	"context"
	"net/http"
	"strings"

	"log/slog"
)

type contextKey string

const ContextKeyLogin contextKey = "github_login"
const ContextKeyToken contextKey = "github_token"

// TokenValidator is implemented by auth.Handler.
type TokenValidator interface {
	ValidateToken(ctx context.Context, token string) (string, error)
}

// Auth returns a middleware that validates Bearer tokens via the GitHub API.
func Auth(v TokenValidator) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			token := extractBearer(r)
			if token == "" {
				writeUnauthorized(w, "missing_token")
				return
			}

			login, err := v.ValidateToken(r.Context(), token)
			if err != nil {
				slog.Warn("auth failed", "err", err, "path", r.URL.Path)
				writeUnauthorized(w, "invalid_token")
				return
			}

			ctx := context.WithValue(r.Context(), ContextKeyLogin, login)
			ctx = context.WithValue(ctx, ContextKeyToken, token)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func writeUnauthorized(w http.ResponseWriter, errCode string) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("WWW-Authenticate", `Bearer realm="copilot-review-mcp"`)
	w.WriteHeader(http.StatusUnauthorized)
	_, _ = w.Write([]byte(`{"error":"` + errCode + `"}`))
}

func extractBearer(r *http.Request) string {
	h := r.Header.Get("Authorization")
	fields := strings.Fields(h)
	if len(fields) == 2 && strings.EqualFold(fields[0], "bearer") {
		return fields[1]
	}
	return ""
}

// TokenFromContext retrieves the GitHub token injected by Auth middleware.
func TokenFromContext(ctx context.Context) string {
	v, _ := ctx.Value(ContextKeyToken).(string)
	return v
}
