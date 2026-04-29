package register

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

type fakeRunner struct {
	output string
	calls  []string
}

func (r *fakeRunner) Run(_ context.Context, name string, args ...string) (string, error) {
	r.calls = append(r.calls, shellish(append([]string{name}, args...)))
	return r.output, nil
}

func TestCopilotRegisterRemovesExistingBeforeAdd(t *testing.T) {
	runner := &fakeRunner{output: "  github (http)\n"}
	agent := NewCopilotAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}})
	if err != nil {
		t.Fatal(err)
	}

	got := strings.Join(runner.calls, "\n")
	for _, want := range []string{
		"gh copilot -- mcp list",
		"gh copilot -- mcp remove github",
		"gh copilot -- mcp add --transport http github http://127.0.0.1:8080/mcp/github",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("calls =\n%s\nmissing %q", got, want)
		}
	}
}

func TestCodexRegisterOverwritesWithoutList(t *testing.T) {
	runner := &fakeRunner{}
	agent := NewCodexAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{
		Name:     "cloudflare-api",
		URL:      "https://mcp.cloudflare.com/mcp",
		TokenEnv: "CLOUDFLARE_API_TOKEN",
	}})
	if err != nil {
		t.Fatal(err)
	}

	got := strings.Join(runner.calls, "\n")
	if strings.Contains(got, "codex mcp list") {
		t.Fatalf("codex should not list before add, calls =\n%s", got)
	}
	want := "codex mcp add cloudflare-api --url https://mcp.cloudflare.com/mcp --bearer-token-env-var CLOUDFLARE_API_TOKEN"
	if !strings.Contains(got, want) {
		t.Fatalf("calls =\n%s\nmissing %q", got, want)
	}
}

func TestClaudeSkipsTokenEnvServer(t *testing.T) {
	runner := &fakeRunner{}
	agent := NewClaudeAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{
		Name:     "cloudflare-api",
		URL:      "https://mcp.cloudflare.com/mcp",
		TokenEnv: "CLOUDFLARE_API_TOKEN",
	}})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "skipped") {
		t.Fatalf("output = %q, want skipped message", out.String())
	}
}
