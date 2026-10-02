package mcpdocker

import (
	"encoding/json"
	"slices"
	"testing"
)

// ProviderConstraint は required check の provider 制約を表す。
type ProviderConstraint struct {
	IsAny bool  // true: 任意の App（-1 や null）
	AppID int64 // IsAny が false のときの対象 GitHub App ID
}

// RequiredCheck は判定対象の必須チェックを表す。
type RequiredCheck struct {
	Context  string
	Provider ProviderConstraint
}

// CheckRunData は取得した check run を表す。
type CheckRunData struct {
	ID         int64
	Name       string
	HeadSHA    string
	Status     string
	Conclusion string
	AppID      int64 // 0 のときは App ID 取得不能 / 欠落
	AppSlug    string
}

// CommitStatusData は取得した commit status を表す。
type CommitStatusData struct {
	Context string
	State   string
}

// CIResult は CI 判定結果を表す。
type CIResult string

const (
	CISuccess CIResult = "CI: success"
	CIPending CIResult = "CI: pending"
	CIFailure CIResult = "CI: failure"
	CIUnknown CIResult = "CI: unknown"
)

// EvaluateCI は references/ci-check.md の照合規則に従って CI 判定を行う。
func EvaluateCI(headSHA string, required []RequiredCheck, runs []CheckRunData, statuses []CommitStatusData) CIResult {
	if headSHA == "" {
		return CIUnknown
	}

	// 各 run の対象 SHA が headSHA と一致するか検証。不一致があれば CI: unknown。
	for _, run := range runs {
		if run.HeadSHA != headSHA {
			return CIUnknown
		}
	}

	// required 未定義のときは報告済みの check run すべてを対象にする。
	if len(required) == 0 {
		if len(runs) == 0 {
			return CIPending
		}
		for _, run := range runs {
			if run.Status != "completed" {
				return CIPending
			}
			if run.Conclusion != "success" {
				return CIFailure
			}
		}
		return CISuccess
	}

	hasPending := false

	for _, req := range required {
		// 1. check run の照合
		var matchedRuns []CheckRunData
		for _, run := range runs {
			if run.Name != req.Context {
				continue
			}
			if req.Provider.IsAny {
				matchedRuns = append(matchedRuns, run)
			} else if run.AppID != 0 && run.AppID == req.Provider.AppID {
				matchedRuns = append(matchedRuns, run)
			}
		}

		// 2. commit status の照合
		// provider 制約が任意（IsAny）の場合のみ commit status を照合対象とする。
		// 具体値 App ID が要求されている場合、commit status には provider ID がないため採用できない。
		var matchedStatus *CommitStatusData
		if req.Provider.IsAny {
			for _, st := range statuses {
				if st.Context == req.Context {
					// 一覧は新しい順に並んでいる前提で、最初のものを最新として採用
					matchedStatus = &st
					break
				}
			}
		}

		// 3. この check の合否判定
		if len(matchedRuns) == 0 && matchedStatus == nil {
			// 一致する provider の run / status が未返却
			hasPending = true
			continue
		}

		// 失敗の判定
		failed := false
		for _, run := range matchedRuns {
			if run.Status == "completed" && run.Conclusion != "success" {
				failed = true
				break
			}
		}
		if matchedStatus != nil && (matchedStatus.State == "failure" || matchedStatus.State == "error") {
			failed = true
		}
		if failed {
			return CIFailure
		}

		// 未完了の判定
		pending := false
		for _, run := range matchedRuns {
			if run.Status != "completed" {
				pending = true
				break
			}
		}
		if matchedStatus != nil && matchedStatus.State == "pending" {
			pending = true
		}
		if pending {
			hasPending = true
			continue
		}

		// 成功の判定: すべて完了かつ成功していること。
		// 同名の check run と commit status が併存する場合は両方が成功のときだけ。
		allSuccess := true
		for _, run := range matchedRuns {
			if run.Status != "completed" || run.Conclusion != "success" {
				allSuccess = false
				break
			}
		}
		if matchedStatus != nil && matchedStatus.State != "success" {
			allSuccess = false
		}
		if !allSuccess {
			return CIUnknown
		}
	}

	if hasPending {
		return CIPending
	}
	return CISuccess
}

