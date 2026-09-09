package skill

import (
	"fmt"
	"sort"
	"strings"
	"testing"
	"testing/fstest"
)

func testCatalogFS() fstest.MapFS {
	return fstest.MapFS{
		"skills/alpha/SKILL.md":               {Data: []byte("alpha skill\n")},
		"skills/alpha/agents/openai.yaml":     {Data: []byte("interface: {}\n")},
		"skills/beta/SKILL.md":                {Data: []byte("beta skill\n")},
		"skills/beta/references/notes.md":     {Data: []byte("notes\n")},
		"skills/.hidden/SKILL.md":             {Data: []byte("hidden\n")},
		"skills/alpha/.mcp-docker-skill.json": {Data: []byte("{}\n")},
		"skills/catalog.json":                 {Data: catalogJSON(map[string]int{"alpha": 3, "beta": 1})},
	}
}

// catalogJSON は revision を指定した catalog.json の中身を組み立てる。
func catalogJSON(revisions map[string]int) []byte {
	entries := make([]string, 0, len(revisions))
	names := make([]string, 0, len(revisions))
	for name := range revisions {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		entries = append(entries, fmt.Sprintf("%q: {\"revision\": %d}", name, revisions[name]))
	}
	return fmt.Appendf(nil, "{\"skills\": {%s}}\n", strings.Join(entries, ", "))
}

func TestLoadCatalog(t *testing.T) {
	skills, err := LoadCatalog(testCatalogFS(), "skills")
	if err != nil {
		t.Fatalf("LoadCatalog returned error: %v", err)
	}
	if got, want := Names(skills), []string{"alpha", "beta"}; strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("names = %v, want %v", got, want)
	}

	alpha := skills[0]
	gotPaths := make([]string, 0, len(alpha.Files))
	for _, f := range alpha.Files {
		gotPaths = append(gotPaths, f.Path)
	}
	// ドットで始まるファイル・ディレクトリは skill の内容に含めない。
	if want := "SKILL.md,agents/openai.yaml"; strings.Join(gotPaths, ",") != want {
		t.Fatalf("alpha files = %v, want %s", gotPaths, want)
	}
	if alpha.ContentHash == "" || alpha.ContentHash == skills[1].ContentHash {
		t.Fatalf("content hash must be non-empty and distinct per skill: %q / %q", alpha.ContentHash, skills[1].ContentHash)
	}
	if alpha.Revision != 3 || skills[1].Revision != 1 {
		t.Fatalf("revisions = %d / %d, want 3 / 1", alpha.Revision, skills[1].Revision)
	}
	// catalog.json は skill ディレクトリではないため配置対象に混ざらない。
	if hasFile(alpha.Files, CatalogName) {
		t.Fatalf("catalog.json must not be part of a skill: %v", gotPaths)
	}
}

func TestLoadCatalogErrors(t *testing.T) {
	tests := []struct {
		name    string
		fsys    fstest.MapFS
		root    string
		wantErr string
	}{
		{
			name:    "missing root",
			fsys:    fstest.MapFS{},
			root:    "skills",
			wantErr: "読み込みに失敗しました",
		},
		{
			name:    "no skills",
			fsys:    fstest.MapFS{"skills/README.md": {Data: []byte("x")}},
			root:    "skills",
			wantErr: "skill がありません",
		},
		{
			name:    "skill without SKILL.md",
			fsys:    fstest.MapFS{"skills/alpha/notes.md": {Data: []byte("x")}},
			root:    "skills",
			wantErr: `skill "alpha" に SKILL.md がありません`,
		},
		{
			name:    "missing catalog.json",
			fsys:    fstest.MapFS{"skills/alpha/SKILL.md": {Data: []byte("x")}},
			root:    "skills",
			wantErr: `skill カタログ "skills/catalog.json" の読み込みに失敗しました`,
		},
		{
			name: "malformed catalog.json",
			fsys: fstest.MapFS{
				"skills/alpha/SKILL.md": {Data: []byte("x")},
				"skills/catalog.json":   {Data: []byte("{\n")},
			},
			root:    "skills",
			wantErr: `skill カタログ "skills/catalog.json" の解析に失敗しました`,
		},
		{
			name: "skill missing revision",
			fsys: fstest.MapFS{
				"skills/alpha/SKILL.md": {Data: []byte("x")},
				"skills/catalog.json":   {Data: catalogJSON(map[string]int{"beta": 1})},
			},
			root:    "skills",
			wantErr: `skill "alpha" の revision が skills/catalog.json にありません`,
		},
		{
			name: "revision below one",
			fsys: fstest.MapFS{
				"skills/alpha/SKILL.md": {Data: []byte("x")},
				"skills/catalog.json":   {Data: catalogJSON(map[string]int{"alpha": 0})},
			},
			root:    "skills",
			wantErr: `skill "alpha" の revision は 1 以上である必要があります: 0`,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := LoadCatalog(tt.fsys, tt.root)
			if err == nil {
				t.Fatalf("LoadCatalog returned nil error, want %q", tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error = %q, want it to contain %q", err, tt.wantErr)
			}
		})
	}
}

func TestContentHashDetectsRename(t *testing.T) {
	files := []File{{Path: "SKILL.md", SHA256: "aaa"}}
	renamed := []File{{Path: "OTHER.md", SHA256: "aaa"}}
	if contentHash(files) == contentHash(renamed) {
		t.Fatal("content hash must change when a file is renamed")
	}
}

func TestSelect(t *testing.T) {
	skills, err := LoadCatalog(testCatalogFS(), "skills")
	if err != nil {
		t.Fatalf("LoadCatalog returned error: %v", err)
	}

	tests := []struct {
		name    string
		names   []string
		want    string
		wantErr string
	}{
		{name: "empty selects all", names: nil, want: "alpha,beta"},
		{name: "single", names: []string{"beta"}, want: "beta"},
		{name: "duplicates collapse", names: []string{"beta", "beta"}, want: "beta"},
		{name: "unknown", names: []string{"gamma"}, wantErr: `不明な skill "gamma"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Select(skills, tt.names)
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("error = %v, want it to contain %q", err, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("Select returned error: %v", err)
			}
			if joined := strings.Join(Names(got), ","); joined != tt.want {
				t.Fatalf("selected = %s, want %s", joined, tt.want)
			}
		})
	}
}
