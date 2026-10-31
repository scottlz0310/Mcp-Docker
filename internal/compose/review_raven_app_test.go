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

func TestRepositoryCommentReaderTrust(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}
	var file composeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name string
		env  map[string]string
		want string
	}{
		{name: "既存リストを共有", env: map[string]string{"REVIEW_RAVEN_TRUSTED_COMMENT_AUTHORS": "reviewer[bot],operator"}, want: "reviewer[bot],operator"},
		{name: "未設定は空", env: map[string]string{}},
		{name: "明示的な空", env: map[string]string{"REVIEW_RAVEN_TRUSTED_COMMENT_AUTHORS": ""}},
		{name: "PR作成者許可を流用しない", env: map[string]string{"THREAD_OWL_ALLOWED_AUTHORS": "pr-author"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			for _, service := range []string{"review-raven", "thread-owl"} {
				t.Run(service, func(t *testing.T) {
					env, err := environmentMap(file.Services[service].Environment)
					if err != nil {
						t.Fatal(err)
					}
					raw, found := env["TRUSTED_COMMENT_AUTHORS"]
					if !found {
						t.Fatal("readerの投稿者許可リストが渡されません")
					}
					got := expandComposeVars(raw, func(key string) (string, bool) {
						value, ok := tc.env[key]
						return value, ok
					})
					if got != tc.want {
						t.Fatalf("readerの投稿者許可リスト = %q, want %q", got, tc.want)
					}
				})
			}
		})
	}
}
