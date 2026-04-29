package main

import (
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/tools/internal/register"
)

func TestValidateUniqueServersReportsCollidingSources(t *testing.T) {
	err := validateUniqueServers([]register.Server{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github", Source: "ROUTE_GITHUB"},
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/copilot-review", Source: "ROUTE_COPILOT_REVIEW"},
	})
	if err == nil {
		t.Fatal("expected duplicate name error")
	}
	got := err.Error()
	for _, want := range []string{`duplicate MCP server name "github"`, "ROUTE_GITHUB", "ROUTE_COPILOT_REVIEW"} {
		if !strings.Contains(got, want) {
			t.Fatalf("error = %q, missing %q", got, want)
		}
	}
}
