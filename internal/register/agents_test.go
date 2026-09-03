package register

import (
	"bytes"
	"context"
	"slices"
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

func listNames(agent Agent) ([]string, error) {
	entries, err := agent.ListEntries(context.Background())
	if err != nil {
		return nil, err
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		names = append(names, entry.Name)
	}
	return names, nil
}

func TestParseListEntries(t *testing.T) {
	cases := []struct {
		name   string
		output string
		want   []Entry
	}{
		{
			name:   "claude 形式は名前と URL を抽出",
			output: "github: http://127.0.0.1:8080/mcp/github (HTTP) - ✓ Connected\n",
			want:   []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
		},
		{
			name:   "URL のない行は URL 空のエントリになる",
			output: "  github (http)\n",
			want:   []Entry{{Name: "github", URL: ""}},
		},
		{
			name:   "codex のテーブルヘッダーはスキップし行から URL を拾う",
			output: "Name  Transport  Url\ngithub  streamable_http  http://127.0.0.1:8080/mcp/github\n",
			want:   []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
		},
		{
			name:   "agy のテーブルヘッダーはスキップし行から URL を拾う",
			output: "NAME        TYPE  STATUS   COMMAND/URL\ngithub      http  enabled  http://127.0.0.1:8080/mcp/github\n",
			want:   []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
		},
		{
			name:   "未登録メッセージは無視",
			output: "No MCP servers configured\n",
			want:   nil,
		},
		{
			name:   "同名の行は重複排除",
			output: "github: http://127.0.0.1:8080/mcp/github (HTTP)\ngithub: http://127.0.0.1:8080/mcp/github (HTTP)\n",
			want:   []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := parseListEntries(tc.output)
			if len(got) != len(tc.want) {
				t.Fatalf("entries = %v, want %v", got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Fatalf("entries = %v, want %v", got, tc.want)
				}
			}
		})
	}
}

func TestCopilotRegisterRemovesExistingBeforeAdd(t *testing.T) {
	runner := &fakeRunner{output: "  github (http)\n"}
	agent := NewCopilotAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}}, []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}})
	if err != nil {
		t.Fatal(err)
	}

	got := strings.Join(runner.calls, "\n")
	for _, want := range []string{
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
	}}, nil)
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
	runner := &fakeRunner{output: "cloudflare-api: https://old.example (HTTP)\n"}
	agent := NewClaudeAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{
		Name:     "cloudflare-api",
		URL:      "https://mcp.cloudflare.com/mcp",
		TokenEnv: "CLOUDFLARE_API_TOKEN",
	}}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "スキップ") {
		t.Fatalf("output = %q, want skip message", out.String())
	}
	got := strings.Join(runner.calls, "\n")
	if strings.Contains(got, "remove cloudflare-api") || strings.Contains(got, "add --transport http --scope user cloudflare-api") {
		t.Fatalf("unsupported server must not be removed or added, calls =\n%s", got)
	}
}

func TestPrintPlanShowsListAndConditionalRemove(t *testing.T) {
	agent := NewCopilotAgent(&fakeRunner{})
	var out bytes.Buffer

	PrintPlan(&out, agent, []Server{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}})

	got := out.String()
	for _, want := range []string{
		"既存登録確認: gh copilot -- mcp list",
		"既存登録があれば削除: gh copilot -- mcp remove github",
		"追加: gh copilot -- mcp add --transport http github http://127.0.0.1:8080/mcp/github",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("plan =\n%s\nmissing %q", got, want)
		}
	}
}

