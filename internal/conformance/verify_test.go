package conformance

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestVerifyFullModernFlow(t *testing.T) {
	const (
		token       = "gateway-token"
		resourceURI = "queue://review/queue"
	)

	triggered := make(chan struct{})
	var triggerOnce sync.Once
	var toolsListCalls int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer "+token {
			w.Header().Set("WWW-Authenticate", `Bearer realm="mcp-gateway", resource_metadata="https://gateway.example/.well-known/oauth-protected-resource"`)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		if r.Method == http.MethodGet || r.Method == http.MethodDelete {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		var request struct {
			ID     json.RawMessage            `json:"id"`
			Method string                     `json:"method"`
			Params map[string]json.RawMessage `json:"params"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Errorf("decode request: %v", err)
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		if request.Method == "initialize" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			if _, err := fmt.Fprintf(w, `{"jsonrpc":"2.0","id":%s,"error":{"code":-32022,"message":"unsupported protocol version: 2025-06-18","data":{"supported":["2026-07-28"],"requested":"2025-06-18"}}}`, request.ID); err != nil {
				t.Errorf("write legacy response: %v", err)
			}
			return
		}

		assertModernHeaders(t, r, request.Method)
		switch request.Method {
		case "server/discover":
			writeResult(t, w, request.ID, map[string]any{
				"resultType":        "complete",
				"supportedVersions": []string{ProtocolVersion},
				"capabilities":      map[string]any{"tools": map[string]any{}, "resources": map[string]any{"subscribe": true}},
			})
		case "tools/list":
			toolsListCalls++
			writeResult(t, w, request.ID, map[string]any{"resultType": "complete", "tools": []any{}})
		case "resources/list":
			writeResult(t, w, request.ID, map[string]any{
				"resultType": "complete",
				"resources":  []any{map[string]any{"uri": resourceURI, "name": "Review Queue"}},
			})
		case "resources/read":
			if got := r.Header.Get("Mcp-Name"); got != resourceURI {
				t.Errorf("Mcp-Name = %q, want %q", got, resourceURI)
			}
			writeResult(t, w, request.ID, map[string]any{
				"resultType": "complete",
				"contents":   []any{map[string]any{"uri": resourceURI, "text": "[]"}},
			})
		case "subscriptions/listen":
			w.Header().Set("Content-Type", "text/event-stream")
			w.Header().Set("X-Accel-Buffering", "no")
			w.WriteHeader(http.StatusOK)
			flusher := w.(http.Flusher)
			if _, err := fmt.Fprintf(w, "data: {\"jsonrpc\":\"2.0\",\"method\":\"notifications/subscriptions/acknowledged\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/subscriptionId\":%s},\"notifications\":{\"resourceSubscriptions\":[%q]}}}\n\n", request.ID, resourceURI); err != nil {
				t.Errorf("write acknowledgement: %v", err)
			}
			if _, err := fmt.Fprint(w, ": keep-alive\n\n"); err != nil {
				t.Errorf("write keep-alive: %v", err)
			}
			flusher.Flush()
			select {
			case <-triggered:
				if _, err := fmt.Fprintf(w, "data: {\"jsonrpc\":\"2.0\",\"method\":\"notifications/resources/updated\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/subscriptionId\":%s},\"uri\":%q}}\n\n", request.ID, resourceURI); err != nil {
					t.Errorf("write resource update: %v", err)
				}
				flusher.Flush()
			case <-r.Context().Done():
			}
		case "tools/call":
			if got := r.Header.Get("Mcp-Name"); got != "enqueue_review" {
				t.Errorf("Mcp-Name = %q, want enqueue_review", got)
			}
			triggerOnce.Do(func() { close(triggered) })
			writeResult(t, w, request.ID, map[string]any{
				"resultType": "complete",
				"isError":    false,
				"content":    []any{},
			})
		default:
			t.Errorf("unexpected method: %s", request.Method)
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)

	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()
	var output bytes.Buffer
	err := Verify(ctx, Options{
		URL:                server.URL,
		Token:              token,
		ResourceURI:        resourceURI,
		RequireAuth:        true,
		RequireKeepAlive:   true,
		RequireNoBuffering: true,
		TriggerTool:        "enqueue_review",
		TriggerArguments:   map[string]any{"owner": "org", "repo": "repo", "prNumber": 1, "reason": "opened"},
		Output:             &output,
	})
	if err != nil {
		t.Fatalf("Verify() error = %v", err)
	}
	if toolsListCalls != 2 {
		t.Fatalf("tools/list calls = %d, want 2", toolsListCalls)
	}
	for _, expected := range []string{
		"未認証リクエストは Bearer challenge 付き 401 で拒否",
		"legacy initialize は 400 / -32022 で拒否",
		"idle中のSSE keep-alive commentが到達",
		"resources/updated の subscriptionId を検証し resource を再read",
	} {
		if !strings.Contains(output.String(), expected) {
			t.Errorf("output does not contain %q:\n%s", expected, output.String())
		}
	}
}

func TestVerifyRejectsNonConformantServer(t *testing.T) {
	tests := []struct {
		name        string
		behavior    conformanceServerBehavior
		resourceURI string
		wantError   string
	}{
		{name: "session header", behavior: conformanceServerBehavior{sessionOnDiscovery: true}, wantError: "Mcp-Session-Idが発行されました"},
		{name: "GET accepted", behavior: conformanceServerBehavior{acceptGET: true}, wantError: "GET status = 200, want 405"},
		{name: "DELETE accepted", behavior: conformanceServerBehavior{acceptDELETE: true}, wantError: "DELETE status = 200, want 405"},
		{name: "legacy initialize accepted", behavior: conformanceServerBehavior{acceptLegacy: true}, wantError: "legacy initialize: status = 200, want 400"},
		{name: "subscription ID mismatch", behavior: conformanceServerBehavior{mismatchedSubscriptionID: true}, resourceURI: "queue://review/queue", wantError: "subscriptionId = 999999"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := newConformanceTestServer(t, tt.behavior)
			err := Verify(t.Context(), Options{
				URL:                server.URL,
				ResourceURI:        tt.resourceURI,
				RequireNoBuffering: tt.resourceURI != "",
			})
			if err == nil || !strings.Contains(err.Error(), tt.wantError) {
				t.Fatalf("Verify() error = %v, want containing %q", err, tt.wantError)
			}
		})
	}
}

func TestVerifyNoBufferingRequirementIsOptIn(t *testing.T) {
	tests := []struct {
		name               string
		requireNoBuffering bool
		wantError          bool
	}{
		{name: "direct endpoint", requireNoBuffering: false, wantError: false},
		{name: "gateway deployment contract", requireNoBuffering: true, wantError: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := newConformanceTestServer(t, conformanceServerBehavior{omitNoBuffering: true})
			err := Verify(t.Context(), Options{
				URL:                server.URL,
				ResourceURI:        "queue://review/queue",
				RequireNoBuffering: tt.requireNoBuffering,
			})
			if tt.wantError {
				if err == nil || !strings.Contains(err.Error(), "X-Accel-Buffering") {
					t.Fatalf("Verify() error = %v, want X-Accel-Buffering error", err)
				}
				return
			}
			if err != nil {
				t.Fatalf("Verify() error = %v", err)
			}
		})
	}
}

func TestVerifyRejectsDiscoveryMismatch(t *testing.T) {
	newDiscoveryServer := func(version string) *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			var request struct {
				ID json.RawMessage `json:"id"`
			}
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				t.Errorf("decode request: %v", err)
				return
			}
			writeResult(t, w, request.ID, map[string]any{
				"resultType":        "complete",
				"supportedVersions": []string{ProtocolVersion},
				"capabilities":      map[string]any{"tools": map[string]any{}},
				"instructions":      version,
			})
		}))
	}
	gateway := newDiscoveryServer("gateway")
	direct := newDiscoveryServer("direct")
	t.Cleanup(gateway.Close)
	t.Cleanup(direct.Close)

	err := Verify(t.Context(), Options{URL: gateway.URL, DirectURL: direct.URL})
	if err == nil || !strings.Contains(err.Error(), "server/discover result が一致しません") {
		t.Fatalf("Verify() error = %v, want discovery mismatch", err)
	}
}

func TestEncodeHeaderValue(t *testing.T) {
	tests := []struct {
		name  string
		value string
		want  string
	}{
		{name: "plain ASCII", value: "queue://review/queue", want: "queue://review/queue"},
		{name: "non ASCII", value: "こんにちは", want: "=?base64?" + base64.StdEncoding.EncodeToString([]byte("こんにちは")) + "?="},
		{name: "surrounding spaces", value: " padded ", want: "=?base64?" + base64.StdEncoding.EncodeToString([]byte(" padded ")) + "?="},
		{name: "sentinel", value: "=?base64?literal?=", want: "=?base64?" + base64.StdEncoding.EncodeToString([]byte("=?base64?literal?=")) + "?="},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := encodeHeaderValue(tt.value); got != tt.want {
				t.Fatalf("encodeHeaderValue(%q) = %q, want %q", tt.value, got, tt.want)
			}
		})
	}
}

type conformanceServerBehavior struct {
	sessionOnDiscovery       bool
	acceptGET                bool
	acceptDELETE             bool
	acceptLegacy             bool
	mismatchedSubscriptionID bool
	omitNoBuffering          bool
}

func newConformanceTestServer(t *testing.T, behavior conformanceServerBehavior) *httptest.Server {
	t.Helper()
	const resourceURI = "queue://review/queue"

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet || r.Method == http.MethodDelete {
			accepted := r.Method == http.MethodGet && behavior.acceptGET ||
				r.Method == http.MethodDelete && behavior.acceptDELETE
			if accepted {
				w.WriteHeader(http.StatusOK)
			} else {
				w.WriteHeader(http.StatusMethodNotAllowed)
			}
			return
		}

		var request struct {
			ID     json.RawMessage `json:"id"`
			Method string          `json:"method"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Errorf("decode request: %v", err)
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		switch request.Method {
		case "server/discover":
			if behavior.sessionOnDiscovery {
				w.Header().Set("Mcp-Session-Id", "legacy-session")
			}
			writeResult(t, w, request.ID, map[string]any{
				"resultType":        "complete",
				"supportedVersions": []string{ProtocolVersion},
				"capabilities":      map[string]any{"tools": map[string]any{}, "resources": map[string]any{"subscribe": true}},
			})
		case "initialize":
			if behavior.acceptLegacy {
				writeResult(t, w, request.ID, map[string]any{"protocolVersion": LegacyProtocolVersion})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			if _, err := fmt.Fprintf(w, `{"jsonrpc":"2.0","id":%s,"error":{"code":-32022,"message":"unsupported protocol version","data":{"supported":["2026-07-28"],"requested":"2025-06-18"}}}`, request.ID); err != nil {
				t.Errorf("write legacy response: %v", err)
			}
		case "tools/list":
			writeResult(t, w, request.ID, map[string]any{"resultType": "complete", "tools": []any{}})
		case "resources/list":
			writeResult(t, w, request.ID, map[string]any{
				"resultType": "complete",
				"resources":  []any{map[string]any{"uri": resourceURI, "name": "Review Queue"}},
			})
		case "resources/read":
			writeResult(t, w, request.ID, map[string]any{
				"resultType": "complete",
				"contents":   []any{map[string]any{"uri": resourceURI, "text": "[]"}},
			})
		case "subscriptions/listen":
			w.Header().Set("Content-Type", "text/event-stream")
			if !behavior.omitNoBuffering {
				w.Header().Set("X-Accel-Buffering", "no")
			}
			w.WriteHeader(http.StatusOK)
			subscriptionID := request.ID
			if behavior.mismatchedSubscriptionID {
				subscriptionID = json.RawMessage("999999")
			}
			if _, err := fmt.Fprintf(w, "data: {\"jsonrpc\":\"2.0\",\"method\":\"notifications/subscriptions/acknowledged\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/subscriptionId\":%s},\"notifications\":{\"resourceSubscriptions\":[%q]}}}\n\n", subscriptionID, resourceURI); err != nil {
				t.Errorf("write acknowledgement: %v", err)
			}
		default:
			t.Errorf("unexpected method: %s", request.Method)
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	return server
}

func assertModernHeaders(t *testing.T, r *http.Request, method string) {
	t.Helper()
	if got := r.Header.Get("MCP-Protocol-Version"); got != ProtocolVersion {
		t.Errorf("MCP-Protocol-Version = %q, want %q", got, ProtocolVersion)
	}
	if got := r.Header.Get("Mcp-Method"); got != method {
		t.Errorf("Mcp-Method = %q, want %q", got, method)
	}
	if got := r.Header.Get("Accept"); !strings.Contains(got, "application/json") || !strings.Contains(got, "text/event-stream") {
		t.Errorf("Accept = %q", got)
	}
}

func writeResult(t *testing.T, w http.ResponseWriter, id json.RawMessage, result map[string]any) {
	t.Helper()
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"result":  result,
	}); err != nil {
		t.Errorf("encode response: %v", err)
	}
}
