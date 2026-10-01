package profile

import (
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestParse(t *testing.T) {
	tests := []struct {
		name    string
		data    string
		want    map[string][]string
		wantErr string
	}{
		{
			name: "CLI ごとのサーバーを宣言できる",
			data: "version: 1\nagents:\n  codex: [thread-owl, review-raven]\n  claude: [github]\n",
			want: map[string][]string{"codex": {"thread-owl", "review-raven"}, "claude": {"github"}},
		},
		{
			name: "空のリストは、何も登録しない宣言として受け付ける",
			data: "version: 1\nagents:\n  claude: []\n",
			want: map[string][]string{"claude": {}},
		},
		{name: "空のファイル", data: "", wantErr: "プロファイルが空です"},
		{name: "version が無い", data: "agents:\n  codex: [thread-owl]\n", wantErr: "version は 1 を指定してください"},
		{name: "未対応の version", data: "version: 2\nagents:\n  codex: [thread-owl]\n", wantErr: "version は 1 を指定してください"},
		{name: "agents が無い", data: "version: 1\n", wantErr: "agents に少なくとも 1 つ"},
		{name: "値の無いエージェント", data: "version: 1\nagents:\n  codex:\n", wantErr: "agents.codex: サーバー名のリストを指定してください"},
		{name: "空のサーバー名", data: "version: 1\nagents:\n  codex: [\"\"]\n", wantErr: "空のサーバー名"},
		{name: "サーバー名の重複", data: "version: 1\nagents:\n  codex: [thread-owl, thread-owl]\n", wantErr: `サーバー "thread-owl" が重複`},
		{name: "未知のキー", data: "version: 1\nagent:\n  codex: [thread-owl]\n", wantErr: "field agent not found"},
		{name: "リストでない値", data: "version: 1\nagents:\n  codex: thread-owl\n", wantErr: "cannot unmarshal"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Parse([]byte(tt.data))
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("Parse() error = %v, want %q を含むエラー", err, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("Parse() error = %v", err)
			}
			if !reflect.DeepEqual(got.agents, tt.want) {
				t.Fatalf("Parse() = %v, want %v", got.agents, tt.want)
			}
		})
	}
}

func TestValidate(t *testing.T) {
	agents := []string{"claude", "codex"}
	servers := []string{"github", "review-raven", "thread-owl"}

	tests := []struct {
		name    string
		profile string
		wantErr string
	}{
		{name: "既知の名前だけ", profile: "version: 1\nagents:\n  codex: [thread-owl]\n"},
		{name: "何も登録しない宣言", profile: "version: 1\nagents:\n  claude: []\n"},
		{name: "不明なエージェント", profile: "version: 1\nagents:\n  cursor: [thread-owl]\n", wantErr: "agents.cursor: 不明なエージェント"},
		{name: "定義にないサーバー", profile: "version: 1\nagents:\n  codex: [thread-owll]\n", wantErr: `定義にない MCP サーバー "thread-owll"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p, err := Parse([]byte(tt.profile))
			if err != nil {
				t.Fatalf("Parse() error = %v", err)
			}
			err = p.Validate(agents, servers)
			if tt.wantErr == "" {
				if err != nil {
					t.Fatalf("Validate() error = %v", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("Validate() error = %v, want %q を含むエラー", err, tt.wantErr)
			}
		})
	}

	t.Run("nil のプロファイルは常に有効", func(t *testing.T) {
		var p *Profile
		if err := p.Validate(agents, servers); err != nil {
			t.Fatalf("Validate() error = %v", err)
		}
	})
}

func TestServers(t *testing.T) {
	p, err := Parse([]byte("version: 1\nagents:\n  codex: [thread-owl]\n  claude: []\n"))
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}

	tests := []struct {
		name   string
		p      *Profile
		agent  string
		want   []string
		wantOK bool
	}{
		{name: "宣言のあるエージェント", p: p, agent: "codex", want: []string{"thread-owl"}, wantOK: true},
		{name: "何も登録しない宣言も、宣言あり", p: p, agent: "claude", want: []string{}, wantOK: true},
		{name: "宣言のないエージェント", p: p, agent: "copilot", want: nil, wantOK: false},
		{name: "nil のプロファイル", p: nil, agent: "codex", want: nil, wantOK: false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := tt.p.Servers(tt.agent)
			if ok != tt.wantOK || !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("Servers(%q) = %v, %v, want %v, %v", tt.agent, got, ok, tt.want, tt.wantOK)
			}
		})
	}

	t.Run("返したリストを書き換えても、プロファイルは変わらない", func(t *testing.T) {
		got, _ := p.Servers("codex")
		got[0] = "changed"
		again, _ := p.Servers("codex")
		if again[0] != "thread-owl" {
			t.Fatalf("Servers() = %v, プロファイルが書き換わりました", again)
		}
	})
}

func TestLoad(t *testing.T) {
	dir := t.TempDir()

	t.Run("ファイルを読める", func(t *testing.T) {
		path := filepath.Join(dir, "profiles.yml")
		if err := os.WriteFile(path, []byte("version: 1\nagents:\n  codex: [thread-owl]\n"), 0o600); err != nil {
			t.Fatal(err)
		}
		p, err := Load(path)
		if err != nil {
			t.Fatalf("Load() error = %v", err)
		}
		if got, ok := p.Servers("codex"); !ok || !reflect.DeepEqual(got, []string{"thread-owl"}) {
			t.Fatalf("Servers() = %v, %v", got, ok)
		}
	})

	t.Run("ファイルが無ければ fs.ErrNotExist", func(t *testing.T) {
		_, err := Load(filepath.Join(dir, "missing.yml"))
		if !errors.Is(err, fs.ErrNotExist) {
			t.Fatalf("Load() error = %v, want fs.ErrNotExist", err)
		}
	})

	t.Run("不正な内容はパスを付けて返す", func(t *testing.T) {
		path := filepath.Join(dir, "broken.yml")
		if err := os.WriteFile(path, []byte("version: 9\nagents:\n  codex: [thread-owl]\n"), 0o600); err != nil {
			t.Fatal(err)
		}
		_, err := Load(path)
		if err == nil || !strings.Contains(err.Error(), path) {
			t.Fatalf("Load() error = %v, want パスを含むエラー", err)
		}
	})
}
