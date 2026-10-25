package reviewgate

import (
	"encoding/json"
	"errors"
	"strconv"
	"strings"
	"testing"
)

const (
	testHeadSHA = "0123456789abcdef0123456789abcdef01234567"

	// testAppID と testOtherAppID は、同名の check を報告する別々の GitHub App の ID。
	testAppID      int64 = 15368
	testOtherAppID int64 = 57789
)

func validRecord() CompletionRecord {
	return CompletionRecord{
		ContractVersion: ContractVersion,
		Repo:            "scottlz0310/Mcp-Docker",
		PRNumber:        305,
		HeadSHA:         testHeadSHA,
		SkillID:         ReviewedSideSkillID,
		SkillRevision:   16,
		SkillCompleted:  true,
		AllReplied:      true,
		CI: FixedHeadCI{
			HeadSHA:  testHeadSHA,
			Complete: true,
			RequiredChecks: []CheckRun{
				{Name: "Go CLI チェック", HeadSHA: testHeadSHA, Status: "completed", Conclusion: "success"},
			},
		},
	}
}

// asUndefinedRequiredChecks は、必須 check が未定義と確認できた記録へ変換する。
// 固定 HEAD で観測した check run は、App ID を付けて ObservedChecks に載せ、RequiredChecks は空にする。
func asUndefinedRequiredChecks(r *CompletionRecord) {
	r.CI.RequiredChecksPolicy = RequiredChecksUndefined
	r.CI.ObservedChecks = append([]CheckRun(nil), r.CI.RequiredChecks...)
	for i := range r.CI.ObservedChecks {
		r.CI.ObservedChecks[i].AppID = testAppID
	}
	r.CI.RequiredChecks = nil
}

