package mcpdocker

import (
	"encoding/json"
	"io/fs"
	"os"
	"path"
	"regexp"
	"slices"
	"sort"
	"strings"
	"testing"
)

// skill の「契約」（行 ID と、停止コード・ラベル・外部の語）を testdata/skill-contract.json に固定する。
//
// skill 本文の再構成（契約表の圧縮、references への移動。#326）で、停止の定義や行 ID を、気づかずに失わないための検査である。
// 停止コードや行 ID を、意図して追加・削除・改名する場合は、testdata/skill-contract.json の差分としてレビューさせる。
//
//   - rowIDs: 契約表の行 ID（R-xx / O-xx）。docs/ や skill 内の相互参照が、この ID を指す
//   - stopCodes: 停止・待機の理由を表すコード。停止の定義の正本
//   - labels: 失敗ではなく、結果・判定を表すラベル（Verdict の Status、サイクルの終端の判定など）
//   - external: 環境変数、購読 CLI のエラーコードなど、skill の外で定義される語
//
// 検査するのは「skill のどこかに、その語・ID がある」こと（SKILL.md と references/ 直下の .md が対象）。
type skillContract struct {
	RowIDs    []string `json:"rowIDs"`
	StopCodes []string `json:"stopCodes"`
	Labels    []string `json:"labels"`
	External  []string `json:"external"`
}

const skillContractPath = "testdata/skill-contract.json"

// UPPER_SNAKE の語（アンダースコアで区切られた 2 語以上の大文字）。停止コード・ラベル・環境変数の形式。
var upperSnakeToken = regexp.MustCompile(`\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b`)

func loadSkillContracts(t *testing.T) map[string]skillContract {
	t.Helper()
	data, err := os.ReadFile(skillContractPath)
	if err != nil {
		t.Fatalf("%s を読めません: %v", skillContractPath, err)
	}
	var contracts map[string]skillContract
	if err := json.Unmarshal(data, &contracts); err != nil {
		t.Fatalf("%s を解釈できません: %v", skillContractPath, err)
	}
	return contracts
}

// skillTexts は、skill の SKILL.md と references/ 直下の .md の本文を、skill ディレクトリからの相対パスで返す。
func skillTexts(t *testing.T, name string) map[string]string {
	t.Helper()
	dir := SkillsRoot + "/" + name
	texts := map[string]string{}
	main, err := fs.ReadFile(SkillsFS, dir+"/SKILL.md")
	if err != nil {
		t.Fatalf("skill %q の SKILL.md を読めません: %v", name, err)
	}
	texts["SKILL.md"] = string(main)
	entries, err := fs.ReadDir(SkillsFS, dir+"/references")
	if err != nil {
		return texts // references/ の無い skill もある
	}
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		data, err := fs.ReadFile(SkillsFS, path.Join(dir, "references", e.Name()))
		if err != nil {
			t.Fatalf("skill %q の references/%s を読めません: %v", name, e.Name(), err)
		}
		texts["references/"+e.Name()] = string(data)
	}
	return texts
}

func skillTokens(texts map[string]string) map[string]struct{} {
	tokens := map[string]struct{}{}
	for _, body := range texts {
		for _, tok := range upperSnakeToken.FindAllString(body, -1) {
			tokens[tok] = struct{}{}
		}
	}
	return tokens
}

func sortedKeys(m map[string]struct{}) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func TestSkillContractCoversAllSkills(t *testing.T) {
	contracts := loadSkillContracts(t)
	entries, err := fs.ReadDir(SkillsFS, SkillsRoot)
	if err != nil {
		t.Fatalf("skills/ を読めません: %v", err)
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		if _, ok := contracts[e.Name()]; !ok {
			t.Errorf("skill %q の契約が %s に無い。行 ID と停止コードを追加してください", e.Name(), skillContractPath)
		}
	}
	for name := range contracts {
		if _, err := fs.Stat(SkillsFS, SkillsRoot+"/"+name+"/SKILL.md"); err != nil {
			t.Errorf("%s に、存在しない skill %q の契約がある", skillContractPath, name)
		}
	}
}

// 1 つの語は、停止コード・ラベル・外部のいずれか 1 つにだけ分類する。行 ID は重複させない。
func TestSkillContractIsWellFormed(t *testing.T) {
	for name, c := range loadSkillContracts(t) {
		t.Run(name, func(t *testing.T) {
			seen := map[string]string{}
			for _, category := range []struct {
				name  string
				words []string
			}{{"stopCodes", c.StopCodes}, {"labels", c.Labels}, {"external", c.External}} {
				for _, w := range category.words {
					if !upperSnakeToken.MatchString(w) {
						t.Errorf("%s の %q は UPPER_SNAKE の語ではない", category.name, w)
					}
					if prev, dup := seen[w]; dup {
						t.Errorf("%q が %s と %s の両方にある", w, prev, category.name)
					}
					seen[w] = category.name
				}
			}
			ids := map[string]struct{}{}
			for _, id := range c.RowIDs {
				if _, dup := ids[id]; dup {
					t.Errorf("行 ID %q が重複している", id)
				}
				ids[id] = struct{}{}
			}
		})
	}
}

