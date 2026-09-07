package skill

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"
	"time"
)

func newTestClient(t *testing.T) Client {
	t.Helper()
	return Client{Name: "claude", Dir: filepath.Join(t.TempDir(), "skills")}
}

func loadOne(t *testing.T, fsys fstest.MapFS) Skill {
	t.Helper()
	skills, err := LoadCatalog(fsys, "skills")
	if err != nil {
		t.Fatalf("LoadCatalog returned error: %v", err)
	}
	return skills[0]
}

func alphaV1(t *testing.T) Skill {
	t.Helper()
	return loadOne(t, fstest.MapFS{
		"skills/alpha/SKILL.md":           {Data: []byte("v1\n")},
		"skills/alpha/agents/openai.yaml": {Data: []byte("v1 agent\n")},
	})
}

func alphaV2(t *testing.T) Skill {
	t.Helper()
	return loadOne(t, fstest.MapFS{"skills/alpha/SKILL.md": {Data: []byte("v2\n")}})
}

func install(t *testing.T, client Client, s Skill, version string) {
	t.Helper()
	status, err := Inspect(client, s)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	plan := PlanInstall(status, s, false)
	if err := Install(plan, s, version, time.Unix(0, 0)); err != nil {
		t.Fatalf("Install returned error: %v", err)
	}
}

func TestInstallWritesFilesAndManifest(t *testing.T) {
	client := newTestClient(t)
	s := alphaV1(t)
	install(t, client, s, "9.9.9")

	dir := filepath.Join(client.Dir, "alpha")
	for _, rel := range []string{"SKILL.md", filepath.Join("agents", "openai.yaml"), ManifestName} {
		if _, err := os.Stat(filepath.Join(dir, rel)); err != nil {
			t.Fatalf("expected %s to exist: %v", rel, err)
		}
	}

	status, err := Inspect(client, s)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	if status.State != StateUpToDate {
		t.Fatalf("state = %s, want %s", status.State, StateUpToDate)
	}
	if status.InstalledVersion != "9.9.9" {
		t.Fatalf("installed version = %q, want 9.9.9", status.InstalledVersion)
	}
}

func TestInstallIsIdempotent(t *testing.T) {
	client := newTestClient(t)
	s := alphaV1(t)
	install(t, client, s, "1.0.0")

	status, err := Inspect(client, s)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	plan := PlanInstall(status, s, false)
	if plan.Action != ActionSkip {
		t.Fatalf("action = %s, want %s", plan.Action, ActionSkip)
	}
	if len(plan.Write) != 0 || len(plan.Delete) != 0 {
		t.Fatalf("skip plan must not touch files: write=%v delete=%v", plan.Write, plan.Delete)
	}
}

func TestInstallForceRewritesUpToDate(t *testing.T) {
	client := newTestClient(t)
	s := alphaV1(t)
	install(t, client, s, "1.0.0")

	status, err := Inspect(client, s)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	plan := PlanInstall(status, s, true)
	if plan.Action != ActionUpdate {
		t.Fatalf("action = %s, want %s", plan.Action, ActionUpdate)
	}
}

func TestInstallRemovesObsoleteManagedFilesOnly(t *testing.T) {
	client := newTestClient(t)
	install(t, client, alphaV1(t), "1.0.0")

	dir := filepath.Join(client.Dir, "alpha")
	userFile := filepath.Join(dir, "user-notes.md")
	if err := os.WriteFile(userFile, []byte("keep me\n"), 0o644); err != nil {
		t.Fatalf("failed to seed user file: %v", err)
	}

	// v2 では agents/openai.yaml が無くなっている。
	v2 := alphaV2(t)
	status, err := Inspect(client, v2)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	if status.State != StateOutdated {
		t.Fatalf("state = %s, want %s", status.State, StateOutdated)
	}
	plan := PlanInstall(status, v2, false)
	if want := []string{"agents/openai.yaml"}; strings.Join(plan.Delete, ",") != strings.Join(want, ",") {
		t.Fatalf("delete = %v, want %v", plan.Delete, want)
	}
	if err := Install(plan, v2, "2.0.0", time.Unix(0, 0)); err != nil {
		t.Fatalf("Install returned error: %v", err)
	}

	if _, err := os.Stat(filepath.Join(dir, "agents")); !os.IsNotExist(err) {
		t.Fatalf("empty agents directory should be cleaned up, err = %v", err)
	}
	// mcp-docker が配置していないファイルは削除しない。
	if _, err := os.Stat(userFile); err != nil {
		t.Fatalf("user file must survive an update: %v", err)
	}
}

