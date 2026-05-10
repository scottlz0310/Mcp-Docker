package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/v2/internal/register"
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

func TestParseSelection(t *testing.T) {
	items := []string{"claude", "copilot", "codex"}
	cases := []struct {
		name      string
		input     string
		want      []string
		wantErr   bool
		wantAbort bool
	}{
		{name: "empty means all", input: "", want: items},
		{name: "only whitespace means all", input: "   \n", want: items},
		{name: "explicit all", input: "all", want: items},
		{name: "all uppercase", input: "ALL", want: items},
		{name: "indices", input: "1,3", want: []string{"claude", "codex"}},
		{name: "names", input: "claude,codex", want: []string{"claude", "codex"}},
		{name: "mixed indices and names", input: "1,codex", want: []string{"claude", "codex"}},
		{name: "deduplicates", input: "1,1,claude", want: []string{"claude"}},
		{name: "tolerates trailing comma", input: "claude,", want: []string{"claude"}},
		{name: "abort with none", input: "none", wantAbort: true},
		{name: "abort with q", input: "q", wantAbort: true},
		{name: "out of range", input: "9", wantErr: true},
		{name: "zero is invalid", input: "0", wantErr: true},
		{name: "unknown name", input: "ghostide", wantErr: true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseSelection(tc.input, items)
			if tc.wantAbort {
				if !errors.Is(err, errAborted) {
					t.Fatalf("err = %v, want errAborted", err)
				}
				return
			}
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got %v", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !equalStringSlices(got, tc.want) {
				t.Fatalf("got %v, want %v", got, tc.want)
			}
		})
	}
}

func TestResolveSelectionRespectsAllAndCSV(t *testing.T) {
	items := []string{"github", "playwright", "copilot-review"}
	cases := []struct {
		name    string
		input   string
		want    []string
		wantErr bool
	}{
		{name: "default all", input: "all", want: items},
		{name: "single", input: "github", want: []string{"github"}},
		{name: "csv", input: "github,playwright", want: []string{"github", "playwright"}},
		{name: "indices", input: "1,3", want: []string{"github", "copilot-review"}},
		{name: "unknown", input: "nope", wantErr: true},
		{name: "empty rejected when not all", input: "  ,  ", wantErr: true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := resolveSelection(tc.input, items, "server")
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got %v", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !equalStringSlices(got, tc.want) {
				t.Fatalf("got %v, want %v", got, tc.want)
			}
		})
	}
}

func TestResolveSelectionEmptyTreatedAsAll(t *testing.T) {
	items := []string{"a", "b"}
	got, err := resolveSelection("", items, "agent")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !equalStringSlices(got, items) {
		t.Fatalf("got %v, want %v", got, items)
	}
}

func TestSelectAgentsByNamesPreservesOrderAndDeduplicates(t *testing.T) {
	specs, err := selectAgentsByNames([]string{"codex", "claude", "claude"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	gotNames := make([]string, len(specs))
	for i, s := range specs {
		gotNames[i] = s.name
	}
	want := []string{"codex", "claude"}
	if !equalStringSlices(gotNames, want) {
		t.Fatalf("got %v, want %v", gotNames, want)
	}
}

func TestSelectAgentsByNamesRejectsUnknown(t *testing.T) {
	if _, err := selectAgentsByNames([]string{"copilot", "vim"}); err == nil {
		t.Fatal("expected error for unknown agent name")
	}
}

func TestFilterServersKeepsOnlySelected(t *testing.T) {
	servers := []register.Server{
		{Name: "github"},
		{Name: "playwright"},
		{Name: "copilot-review"},
	}
	got := filterServers(servers, []string{"playwright", "copilot-review"})
	wantNames := []string{"playwright", "copilot-review"}
	gotNames := make([]string, len(got))
	for i, s := range got {
		gotNames[i] = s.Name
	}
	if !equalStringSlices(gotNames, wantNames) {
		t.Fatalf("got %v, want %v", gotNames, wantNames)
	}
}

func TestRegisterMultiAgentMultiServerDryRun(t *testing.T) {
	dir := t.TempDir()
	composePath := filepath.Join(dir, "docker-compose.yml")
	externalPath := filepath.Join(dir, "mcp-external.yml")
	if err := os.WriteFile(composePath, []byte(`services:
  mcp-gateway:
    environment:
      ROUTE_GITHUB: /mcp/github|http://github-mcp:8082
      ROUTE_COPILOT_REVIEW: /mcp/copilot-review|http://copilot-review-mcp:8084
      ROUTE_PLAYWRIGHT: /mcp/playwright|http://playwright-mcp:8086
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
		"--agent", "claude,codex",
		"--server", "github,playwright",
		"--compose", composePath,
		"--external", externalPath,
	}, &stdout, &stderr, errorReader{})
	if err != nil {
		t.Fatalf("run returned error: %v\nstderr=%s", err, stderr.String())
	}

	got := stdout.String()
	for _, want := range []string{
		"claude の dry-run 計画:",
		"codex の dry-run 計画:",
		"github",
		"playwright",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("stdout missing %q: %s", want, got)
		}
	}
	if strings.Contains(got, "copilot の dry-run 計画:") {
		t.Fatalf("copilot should not be selected: %s", got)
	}
	if strings.Contains(got, "copilot-review") {
		t.Fatalf("copilot-review server should not be selected: %s", got)
	}
}

func TestRegisterRejectsInteractiveOnNonTTY(t *testing.T) {
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
		"--interactive",
		"--compose", composePath,
		"--external", externalPath,
	}, &stdout, &stderr, strings.NewReader(""))
	if err == nil {
		t.Fatal("expected non-TTY interactive to error")
	}
	if !strings.Contains(err.Error(), "TTY") {
		t.Fatalf("error = %v, want message about TTY", err)
	}
}

func TestRegisterUnknownAgentValueErrors(t *testing.T) {
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
		"--agent", "claude,vim",
		"--compose", composePath,
		"--external", externalPath,
	}, &stdout, &stderr, errorReader{})
	if err == nil {
		t.Fatal("expected unknown agent error")
	}
	if !strings.Contains(err.Error(), "vim") {
		t.Fatalf("error = %v, want to mention unknown agent", err)
	}
}

func equalStringSlices(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
