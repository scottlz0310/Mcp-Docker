package register

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
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

func TestAntigravityRegister(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "antigravity-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(tmpDir) }()

	configPath := filepath.Join(tmpDir, "mcp_config.json")
	agent := AntigravityAgent{
		baseAgent:  baseAgent{name: "antigravity", runner: &fakeRunner{}},
		configPath: configPath,
	}

	// 1. List when file does not exist
	names, err := listNames(agent)
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 0 {
		t.Errorf("expected empty list for non-existing file, got %v", names)
	}

	// 2. Pre-create config with other keys to test preservation
	initialJSON := `{
  "colorScheme": "dark",
  "editor": "code",
  "mcpServers": {
    "existing-server": {
      "serverUrl": "http://127.0.0.1:9090"
    }
  }
}`
	if err := os.WriteFile(configPath, []byte(initialJSON), 0644); err != nil {
		t.Fatal(err)
	}

	// 3. Add a new server
	err = agent.Add(context.Background(), Server{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"})
	if err != nil {
		t.Fatal(err)
	}

	// 4. Verify list contains both servers
	names, err = listNames(agent)
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 2 {
		t.Errorf("expected 2 servers, got %d: %v", len(names), names)
	}
	hasGithub := false
	hasExisting := false
	for _, n := range names {
		if n == "github" {
			hasGithub = true
		}
		if n == "existing-server" {
			hasExisting = true
		}
	}
	if !hasGithub || !hasExisting {
		t.Errorf("missing expected servers in list: %v", names)
	}

	// 5. Verify other keys (colorScheme, editor) were preserved
	content, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	var finalConfig map[string]any
	if err := json.Unmarshal(content, &finalConfig); err != nil {
		t.Fatal(err)
	}
	if finalConfig["colorScheme"] != "dark" || finalConfig["editor"] != "code" {
		t.Errorf("lost other top-level keys: %s", string(content))
	}

	// 6. Test Remove and ensure key preservation
	err = agent.Remove(context.Background(), "github")
	if err != nil {
		t.Fatal(err)
	}
	names, err = listNames(agent)
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 1 || names[0] != "existing-server" {
		t.Errorf("expected only existing-server, got %v", names)
	}
	content, err = os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	var configAfterRemove map[string]any
	if err := json.Unmarshal(content, &configAfterRemove); err != nil {
		t.Fatal(err)
	}
	if configAfterRemove["colorScheme"] != "dark" || configAfterRemove["editor"] != "code" {
		t.Errorf("lost other top-level keys after remove: %s", string(content))
	}
}

func TestAntigravityErrorPaths(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "antigravity-test-errors-*")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(tmpDir) }()

	configPath := filepath.Join(tmpDir, "mcp_config.json")
	agent := AntigravityAgent{
		baseAgent:  baseAgent{name: "antigravity", runner: &fakeRunner{}},
		configPath: configPath,
	}

	// 1. Invalid JSON file
	if err := os.WriteFile(configPath, []byte("invalid-json"), 0644); err != nil {
		t.Fatal(err)
	}

	// List should error
	_, err = listNames(agent)
	if err == nil {
		t.Error("expected error from List with invalid JSON")
	}

	// Add should error
	err = agent.Add(context.Background(), Server{Name: "github", URL: "http://127.0.0.1:8080"})
	if err == nil {
		t.Error("expected error from Add with invalid JSON")
	}

	// Remove should error
	err = agent.Remove(context.Background(), "github")
	if err == nil {
		t.Error("expected error from Remove with invalid JSON")
	}

	// 2. Test AddCommand and RemoveCommand outputs
	cmdAdd := agent.AddCommand(Server{Name: "github", URL: "http://127.0.0.1:8080"})
	if len(cmdAdd) < 5 || cmdAdd[2] != "add" || cmdAdd[3] != "github" {
		t.Errorf("unexpected AddCommand output: %v", cmdAdd)
	}

	cmdRemove := agent.RemoveCommand("github")
	if len(cmdRemove) < 4 || cmdRemove[2] != "remove" || cmdRemove[3] != "github" {
		t.Errorf("unexpected RemoveCommand output: %v", cmdRemove)
	}
}