func TestCompletionRecordValidate(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*CompletionRecord)
		code   StopCode
	}{
		{name: "valid", mutate: func(*CompletionRecord) {}, code: ""},
		{name: "contract version", mutate: func(r *CompletionRecord) { r.ContractVersion = 2 }, code: StopCompletionRecordInvalid},
		{name: "repository", mutate: func(r *CompletionRecord) { r.Repo = "Mcp-Docker" }, code: StopCompletionRecordInvalid},
		{name: "repository whitespace", mutate: func(r *CompletionRecord) { r.Repo = "scottlz0310/Mcp Docker" }, code: StopCompletionRecordInvalid},
		{name: "head format", mutate: func(r *CompletionRecord) { r.HeadSHA = "0123" }, code: StopCompletionRecordInvalid},
		{name: "skill id", mutate: func(r *CompletionRecord) { r.SkillID = "thread-owl-pr-reviewer" }, code: StopSkillUnavailable},
		{name: "skill revision", mutate: func(r *CompletionRecord) { r.SkillRevision = 0 }, code: StopSkillUnavailable},
		{name: "skill incomplete", mutate: func(r *CompletionRecord) { r.SkillCompleted = false }, code: StopReviewIncomplete},
		{name: "reply incomplete", mutate: func(r *CompletionRecord) { r.AllReplied = false }, code: StopReviewIncomplete},
		{name: "unresolved", mutate: func(r *CompletionRecord) { r.UnresolvedCount = 1 }, code: StopReviewIncomplete},
		{name: "ci head mismatch", mutate: func(r *CompletionRecord) { r.CI.HeadSHA = strings.Repeat("f", 40) }, code: StopHeadMismatch},
		{name: "ci pending", mutate: func(r *CompletionRecord) { r.CI.Complete = false }, code: StopCINotGreen},
		{name: "no required checks", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks = nil }, code: StopCINotGreen},
		{name: "check head mismatch", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks[0].HeadSHA = strings.Repeat("f", 40) }, code: StopHeadMismatch},
		{name: "check failed", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks[0].Conclusion = "failure" }, code: StopCINotGreen},
		{name: "duplicate check", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks = append(r.CI.RequiredChecks, r.CI.RequiredChecks[0]) }, code: StopCompletionRecordInvalid},
		{name: "defined policy explicit", mutate: func(r *CompletionRecord) { r.CI.RequiredChecksPolicy = RequiredChecksDefined }, code: ""},
		{name: "defined policy without required checks", mutate: func(r *CompletionRecord) {
			r.CI.RequiredChecksPolicy = RequiredChecksDefined
			r.CI.RequiredChecks = nil
		}, code: StopCINotGreen},
		{name: "defined policy with observed checks", mutate: func(r *CompletionRecord) {
			r.CI.ObservedChecks = append([]CheckRun(nil), r.CI.RequiredChecks...)
		}, code: StopCompletionRecordInvalid},
		{name: "unsupported policy", mutate: func(r *CompletionRecord) { r.CI.RequiredChecksPolicy = "none" }, code: StopCompletionRecordInvalid},
		{name: "undefined policy", mutate: asUndefinedRequiredChecks, code: ""},
		{name: "undefined policy without observed checks", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks = nil
		}, code: StopCINotGreen},
		{name: "undefined policy with required checks", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.RequiredChecks = []CheckRun{{Name: "x", HeadSHA: testHeadSHA, Status: "completed", Conclusion: "success"}}
		}, code: StopCompletionRecordInvalid},
		{name: "undefined policy ci pending", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.Complete = false
		}, code: StopCINotGreen},
		{name: "undefined policy observed failed", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks = append(r.CI.ObservedChecks, CheckRun{Name: "Lint", AppID: testAppID, HeadSHA: testHeadSHA, Status: "completed", Conclusion: "failure"})
		}, code: StopCINotGreen},
		{name: "undefined policy observed in progress", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks = append(r.CI.ObservedChecks, CheckRun{Name: "Lint", AppID: testAppID, HeadSHA: testHeadSHA, Status: "in_progress"})
		}, code: StopCINotGreen},
		{name: "undefined policy observed head mismatch", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks[0].HeadSHA = strings.Repeat("f", 40)
		}, code: StopHeadMismatch},
		{name: "undefined policy observed duplicate", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks = append(r.CI.ObservedChecks, r.CI.ObservedChecks[0])
		}, code: StopCompletionRecordInvalid},
		{name: "undefined policy same name from different apps", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			other := r.CI.ObservedChecks[0]
			other.AppID = testOtherAppID
			r.CI.ObservedChecks = append(r.CI.ObservedChecks, other)
		}, code: ""},
		{name: "undefined policy same name from different apps one failed", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			other := r.CI.ObservedChecks[0]
			other.AppID = testOtherAppID
			other.Conclusion = "failure"
			r.CI.ObservedChecks = append(r.CI.ObservedChecks, other)
		}, code: StopCINotGreen},
		{name: "undefined policy observed without app id", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks[0].AppID = 0
		}, code: StopCompletionRecordInvalid},
		{name: "undefined policy observed negative app id", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks[0].AppID = -1
		}, code: StopCompletionRecordInvalid},
		{name: "required check with app id", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks[0].AppID = testAppID }, code: ""},
		{name: "required checks same name different apps are duplicates", mutate: func(r *CompletionRecord) {
			r.CI.RequiredChecks[0].AppID = testAppID
			other := r.CI.RequiredChecks[0]
			other.AppID = testOtherAppID
			r.CI.RequiredChecks = append(r.CI.RequiredChecks, other)
		}, code: StopCompletionRecordInvalid},
		{name: "required check negative app id", mutate: func(r *CompletionRecord) { r.CI.RequiredChecks[0].AppID = -1 }, code: StopCompletionRecordInvalid},
		{name: "undefined policy observed empty name", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks[0].Name = " "
		}, code: StopCompletionRecordInvalid},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			record := validRecord()
			tt.mutate(&record)
			err := record.Validate()
			if tt.code == "" {
				if err != nil {
					t.Fatalf("Validate returned error: %v", err)
				}
				return
			}

			var stopErr *StopError
			if !errors.As(err, &stopErr) {
				t.Fatalf("Validate error = %v, want *StopError", err)
			}
			if stopErr.Code != tt.code {
				t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, tt.code)
			}
		})
	}
}

func TestCompletionRecordValidateFor(t *testing.T) {
	record := validRecord()
	target := ValidationTarget{
		Repo:          record.Repo,
		PRNumber:      record.PRNumber,
		HeadSHA:       record.HeadSHA,
		SkillRevision: record.SkillRevision,
	}
	if err := record.ValidateFor(target); err != nil {
		t.Fatalf("ValidateFor returned error: %v", err)
	}

	tests := []struct {
		name   string
		mutate func(*ValidationTarget)
		code   StopCode
	}{
		{name: "repository mismatch", mutate: func(target *ValidationTarget) { target.Repo = "scottlz0310/other" }, code: StopReviewStatusMismatch},
		{name: "pr mismatch", mutate: func(target *ValidationTarget) { target.PRNumber++ }, code: StopReviewStatusMismatch},
		{name: "head mismatch", mutate: func(target *ValidationTarget) { target.HeadSHA = strings.Repeat("f", 40) }, code: StopHeadMismatch},
		{name: "skill revision mismatch", mutate: func(target *ValidationTarget) { target.SkillRevision++ }, code: StopSkillUnavailable},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mismatched := target
			tt.mutate(&mismatched)
			err := record.ValidateFor(mismatched)
			var stopErr *StopError
			if !errors.As(err, &stopErr) {
				t.Fatalf("ValidateFor error = %v, want *StopError", err)
			}
			if stopErr.Code != tt.code {
				t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, tt.code)
			}
		})
	}
}

