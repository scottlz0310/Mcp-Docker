package mcpdocker

import (
	"io/fs"
	"regexp"
	"strings"
	"testing"
	"unicode/utf8"
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

// skillSizeBudget は skill の大きさの上限。skill は起動のたびに SKILL.md の全文がコンテキストへ載るため、
// 肥大化を PR の段階で検知する。references/ は該当する手順に入るときだけ読まれるが、本文を移して
// 総量を隠せないよう、SKILL.md と references/ の合計（maxTotalRunes）にも上限を置く。
//
// 上限は「これ以上増やさない」ための天井であり、本文を分割・削減する PR ごとに下げる。
// 最終目標は Anthropic の Skill authoring best practices が示す「本文 500 行以内」。
// 増やす場合は、上限を引き上げる差分そのものを理由付きでレビューさせる。
var skillSizeBudgets = []struct {
	skill         string
	maxLines      int // SKILL.md の行数
	maxRunes      int // SKILL.md の文字数
	maxTotalRunes int // SKILL.md と references/ 配下の .md の合計文字数
}{
	// #325: Phase W の待機 timeout の理由の注記で +120 文字
	// #326 PR3: Phase 6.6（カバレッジ）と Phase 7.5（完了記録）を references/ へ移動（SKILL.md は -92 行。合計は入口の注記と見出し分で +841 文字）
	// #326 PR5: 完了記録の JSON 例の revision の手書き（18）を、取得元を示す記述に置換（合計 +38 文字）
	// Phase W: タイムアウト後の確認（現在値の再取得、Squirrel Notifier の公開状態、再購読）を references/review-wait.md へ置く
	// （SKILL.md は行数を変えず入口の記述だけで +399 文字。合計は新しい reference の分で +3,196 文字。暫定で、D4 で待機をエージェントから外す際に整理する。
	// 打ち切る前に review://status をもう一度取得する手順 2a を含む）
	{skill: "review-raven-thread-owl-cycle", maxLines: 1070, maxRunes: 75467, maxTotalRunes: 83188},
	// #326: CI 判定を references/ci-check.md へ集約。#331/#332: required checks の集合、provider 制約、未対応 ruleset rule の解決を追加
	// #326 PR2a: queue 待機とローカル検証の隔離手順を references/ へ移動（SKILL.md は -39 行。合計は入口の注記と見出し分で +1,402 文字）
	// #326 PR2b: Verdict 投稿と再レビュー・thread follow-up の手順を references/ へ移動（SKILL.md は -69 行。合計は入口の注記と見出し分で +143 文字）
	// #326 PR4-1: 契約表を共通規則 + 1 行 1 操作の表へ、停止コードを 1 つの表へ圧縮し、{OWL} の discovery を references/discovery.md へ移動
	// （SKILL.md は -259 行・-11,615 文字。合計は新しい reference の分を含めて -9,744 文字。目標 26,000 文字には届かず、残りは契約表 22 行）
	{skill: "thread-owl-pr-reviewer", maxLines: 354, maxRunes: 27559, maxTotalRunes: 45181},
}

// skillMarkdownRunes は skill ディレクトリ配下の .md ファイルの合計文字数を返す。
func skillMarkdownRunes(t *testing.T, name string) int {
	t.Helper()
	total := 0
	err := fs.WalkDir(SkillsFS, SkillsRoot+"/"+name, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(p, ".md") {
			return nil
		}
		data, err := fs.ReadFile(SkillsFS, p)
		if err != nil {
			return err
		}
		total += utf8.RuneCount(data)
		return nil
	})
	if err != nil {
		t.Fatalf("skill %q の .md を集計できません: %v", name, err)
	}
	return total
}

func TestSkillSizeBudget(t *testing.T) {
	for _, b := range skillSizeBudgets {
		t.Run(b.skill, func(t *testing.T) {
			body := readSkill(t, b.skill)
			lines := strings.Count(body, "\n")
			runes := utf8.RuneCountInString(body)
			total := skillMarkdownRunes(t, b.skill)
			t.Logf("SKILL.md の大きさ: %d/%d 行, %d/%d 文字。references を含む合計: %d/%d 文字",
				lines, b.maxLines, runes, b.maxRunes, total, b.maxTotalRunes)
			if lines > b.maxLines {
				t.Errorf("skill %q の行数 = %d, 上限 %d を超えています", b.skill, lines, b.maxLines)
			}
			if runes > b.maxRunes {
				t.Errorf("skill %q の文字数 = %d, 上限 %d を超えています", b.skill, runes, b.maxRunes)
			}
			if total > b.maxTotalRunes {
				t.Errorf("skill %q の合計文字数（references を含む）= %d, 上限 %d を超えています", b.skill, total, b.maxTotalRunes)
			}
		})
	}
}

// 上限の登録漏れで、新しい skill が計測の対象外になることを防ぐ。
func TestSkillSizeBudgetCoversAllSkills(t *testing.T) {
	entries, err := fs.ReadDir(SkillsFS, SkillsRoot)
	if err != nil {
		t.Fatalf("skill カタログを読めません: %v", err)
	}
	budgeted := make(map[string]bool, len(skillSizeBudgets))
	for _, b := range skillSizeBudgets {
		budgeted[b.skill] = true
	}
	for _, e := range entries {
		if !e.IsDir() || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		if !budgeted[e.Name()] {
			t.Errorf("skill %q の SKILL.md サイズ上限が skillSizeBudgets にありません", e.Name())
		}
	}
}