func TestReviewerCIProviderMatching(t *testing.T) {
	const headSHA = "9f25427ef2ca2652dcae8d6342c98c8c1b97a741"

	t.Run("provider 一致 (具体値 App ID)", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 15368, AppSlug: "github-actions"},
		}
		if got := EvaluateCI(headSHA, required, runs, nil); got != CISuccess {
			t.Errorf("EvaluateCI() = %v, want %v", got, CISuccess)
		}
	})

	t.Run("provider 不一致 (同名だが App ID が異なる)", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 99999, AppSlug: "other-app"},
		}
		// provider が一致する run がないため未返却 (pending)
		if got := EvaluateCI(headSHA, required, runs, nil); got != CIPending {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIPending)
		}
	})

	t.Run("同名の別 provider が併存し指定 provider が成功", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "failure", AppID: 99999, AppSlug: "other-app"},
			{ID: 2, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 15368, AppSlug: "github-actions"},
		}
		// AppID 15368 の run だけが採用されるため成功
		if got := EvaluateCI(headSHA, required, runs, nil); got != CISuccess {
			t.Errorf("EvaluateCI() = %v, want %v", got, CISuccess)
		}
	})

	t.Run("同名の別 provider が併存し指定 provider が失敗", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 99999}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "failure", AppID: 99999, AppSlug: "other-app"},
			{ID: 2, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 15368, AppSlug: "github-actions"},
		}
		// AppID 99999 の run だけが採用されるため失敗
		if got := EvaluateCI(headSHA, required, runs, nil); got != CIFailure {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIFailure)
		}
	})

	t.Run("未返却 (runs 空)", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		if got := EvaluateCI(headSHA, required, nil, nil); got != CIPending {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIPending)
		}
	})

	t.Run("-1 (任意の App を許容)", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{IsAny: true}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 88888, AppSlug: "any-app"},
		}
		if got := EvaluateCI(headSHA, required, runs, nil); got != CISuccess {
			t.Errorf("EvaluateCI() = %v, want %v", got, CISuccess)
		}
	})

	t.Run("-1 で commit status による成功", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "codecov/patch", Provider: ProviderConstraint{IsAny: true}},
		}
		statuses := []CommitStatusData{
			{Context: "codecov/patch", State: "success"},
		}
		if got := EvaluateCI(headSHA, required, nil, statuses); got != CISuccess {
			t.Errorf("EvaluateCI() = %v, want %v", got, CISuccess)
		}
	})

	t.Run("-1 で check run と commit status の両方が存在し一方が失敗", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "codecov/patch", Provider: ProviderConstraint{IsAny: true}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "codecov/patch", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 123},
		}
		statuses := []CommitStatusData{
			{Context: "codecov/patch", State: "failure"},
		}
		if got := EvaluateCI(headSHA, required, runs, statuses); got != CIFailure {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIFailure)
		}
	})

	t.Run("provider ID 欠落 run は具体値 App ID の required を満たさない", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		runs := []CheckRunData{
			{ID: 1, Name: "Frontend", HeadSHA: headSHA, Status: "completed", Conclusion: "success", AppID: 0},
		}
		if got := EvaluateCI(headSHA, required, runs, nil); got != CIPending {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIPending)
		}
	})

	t.Run("commit status は具体値 App ID の required を満たさない", func(t *testing.T) {
		required := []RequiredCheck{
			{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		}
		statuses := []CommitStatusData{
			{Context: "Frontend", State: "success"},
		}
		if got := EvaluateCI(headSHA, required, nil, statuses); got != CIPending {
			t.Errorf("EvaluateCI() = %v, want %v", got, CIPending)
		}
	})
}

// RulesetCheck は ruleset の required_status_checks 内の check。
type RulesetCheck struct {
	Context       string `json:"context"`
	IntegrationID *int64 `json:"integration_id"`
}

// RulesetRule は ruleset の rule。
type RulesetRule struct {
	Type   string `json:"type"`
	Checks []RulesetCheck
}

// ClassicProtection は classic branch protection の要約。
type ClassicProtection struct {
	Enabled  bool
	Contexts []string
	Checks   []struct {
		Context string
		AppID   *int64 // nil は欠落/null
	}
}