func TestNewAntigravityAgentAndRegister(t *testing.T) {
	// 1. Test constructor and interface methods
	runner := &fakeRunner{}
	agent := NewAntigravityAgent(runner)
	if agent.Name() != "antigravity" {
		t.Errorf("expected name antigravity, got %q", agent.Name())
	}
	if !agent.OverwritesOnAdd() {
		t.Error("expected OverwritesOnAdd to be true")
	}

	// 2. Test Register integration
	tmpDir, err := os.MkdirTemp("", "antigravity-register-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(tmpDir) }()

	configPath := filepath.Join(tmpDir, "mcp_config.json")

	testAgent := AntigravityAgent{
		baseAgent:  baseAgent{name: "antigravity", runner: runner},
		configPath: configPath,
	}

	servers := []Server{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
		{Name: "playwright", URL: "http://127.0.0.1:8080/mcp/playwright"},
	}

	var out bytes.Buffer
	err = Register(context.Background(), &out, testAgent, servers, nil)
	if err != nil {
		t.Fatal(err)
	}

	names, err := listNames(testAgent)
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 2 {
		t.Errorf("expected 2 servers, got %v", names)
	}
}

func TestAntigravityMcpServersNotObject(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "antigravity-non-obj-*")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(tmpDir) }()

	configPath := filepath.Join(tmpDir, "mcp_config.json")
	agent := AntigravityAgent{
		baseAgent:  baseAgent{name: "antigravity", runner: &fakeRunner{}},
		configPath: configPath,
	}

	// 1. mcpServers is a string, not an object
	invalidJSON := `{"mcpServers": "not-an-object"}`
	if err := os.WriteFile(configPath, []byte(invalidJSON), 0644); err != nil {
		t.Fatal(err)
	}

	// List should return nil, nil (not crash or fail)
	names, err := listNames(agent)
	if err != nil {
		t.Fatalf("List returned error when mcpServers is not an object: %v", err)
	}
	if len(names) != 0 {
		t.Errorf("expected 0 names, got %v", names)
	}

	// Add should overwrite it or handle it cleanly
	err = agent.Add(context.Background(), Server{Name: "github", URL: "http://127.0.0.1:8080"})
	if err != nil {
		t.Fatalf("Add failed when mcpServers is not an object: %v", err)
	}

	names, err = listNames(agent)
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 1 || names[0] != "github" {
		t.Errorf("expected [github], got %v", names)
	}
}

func TestAntigravitySafeWriteFileErrors(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "antigravity-write-error-*")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(tmpDir) }()

	filePath := filepath.Join(tmpDir, "some-file")
	if err := os.WriteFile(filePath, []byte("hello"), 0644); err != nil {
		t.Fatal(err)
	}

	badConfigPath := filepath.Join(filePath, "mcp_config.json")
	agent := AntigravityAgent{
		baseAgent:  baseAgent{name: "antigravity", runner: &fakeRunner{}},
		configPath: badConfigPath,
	}

	err = agent.Add(context.Background(), Server{Name: "github", URL: "http://127.0.0.1:8080"})
	if err == nil {
		t.Error("expected error when directory creation fails")
	}
}

func TestAntigravityAgent_DefaultConfigPath(t *testing.T) {
	agent := AntigravityAgent{
		baseAgent: baseAgent{name: "antigravity", runner: &fakeRunner{}},
	}
	path, err := agent.getConfigPath()
	if err != nil {
		t.Fatalf("getConfigPath failed: %v", err)
	}
	home, err := os.UserHomeDir()
	if err != nil {
		t.Fatal(err)
	}
	expected := filepath.Join(home, ".gemini", "config", "mcp_config.json")
	if path != expected {
		t.Errorf("expected config path %q, got %q", expected, path)
	}
}
