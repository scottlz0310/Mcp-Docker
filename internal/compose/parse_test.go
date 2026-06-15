package compose

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestParseRoutesFromComposeEnvironment(t *testing.T) {
	data := []byte(`
services:
  mcp-gateway:
    environment:
      - MCP_GATEWAY_PORT=${MCP_GATEWAY_PORT:-8080}
      - ROUTE_GITHUB=/mcp/github|http://github-mcp:8082
      - ROUTE_REVIEW_RAVEN=/mcp/review-raven|http://review-raven:8083
      - ROUTE_PLAYWRIGHT=/mcp/playwright|http://playwright-mcp:8931|auth=none
`)
	servers, err := Parse(data, func(string) (string, bool) { return "", false })
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]string{
		"review-raven": "http://127.0.0.1:8080/mcp/review-raven",
		"github":       "http://127.0.0.1:8080/mcp/github",
		"playwright":   "http://127.0.0.1:8080/mcp/playwright",
	}
	if len(servers) != len(want) {
		t.Fatalf("got %d servers, want %d", len(servers), len(want))
	}
	for _, server := range servers {
		if got := server.URL; got != want[server.Name] {
			t.Fatalf("%s URL = %q, want %q", server.Name, got, want[server.Name])
		}
		if server.Source == "" {
			t.Fatalf("%s Source is empty", server.Name)
		}
	}
}

func TestRepositoryComposeMCPRouteContract(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}

	gateway, err := gatewayEnv(data)
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name string
		key  string
		want string
	}{
		{
			name: "review-raven の upstream endpoint",
			key:  "ROUTE_REVIEW_RAVEN",
			want: "/mcp/review-raven|http://review-raven:${REVIEW_RAVEN_PORT:-8083}/mcp",
		},
		{
			name: "thread-owl の upstream endpoint",
			key:  "ROUTE_THREAD_OWL",
			want: "/mcp/thread-owl|http://thread-owl:${THREAD_OWL_PORT:-3000}/mcp",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := gateway[tt.key]; got != tt.want {
				t.Fatalf("%s = %q, want %q", tt.key, got, tt.want)
			}
		})
	}

	var file composeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	threadOwl, ok := file.Services["thread-owl"]
	if !ok {
		t.Fatal("services.thread-owl not found")
	}
	threadOwlEnv, err := environmentMap(threadOwl.Environment)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := threadOwlEnv["MCP_HTTP_PATH"]; ok {
		t.Fatal("thread-owl must use its default /mcp endpoint")
	}
}

func TestParseUsesEnvironmentPortOverride(t *testing.T) {
	data := []byte(`
services:
  mcp-gateway:
    environment:
      MCP_GATEWAY_PORT: ${MCP_GATEWAY_PORT:-8080}
      ROUTE_GITHUB: /mcp/github|http://github-mcp:8082
`)
	servers, err := Parse(data, func(key string) (string, bool) {
		if key == "MCP_GATEWAY_PORT" {
			return "18080", true
		}
		return "", false
	})
	if err != nil {
		t.Fatal(err)
	}
	if got, want := servers[0].URL, "http://127.0.0.1:18080/mcp/github"; got != want {
		t.Fatalf("URL = %q, want %q", got, want)
	}
}

func TestParseExpandsRouteVariables(t *testing.T) {
	const cloudflareRoute = "ROUTE_CLOUDFLARE=${CLOUDFLARE_API_TOKEN:+/mcp/cloudflare|https://mcp.cloudflare.com/mcp|auth=oauth|upstream_bearer_token_env=CLOUDFLARE_API_TOKEN}"

	tests := []struct {
		name   string
		env    map[string]string
		routes []string
		want   map[string]string
	}{
		{
			name:   "変数設定済みなら :+ ルートが登録される",
			env:    map[string]string{"CLOUDFLARE_API_TOKEN": "dummy-token"},
			routes: []string{cloudflareRoute},
			want:   map[string]string{"cloudflare": "http://127.0.0.1:8080/mcp/cloudflare"},
		},
		{
			name:   "変数未設定なら :+ ルートはスキップされる",
			env:    map[string]string{},
			routes: []string{cloudflareRoute},
			want:   map[string]string{},
		},
		{
			name: "path 内の ${VAR} と ${VAR:-default} を展開する",
			env:  map[string]string{"GITHUB_PATH": "/mcp/github"},
			routes: []string{
				"ROUTE_GITHUB=${GITHUB_PATH}|http://github-mcp:8082",
				"ROUTE_PLAYWRIGHT=${PLAYWRIGHT_PATH:-/mcp/playwright}|http://playwright-mcp:8931|auth=none",
			},
			want: map[string]string{
				"github":     "http://127.0.0.1:8080/mcp/github",
				"playwright": "http://127.0.0.1:8080/mcp/playwright",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			lines := []string{"services:", "  mcp-gateway:", "    environment:"}
			for _, route := range tt.routes {
				lines = append(lines, "      - "+route)
			}
			data := []byte(strings.Join(lines, "\n") + "\n")

			servers, err := Parse(data, func(key string) (string, bool) {
				val, ok := tt.env[key]
				return val, ok
			})
			if err != nil {
				t.Fatal(err)
			}
			if len(servers) != len(tt.want) {
				t.Fatalf("got %d servers (%v), want %d", len(servers), servers, len(tt.want))
			}
			for _, server := range servers {
				if got := server.URL; got != tt.want[server.Name] {
					t.Fatalf("%s URL = %q, want %q", server.Name, got, tt.want[server.Name])
				}
			}
		})
	}
}

func TestGatewayOrigin(t *testing.T) {
	const portYAML = `
services:
  mcp-gateway:
    environment:
      - MCP_GATEWAY_PORT=${MCP_GATEWAY_PORT:-9090}
`
	cases := []struct {
		name string
		yaml string
		env  map[string]string
		want string
	}{
		{
			name: "environment 未定義ならデフォルトポート",
			yaml: "services:\n  mcp-gateway: {}\n",
			want: "http://127.0.0.1:8080/",
		},
		{
			name: "compose の既定値を展開",
			yaml: portYAML,
			want: "http://127.0.0.1:9090/",
		},
		{
			name: "実環境変数が優先される",
			yaml: portYAML,
			env:  map[string]string{"MCP_GATEWAY_PORT": "7000"},
			want: "http://127.0.0.1:7000/",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := gatewayOrigin([]byte(tc.yaml), func(key string) (string, bool) {
				val, ok := tc.env[key]
				return val, ok
			})
			if err != nil {
				t.Fatal(err)
			}
			if got != tc.want {
				t.Fatalf("origin = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestParseHandlesUnsupportedVariables(t *testing.T) {
	data := []byte(`
services:
  mcp-gateway:
    environment:
      - ROUTE_GITHUB=${UNSUPPORTED-default}|http://github-mcp:8082
`)
	servers, err := Parse(data, func(key string) (string, bool) {
		return "", false
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(servers) != 1 {
		t.Fatalf("got %d servers, want 1", len(servers))
	}
	if got, want := servers[0].URL, "http://127.0.0.1:8080/${UNSUPPORTED-default}"; got != want {
		t.Fatalf("URL = %q, want %q", got, want)
	}
}