// 行 ID（R-09 など）の見出し（### R-09: …）または表の行（| R-09 | …）。
var rowIDLine = regexp.MustCompile(`(?m)^(?:#{3} |\| )([A-Z]-\d+[ab]?)\b`)

// 契約表の行 ID は、SKILL.md の見出し（### R-09: …）または表の行（| R-09 | …）と、双方向に一致させる。
// 契約にある ID が SKILL.md から消えた場合と、SKILL.md に新しい ID を足して契約への登録を忘れた場合の、どちらも検出する。
func TestSkillContractRowIDsMatch(t *testing.T) {
	for name, c := range loadSkillContracts(t) {
		t.Run(name, func(t *testing.T) {
			found := map[string]struct{}{}
			for _, m := range rowIDLine.FindAllStringSubmatch(skillTexts(t, name)["SKILL.md"], -1) {
				found[m[1]] = struct{}{}
			}

			registered := map[string]struct{}{}
			for _, id := range c.RowIDs {
				registered[id] = struct{}{}
				if _, ok := found[id]; !ok {
					t.Errorf("行 ID %q が SKILL.md に無い（見出し「### %s: …」または表の行「| %s | …」として残す）", id, id, id)
				}
			}
			for _, id := range sortedKeys(found) {
				if _, ok := registered[id]; !ok {
					t.Errorf("SKILL.md の行 ID %q が契約に無い。意図した追加なら、%s の rowIDs に追加してください", id, skillContractPath)
				}
			}
		})
	}
}

// skill 内の UPPER_SNAKE の語は、すべて契約に分類されている。契約の語は、skill のどこかに残っている。
func TestSkillContractTokensAreClassified(t *testing.T) {
	for name, c := range loadSkillContracts(t) {
		t.Run(name, func(t *testing.T) {
			found := skillTokens(skillTexts(t, name))
			known := map[string]struct{}{}
			for _, words := range [][]string{c.StopCodes, c.Labels, c.External} {
				for _, w := range words {
					known[w] = struct{}{}
				}
			}

			var unclassified []string
			for _, tok := range sortedKeys(found) {
				if _, ok := known[tok]; !ok {
					unclassified = append(unclassified, tok)
				}
			}
			if len(unclassified) > 0 {
				t.Errorf("契約に未分類の語がある: %s。停止・待機の理由なら stopCodes、結果のラベルなら labels、skill の外の語なら external へ、%s に追加してください",
					strings.Join(unclassified, ", "), skillContractPath)
			}

			var lost []string
			for _, w := range slices.Concat(c.StopCodes, c.Labels, c.External) {
				if _, ok := found[w]; !ok {
					lost = append(lost, w)
				}
			}
			sort.Strings(lost)
			if len(lost) > 0 {
				t.Errorf("契約にある語が、skill から消えている: %s。意図した削除なら、%s からも削除してください（停止の定義を失っていないか確認する）",
					strings.Join(lost, ", "), skillContractPath)
			}
		})
	}
}

// 停止コードの表（SKILL.md の「## 停止コード」節）を持つ skill。この表が、停止コードの定義の正本である。
// 表のコードは、契約の stopCodes と双方向に一致させる（表にない停止コードも、表だけにあるコードも検出する）。
// 本文を圧縮して表を置いた skill から追加する（#326）。
var stopCodeRegistrySkills = []string{"thread-owl-pr-reviewer", "review-raven-thread-owl-cycle"}

// 停止コードの表の行（| `CODE` | …）。
var stopCodeRow = regexp.MustCompile("(?m)^\\| `([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)` \\|")

func TestSkillStopCodeRegistry(t *testing.T) {
	contracts := loadSkillContracts(t)
	for _, name := range stopCodeRegistrySkills {
		t.Run(name, func(t *testing.T) {
			c, ok := contracts[name]
			if !ok {
				t.Fatalf("skill %q の契約が %s に無い", name, skillContractPath)
			}
			_, section, found := strings.Cut(skillTexts(t, name)["SKILL.md"], "\n## 停止コード\n")
			if !found {
				t.Fatalf("skill %q の SKILL.md に「## 停止コード」節が無い", name)
			}
			if end := strings.Index(section, "\n## "); end >= 0 {
				section = section[:end]
			}

			listed := map[string]struct{}{}
			for _, m := range stopCodeRow.FindAllStringSubmatch(section, -1) {
				if _, dup := listed[m[1]]; dup {
					t.Errorf("停止コード %q が表に重複している", m[1])
				}
				listed[m[1]] = struct{}{}
			}

			registered := map[string]struct{}{}
			for _, code := range c.StopCodes {
				registered[code] = struct{}{}
				if _, ok := listed[code]; !ok {
					t.Errorf("停止コード %q が、SKILL.md の「停止コード」表にない（条件と動作を表へ追加してください）", code)
				}
			}
			for _, code := range sortedKeys(listed) {
				if _, ok := registered[code]; !ok {
					t.Errorf("「停止コード」表の %q が契約の stopCodes にない。意図した追加なら、%s の stopCodes に追加してください", code, skillContractPath)
				}
			}
		})
	}
}
