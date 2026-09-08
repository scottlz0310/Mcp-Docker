package skill

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestClientsResolveSkillDirectories(t *testing.T) {
	home := filepath.Join("home", "user")
	want := map[string]string{
		"claude":      filepath.Join(home, ".claude", "skills"),
		"copilot":     filepath.Join(home, ".copilot", "skills"),
		"codex":       filepath.Join(home, ".codex", "skills"),
		"antigravity": filepath.Join(home, ".gemini", "antigravity-cli", "skills"),
	}

	clients := Clients(home)
	if len(clients) != len(want) {
		t.Fatalf("clients = %d, want %d", len(clients), len(want))
	}
	for _, c := range clients {
		t.Run(c.Name, func(t *testing.T) {
			if c.Dir != want[c.Name] {
				t.Fatalf("dir = %q, want %q", c.Dir, want[c.Name])
			}
		})
	}
}

func TestUserHomeHonorsOverride(t *testing.T) {
	t.Setenv("MCP_DOCKER_SKILL_HOME", filepath.Join("tmp", "isolated"))
	home, err := UserHome()
	if err != nil {
		t.Fatalf("UserHome returned error: %v", err)
	}
	if want := filepath.Join("tmp", "isolated"); home != want {
		t.Fatalf("home = %q, want %q", home, want)
	}
}

func TestSelectClients(t *testing.T) {
	clients := Clients("home")

	tests := []struct {
		name    string
		names   []string
		want    string
		wantErr string
	}{
		{name: "empty selects all", names: nil, want: "claude,copilot,codex,antigravity"},
		{name: "subset keeps request order", names: []string{"codex", "claude"}, want: "codex,claude"},
		{name: "duplicates collapse", names: []string{"claude", "claude"}, want: "claude"},
		{name: "unknown", names: []string{"cursor"}, wantErr: `不明なクライアント "cursor"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := SelectClients(clients, tt.names)
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("error = %v, want it to contain %q", err, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("SelectClients returned error: %v", err)
			}
			names := make([]string, 0, len(got))
			for _, c := range got {
				names = append(names, c.Name)
			}
			if joined := strings.Join(names, ","); joined != tt.want {
				t.Fatalf("selected = %s, want %s", joined, tt.want)
			}
		})
	}
}