func TestAntigravityAgentPropertiesAndCommands(t *testing.T) {
	runner := &fakeRunner{}
	agent := NewAntigravityAgent(runner)

	if agent.Name() != "antigravity" {
		t.Errorf("expected name antigravity, got %q", agent.Name())
	}
	if !agent.OverwritesOnAdd() {
		t.Error("expected OverwritesOnAdd to be true")
	}

	cmdAdd := agent.AddCommand(Server{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"})
	wantAdd := []string{"agy", "mcp", "add", "github", "http://127.0.0.1:8080/mcp/github"}
	if !slices.Equal(cmdAdd, wantAdd) {
		t.Errorf("AddCommand = %v, want %v", cmdAdd, wantAdd)
	}

	cmdRemove := agent.RemoveCommand("github")
	wantRemove := []string{"agy", "mcp", "remove", "github"}
	if !slices.Equal(cmdRemove, wantRemove) {
		t.Errorf("RemoveCommand = %v, want %v", cmdRemove, wantRemove)
	}

	cmdList := listCommand(agent)
	wantList := []string{"agy", "mcp", "list"}
	if !slices.Equal(cmdList, wantList) {
		t.Errorf("listCommand = %v, want %v", cmdList, wantList)
	}
}

func TestAntigravityAgentListEntries(t *testing.T) {
	runner := &fakeRunner{
		output: "NAME        TYPE  STATUS   COMMAND/URL\ngithub      http  enabled  http://127.0.0.1:8080/mcp/github\nplaywright  http  enabled  http://127.0.0.1:8080/mcp/playwright\n",
	}
	agent := NewAntigravityAgent(runner)

	entries, err := agent.ListEntries(context.Background())
	if err != nil {
		t.Fatalf("ListEntries failed: %v", err)
	}
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(entries))
	}
	if entries[0].Name != "github" || entries[0].URL != "http://127.0.0.1:8080/mcp/github" {
		t.Errorf("entry[0] = %+v, want github", entries[0])
	}
	if entries[1].Name != "playwright" || entries[1].URL != "http://127.0.0.1:8080/mcp/playwright" {
		t.Errorf("entry[1] = %+v, want playwright", entries[1])
	}

	if len(runner.calls) != 1 || runner.calls[0] != "agy mcp list" {
		t.Errorf("calls = %v, want [agy mcp list]", runner.calls)
	}
}

func TestAntigravityAgentRegisterOverwritesWithoutRemove(t *testing.T) {
	runner := &fakeRunner{
		output: "NAME  TYPE  STATUS  COMMAND/URL\ngithub  http  enabled  http://127.0.0.1:8080/mcp/github\n",
	}
	agent := NewAntigravityAgent(runner)
	var out bytes.Buffer

	servers := []Server{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
		{Name: "playwright", URL: "http://127.0.0.1:8080/mcp/playwright"},
	}

	err := Register(context.Background(), &out, agent, servers, nil)
	if err != nil {
		t.Fatal(err)
	}

	got := strings.Join(runner.calls, "\n")
	if strings.Contains(got, "agy mcp remove") {
		t.Fatalf("antigravity should overwrite on add and not remove, calls =\n%s", got)
	}
	for _, want := range []string{
		"agy mcp add github http://127.0.0.1:8080/mcp/github",
		"agy mcp add playwright http://127.0.0.1:8080/mcp/playwright",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("calls =\n%s\nmissing %q", got, want)
		}
	}
}

func TestAntigravityAgentRemove(t *testing.T) {
	runner := &fakeRunner{}
	agent := NewAntigravityAgent(runner)

	err := agent.Remove(context.Background(), "github")
	if err != nil {
		t.Fatal(err)
	}

	if len(runner.calls) != 1 || runner.calls[0] != "agy mcp remove github" {
		t.Errorf("calls = %v, want [agy mcp remove github]", runner.calls)
	}
}

func TestAntigravityAgentSkipsTokenEnvServer(t *testing.T) {
	runner := &fakeRunner{}
	agent := NewAntigravityAgent(runner)
	var out bytes.Buffer

	err := Register(context.Background(), &out, agent, []Server{{
		Name:     "cloudflare-api",
		URL:      "https://mcp.cloudflare.com/mcp",
		TokenEnv: "CLOUDFLARE_API_TOKEN",
	}}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "スキップ") {
		t.Fatalf("output = %q, want skip message", out.String())
	}
	got := strings.Join(runner.calls, "\n")
	if strings.Contains(got, "agy mcp add") || strings.Contains(got, "agy mcp remove") {
		t.Fatalf("unsupported server must not be added or removed, calls =\n%s", got)
	}
}

func TestPrintPlanAntigravity(t *testing.T) {
	agent := NewAntigravityAgent(&fakeRunner{})
	var out bytes.Buffer

	PrintPlan(&out, agent, []Server{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}})

	got := out.String()
	want := "追加/上書き: agy mcp add github http://127.0.0.1:8080/mcp/github"
	if !strings.Contains(got, want) {
		t.Fatalf("PrintPlan output =\n%s\nmissing %q", got, want)
	}
}
