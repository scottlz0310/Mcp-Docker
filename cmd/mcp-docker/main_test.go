package main

import (
	"bytes"
	"context"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/tools/internal/register"
)

func TestVersionCommand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{"--version"}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if got, want := stdout.String(), "mcp-docker 2.7.0\n"; got != want {
		t.Fatalf("stdout = %q, want %q", got, want)
	}
	if stderr.Len() != 0 {
		t.Fatalf("stderr = %q, want empty", stderr.String())
	}
}

func TestValidateUniqueServersReportsCollidingSources(t *testing.T) {
	err := validateUniqueServers([]register.Server{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github", Source: "ROUTE_GITHUB"},
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/copilot-review", Source: "ROUTE_COPILOT_REVIEW"},
	})
	if err == nil {
		t.Fatal("expected duplicate name error")
	}
	got := err.Error()
	for _, want := range []string{`MCP サーバー名 "github" が重複しています`, "ROUTE_GITHUB", "ROUTE_COPILOT_REVIEW"} {
		if !strings.Contains(got, want) {
			t.Fatalf("error = %q, missing %q", got, want)
		}
	}
}
