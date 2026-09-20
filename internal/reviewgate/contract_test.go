package reviewgate

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

const testHeadSHA = "0123456789abcdef0123456789abcdef01234567"

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
