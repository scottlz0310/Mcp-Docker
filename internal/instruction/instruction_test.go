package instruction

import (
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestClients(t *testing.T) {
	home := filepath.Join("test-home")
	clients := Clients(home)
	want := map[string]string{
		"claude":      filepath.Join(home, ".claude", "CLAUDE.md"),
		"copilot":     filepath.Join(home, ".copilot", "copilot-instructions.md"),
		"codex":       filepath.Join(home, ".codex", "AGENTS.md"),
		"antigravity": filepath.Join(home, ".gemini", "GEMINI.md"),
	}
	if len(clients) != len(want) {
		t.Fatalf("Clients() の件数 = %d, want %d", len(clients), len(want))
	}
	for _, client := range clients {
		if client.Path != want[client.Name] {
			t.Errorf("%s のパス = %s, want %s", client.Name, client.Path, want[client.Name])
		}
	}
}

func TestConfigRoundTrip(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "nested", "instructions.json")
	t.Setenv("MCP_DOCKER_INSTRUCTION_CONFIG", configPath)

	source := filepath.Join(t.TempDir(), "CLAUDE.md")
	if err := os.WriteFile(source, []byte("# user instructions\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := SaveConfig(Config{Source: source, Mode: ModeSymlink}); err != nil {
		t.Fatal(err)
	}

	got, err := Resolve("")
	if err != nil {
		t.Fatal(err)
	}
	if got.Source != source || got.Mode != ModeSymlink {
		t.Fatalf("Resolve() = %#v, want source=%q mode=%q", got, source, ModeSymlink)
	}
	if _, err := os.Stat(configPath); err != nil {
		t.Fatalf("設定ファイルが作成されていません: %v", err)
	}
}

func TestLinkCreatesIdempotentSymlinkAndBacksUpExistingFile(t *testing.T) {
	source := filepath.Join(t.TempDir(), "CLAUDE.md")
	if err := os.WriteFile(source, []byte("# user instructions\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), ".claude", "CLAUDE.md")
	client := Client{Name: "claude", Path: target}
	now := time.Date(2026, 9, 17, 1, 2, 3, 4, time.UTC)

	result, err := Link(source, client, now)
	if err != nil {
		if errors.Is(err, os.ErrPermission) {
			t.Skipf("symlink を作成できない環境です: %v", err)
		}
		t.Fatal(err)
	}
	if result.Action != ActionLink {
		t.Fatalf("初回 Link() action = %q, want %q", result.Action, ActionLink)
	}
	status, err := Inspect(source, client)
	if err != nil {
		t.Fatal(err)
	}
	if status.State != StateLinked {
		t.Fatalf("初回配置後の state = %q, want %q", status.State, StateLinked)
	}
	if status.LinkType != "symlink" {
		t.Fatalf("初回配置後の link type = %q, want symlink", status.LinkType)
	}

	result, err = Link(source, client, now)
	if err != nil {
		t.Fatal(err)
	}
	if result.Action != ActionSkip {
		t.Fatalf("同一リンクの Link() action = %q, want %q", result.Action, ActionSkip)
	}

	if err := os.Remove(target); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("keep this file\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	result, err = Link(source, client, now)
	if err != nil {
		t.Fatal(err)
	}
	if result.Action != ActionReplace || result.BackupPath == "" {
		t.Fatalf("既存ファイル置換の結果 = %#v", result)
	}
	backup, err := os.ReadFile(result.BackupPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(backup) != "keep this file\n" {
		t.Fatalf("バックアップ内容 = %q", backup)
	}
	status, err = Inspect(source, client)
	if err != nil {
		t.Fatal(err)
	}
	if status.State != StateLinked {
		t.Fatalf("置換後の state = %q, want %q", status.State, StateLinked)
	}
}

func TestInspectClassifiesDirectoryAndBrokenLink(t *testing.T) {
	source := filepath.Join(t.TempDir(), "CLAUDE.md")
	if err := os.WriteFile(source, []byte("# user instructions\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), ".claude", "CLAUDE.md")
	client := Client{Name: "claude", Path: target}
	if err := os.MkdirAll(target, 0o700); err != nil {
		t.Fatal(err)
	}
	status, err := Inspect(source, client)
	if err != nil {
		t.Fatal(err)
	}
	if status.State != StateDirectory {
		t.Fatalf("directory state = %q, want %q", status.State, StateDirectory)
	}
	if err := os.RemoveAll(target); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(t.TempDir(), "missing.md"), target); err != nil {
		if errors.Is(err, os.ErrPermission) {
			t.Skipf("symlink を作成できない環境です: %v", err)
		}
		t.Fatal(err)
	}
	status, err = Inspect(source, client)
	if err != nil {
		t.Fatal(err)
	}
	if status.State != StateBroken {
		t.Fatalf("broken link state = %q, want %q", status.State, StateBroken)
	}
	if _, err := os.Stat(target); !errors.Is(err, fs.ErrNotExist) {
		t.Fatalf("壊れたリンクの Stat() error = %v, want not-exist", err)
	}
}

func TestValidateSourceRejectsDirectory(t *testing.T) {
	if _, err := ValidateSource(t.TempDir()); err == nil {
		t.Fatal("ディレクトリを source として受け入れました")
	}
}
