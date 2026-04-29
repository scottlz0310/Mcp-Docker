package external

import "testing"

func TestParseExternalServers(t *testing.T) {
	servers, err := Parse([]byte(`
servers:
  - name: cloudflare-api
    url: https://mcp.cloudflare.com/mcp
    tokenEnv: CLOUDFLARE_API_TOKEN
  - name: supabase
    url: https://mcp.supabase.com/mcp
`))
	if err != nil {
		t.Fatal(err)
	}
	if got, want := len(servers), 2; got != want {
		t.Fatalf("len = %d, want %d", got, want)
	}
	if got, want := servers[0].TokenEnv, "CLOUDFLARE_API_TOKEN"; got != want {
		t.Fatalf("TokenEnv = %q, want %q", got, want)
	}
}
