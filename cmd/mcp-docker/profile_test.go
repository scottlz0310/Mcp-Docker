package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/v2/internal/profile"
	"github.com/scottlz0310/mcp-docker/v2/internal/register"
)

var profileTestServers = []register.Server{
	{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
	{Name: "review-raven", URL: "http://127.0.0.1:8080/mcp/review-raven"},
	{Name: "thread-owl", URL: "http://127.0.0.1:8080/mcp/thread-owl"},
}

func mustParseProfile(t *testing.T, data string) *profile.Profile {
	t.Helper()
	p, err := profile.Parse([]byte(data))
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func namesOf(servers []register.Server) []string {
	names := make([]string, 0, len(servers))
	for _, server := range servers {
		names = append(names, server.Name)
	}
	return names
}

func TestResolveProfile(t *testing.T) {
	dir := t.TempDir()
	write := func(name, data string) string {
		path := filepath.Join(dir, name)
		if err := os.WriteFile(path, []byte(data), 0o600); err != nil {
			t.Fatal(err)
		}
		return path
	}
	valid := write("valid.yml", "version: 1\nagents:\n  codex: [thread-owl]\n")
	unknownAgent := write("unknown-agent.yml", "version: 1\nagents:\n  cursor: [thread-owl]\n")
	unknownServer := write("unknown-server.yml", "version: 1\nagents:\n  codex: [playwright]\n")
	broken := write("broken.yml", "version: 2\nagents:\n  codex: [thread-owl]\n")
	missing := filepath.Join(dir, "missing.yml")

	tests := []struct {
		name     string
		path     string
		explicit bool
		wantNil  bool
		wantErr  string
	}{
		{name: "宣言を読める", path: valid},
		{name: "既定のパスにファイルが無ければ、使わない", path: missing, wantNil: true},
		{name: "明示したファイルが無ければ、エラー", path: missing, explicit: true, wantErr: "プロファイル:"},
		{name: "不明なエージェントは、エラー", path: unknownAgent, wantErr: "不明なエージェント"},
		{name: "定義にないサーバー（誤記、無効化したサーバー）は、エラー", path: unknownServer, wantErr: `定義にない MCP サーバー "playwright"`},
		{name: "不正な内容は、エラー", path: broken, wantErr: "version は 1"},
		{name: "既定のパスでも、不正な内容は握りつぶさない", path: broken, explicit: false, wantErr: "version は 1"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := resolveProfile(tt.path, tt.explicit, allAgentNames, namesOf(profileTestServers))
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("resolveProfile() error = %v, want %q を含むエラー", err, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("resolveProfile() error = %v", err)
			}
			if (got == nil) != tt.wantNil {
				t.Fatalf("resolveProfile() = %v, wantNil %v", got, tt.wantNil)
			}
		})
	}
}

func TestServersForAgent(t *testing.T) {
	prof := mustParseProfile(t, "version: 1\nagents:\n  codex: [thread-owl, review-raven]\n  claude: []\n")
	chosen := []register.Server{profileTestServers[0]}

	tests := []struct {
		name     string
		agent    string
		explicit bool
		prof     *profile.Profile
		want     []string
	}{
		{name: "宣言のある agent は、宣言されたサーバーだけ（宣言の順）", agent: "codex", prof: prof, want: []string{"thread-owl", "review-raven"}},
		{name: "何も登録しない宣言", agent: "claude", prof: prof, want: []string{}},
		{name: "宣言のない agent は、全サーバー（従来どおり）", agent: "copilot", prof: prof, want: []string{"github", "review-raven", "thread-owl"}},
		{name: "プロファイルが無ければ、全サーバー（従来どおり）", agent: "codex", prof: nil, want: []string{"github", "review-raven", "thread-owl"}},
		{name: "--server の指定は、プロファイルより優先する", agent: "codex", explicit: true, prof: prof, want: []string{"github"}},
		{name: "--server の指定は、宣言のない agent にも同じ", agent: "copilot", explicit: true, prof: prof, want: []string{"github"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := namesOf(serversForAgent(tt.agent, profileTestServers, chosen, tt.explicit, tt.prof))
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("serversForAgent() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestKeepForAgent(t *testing.T) {
	prof := mustParseProfile(t, "version: 1\nagents:\n  codex: [thread-owl]\n  claude: []\n")

	tests := []struct {
		name       string
		agent      string
		registered []register.Server
		prof       *profile.Profile
		want       []string
	}{
		{name: "宣言のある agent は、宣言だけを残す", agent: "codex", registered: []register.Server{profileTestServers[2]}, prof: prof, want: []string{"thread-owl"}},
		{name: "今回登録するサーバーも残す（登録した直後に、prune で消さない）", agent: "codex", registered: []register.Server{profileTestServers[0]}, prof: prof, want: []string{"github", "thread-owl"}},
		{name: "何も登録しない宣言は、何も残さない", agent: "claude", registered: nil, prof: prof, want: []string{}},
		{name: "宣言のない agent は、定義の全サーバーを残す（従来どおり）", agent: "copilot", registered: nil, prof: prof, want: []string{"github", "review-raven", "thread-owl"}},
		{name: "プロファイルが無ければ、定義の全サーバーを残す（従来どおり）", agent: "codex", registered: nil, prof: nil, want: []string{"github", "review-raven", "thread-owl"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := namesOf(keepForAgent(tt.agent, profileTestServers, tt.registered, tt.prof))
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("keepForAgent() = %v, want %v", got, tt.want)
			}
		})
	}
}

// プロファイルのある agent の prune は、gateway 配下で、プロファイルにない登録を削除候補にする。
// gateway 配下ではない登録（stdio、claude.ai のコネクタ、他の URL）は、候補にしない。
func TestPruneCandidatesWithProfile(t *testing.T) {
	origins := []string{"http://127.0.0.1:8080/"}
	existing := []register.Entry{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
		{Name: "review-raven", URL: "http://127.0.0.1:8080/mcp/review-raven"},
		{Name: "thread-owl", URL: "http://127.0.0.1:8080/mcp/thread-owl"},
		{Name: "old-route", URL: "http://127.0.0.1:8080/mcp/old-route"},
		{Name: "playwright", URL: ""},
		{Name: "claude-ai-connector", URL: "https://mcp.example.com/mcp"},
	}
	prof := mustParseProfile(t, "version: 1\nagents:\n  codex: [thread-owl, review-raven]\n")

	tests := []struct {
		name       string
		agent      string
		registered []register.Server
		wantStale  []string
	}{
		{
			name:       "プロファイルにない gateway 配下の登録と、定義にない登録が候補になる",
			agent:      "codex",
			registered: []register.Server{profileTestServers[1], profileTestServers[2]},
			wantStale:  []string{"github", "old-route"},
		},
		{
			name:       "宣言のない agent は、従来どおり、定義にない登録だけが候補になる",
			agent:      "copilot",
			registered: profileTestServers,
			wantStale:  []string{"old-route"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			keep := keepForAgent(tt.agent, profileTestServers, tt.registered, prof)
			var got []string
			for _, entry := range register.StaleEntries(existing, keep, origins) {
				got = append(got, entry.Name)
			}
			if !reflect.DeepEqual(got, tt.wantStale) {
				t.Fatalf("stale = %v, want %v", got, tt.wantStale)
			}
		})
	}
}

func writeRegisterFixtures(t *testing.T, profileYAML string) (composePath, externalPath, profilePath string) {
	t.Helper()
	dir := t.TempDir()
	composePath = filepath.Join(dir, "docker-compose.yml")
	externalPath = filepath.Join(dir, "mcp-external.yml")
	profilePath = filepath.Join(dir, "mcp-profiles.yml")
	compose := `services:
  mcp-gateway:
    environment:
      ROUTE_GITHUB: /mcp/github|http://github-mcp:8082
      ROUTE_REVIEW_RAVEN: /mcp/review-raven|http://review-raven:8084
      ROUTE_THREAD_OWL: /mcp/thread-owl|http://thread-owl:3000/mcp
`
	files := map[string]string{composePath: compose, externalPath: "servers: []\n", profilePath: profileYAML}
	for path, data := range files {
		if err := os.WriteFile(path, []byte(data), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return composePath, externalPath, profilePath
}

// 登録の計画は、agent ごとのセクションに分かれる。そのセクションの本文を返す。
func planSection(t *testing.T, output, agent string) string {
	t.Helper()
	header := agent + " の dry-run 計画:"
	_, rest, ok := strings.Cut(output, header)
	if !ok {
		t.Fatalf("%q の計画がありません: %s", agent, output)
	}
	for _, other := range allAgentNames {
		if other == agent {
			continue
		}
		if before, _, found := strings.Cut(rest, other+" の dry-run 計画:"); found {
			rest = before
		}
	}
	return rest
}

func TestRegisterDryRunFollowsProfile(t *testing.T) {
	profileYAML := "version: 1\nagents:\n  codex: [thread-owl, review-raven]\n"

	tests := []struct {
		name       string
		extraArgs  []string
		wantCodex  []string
		avoidCodex []string
		wantClaude []string
	}{
		{
			name:       "プロファイルの agent は宣言だけ、宣言のない agent は全サーバー",
			wantCodex:  []string{"thread-owl", "review-raven"},
			avoidCodex: []string{"github"},
			wantClaude: []string{"github", "review-raven", "thread-owl"},
		},
		{
			name:       "--server の指定は、プロファイルより優先する",
			extraArgs:  []string{"--server", "github"},
			wantCodex:  []string{"github"},
			avoidCodex: []string{"thread-owl", "review-raven"},
			wantClaude: []string{"github"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			composePath, externalPath, profilePath := writeRegisterFixtures(t, profileYAML)
			args := append([]string{
				"register", "--dry-run", "--agent", "codex,claude",
				"--compose", composePath, "--external", externalPath, "--profile", profilePath,
			}, tt.extraArgs...)

			var stdout, stderr bytes.Buffer
			if err := run(context.Background(), args, &stdout, &stderr, errorReader{}); err != nil {
				t.Fatalf("run() error = %v\nstderr=%s", err, stderr.String())
			}

			codex := planSection(t, stdout.String(), "codex")
			for _, want := range tt.wantCodex {
				if !strings.Contains(codex, "mcp/"+want) {
					t.Errorf("codex の計画に %q がありません: %s", want, codex)
				}
			}
			for _, avoid := range tt.avoidCodex {
				if strings.Contains(codex, "mcp/"+avoid) {
					t.Errorf("codex の計画に %q があってはいけません: %s", avoid, codex)
				}
			}
			claude := planSection(t, stdout.String(), "claude")
			for _, want := range tt.wantClaude {
				if !strings.Contains(claude, "mcp/"+want) {
					t.Errorf("claude の計画に %q がありません: %s", want, claude)
				}
			}
		})
	}
}

func TestRegisterRejectsInvalidProfile(t *testing.T) {
	tests := []struct {
		name    string
		profile string
		wantErr string
	}{
		{name: "定義にないサーバー", profile: "version: 1\nagents:\n  codex: [thread-owll]\n", wantErr: `定義にない MCP サーバー "thread-owll"`},
		{name: "不明なエージェント", profile: "version: 1\nagents:\n  cursor: [thread-owl]\n", wantErr: "不明なエージェント"},
		{name: "version の不一致", profile: "version: 2\nagents:\n  codex: [thread-owl]\n", wantErr: "version は 1"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			composePath, externalPath, profilePath := writeRegisterFixtures(t, tt.profile)

			var stdout, stderr bytes.Buffer
			err := run(context.Background(), []string{
				"register", "--dry-run", "--agent", "codex",
				"--compose", composePath, "--external", externalPath, "--profile", profilePath,
			}, &stdout, &stderr, errorReader{})
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("run() error = %v, want %q を含むエラー", err, tt.wantErr)
			}
			if strings.Contains(stdout.String(), "dry-run 計画") {
				t.Fatalf("不正なプロファイルでは、計画を出さずに失敗するはずです: %s", stdout.String())
			}
		})
	}
}

func TestRegisterExplicitMissingProfileFails(t *testing.T) {
	composePath, externalPath, _ := writeRegisterFixtures(t, "version: 1\nagents:\n  codex: [thread-owl]\n")

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"register", "--dry-run", "--agent", "codex",
		"--compose", composePath, "--external", externalPath,
		"--profile", filepath.Join(t.TempDir(), "missing.yml"),
	}, &stdout, &stderr, errorReader{})
	if err == nil || !strings.Contains(err.Error(), "プロファイル:") {
		t.Fatalf("run() error = %v, want プロファイルのエラー", err)
	}
}

// fake の claude CLI を PATH に置く。list の出力として lines を返す（引数は見ない）。
func installFakeClaude(t *testing.T, lines []string) {
	t.Helper()
	dir := t.TempDir()
	var name, content string
	if runtime.GOOS == "windows" {
		name = "claude.bat"
		content = "@echo off\r\n"
		for _, line := range lines {
			content += "echo " + line + "\r\n"
		}
	} else {
		name = "claude"
		content = "#!/bin/sh\n"
		for _, line := range lines {
			content += "echo '" + line + "'\n"
		}
	}
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", dir+string(filepath.ListSeparator)+os.Getenv("PATH"))
}

// プロファイルのある agent の prune の dry-run は、プロファイルにない gateway 配下の登録を候補にし、
// gateway 配下ではない登録は、名前だけを一覧する。URL（認証情報を含み得る）は出力しない。
func TestRegisterDryRunPruneWithProfile(t *testing.T) {
	composePath, externalPath, profilePath := writeRegisterFixtures(t, "version: 1\nagents:\n  claude: [thread-owl]\n")
	installFakeClaude(t, []string{
		"github: http://127.0.0.1:8080/mcp/github - Connected",
		"thread-owl: http://127.0.0.1:8080/mcp/thread-owl - Connected",
		"connector: https://user:secret@mcp.example.com/mcp?access_token=abc123 - Connected",
		"stdio-srv: npx some-package - Connected",
	})

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"register", "--agent", "claude", "--dry-run", "--prune",
		"--compose", composePath, "--external", externalPath, "--profile", profilePath,
	}, &stdout, &stderr, errorReader{})
	if err != nil {
		t.Fatalf("run() error = %v\nstderr=%s", err, stderr.String())
	}

	got := stdout.String()
	_, prunePlan, ok := strings.Cut(got, "claude の stale エントリ削除計画:")
	if !ok {
		t.Fatalf("prune の計画がありません: %s", got)
	}
	if !strings.Contains(prunePlan, "- github (") {
		t.Errorf("プロファイルにない gateway 配下の github が、削除候補になっていません: %s", prunePlan)
	}
	if strings.Contains(prunePlan, "thread-owl") {
		t.Errorf("プロファイルにある thread-owl が、削除候補になっています: %s", prunePlan)
	}
	for _, want := range []string{"claude の管理対象外の登録", "- connector", "- stdio-srv"} {
		if !strings.Contains(got, want) {
			t.Errorf("出力に %q がありません: %s", want, got)
		}
	}
	for _, secret := range []string{"secret", "access_token", "mcp.example.com"} {
		if strings.Contains(got, secret) {
			t.Errorf("出力に、管理対象外の登録の URL（認証情報を含み得る）の一部 %q が出ています: %s", secret, got)
		}
	}
}
