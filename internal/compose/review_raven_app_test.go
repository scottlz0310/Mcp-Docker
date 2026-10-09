package compose

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestRepositoryReviewRavenAppContract(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}
	var file composeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	for _, tt := range []struct{ service, name, want string }{
		{"mcp-gateway", "REVIEW_RAVEN_PROXY_SECRET", "${REVIEW_RAVEN_PROXY_SECRET:?"},
		{"review-raven", "REVIEW_RAVEN_AUTH_MODE", "github-app"},
		{"review-raven", "REVIEW_RAVEN_PROXY_SECRET", "${REVIEW_RAVEN_PROXY_SECRET:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_ID", "${REVIEW_RAVEN_GITHUB_APP_ID:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID", "${REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_OWNER", "${REVIEW_RAVEN_GITHUB_APP_OWNER:?"},
		{"review-raven", "REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64", "${REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64:?"},
	} {
		t.Run(tt.name, func(t *testing.T) {
			env, err := environmentMap(file.Services[tt.service].Environment)
			if err != nil {
				t.Fatal(err)
			}
			value, found := env[tt.name]
			if !found {
				t.Fatalf("%sが渡されません", tt.name)
			}
			if strings.HasPrefix(tt.want, "${") {
				if !strings.HasPrefix(value, tt.want) {
					t.Fatalf("%sの必須注入がありません", tt.name)
				}
			} else if value != tt.want {
				t.Fatalf("%s = %q", tt.name, value)
			}
		})
	}
}