func mergeConstraint(a, b ProviderConstraint) (ProviderConstraint, bool) {
	if a == b {
		return a, true
	}
	if a.IsAny {
		return b, true
	}
	if b.IsAny {
		return a, true
	}
	// 異なる具体値 App ID が指定されており矛盾する
	return ProviderConstraint{}, false
}

// ResolveRequiredChecks はリポジトリ設定から required checks 集合を解決する。
// 判定不能な場合は ok = false (CI: unknown)。
func ResolveRequiredChecks(rules []RulesetRule, classic ClassicProtection) (checks []RequiredCheck, ok bool, isUndefined bool) {
	// 1. 未対応 ruleset rule の検査
	unsupportedRules := []string{"workflows", "code_scanning", "code_quality", "code_coverage"}
	for _, r := range rules {
		if slices.Contains(unsupportedRules, r.Type) {
			return nil, false, false
		}
	}

	// 2. ruleset の required_status_checks
	rulesetMap := make(map[string]ProviderConstraint)
	for _, r := range rules {
		if r.Type == "required_status_checks" {
			for _, c := range r.Checks {
				var p ProviderConstraint
				if c.IntegrationID == nil || *c.IntegrationID == -1 {
					p = ProviderConstraint{IsAny: true}
				} else {
					p = ProviderConstraint{IsAny: false, AppID: *c.IntegrationID}
				}
				if existing, exists := rulesetMap[c.Context]; exists {
					merged, okMerge := mergeConstraint(existing, p)
					if !okMerge {
						return nil, false, false
					}
					rulesetMap[c.Context] = merged
				} else {
					rulesetMap[c.Context] = p
				}
			}
		}
	}

	// 3. classic の要約
	classicMap := make(map[string]ProviderConstraint)
	if classic.Enabled {
		// checks[] の解決
		for _, c := range classic.Checks {
			if c.AppID == nil {
				// app_id が省略または null: 省略時に直近の提供 App が自動選択され provider を特定できないため unknown
				return nil, false, false
			}
			var p ProviderConstraint
			if *c.AppID == -1 {
				p = ProviderConstraint{IsAny: true}
			} else {
				p = ProviderConstraint{IsAny: false, AppID: *c.AppID}
			}
			if existing, exists := classicMap[c.Context]; exists {
				merged, okMerge := mergeConstraint(existing, p)
				if !okMerge {
					return nil, false, false
				}
				classicMap[c.Context] = merged
			} else {
				classicMap[c.Context] = p
			}
		}

		// contexts[] の解決
		for _, ctx := range classic.Contexts {
			// checks[] に同じ context があればその制約に従う。
			if _, exists := classicMap[ctx]; !exists {
				// checks[] の裏付けがない legacy context: 暗黙の App 制約を解決できないため unknown
				return nil, false, false
			}
		}
	}

	// 4. 和集合の形成
	allContexts := make(map[string]ProviderConstraint)
	for ctx, p := range rulesetMap {
		allContexts[ctx] = p
	}
	for ctx, cp := range classicMap {
		if rp, exists := allContexts[ctx]; exists {
			merged, okMerge := mergeConstraint(rp, cp)
			if !okMerge {
				return nil, false, false
			}
			allContexts[ctx] = merged
		} else {
			allContexts[ctx] = cp
		}
	}

	if len(allContexts) == 0 {
		return nil, true, true // required 未定義
	}

	result := make([]RequiredCheck, 0, len(allContexts))
	for ctx, p := range allContexts {
		result = append(result, RequiredCheck{Context: ctx, Provider: p})
	}
	return result, true, false
}

