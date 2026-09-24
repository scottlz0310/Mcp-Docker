//go:build e2e

package skill_test

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"
	"time"

	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

type agySkillsResponse struct {
	Command struct {
		Data struct {
			Skills []struct {
				Name string `json:"name"`
				Path string `json:"path"`
			} `json:"skills"`
		} `json:"data"`
	} `json:"command"`
}

func TestAntigravitySkillDiscoveryE2E(t *testing.T) {
	agyPath, err := exec.LookPath("agy")
	if err != nil {
		t.Skip("agy CLI not found in PATH")
	}

	tmpHome := t.TempDir()

	// 1. Antigravity クライアント取得
	clients := skill.Clients(tmpHome)
	var agyClient *skill.Client
	for _, c := range clients {
		if c.Name == "antigravity" {
			agyClient = &c
			break
		}
	}
	if agyClient == nil {
		t.Fatal("antigravity client not found")
	}

	// 期待配置先が .gemini/config/skills であることを確認
	expectedSkillDir := filepath.Join(tmpHome, ".gemini", "config", "skills")
	if agyClient.Dir != expectedSkillDir {
		t.Fatalf("agyClient.Dir = %q, want %q", agyClient.Dir, expectedSkillDir)
	}

	// 2. テスト用スキルカタログをロード＆インストール
	testSkillMD := `---
name: e2e-test-skill
description: E2E Test Skill for Antigravity discovery
---
# E2E Test Skill
`
	fsys := fstest.MapFS{
		"skills/e2e-test-skill/SKILL.md": {Data: []byte(testSkillMD)},
		"skills/catalog.json":            {Data: []byte(`{"skills": {"e2e-test-skill": {"revision": 1}}}`)},
	}
	catalog, err := skill.LoadCatalog(fsys, "skills")
	if err != nil {
		t.Fatalf("LoadCatalog failed: %v", err)
	}
	s := catalog[0]

	status, err := skill.Inspect(*agyClient, s)
	if err != nil {
		t.Fatalf("Inspect failed: %v", err)
	}
	plan := skill.PlanInstall(status, s, false)
	if err := skill.Install(plan, s, "v1.0.0", time.Now()); err != nil {
		t.Fatalf("Install failed: %v", err)
	}

	// 3. agy を一時ホーム（USERPROFILE / HOME）に向けて実行
	// 既存の USERPROFILE / HOME を一時ディレクトリに上書き
	env := make([]string, 0, len(os.Environ())+2)
	for _, e := range os.Environ() {
		if strings.HasPrefix(strings.ToUpper(e), "USERPROFILE=") || strings.HasPrefix(strings.ToUpper(e), "HOME=") {
			continue
		}
		env = append(env, e)
	}
	env = append(env, "USERPROFILE="+tmpHome, "HOME="+tmpHome)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, agyPath, "-p", "/skills", "--output-format", "json")
	cmd.Env = env
	out, err := cmd.CombinedOutput()
	if err != nil {
		outStr := string(out)
		if strings.Contains(outStr, "Waiting for authentication") || strings.Contains(outStr, "accounts.google.com") {
			t.Skipf("agy is unauthenticated; skipping E2E test in non-interactive environment")
		}
		t.Fatalf("agy command failed: %v, output: %s", err, outStr)
	}

	var resp agySkillsResponse
	if err := json.Unmarshal(out, &resp); err != nil {
		t.Fatalf("json unmarshal failed: %v, raw output: %s", err, string(out))
	}

	// 4. agy がスキルを認識し、パスが .gemini/config/skills 配下になっていることを検証
	var found bool
	var detectedPath string
	for _, item := range resp.Command.Data.Skills {
		if item.Name == "e2e-test-skill" {
			found = true
			detectedPath = item.Path
			break
		}
	}

	if !found {
		t.Fatalf("skill %q not discovered by agy; discovered skills: %+v", "e2e-test-skill", resp.Command.Data.Skills)
	}

	wantPath := filepath.Join(expectedSkillDir, "e2e-test-skill", "SKILL.md")
	if !strings.EqualFold(filepath.Clean(detectedPath), filepath.Clean(wantPath)) {
		t.Fatalf("detected skill path = %q, want %q", detectedPath, wantPath)
	}
}
