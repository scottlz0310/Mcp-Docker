package register

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

type fakeAgent struct {
	name    string
	entries []Entry
	removed []string
}

func (f *fakeAgent) Name() string { return f.name }

func (f *fakeAgent) ListEntries(context.Context) ([]Entry, error) { return f.entries, nil }

func (f *fakeAgent) Add(context.Context, Server) error { return nil }

func (f *fakeAgent) Remove(_ context.Context, name string) error {
	f.removed = append(f.removed, name)
	return nil
}

func (f *fakeAgent) OverwritesOnAdd() bool { return true }

func (f *fakeAgent) AddCommand(s Server) []string { return []string{"add", s.Name} }

func (f *fakeAgent) RemoveCommand(name string) []string { return []string{"remove", name} }

func TestStaleEntries(t *testing.T) {
	available := []Server{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}}
	defaultOrigins := []string{"http://127.0.0.1:8080/"}

	cases := []struct {
		name    string
		entries []Entry
		origins []string
		want    []string
	}{
		{
			name:    "計画内のエントリは候補外",
			entries: []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
			want:    nil,
		},
		{
			name:    "gateway 配下で計画外なら候補",
			entries: []Entry{{Name: "cloudflare", URL: "http://127.0.0.1:8080/${CLOUDFLARE_API_TOKEN:+/mcp/cloudflare"}},
			want:    []string{"cloudflare"},
		},
		{
			name:    "gateway 配下以外の URL は候補外",
			entries: []Entry{{Name: "personal", URL: "https://example.com/mcp"}},
			want:    nil,
		},
		{
			name:    "URL 不明のエントリは候補外",
			entries: []Entry{{Name: "stdio-server"}},
			want:    nil,
		},
		{
			name: "複数候補は登録順を保持",
			entries: []Entry{
				{Name: "old-a", URL: "http://127.0.0.1:8080/mcp/old-a"},
				{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
				{Name: "old-b", URL: "http://127.0.0.1:8080/mcp/old-b"},
			},
			want: []string{"old-a", "old-b"},
		},
		{
			name:    "TLS 切替後も旧 origin のエントリを候補にする",
			entries: []Entry{{Name: "old-http", URL: "http://127.0.0.1:8080/mcp/old-http"}},
			origins: []string{"https://localhost:8080/", "http://127.0.0.1:8080/"},
			want:    []string{"old-http"},
		},
		{
			name:    "どの origin にも一致しない URL は候補外",
			entries: []Entry{{Name: "other-host", URL: "http://192.168.0.10:8080/mcp/other"}},
			origins: []string{"https://localhost:8080/", "http://127.0.0.1:8080/"},
			want:    nil,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			origins := tc.origins
			if origins == nil {
				origins = defaultOrigins
			}
			stale := StaleEntries(tc.entries, available, origins)
			got := make([]string, 0, len(stale))
			for _, entry := range stale {
				got = append(got, entry.Name)
			}
			if len(got) != len(tc.want) {
				t.Fatalf("stale = %v, want %v", got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Fatalf("stale = %v, want %v", got, tc.want)
				}
			}
		})
	}
}

func TestPruneRemovesEntriesInOrder(t *testing.T) {
	agent := &fakeAgent{name: "claude"}
	var out bytes.Buffer

	err := Prune(context.Background(), &out, agent, []Entry{
		{Name: "old-a", URL: "http://127.0.0.1:8080/mcp/old-a"},
		{Name: "old-b", URL: "http://127.0.0.1:8080/mcp/old-b"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(agent.removed) != 2 || agent.removed[0] != "old-a" || agent.removed[1] != "old-b" {
		t.Fatalf("removed = %v, want [old-a old-b]", agent.removed)
	}
	if !strings.Contains(out.String(), "old-a: http://127.0.0.1:8080/mcp/old-a を削除します") {
		t.Fatalf("output = %q, want delete message", out.String())
	}
}

func TestPrintPrunePlan(t *testing.T) {
	agent := &fakeAgent{name: "claude"}
	var out bytes.Buffer

	PrintPrunePlan(&out, agent, []Entry{{Name: "old-a", URL: "http://127.0.0.1:8080/mcp/old-a"}})

	got := out.String()
	for _, want := range []string{
		"claude の stale エントリ削除計画:",
		"old-a (http://127.0.0.1:8080/mcp/old-a)",
		"削除: remove old-a",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("plan =\n%s\nmissing %q", got, want)
		}
	}
	if len(agent.removed) != 0 {
		t.Fatalf("plan must not remove entries, removed = %v", agent.removed)
	}
}

// keep が定義の全サーバーより小さくても（プロファイルの宣言）、keep に無い gateway 配下の登録だけが候補になる。
func TestStaleEntriesWithSubsetKeep(t *testing.T) {
	keep := []Server{{Name: "thread-owl", URL: "http://127.0.0.1:8080/mcp/thread-owl"}}
	origins := []string{"http://127.0.0.1:8080/"}
	entries := []Entry{
		{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
		{Name: "thread-owl", URL: "http://127.0.0.1:8080/mcp/thread-owl"},
		{Name: "playwright", URL: ""},
		{Name: "other", URL: "https://mcp.example.com/mcp"},
	}

	stale := StaleEntries(entries, keep, origins)

	if len(stale) != 1 || stale[0].Name != "github" {
		t.Fatalf("stale = %v, want [github]", stale)
	}
}

func TestUnmanagedEntries(t *testing.T) {
	origins := []string{"http://127.0.0.1:8080/"}
	cases := []struct {
		name    string
		entries []Entry
		want    []string
	}{
		{
			name: "gateway 配下ではない登録と、URL を特定できない登録",
			entries: []Entry{
				{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"},
				{Name: "stdio-server", URL: ""},
				{Name: "connector", URL: "https://mcp.example.com/mcp"},
			},
			want: []string{"stdio-server", "connector"},
		},
		{
			name:    "すべて gateway 配下なら、空",
			entries: []Entry{{Name: "github", URL: "http://127.0.0.1:8080/mcp/github"}},
			want:    nil,
		},
		{name: "登録なし", entries: nil, want: nil},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var got []string
			for _, entry := range UnmanagedEntries(tc.entries, origins) {
				got = append(got, entry.Name)
			}
			if strings.Join(got, ",") != strings.Join(tc.want, ",") {
				t.Fatalf("UnmanagedEntries() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestPrintUnmanaged(t *testing.T) {
	cases := []struct {
		name    string
		entries []Entry
		want    []string
		wantNot string
	}{
		{
			name:    "URL の有無にかかわらず一覧し、削除しないと明記する",
			entries: []Entry{{Name: "stdio-server"}, {Name: "connector", URL: "https://mcp.example.com/mcp"}},
			want: []string{
				"claude の管理対象外の登録（gateway 配下ではないため、削除しません）:",
				"- stdio-server",
				"- connector (https://mcp.example.com/mcp)",
			},
		},
		{name: "登録がなければ、何も表示しない", entries: nil, wantNot: "管理対象外"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			agent := &fakeAgent{name: "claude"}
			var out bytes.Buffer

			PrintUnmanaged(&out, agent, tc.entries)

			got := out.String()
			for _, want := range tc.want {
				if !strings.Contains(got, want) {
					t.Fatalf("output =\n%s\nmissing %q", got, want)
				}
			}
			if tc.wantNot != "" && strings.Contains(got, tc.wantNot) {
				t.Fatalf("output = %q, must not contain %q", got, tc.wantNot)
			}
			if len(agent.removed) != 0 {
				t.Fatalf("must not remove entries, removed = %v", agent.removed)
			}
		})
	}
}
