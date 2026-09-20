package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	mcpdocker "github.com/scottlz0310/mcp-docker/v2"
	"github.com/scottlz0310/mcp-docker/v2/internal/reviewgate"
	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

const reviewGateTestHeadSHA = "0123456789abcdef0123456789abcdef01234567"

func TestRunReviewGateValidate(t *testing.T) {
	revision := embeddedReviewGateTestRevision(t)
	recordPath := writeReviewGateTestRecord(t, revision)

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"reviewgate", "validate",
		"--record", recordPath,
		"--repo", "scottlz0310/Mcp-Docker",
		"--pr", "307",
		"--head-sha", reviewGateTestHeadSHA,
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if !strings.Contains(stdout.String(), "reviewgate: valid") {
		t.Fatalf("stdout = %q, want validation success", stdout.String())
	}
}

func TestRunReviewGateValidateRejectsCurrentHeadMismatch(t *testing.T) {
	revision := embeddedReviewGateTestRevision(t)
	recordPath := writeReviewGateTestRecord(t, revision)

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"reviewgate", "validate",
		"--record", recordPath,
		"--repo", "scottlz0310/Mcp-Docker",
		"--pr", "307",
		"--head-sha", strings.Repeat("f", 40),
	}, &stdout, &stderr, strings.NewReader(""))
	var stopErr *reviewgate.StopError
	if !errors.As(err, &stopErr) {
		t.Fatalf("error = %v, want *reviewgate.StopError", err)
	}
	if stopErr.Code != reviewgate.StopHeadMismatch {
		t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, reviewgate.StopHeadMismatch)
	}
}

func TestRunReviewGateValidateRejectsOldEmbeddedSkillRevision(t *testing.T) {
	revision := embeddedReviewGateTestRevision(t)
	recordPath := writeReviewGateTestRecord(t, revision-1)

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"reviewgate", "validate",
		"--record", recordPath,
		"--repo", "scottlz0310/Mcp-Docker",
		"--pr", "307",
		"--head-sha", reviewGateTestHeadSHA,
	}, &stdout, &stderr, strings.NewReader(""))
	var stopErr *reviewgate.StopError
	if !errors.As(err, &stopErr) {
		t.Fatalf("error = %v, want *reviewgate.StopError", err)
	}
	if stopErr.Code != reviewgate.StopSkillUnavailable {
		t.Fatalf("StopError.Code = %q, want %q", stopErr.Code, reviewgate.StopSkillUnavailable)
	}
}

func embeddedReviewGateTestRevision(t *testing.T) int {
	t.Helper()
	catalog, err := skill.LoadCatalog(mcpdocker.SkillsFS, mcpdocker.SkillsRoot)
	if err != nil {
		t.Fatalf("LoadCatalog returned error: %v", err)
	}
	selected, err := skill.Select(catalog, []string{reviewgate.ReviewedSideSkillID})
	if err != nil {
		t.Fatalf("Select returned error: %v", err)
	}
	return selected[0].Revision
}

func writeReviewGateTestRecord(t *testing.T, revision int) string {
	t.Helper()
	record := reviewgate.CompletionRecord{
		ContractVersion: reviewgate.ContractVersion,
		Repo:            "scottlz0310/Mcp-Docker",
		PRNumber:        307,
		HeadSHA:         reviewGateTestHeadSHA,
		SkillID:         reviewgate.ReviewedSideSkillID,
		SkillRevision:   revision,
		SkillCompleted:  true,
		AllReplied:      true,
		UnresolvedCount: 0,
		CI: reviewgate.FixedHeadCI{
			HeadSHA:  reviewGateTestHeadSHA,
			Complete: true,
			RequiredChecks: []reviewgate.CheckRun{
				{Name: "Go CLI チェック", HeadSHA: reviewGateTestHeadSHA, Status: "completed", Conclusion: "success"},
			},
		},
	}
	data, err := json.Marshal(record)
	if err != nil {
		t.Fatalf("Marshal returned error: %v", err)
	}
	path := filepath.Join(t.TempDir(), "completion.json")
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatalf("WriteFile returned error: %v", err)
	}
	return path
}
