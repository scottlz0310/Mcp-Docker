// Package skill は skill カタログの読み込みと各 CLI クライアントへの配置を扱う。
package skill

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"
)

// ManifestName は配置先に書き出す配置メタデータのファイル名。
const ManifestName = ".mcp-docker-skill.json"

// File は skill を構成する 1 ファイル。Path は skill ディレクトリからの相対パス（slash 区切り）。
type File struct {
	Path   string
	Data   []byte
	SHA256 string
}

// Skill は 1 つの skill 定義。
type Skill struct {
	Name  string
	Files []File
	// ContentHash は skill 全体のハッシュ。配置済みが最新かどうかの判定に使う。
	ContentHash string
}

// LoadCatalog は fsys の root 配下から skill を読み込む。
// 各サブディレクトリを 1 つの skill として扱い、SKILL.md を必須とする。
func LoadCatalog(fsys fs.FS, root string) ([]Skill, error) {
	entries, err := fs.ReadDir(fsys, root)
	if err != nil {
		return nil, fmt.Errorf("skill カタログ %q の読み込みに失敗しました: %w", root, err)
	}

	var skills []Skill
	for _, entry := range entries {
		if !entry.IsDir() || strings.HasPrefix(entry.Name(), ".") {
			continue
		}
		s, err := loadSkill(fsys, path.Join(root, entry.Name()), entry.Name())
		if err != nil {
			return nil, err
		}
		skills = append(skills, s)
	}
	if len(skills) == 0 {
		return nil, fmt.Errorf("skill カタログ %q に skill がありません", root)
	}
	sort.Slice(skills, func(i, j int) bool { return skills[i].Name < skills[j].Name })
	return skills, nil
}

func loadSkill(fsys fs.FS, dir, name string) (Skill, error) {
	var files []File
	err := fs.WalkDir(fsys, dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if p != dir && strings.HasPrefix(d.Name(), ".") {
				return fs.SkipDir
			}
			return nil
		}
		if strings.HasPrefix(d.Name(), ".") {
			return nil
		}
		data, err := fs.ReadFile(fsys, p)
		if err != nil {
			return err
		}
		rel, err := relSlash(dir, p)
		if err != nil {
			return err
		}
		files = append(files, File{Path: rel, Data: data, SHA256: hashBytes(data)})
		return nil
	})
	if err != nil {
		return Skill{}, fmt.Errorf("skill %q の読み込みに失敗しました: %w", name, err)
	}
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })

	if !hasFile(files, "SKILL.md") {
		return Skill{}, fmt.Errorf("skill %q に SKILL.md がありません", name)
	}
	return Skill{Name: name, Files: files, ContentHash: contentHash(files)}, nil
}

func relSlash(dir, p string) (string, error) {
	prefix := dir + "/"
	if !strings.HasPrefix(p, prefix) {
		return "", fmt.Errorf("skill ディレクトリ %q の外のパスです: %q", dir, p)
	}
	return strings.TrimPrefix(p, prefix), nil
}

func hasFile(files []File, name string) bool {
	for _, f := range files {
		if f.Path == name {
			return true
		}
	}
	return false
}

// contentHash は skill 全体を 1 つのハッシュに畳み込む。
// ファイルの追加・削除・改名も検知できるよう、パスとハッシュの両方を混ぜる。
func contentHash(files []File) string {
	h := sha256.New()
	for _, f := range files {
		fmt.Fprintf(h, "%s\x00%s\x00", f.Path, f.SHA256)
	}
	return hex.EncodeToString(h.Sum(nil))
}

func hashBytes(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// Select は names に含まれる skill だけを返す。names が空、または "all" を含む場合はすべて返す。
func Select(skills []Skill, names []string) ([]Skill, error) {
	if len(names) == 0 {
		return skills, nil
	}
	byName := make(map[string]Skill, len(skills))
	for _, s := range skills {
		byName[s.Name] = s
	}
	out := make([]Skill, 0, len(names))
	seen := make(map[string]struct{}, len(names))
	for _, name := range names {
		s, ok := byName[name]
		if !ok {
			return nil, fmt.Errorf("不明な skill %q (利用可能: %s)", name, strings.Join(Names(skills), ", "))
		}
		if _, dup := seen[name]; dup {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, s)
	}
	if len(out) == 0 {
		return nil, errors.New("skill が選択されていません")
	}
	return out, nil
}

// Names は skill 名の一覧を返す。
func Names(skills []Skill) []string {
	names := make([]string, 0, len(skills))
	for _, s := range skills {
		names = append(names, s.Name)
	}
	return names
}
