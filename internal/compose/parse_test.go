package compose

import "testing"

func TestParseRoutesFromComposeEnvironment(t *testing.T) {
	data := []byte(`
services:
  mcp-gateway:
    environment:
      - MCP_GATEWAY_PORT=${MCP_GATEWAY_PORT:-8080}
      - ROUTE_GITHUB=/mcp/github|http://github-mcp:8082
      - ROUTE_COPILOT_REVIEW=/mcp/copilot-review|http://copilot-review-mcp:8083
      - ROUTE_PLAYWRIGHT=/mcp/playwright|http://playwright-mcp:8931|auth=none
`)
	servers, err := Parse(data, func(string) (string, bool) { return "", false })
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]string{
		"copilot-review": "http://127.0.0.1:8080/mcp/copilot-review",
		"github":         "http://127.0.0.1:8080/mcp/github",
		"playwright":     "http://127.0.0.1:8080/mcp/playwright",
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