func TestDecodeCompletionRecordUndefinedRequiredChecks(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*CompletionRecord)
		code   StopCode
	}{
		{name: "observed checks only", mutate: asUndefinedRequiredChecks, code: ""},
		{name: "no observed checks", mutate: func(r *CompletionRecord) {
			asUndefinedRequiredChecks(r)
			r.CI.ObservedChecks = nil
		}, code: StopCINotGreen},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			record := validRecord()
			tt.mutate(&record)
			data, err := json.Marshal(record)
			if err != nil {
				t.Fatalf("json.Marshal returned error: %v", err)
			}

			got, err := DecodeCompletionRecord(data)
			if tt.code == "" {
				if err != nil {
					t.Fatalf("DecodeCompletionRecord returned error: %v", err)
				}
				if got.CI.RequiredChecksPolicy != RequiredChecksUndefined || len(got.CI.ObservedChecks) != 1 || len(got.CI.RequiredChecks) != 0 {
					t.Fatalf("decoded CI = %+v, want undefined policy with 1 observed check and no required checks", got.CI)
				}
				return
			}
			var stopErr *StopError
			if !errors.As(err, &stopErr) {
				t.Fatalf("DecodeCompletionRecord error = %v, want *StopError", err)
			}
			if stopErr.Code != tt.code {
				t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, tt.code)
			}
		})
	}
}

// 別の GitHub App が同名の check を報告した記録を、リテラルの JSON から読み込める。
func TestDecodeCompletionRecordSameNameFromDifferentApps(t *testing.T) {
	check := func(appID int) string {
		return `{"name":"build","appId":` + strconv.Itoa(appID) + `,"headSha":"` + testHeadSHA + `","status":"completed","conclusion":"success"}`
	}
	data := `{"contractVersion":1,"repo":"scottlz0310/Mcp-Docker","prNumber":305,"headSha":"` + testHeadSHA + `",` +
		`"skillId":"review-raven-thread-owl-cycle","skillRevision":16,"skillCompleted":true,"all_replied":true,"unresolved_count":0,` +
		`"ci":{"headSha":"` + testHeadSHA + `","complete":true,"requiredChecksPolicy":"undefined","requiredChecks":[],` +
		`"observedChecks":[` + check(15368) + `,` + check(57789) + `]}}`

	record, err := DecodeCompletionRecord([]byte(data))
	if err != nil {
		t.Fatalf("DecodeCompletionRecord returned error: %v", err)
	}
	if got := record.CI.ObservedChecks; len(got) != 2 || got[0].AppID != 15368 || got[1].AppID != 57789 {
		t.Fatalf("ObservedChecks = %+v, want 2 checks with app IDs 15368 and 57789", got)
	}
}

func TestDecodeCompletionRecordRejectsAmbiguousJSON(t *testing.T) {
	data, err := json.Marshal(validRecord())
	if err != nil {
		t.Fatalf("json.Marshal returned error: %v", err)
	}

	if _, err := DecodeCompletionRecord(data); err != nil {
		t.Fatalf("DecodeCompletionRecord returned error: %v", err)
	}

	tests := []struct {
		name string
		data string
	}{
		{name: "unknown field", data: string(data[:len(data)-1]) + `,"extra":true}`},
		{name: "multiple values", data: string(data) + " {}"},
		{name: "invalid json", data: "{"},
	}
	topLevelDuplicate := strings.Replace(string(data), `"skillCompleted":true`, `"skillCompleted":false,"skillCompleted":true`, 1)
	if topLevelDuplicate == string(data) {
		t.Fatal("failed to construct top-level duplicate-key test input")
	}
	nestedDuplicate := strings.Replace(string(data), `"headSha":"`+testHeadSHA+`","complete"`, `"headSha":"`+testHeadSHA+`","headSha":"`+strings.Repeat("f", 40)+`","complete"`, 1)
	if nestedDuplicate == string(data) {
		t.Fatal("failed to construct nested duplicate-key test input")
	}
	tests = append(tests,
		struct {
			name string
			data string
		}{name: "top-level duplicate key", data: topLevelDuplicate},
		struct {
			name string
			data string
		}{name: "nested duplicate key", data: nestedDuplicate},
	)
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := DecodeCompletionRecord([]byte(tt.data))
			var stopErr *StopError
			if !errors.As(err, &stopErr) {
				t.Fatalf("DecodeCompletionRecord error = %v, want *StopError", err)
			}
			if stopErr.Code != StopCompletionRecordInvalid {
				t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, StopCompletionRecordInvalid)
			}
		})
	}
}
