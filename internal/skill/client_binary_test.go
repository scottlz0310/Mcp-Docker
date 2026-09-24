package skill_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

// TestAntigravityBinarySkillPathMatch は、実 agy バイナリ内の埋め込み探索パス定数を
// 静的解析（バイナリ走査）し、Mcp-Docker の clientLayouts の定義と一致しているかを検証する。
// agy プロセスを起動しないため、CI 上の無認証 runner でも高速かつ安全に仕様乖離を検知できる。
func TestAntigravityBinarySkillPathMatch(t *testing.T) {
	agyPath, err := exec.LookPath("agy")
	if err != nil {
		t.Skip("agy CLI not found in PATH")
	}

	data, err := os.ReadFile(agyPath)
	if err != nil {
		t.Fatalf("failed to read agy binary at %s: %v", agyPath, err)
	}

	// バイナリ内の .gemini/.../skills 探索パスを抽出
	re := regexp.MustCompile(`\.gemini[/\\][a-zA-Z0-9_\-\/\\]*skills[/\\]?`)
	matches := re.FindAllString(string(data), -1)
	if len(matches) == 0 {
		t.Fatalf("no skill discovery path found in agy binary at %s", agyPath)
	}

	// 抽出されたパスをスラッシュ区切りで正規化（例: ".gemini/config/skills"）
	detectedRaw := filepath.ToSlash(matches[0])
	detected := strings.Trim(strings.TrimPrefix(detectedRaw, "/"), "/")

	// Mcp-Docker 側の Antigravity クライアント定義を取得
	dummyHome := filepath.Join("dummy", "home")
	clients := skill.Clients(dummyHome)
	var agyClient *skill.Client
	for _, c := range clients {
		if c.Name == "antigravity" {
			agyClient = &c
			break
		}
	}
	if agyClient == nil {
		t.Fatal("antigravity client definition not found in Mcp-Docker")
	}

	// Mcp-Docker の定義パス（dummy/home/.gemini/config/skills）から相対部分を抽出
	rel, err := filepath.Rel(dummyHome, agyClient.Dir)
	if err != nil {
		t.Fatalf("filepath.Rel failed: %v", err)
	}
	expected := filepath.ToSlash(rel)

	if !strings.EqualFold(detected, expected) {
		t.Fatalf("Antigravity CLI binary discovery path mismatch: agy expects %q, but Mcp-Docker defines %q", detected, expected)
	}
}