func TestInspectStates(t *testing.T) {
	s := alphaV1(t)

	tests := []struct {
		name  string
		setup func(t *testing.T, client Client)
		want  State
	}{
		{
			name:  "absent",
			setup: func(*testing.T, Client) {},
			want:  StateAbsent,
		},
		{
			name: "up to date",
			setup: func(t *testing.T, client Client) {
				install(t, client, s, "1.0.0")
			},
			want: StateUpToDate,
		},
		{
			name: "outdated",
			setup: func(t *testing.T, client Client) {
				install(t, client, alphaV2(t), "1.0.0")
			},
			want: StateOutdated,
		},
		{
			name: "modified after install",
			setup: func(t *testing.T, client Client) {
				install(t, client, s, "1.0.0")
				path := filepath.Join(client.Dir, "alpha", "SKILL.md")
				if err := os.WriteFile(path, []byte("local edit\n"), 0o644); err != nil {
					t.Fatalf("failed to edit installed skill: %v", err)
				}
			},
			want: StateModified,
		},
		{
			name: "unmanaged copy",
			setup: func(t *testing.T, client Client) {
				dir := filepath.Join(client.Dir, "alpha")
				if err := os.MkdirAll(dir, 0o755); err != nil {
					t.Fatalf("failed to create dir: %v", err)
				}
				if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("hand copied\n"), 0o644); err != nil {
					t.Fatalf("failed to seed skill: %v", err)
				}
			},
			want: StateUnmanaged,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			client := newTestClient(t)
			tt.setup(t, client)
			status, err := Inspect(client, s)
			if err != nil {
				t.Fatalf("Inspect returned error: %v", err)
			}
			if status.State != tt.want {
				t.Fatalf("state = %s, want %s", status.State, tt.want)
			}
		})
	}
}

func TestPlanInstallActions(t *testing.T) {
	tests := []struct {
		name       string
		state      State
		force      bool
		want       Action
		wantConfrm bool
	}{
		{name: "absent installs", state: StateAbsent, want: ActionInstall},
		{name: "outdated updates", state: StateOutdated, want: ActionUpdate},
		{name: "modified updates", state: StateModified, want: ActionUpdate},
		{name: "up to date skips", state: StateUpToDate, want: ActionSkip},
		{name: "up to date with force updates", state: StateUpToDate, force: true, want: ActionUpdate},
		{name: "unmanaged needs confirmation", state: StateUnmanaged, want: ActionAdopt, wantConfrm: true},
	}
	s := alphaV1(t)
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			plan := PlanInstall(Status{State: tt.state}, s, tt.force)
			if plan.Action != tt.want {
				t.Fatalf("action = %s, want %s", plan.Action, tt.want)
			}
			if plan.NeedsConfirm() != tt.wantConfrm {
				t.Fatalf("NeedsConfirm() = %v, want %v", plan.NeedsConfirm(), tt.wantConfrm)
			}
		})
	}
}

func TestPlanRemove(t *testing.T) {
	tests := []struct {
		name  string
		state State
		force bool
		want  Action
	}{
		{name: "absent skips", state: StateAbsent, want: ActionSkip},
		{name: "managed removes", state: StateUpToDate, want: ActionRemove},
		{name: "unmanaged skips without force", state: StateUnmanaged, want: ActionSkip},
		{name: "unmanaged removes with force", state: StateUnmanaged, force: true, want: ActionRemove},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			plan := PlanRemove(Status{State: tt.state}, tt.force)
			if plan.Action != tt.want {
				t.Fatalf("action = %s, want %s", plan.Action, tt.want)
			}
		})
	}
}

func TestRemoveDeletesInstalledSkill(t *testing.T) {
	client := newTestClient(t)
	s := alphaV1(t)
	install(t, client, s, "1.0.0")

	status, err := Inspect(client, s)
	if err != nil {
		t.Fatalf("Inspect returned error: %v", err)
	}
	if err := Remove(PlanRemove(status, false)); err != nil {
		t.Fatalf("Remove returned error: %v", err)
	}
	if _, err := os.Stat(filepath.Join(client.Dir, "alpha")); !os.IsNotExist(err) {
		t.Fatalf("skill directory should be gone, err = %v", err)
	}
}

func TestRemoveRelativeRejectsEscape(t *testing.T) {
	dir := t.TempDir()
	err := removeRelative(dir, "../escape.md")
	if err == nil || !strings.Contains(err.Error(), "外を指す削除対象") {
		t.Fatalf("error = %v, want an escape rejection", err)
	}
}
