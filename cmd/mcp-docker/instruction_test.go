package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInstructionConfigureStatusAndDryRun(t *testing.T) {
	home := t.TempDir()
	configPath := filepath.Join(t.TempDir(), "instructions.json")
	source := filepath.Join(t.TempDir(), "user-instructions.md")
	if err := os.WriteFile(source, []byte("# source\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("MCP_DOCKER_INSTRUCTION_HOME", home)
	t.Setenv("MCP_DOCKER_INSTRUCTION_CONFIG", configPath)

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"instruction", "configure", "--source", source,
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("configure error: %v", err)
	}
	if !strings.Contains(stdout.String(), "instruction source を設定しました") {
		t.Fatalf("configure output = %q", stdout.String())
	}

	stdout.Reset()
	err = run(context.Background(), []string{
		"instruction", "status", "--agent", "claude,codex",
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("status error: %v", err)
	}
	for _, want := range []string{"claude", "codex", "未配置", source} {
		if !strings.Contains(stdout.String(), want) {
			t.Fatalf("status output = %q, missing %q", stdout.String(), want)
		}
	}

	stdout.Reset()
	err = run(context.Background(), []string{
		"instruction", "link", "--agent", "claude", "--dry-run",
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("dry-run error: %v", err)
	}
	if !strings.Contains(stdout.String(), "リンク作成") {
		t.Fatalf("dry-run output = %q", stdout.String())
	}
	if _, err := os.Lstat(filepath.Join(home, ".claude", "CLAUDE.md")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("dry-run が配置先を作成しました: %v", err)
	}
}

func TestInstructionLinkRequiresConfirmationForExistingFile(t *testing.T) {
	home := t.TempDir()
	configPath := filepath.Join(t.TempDir(), "instructions.json")
	source := filepath.Join(t.TempDir(), "user-instructions.md")
	target := filepath.Join(home, ".claude", "CLAUDE.md")
	if err := os.WriteFile(source, []byte("# source\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("# keep\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("MCP_DOCKER_INSTRUCTION_HOME", home)
	t.Setenv("MCP_DOCKER_INSTRUCTION_CONFIG", configPath)

	if err := run(context.Background(), []string{
		"instruction", "configure", "--source", source,
	}, &bytes.Buffer{}, &bytes.Buffer{}, strings.NewReader("")); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"instruction", "link", "--agent", "claude",
	}, &stdout, &stderr, strings.NewReader("n\n"))
	if err != nil {
		t.Fatalf("link (拒否) error: %v", err)
	}
	content, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "# keep\n" {
		t.Fatalf("拒否後の既存ファイル = %q", content)
	}
	if !strings.Contains(stdout.String(), "実行しますか？") {
		t.Fatalf("確認プロンプトがありません: %q", stdout.String())
	}

	stdout.Reset()
	err = run(context.Background(), []string{
		"instruction", "link", "--agent", "claude", "--yes",
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		if strings.Contains(err.Error(), "symlink を作成できません") {
			t.Skipf("symlink を作成できない環境です: %v", err)
		}
		t.Fatalf("link (--yes) error: %v", err)
	}
	entries, err := os.ReadDir(filepath.Dir(target))
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 2 {
		t.Fatalf("置換後の配置件数 = %d, want target と backup の2件", len(entries))
	}
	status, err := os.Lstat(target)
	if err != nil {
		t.Fatal(err)
	}
	if status.Mode()&os.ModeSymlink == 0 {
		t.Fatalf("置換後の配置が symlink ではありません: %s", status.Mode())
	}
}

func TestInstructionRepairDoesNotReplaceRegularFile(t *testing.T) {
	home := t.TempDir()
	configPath := filepath.Join(t.TempDir(), "instructions.json")
	source := filepath.Join(t.TempDir(), "user-instructions.md")
	target := filepath.Join(home, ".codex", "AGENTS.md")
	if err := os.WriteFile(source, []byte("# source\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("# keep\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("MCP_DOCKER_INSTRUCTION_HOME", home)
	t.Setenv("MCP_DOCKER_INSTRUCTION_CONFIG", configPath)

	if err := run(context.Background(), []string{
		"instruction", "configure", "--source", source,
	}, &bytes.Buffer{}, &bytes.Buffer{}, strings.NewReader("")); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	err := run(context.Background(), []string{
		"instruction", "repair", "--agent", "codex", "--yes",
	}, &stdout, &stderr, strings.NewReader(""))
	if err != nil {
		t.Fatalf("repair error: %v", err)
	}
	content, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "# keep\n" {
		t.Fatalf("repair 後の通常ファイル = %q", content)
	}
	if !strings.Contains(stdout.String(), "修復対象外") {
		t.Fatalf("repair output = %q", stdout.String())
	}
}
