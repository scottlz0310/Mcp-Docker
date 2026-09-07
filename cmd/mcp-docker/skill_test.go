package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

// runSkillCommand は隔離したホームディレクトリで skill サブコマンドを実行する。
func runSkillCommand(t *testing.T, home string, stdin string, args ...string) (string, error) {
	t.Helper()
	t.Setenv("MCP_DOCKER_SKILL_HOME", home)
	var stdout, stderr bytes.Buffer
	err := run(context.Background(), args, &stdout, &stderr, strings.NewReader(stdin))
	return stdout.String(), err
}

func TestSkillListShowsEmbeddedCatalog(t *testing.T) {
	out, err := runSkillCommand(t, t.TempDir(), "", "skill", "list")
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	for _, name := range []string{"review-raven-thread-owl-cycle", "thread-owl-pr-reviewer"} {
		if !strings.Contains(out, name) {
			t.Fatalf("stdout = %q, want it to list %s", out, name)
		}
	}
}

func TestSkillInstallIsIdempotentAcrossClients(t *testing.T) {
	home := t.TempDir()

	out, err := runSkillCommand(t, home, "", "skill", "install", "--yes")
	if err != nil {
		t.Fatalf("first install returned error: %v", err)
	}
	if !strings.Contains(out, string(skill.ActionInstall)) {
		t.Fatalf("stdout = %q, want it to report %s", out, skill.ActionInstall)
	}

	for _, client := range skill.Clients(home) {
		t.Run(client.Name, func(t *testing.T) {
			path := filepath.Join(client.Dir, "thread-owl-pr-reviewer", "SKILL.md")
			if _, err := os.Stat(path); err != nil {
				t.Fatalf("expected %s to exist: %v", path, err)
			}
		})
	}

	out, err = runSkillCommand(t, home, "", "skill", "install", "--yes")
	if err != nil {
		t.Fatalf("second install returned error: %v", err)
	}
	if strings.Contains(out, string(skill.ActionInstall)) {
		t.Fatalf("stdout = %q, want a re-run to skip instead of reinstalling", out)
	}

	out, err = runSkillCommand(t, home, "", "skill", "status")
	if err != nil {
		t.Fatalf("status returned error: %v", err)
	}
	if strings.Contains(out, string(skill.StateOutdated)) || strings.Contains(out, string(skill.StateAbsent)) {
		t.Fatalf("stdout = %q, want every entry to be %s", out, skill.StateUpToDate)
	}
}

func TestSkillInstallDryRunWritesNothing(t *testing.T) {
	home := t.TempDir()
	out, err := runSkillCommand(t, home, "", "skill", "install", "--agent", "claude", "--dry-run")
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if !strings.Contains(out, "書き込み: SKILL.md") {
		t.Fatalf("stdout = %q, want a write plan", out)
	}
	if _, err := os.Stat(filepath.Join(home, ".claude")); !os.IsNotExist(err) {
		t.Fatalf("--dry-run must not create %s, err = %v", filepath.Join(home, ".claude"), err)
	}
}

func TestSkillInstallAdoptRequiresConfirmation(t *testing.T) {
	home := t.TempDir()
	dir := filepath.Join(home, ".claude", "skills", "thread-owl-pr-reviewer")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("failed to seed unmanaged skill: %v", err)
	}
	handCopied := filepath.Join(dir, "SKILL.md")
	if err := os.WriteFile(handCopied, []byte("hand copied\n"), 0o644); err != nil {
		t.Fatalf("failed to seed unmanaged skill: %v", err)
	}

	out, err := runSkillCommand(t, home, "n\n", "skill", "install", "--agent", "claude", "--skill", "thread-owl-pr-reviewer")
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if !strings.Contains(out, "中止しました") {
		t.Fatalf("stdout = %q, want the adopt to be aborted", out)
	}
	data, err := os.ReadFile(handCopied)
	if err != nil {
		t.Fatalf("failed to read seeded skill: %v", err)
	}
	if string(data) != "hand copied\n" {
		t.Fatalf("declining the prompt must not overwrite the file, got %q", data)
	}

	if _, err := runSkillCommand(t, home, "y\n", "skill", "install", "--agent", "claude", "--skill", "thread-owl-pr-reviewer"); err != nil {
		t.Fatalf("confirmed install returned error: %v", err)
	}
	data, err = os.ReadFile(handCopied)
	if err != nil {
		t.Fatalf("failed to read installed skill: %v", err)
	}
	if string(data) == "hand copied\n" {
		t.Fatal("confirming the prompt must overwrite the unmanaged copy")
	}
}

func TestSkillUninstallProtectsUnmanagedCopies(t *testing.T) {
	home := t.TempDir()
	dir := filepath.Join(home, ".claude", "skills", "thread-owl-pr-reviewer")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("failed to seed unmanaged skill: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("hand copied\n"), 0o644); err != nil {
		t.Fatalf("failed to seed unmanaged skill: %v", err)
	}

	out, err := runSkillCommand(t, home, "", "skill", "uninstall", "--agent", "claude", "--skill", "thread-owl-pr-reviewer", "--yes")
	if err != nil {
		t.Fatalf("run returned error: %v", err)
	}
	if !strings.Contains(out, "--force") {
		t.Fatalf("stdout = %q, want a hint that --force is required", out)
	}
	if _, err := os.Stat(dir); err != nil {
		t.Fatalf("unmanaged skill must survive uninstall without --force: %v", err)
	}

	if _, err := runSkillCommand(t, home, "", "skill", "uninstall", "--agent", "claude", "--skill", "thread-owl-pr-reviewer", "--yes", "--force"); err != nil {
		t.Fatalf("forced uninstall returned error: %v", err)
	}
	if _, err := os.Stat(dir); !os.IsNotExist(err) {
		t.Fatalf("forced uninstall must remove the directory, err = %v", err)
	}
}

func TestSkillArgumentValidation(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantErr string
	}{
		{name: "unknown subcommand", args: []string{"skill", "deploy"}, wantErr: `不明な skill サブコマンド "deploy"`},
		{name: "unknown agent", args: []string{"skill", "status", "--agent", "cursor"}, wantErr: `--agent: 不明な選択肢 "cursor"`},
		{name: "unknown skill", args: []string{"skill", "status", "--skill", "nope"}, wantErr: `--skill: 不明な選択肢 "nope"`},
		{name: "positional argument", args: []string{"skill", "status", "extra"}, wantErr: "想定外の引数です"},
		{name: "missing catalog", args: []string{"skill", "list", "--skills-dir", "does-not-exist"}, wantErr: "読み込みに失敗しました"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := runSkillCommand(t, t.TempDir(), "", tt.args...)
			if err == nil {
				t.Fatalf("run returned nil error, want %q", tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error = %q, want it to contain %q", err, tt.wantErr)
			}
		})
	}
}
