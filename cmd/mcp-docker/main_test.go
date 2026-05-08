package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/tools/internal/register"
)

var errUnexpectedStdinRead = errors.New("unexpected stdin read")

type errorReader struct{}

func (errorReader) Read([]byte) (int, error) {
	return 0, errUnexpectedStdinRead
}

func TestVersionCommand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{"--version"}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if got, want := stdout.String(), "mcp-docker "+version+"\n"; got != want {
		t.Fatalf("stdout = %q, want %q", got, want)
	}
	if stderr.Len() != 0 {
		t.Fatalf("stderr = %q, want empty", stderr.String())
	}
}

func TestRegisterDryRunDoesNotPromptForRouteNames(t *testing.T) {
	dir := t.TempDir()
	composePath := filepath.Join(dir, "docker-compose.yml")
	externalPath := filepath.Join(dir, "mcp-external.yml")
	if err := os.WriteFile(composePath, []byte(`services:
  mcp-gateway:
    environment:
      ROUTE_GITHUB: /mcp/github|http://github-mcp:8082
`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(externalPath, []byte("servers: []\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"register",
		"--dry-run",
		"--compose", composePath,
		"--external", externalPath,
	}, &stdout, &stderr, errorReader{})
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	got := stdout.String()
	if strings.Contains(got, "[Enter to accept") {
		t.Fatalf("stdout = %q, dry-run should not prompt for route names", got)
	}
	if !strings.Contains(got, "claude の dry-run 計画:") {
		t.Fatalf("stdout = %q, want dry-run plan", got)
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