func TestReviewerCIProviderAmbiguity(t *testing.T) {
	appID := int64(15368)
	appID2 := int64(99999)

	t.Run("PR #137 再現ケース: classic checks に具体値 App ID があり contexts にも同名が含まれる", func(t *testing.T) {
		classic := ClassicProtection{
			Enabled:  true,
			Contexts: []string{"Frontend", "Rust"},
			Checks: []struct {
				Context string
				AppID   *int64
			}{
				{Context: "Frontend", AppID: &appID},
				{Context: "Rust", AppID: &appID},
			},
		}
		checks, ok, isUndefined := ResolveRequiredChecks(nil, classic)
		if !ok || isUndefined {
			t.Fatalf("ResolveRequiredChecks() ok=%v, isUndefined=%v; want ok=true, isUndefined=false", ok, isUndefined)
		}
		if len(checks) != 2 {
			t.Fatalf("checks count = %d, want 2", len(checks))
		}
		for _, c := range checks {
			if c.Provider.IsAny || c.Provider.AppID != 15368 {
				t.Errorf("check %s provider = %+v, want AppID=15368", c.Context, c.Provider)
			}
		}
	})

	t.Run("classic checks の app_id が欠落/null の場合は unknown", func(t *testing.T) {
		classic := ClassicProtection{
			Enabled: true,
			Checks: []struct {
				Context string
				AppID   *int64
			}{
				{Context: "Frontend", AppID: nil},
			},
		}
		_, ok, _ := ResolveRequiredChecks(nil, classic)
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("classic contexts に checks の裏付けがない項目がある場合は unknown", func(t *testing.T) {
		classic := ClassicProtection{
			Enabled:  true,
			Contexts: []string{"Frontend", "LegacyContextWithoutCheck"},
			Checks: []struct {
				Context string
				AppID   *int64
			}{
				{Context: "Frontend", AppID: &appID},
			},
		}
		_, ok, _ := ResolveRequiredChecks(nil, classic)
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("ruleset に未対応 rule (workflows 等) がある場合は unknown", func(t *testing.T) {
		rules := []RulesetRule{
			{Type: "workflows"},
		}
		_, ok, _ := ResolveRequiredChecks(rules, ClassicProtection{})
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("ruleset と classic で矛盾する App ID が指定された場合は unknown", func(t *testing.T) {
		rules := []RulesetRule{
			{
				Type: "required_status_checks",
				Checks: []RulesetCheck{
					{Context: "Frontend", IntegrationID: &appID},
				},
			},
		}
		classic := ClassicProtection{
			Enabled:  true,
			Contexts: []string{"Frontend"},
			Checks: []struct {
				Context string
				AppID   *int64
			}{
				{Context: "Frontend", AppID: &appID2},
			},
		}
		_, ok, _ := ResolveRequiredChecks(rules, classic)
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("同一 ruleset 内で同じ context に異なる App ID がある場合は unknown", func(t *testing.T) {
		rules := []RulesetRule{
			{
				Type: "required_status_checks",
				Checks: []RulesetCheck{
					{Context: "Frontend", IntegrationID: &appID},
					{Context: "Frontend", IntegrationID: &appID2},
				},
			},
		}
		_, ok, _ := ResolveRequiredChecks(rules, ClassicProtection{})
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("同一 classic 内で同じ context に異なる App ID がある場合は unknown", func(t *testing.T) {
		classic := ClassicProtection{
			Enabled:  true,
			Contexts: []string{"Frontend"},
			Checks: []struct {
				Context string
				AppID   *int64
			}{
				{Context: "Frontend", AppID: &appID},
				{Context: "Frontend", AppID: &appID2},
			},
		}
		_, ok, _ := ResolveRequiredChecks(nil, classic)
		if ok {
			t.Error("ResolveRequiredChecks() ok=true, want false (CI: unknown)")
		}
	})

	t.Run("同一 ruleset 内で同じ context に同一 App ID が重複している場合は正常採用", func(t *testing.T) {
		rules := []RulesetRule{
			{
				Type: "required_status_checks",
				Checks: []RulesetCheck{
					{Context: "Frontend", IntegrationID: &appID},
					{Context: "Frontend", IntegrationID: &appID},
				},
			},
		}
		checks, ok, _ := ResolveRequiredChecks(rules, ClassicProtection{})
		if !ok || len(checks) != 1 || checks[0].Provider.AppID != 15368 {
			t.Errorf("ResolveRequiredChecks() = %+v, ok=%v; want 1 check with AppID=15368", checks, ok)
		}
	})
}

// rawCheckRun は GitHub API /commits/{sha}/check-runs の 1 要素を表す JSON 構造体。
type rawCheckRun struct {
	ID         int64   `json:"id"`
	Name       string  `json:"name"`
	HeadSHA    string  `json:"head_sha"`
	Status     string  `json:"status"`
	Conclusion *string `json:"conclusion"`
	App        struct {
		ID   int64  `json:"id"`
		Slug string `json:"slug"`
	} `json:"app"`
}

// ghAPIFallbackRun は gh api fallback の jq 式
// `.check_runs[] | {id, name, head_sha, status, conclusion, app: {id: .app.id, slug: .app.slug}}`
// のパース結果を表す。
type ghAPIFallbackRun struct {
	ID         int64   `json:"id"`
	Name       string  `json:"name"`
	HeadSHA    string  `json:"head_sha"`
	Status     string  `json:"status"`
	Conclusion *string `json:"conclusion"`
	App        struct {
		ID   int64  `json:"id"`
		Slug string `json:"slug"`
	} `json:"app"`
}

func TestReviewerCIReaderConsistency(t *testing.T) {
	const headSHA = "9f25427ef2ca2652dcae8d6342c98c8c1b97a741"
	success := "success"

	rawGitHubRuns := []rawCheckRun{
		{
			ID:         1001,
			Name:       "Frontend",
			HeadSHA:    headSHA,
			Status:     "completed",
			Conclusion: &success,
			App: struct {
				ID   int64  `json:"id"`
				Slug string `json:"slug"`
			}{ID: 15368, Slug: "github-actions"},
		},
		{
			ID:         1002,
			Name:       "Rust",
			HeadSHA:    headSHA,
			Status:     "completed",
			Conclusion: &success,
			App: struct {
				ID   int64  `json:"id"`
				Slug string `json:"slug"`
			}{ID: 15368, Slug: "github-actions"},
		},
	}

	rawJSON, err := json.Marshal(rawGitHubRuns)
	if err != nil {
		t.Fatalf("json.Marshal failed: %v", err)
	}

	// 1. review-raven 経路の読み取り (CheckRunOutput 相当)
	var ravenRuns []CheckRunData
	var rawParsed []rawCheckRun
	if err := json.Unmarshal(rawJSON, &rawParsed); err != nil {
		t.Fatalf("raven unmarshal failed: %v", err)
	}
	for _, r := range rawParsed {
		conclusion := ""
		if r.Conclusion != nil {
			conclusion = *r.Conclusion
		}
		ravenRuns = append(ravenRuns, CheckRunData{
			ID:         r.ID,
			Name:       r.Name,
			HeadSHA:    r.HeadSHA,
			Status:     r.Status,
			Conclusion: conclusion,
			AppID:      r.App.ID,
			AppSlug:    r.App.Slug,
		})
	}

	// 2. gh api fallback 経路の読み取り (jq 抽出結果相当)
	var ghFallbackRuns []CheckRunData
	var ghParsed []ghAPIFallbackRun
	if err := json.Unmarshal(rawJSON, &ghParsed); err != nil {
		t.Fatalf("gh fallback unmarshal failed: %v", err)
	}
	for _, r := range ghParsed {
		conclusion := ""
		if r.Conclusion != nil {
			conclusion = *r.Conclusion
		}
		ghFallbackRuns = append(ghFallbackRuns, CheckRunData{
			ID:         r.ID,
			Name:       r.Name,
			HeadSHA:    r.HeadSHA,
			Status:     r.Status,
			Conclusion: conclusion,
			AppID:      r.App.ID,
			AppSlug:    r.App.Slug,
		})
	}

	// 3. データ構造の一致検証
	if len(ravenRuns) != len(ghFallbackRuns) {
		t.Fatalf("run count mismatch: raven=%d, gh=%d", len(ravenRuns), len(ghFallbackRuns))
	}
	for i := range ravenRuns {
		if ravenRuns[i] != ghFallbackRuns[i] {
			t.Errorf("run[%d] mismatch: raven=%+v, gh=%+v", i, ravenRuns[i], ghFallbackRuns[i])
		}
	}

	// 4. CI 判定結果の一致検証
	required := []RequiredCheck{
		{Context: "Frontend", Provider: ProviderConstraint{AppID: 15368}},
		{Context: "Rust", Provider: ProviderConstraint{AppID: 15368}},
	}

	resRaven := EvaluateCI(headSHA, required, ravenRuns, nil)
	resGH := EvaluateCI(headSHA, required, ghFallbackRuns, nil)
	if resRaven != resGH {
		t.Errorf("EvaluateCI result mismatch: raven=%v, gh=%v", resRaven, resGH)
	}
	if resRaven != CISuccess {
		t.Errorf("expected success, got %v", resRaven)
	}
}
