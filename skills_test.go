package mcpdocker

import (
	"io/fs"
	"regexp"
	"strings"
	"testing"
)

const (
	verdictRuleBegin = "<!-- verdict-match-rule:begin -->"
	verdictRuleEnd   = "<!-- verdict-match-rule:end -->"
)

var verdictRuleSkills = []string{"thread-owl-pr-reviewer", "review-raven-thread-owl-cycle"}

func readSkill(t *testing.T, name string) string {
	t.Helper()
	data, err := fs.ReadFile(SkillsFS, SkillsRoot+"/"+name+"/SKILL.md")
	if err != nil {
		t.Fatalf("skill %q の SKILL.md を読めません: %v", name, err)
	}
	return string(data)
}

func extractVerdictRule(t *testing.T, skill string) string {
	t.Helper()
	body := readSkill(t, skill)
	if n := strings.Count(body, verdictRuleBegin); n != 1 {
		t.Fatalf("skill %q の開始マーカー数 = %d, want 1", skill, n)
	}
	if n := strings.Count(body, verdictRuleEnd); n != 1 {
		t.Fatalf("skill %q の終了マーカー数 = %d, want 1", skill, n)
	}
	_, rest, _ := strings.Cut(body, verdictRuleBegin)
	rule, _, _ := strings.Cut(rest, verdictRuleEnd)
	if strings.TrimSpace(rule) == "" {
		t.Fatalf("skill %q の Verdict 照合規則が空です", skill)
	}
	return rule
}

// 照合規則の文書から、行頭 `^` で始まる正規表現を記載順に取り出す。
func verdictRulePatterns(t *testing.T) []*regexp.Regexp {
	t.Helper()
	var patterns []*regexp.Regexp
	for line := range strings.Lines(extractVerdictRule(t, verdictRuleSkills[0])) {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "^") {
			patterns = append(patterns, regexp.MustCompile(line))
		}
	}
	if len(patterns) != 3 {
		t.Fatalf("照合規則の正規表現数 = %d, want 3", len(patterns))
	}
	return patterns
}

// matchVerdict は SKILL.md に書かれた手順 1〜4 を実装し、書式一致時の SHA を返す。
func matchVerdict(patterns []*regexp.Regexp, body string) (sha string, ok bool) {
	positions := make([]int, len(patterns))
	counts := make([]int, len(patterns))
	for i, line := range strings.Split(body, "\n") {
		line = strings.TrimSuffix(line, "\r")
		for j, p := range patterns {
			if m := p.FindStringSubmatch(line); m != nil {
				counts[j]++
				positions[j] = i
				if len(m) > 1 {
					sha = m[1]
				}
			}
		}
	}
	for _, c := range counts {
		if c != 1 {
			return "", false
		}
	}
	if positions[0] > positions[1] || positions[0] > positions[2] {
		return "", false
	}
	return sha, true
}

func TestVerdictMatchRuleIsIdenticalAcrossSkills(t *testing.T) {
	want := extractVerdictRule(t, verdictRuleSkills[0])
	for _, skill := range verdictRuleSkills[1:] {
		t.Run(skill, func(t *testing.T) {
			if got := extractVerdictRule(t, skill); got != want {
				t.Errorf("skill %q の Verdict 照合規則が正本（%s）と一致しません", skill, verdictRuleSkills[0])
			}
		})
	}
}

func TestVerdictMatchRule(t *testing.T) {
	patterns := verdictRulePatterns(t)
	const sha = "66ff8c6a1b2c3d4e5f60718293a4b5c6d7e8f901"

	body := readSkill(t, "thread-owl-pr-reviewer")
	// 固定部分は thread-owl の post_review_verdict が組み立てるので、skill 側に手組み用テンプレートを残さない。
	if strings.Contains(body, "```markdown\n## @thread-owl Review Verdict") {
		t.Error("reviewer skill に Verdict コメントのテンプレートが残っています")
	}

	// thread-owl の buildVerdictBody と同じ構成（見出し・summary・区切り線・HEAD 行・Status 行）。
	valid := "## @thread-owl Review Verdict: APPROVED\n\nサマリー\n\n---\n- Reviewed HEAD SHA: `" + sha + "`\n- Status: `READY_TO_MERGE`\n"

	tests := []struct {
		name    string
		body    string
		wantOK  bool
		wantSHA string
	}{
		{name: "post_review_verdict が組み立てる本文", body: valid, wantOK: true, wantSHA: sha},
		{name: "CRLF 改行", body: strings.ReplaceAll(valid, "\n", "\r\n"), wantOK: true, wantSHA: sha},
		{
			name:   "thread-owl#217 の逸脱",
			body:   "## @thread-owl Review Verdict: READY_TO_MERGE\n\n- Reviewed HEAD: `" + sha + "`\n- 判定: `READY_TO_MERGE`\n",
			wantOK: false,
		},
		{name: "Status のバッククォート省略", body: strings.Replace(valid, "`READY_TO_MERGE`", "READY_TO_MERGE", 1), wantOK: false},
		{name: "行頭の - 省略", body: strings.Replace(valid, "- Status:", "Status:", 1), wantOK: false},
		{name: "行末の空白", body: strings.Replace(valid, "APPROVED\n", "APPROVED \n", 1), wantOK: false},
		{name: "SHA が大文字", body: strings.Replace(valid, sha, strings.ToUpper(sha), 1), wantOK: false},
		{name: "SHA が短縮形", body: strings.Replace(valid, sha, sha[:7], 1), wantOK: false},
		{name: "見出しの重複", body: "## @thread-owl Review Verdict: APPROVED\n" + valid, wantOK: false},
		{
			name:   "見出しがメタデータより後",
			body:   "- Reviewed HEAD SHA: `" + sha + "`\n- Status: `READY_TO_MERGE`\n## @thread-owl Review Verdict: APPROVED\n",
			wantOK: false,
		},
	}
	_, afterResult, found := strings.Cut(body, "```markdown\n## @thread-owl Review Result")
	if !found {
		t.Fatal("reviewer skill にレビュー完了サマリーのテンプレートが見つかりません")
	}
	result, _, _ := strings.Cut(afterResult, "\n```")
	result = "## @thread-owl Review Result" + strings.ReplaceAll(result, "<reviewedHeadSha>", sha)
	if strings.Contains(result, "Review Verdict") {
		t.Error("レビュー完了サマリーが Verdict 候補（部分文字列 Review Verdict）になっています")
	}
	tests = append(tests, struct {
		name    string
		body    string
		wantOK  bool
		wantSHA string
	}{name: "レビュー完了サマリーのテンプレート", body: result, wantOK: false})

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotSHA, gotOK := matchVerdict(patterns, tt.body)
			if gotOK != tt.wantOK || gotSHA != tt.wantSHA {
				t.Errorf("matchVerdict() = (%q, %v), want (%q, %v)", gotSHA, gotOK, tt.wantSHA, tt.wantOK)
			}
		})
	}
}
