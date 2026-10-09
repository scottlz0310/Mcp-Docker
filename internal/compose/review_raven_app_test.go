package compose

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestReviewRavenAppOverride(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.review-raven-app.yml"))
	if err != nil {
		t.Fatal(err)
	}
	var file composeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	if len(file.Services) != 2 {
		t.Fatal("専用App設定が無関係なサービスを変更しています")
	}
	for _, tt := range []struct{ service, name, want string }{
		{"mcp-gateway", "ROUTE_REVIEW_RAVEN", "/mcp/review-raven|http://review-raven:${REVIEW_RAVEN_PORT:-8083}/mcp"},
		{"review-raven", "REVIEW_RAVEN_AUTH_MODE", "github-app"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_ID", "${REVIEW_RAVEN_GITHUB_APP_ID:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID", "${REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_OWNER", "${REVIEW_RAVEN_GITHUB_APP_OWNER:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64", "${REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64:?"},
	} {
		t.Run(tt.name, func(t *testing.T) {
			node := file.Services[tt.service].Environment
			found := false
			for _, entry := range node.Content {
				key, value, _ := strings.Cut(entry.Value, "=")
				if key == tt.name {
					found = true
					if strings.HasPrefix(tt.want, "${") {
						if !strings.HasPrefix(value, tt.want) {
							t.Fatalf("%sの必須注入がありません", key)
						}
					} else if value != tt.want {
						t.Fatalf("%s = %q", key, value)
					}
				}
			}
			if !found {
				t.Fatalf("%sが渡されません", tt.name)
			}
		})
	}
}
