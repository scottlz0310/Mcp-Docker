package compose

import (
	"os"
	"path/filepath"
	"slices"
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
			name: "github の upstream endpoint（GitHub App token 注入・auth=none なし）",
			key:  "ROUTE_GITHUB",
			want: "/mcp/github|http://github-mcp:${GITHUB_MCP_HTTP_PORT:-8082}|upstream_github_app=true",
		},
		{
			name: "review-raven の upstream endpoint（専用proxyの共有Bearer注入）",
			key:  "ROUTE_REVIEW_RAVEN",
			want: "/mcp/review-raven|http://review-raven:${REVIEW_RAVEN_PORT:-8083}/mcp|upstream_bearer_token_env=REVIEW_RAVEN_PROXY_SECRET",
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

	for _, serviceName := range []string{"github-mcp", "mcp-gateway", "review-raven"} {
		service, ok := file.Services[serviceName]
		if !ok {
			t.Fatalf("services.%s not found", serviceName)
		}
		env, envErr := environmentMap(service.Environment)
		if envErr != nil {
			t.Fatal(envErr)
		}
		for _, key := range []string{
			"GITHUB_PERSONAL_ACCESS_TOKEN",
			"MCP_GITHUB_PAT",
			"REVIEW_RAVEN_DEFAULT_USER",
			"GITHUB_APP_CLIENT_ID",
			"GITHUB_MCP_CLIENT_ID",
			"GITHUB_MCP_CLIENT_SECRET",
			"GITHUB_MCP_OAUTH_SCOPES",
		} {
			if _, exists := env[key]; exists {
				t.Fatalf("services.%s must not receive deprecated credential %s", serviceName, key)
			}
		}
		if serviceName == "mcp-gateway" && env["GITHUB_APP_ID"] != "${GITHUB_APP_ID}" {
			t.Fatalf("services.mcp-gateway must receive the numeric GITHUB_APP_ID")
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

func TestParseUsesPublicURLOverride(t *testing.T) {
	data := []byte(`
services:
  mcp-gateway:
    environment:
      MCP_GATEWAY_PORT: ${MCP_GATEWAY_PORT:-8080}
      ROUTE_GITHUB: /mcp/github|http://github-mcp:8082
`)
	tests := []struct {
		name string
		env  map[string]string
		want string
	}{
		{
			name: "MCP_GATEWAY_PUBLIC_URL が HTTPS なら HTTPS URL を登録する",
			env:  map[string]string{"MCP_GATEWAY_PUBLIC_URL": "https://localhost:8080"},
			want: "https://localhost:8080/mcp/github",
		},
		{
			name: "PUBLIC_URL の末尾スラッシュは正規化される",
			env:  map[string]string{"MCP_GATEWAY_PUBLIC_URL": "https://localhost:8080/"},
			want: "https://localhost:8080/mcp/github",
		},
		{
			name: "旧名 MCP_GATEWAY_BASE_URL にフォールバックする",
			env:  map[string]string{"MCP_GATEWAY_BASE_URL": "https://localhost:9443"},
			want: "https://localhost:9443/mcp/github",
		},
		{
			name: "PUBLIC_URL は MCP_GATEWAY_PORT より優先される",
			env: map[string]string{
				"MCP_GATEWAY_PUBLIC_URL": "https://localhost:8443",
				"MCP_GATEWAY_PORT":       "18080",
			},
			want: "https://localhost:8443/mcp/github",
		},
		{
			name: "未設定なら従来どおり http://127.0.0.1 を使用する",
			env:  map[string]string{},
			want: "http://127.0.0.1:8080/mcp/github",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			servers, err := Parse(data, func(key string) (string, bool) {
				val, ok := tt.env[key]
				return val, ok
			})
			if err != nil {
				t.Fatal(err)
			}
			if got := servers[0].URL; got != tt.want {
				t.Fatalf("URL = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestGatewayOrigins(t *testing.T) {
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
		want []string
	}{
		{
			name: "environment 未定義ならデフォルトポート",
			yaml: "services:\n  mcp-gateway: {}\n",
			want: []string{"http://127.0.0.1:8080/"},
		},
		{
			name: "compose の既定値を展開",
			yaml: portYAML,
			want: []string{"http://127.0.0.1:9090/"},
		},
		{
			name: "実環境変数が優先される",
			yaml: portYAML,
			env:  map[string]string{"MCP_GATEWAY_PORT": "7000"},
			want: []string{"http://127.0.0.1:7000/"},
		},
		{
			name: "PUBLIC_URL 設定時はデフォルト origin も併せて返す",
			yaml: portYAML,
			env:  map[string]string{"MCP_GATEWAY_PUBLIC_URL": "https://localhost:8080"},
			want: []string{"https://localhost:8080/", "http://127.0.0.1:9090/"},
		},
		{
			name: "PUBLIC_URL がデフォルト origin と同値なら重複しない",
			yaml: portYAML,
			env:  map[string]string{"MCP_GATEWAY_PUBLIC_URL": "http://127.0.0.1:9090"},
			want: []string{"http://127.0.0.1:9090/"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := gatewayOrigins([]byte(tc.yaml), func(key string) (string, bool) {
				val, ok := tc.env[key]
				return val, ok
			})
			if err != nil {
				t.Fatal(err)
			}
			if len(got) != len(tc.want) {
				t.Fatalf("origins = %v, want %v", got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Fatalf("origins = %v, want %v", got, tc.want)
				}
			}
		})
	}
}

func TestGatewayOriginsFromFile(t *testing.T) {
	// 空文字の Setenv で実環境の値を無効化する（gatewayBaseURL / gatewayPort は空値を未設定扱いする）
	for _, key := range []string{"MCP_GATEWAY_PUBLIC_URL", "MCP_GATEWAY_BASE_URL", "MCP_GATEWAY_PORT"} {
		t.Setenv(key, "")
	}

	t.Run("compose ファイルから origin を読み取る", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "docker-compose.yml")
		if err := os.WriteFile(path, []byte("services:\n  mcp-gateway: {}\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		got, err := GatewayOrigins(path)
		if err != nil {
			t.Fatal(err)
		}
		want := []string{"http://127.0.0.1:8080/"}
		if len(got) != 1 || got[0] != want[0] {
			t.Fatalf("origins = %v, want %v", got, want)
		}
	})

	t.Run("ファイルが存在しなければエラーを返す", func(t *testing.T) {
		if _, err := GatewayOrigins(filepath.Join(t.TempDir(), "missing.yml")); err == nil {
			t.Fatal("expected error for missing compose file")
		}
	})
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

func TestExpandComposeVars(t *testing.T) {
	const playwrightRoute = "${PLAYWRIGHT_MCP_ENABLED:+/mcp/playwright|http://playwright-mcp:${PLAYWRIGHT_MCP_PORT:-8931}|auth=none}"

	tests := []struct {
		name string
		raw  string
		env  map[string]string
		want string
	}{
		{name: "変数なし", raw: "/mcp/github|http://github-mcp:8082", want: "/mcp/github|http://github-mcp:8082"},
		{name: "${VAR} は値に置き換わる", raw: "pre-${A}-post", env: map[string]string{"A": "x"}, want: "pre-x-post"},
		{name: "${VAR} は未設定なら空", raw: "pre-${A}-post", want: "pre--post"},
		{name: "${VAR:-default} は設定済みなら値", raw: "${A:-d}", env: map[string]string{"A": "x"}, want: "x"},
		{name: "${VAR:-default} は未設定なら default", raw: "${A:-d}", want: "d"},
		{name: "${VAR:-default} は空文字なら default", raw: "${A:-d}", env: map[string]string{"A": ""}, want: "d"},
		{name: "${VAR:+alt} は設定済みなら alt", raw: "${A:+alt}", env: map[string]string{"A": "x"}, want: "alt"},
		{name: "${VAR:+alt} は未設定なら空", raw: "${A:+alt}", want: ""},
		{name: "default の中の入れ子（外側が設定済み）", raw: "${A:-${B:-c}}", env: map[string]string{"A": "a", "B": "b"}, want: "a"},
		{name: "default の中の入れ子（内側が設定済み）", raw: "${A:-${B:-c}}", env: map[string]string{"B": "b"}, want: "b"},
		{name: "default の中の入れ子（どちらも未設定）", raw: "${A:-${B:-c}}", want: "c"},
		{
			name: "alt の中の入れ子（無効の間は、ルートが空になる）",
			raw:  playwrightRoute,
			want: "",
		},
		{
			name: "alt の中の入れ子（有効、ポートは既定）",
			raw:  playwrightRoute,
			env:  map[string]string{"PLAYWRIGHT_MCP_ENABLED": "1"},
			want: "/mcp/playwright|http://playwright-mcp:8931|auth=none",
		},
		{
			name: "alt の中の入れ子（有効、ポートを指定）",
			raw:  playwrightRoute,
			env:  map[string]string{"PLAYWRIGHT_MCP_ENABLED": "1", "PLAYWRIGHT_MCP_PORT": "9000"},
			want: "/mcp/playwright|http://playwright-mcp:9000|auth=none",
		},
		{
			name: "1 つの文字列に複数の変数",
			raw:  "${A:-a}/${B:+b}/${C}",
			env:  map[string]string{"B": "1", "C": "c"},
			want: "a/b/c",
		},
		{name: "未対応の書式はそのまま残す", raw: "${A-d}", want: "${A-d}"},
		{name: "閉じていない ${ はそのまま残す", raw: "pre-${A:-x", want: "pre-${A:-x"},
		{name: "展開した値は再展開しない", raw: "${A}", env: map[string]string{"A": "${B}", "B": "b"}, want: "${B}"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := expandComposeVars(tt.raw, func(key string) (string, bool) {
				val, ok := tt.env[key]
				return val, ok
			})
			if got != tt.want {
				t.Fatalf("expandComposeVars(%q) = %q, want %q", tt.raw, got, tt.want)
			}
		})
	}
}

// 入れ子の alt を持つ ROUTE_PLAYWRIGHT は、無効の間は登録対象外で、有効なら path 以降が壊れずに登録される。
func TestParsePlaywrightRouteIsOptional(t *testing.T) {
	data := []byte(`services:
  mcp-gateway:
    environment:
      - ROUTE_GITHUB=/mcp/github|http://github-mcp:8082
      - ROUTE_PLAYWRIGHT=${PLAYWRIGHT_MCP_ENABLED:+/mcp/playwright|http://playwright-mcp:${PLAYWRIGHT_MCP_PORT:-8931}|auth=none}
`)

	tests := []struct {
		name string
		env  map[string]string
		want []string
	}{
		{name: "無効なら、playwright は登録対象外", env: map[string]string{}, want: []string{"github"}},
		{name: "有効なら、playwright も登録対象", env: map[string]string{"PLAYWRIGHT_MCP_ENABLED": "1"}, want: []string{"github", "playwright"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			servers, err := Parse(data, func(key string) (string, bool) {
				val, ok := tt.env[key]
				return val, ok
			})
			if err != nil {
				t.Fatal(err)
			}
			var got []string
			for _, server := range servers {
				got = append(got, server.Name)
			}
			if strings.Join(got, ",") != strings.Join(tt.want, ",") {
				t.Fatalf("servers = %v, want %v", got, tt.want)
			}
		})
	}
}

// サービス間のルート（名前が _INTERNAL で終わる ROUTE_*）は、有効でも、agent 向けの登録の対象外。
func TestParseExcludesInternalRoutes(t *testing.T) {
	data := []byte(`services:
  mcp-gateway:
    environment:
      - ROUTE_GITHUB=/mcp/github|http://github-mcp:8082
      - ROUTE_REVIEW_RAVEN=/mcp/review-raven|http://review-raven:8083/mcp
      - ROUTE_REVIEW_RAVEN_INTERNAL=${REVIEW_INTERNAL_LINK_ENABLED:+/mcp/review-raven-internal|http://review-raven:8083/internal/mcp|upstream_bearer_token_env=REVIEW_RAVEN_INTERNAL_PROXY_SECRET|required_audience=review-raven-internal}
      - ROUTE_THREAD_OWL=/mcp/thread-owl|http://thread-owl:3000/mcp
      - ROUTE_THREAD_OWL_INTERNAL=${REVIEW_INTERNAL_LINK_ENABLED:+/mcp/thread-owl-internal|http://thread-owl:3000/internal/mcp|upstream_bearer_token_env=THREAD_OWL_INTERNAL_PROXY_SECRET|required_audience=thread-owl-internal}
`)
	for _, enabled := range []bool{false, true} {
		lookup := func(key string) (string, bool) {
			if enabled && key == "REVIEW_INTERNAL_LINK_ENABLED" {
				return "1", true
			}
			return "", false
		}
		servers, err := Parse(data, lookup)
		if err != nil {
			t.Fatal(err)
		}
		var names []string
		for _, s := range servers {
			names = append(names, s.Name)
			if strings.Contains(s.URL, "internal") {
				t.Fatalf("enabled=%v: internal route must not be registered: %s", enabled, s.URL)
			}
		}
		if got, want := strings.Join(names, ","), "github,review-raven,thread-owl"; got != want {
			t.Fatalf("enabled=%v: registered = %s, want %s", enabled, got, want)
		}
	}
}

// リポジトリの docker-compose.yml の内部ルートは、実際に登録の対象外で、内部面専用の保護（audience と共有 Bearer）を持つ。
func TestRepositoryComposeInternalRoutes(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}
	gateway, err := gatewayEnv(data)
	if err != nil {
		t.Fatal(err)
	}
	for _, tt := range []struct{ key, path, secret, audience string }{
		{"ROUTE_REVIEW_RAVEN_INTERNAL", "/mcp/review-raven-internal|http://review-raven:${REVIEW_RAVEN_PORT:-8083}/internal/mcp", "REVIEW_RAVEN_INTERNAL_PROXY_SECRET", "review-raven-internal"},
		{"ROUTE_THREAD_OWL_INTERNAL", "/mcp/thread-owl-internal|http://thread-owl:${THREAD_OWL_PORT:-3000}/internal/mcp", "THREAD_OWL_INTERNAL_PROXY_SECRET", "thread-owl-internal"},
	} {
		t.Run(tt.key, func(t *testing.T) {
			value := gateway[tt.key]
			// 無効の間はルートが空になる（スイッチ ${REVIEW_INTERNAL_LINK_ENABLED:+...} の中に定義する）
			if !strings.HasPrefix(value, "${REVIEW_INTERNAL_LINK_ENABLED:+") {
				t.Fatalf("%s must be opt-in behind REVIEW_INTERNAL_LINK_ENABLED, got %q", tt.key, value)
			}
			for _, want := range []string{tt.path, "upstream_bearer_token_env=" + tt.secret, "required_audience=" + tt.audience} {
				if !strings.Contains(value, want) {
					t.Fatalf("%s = %q, want it to contain %q", tt.key, value, want)
				}
			}
			if strings.Contains(value, "auth=none") {
				t.Fatalf("%s must be authenticated", tt.key)
			}
		})
	}

	// 内部ルートの audience は、agent 向けのルート（既定の audience）と重ならない
	if strings.Contains(gateway["ROUTE_REVIEW_RAVEN"], "required_audience") || strings.Contains(gateway["ROUTE_THREAD_OWL"], "required_audience") {
		t.Fatal("agent-facing routes must keep the default audience")
	}

	lookup := func(key string) (string, bool) {
		if key == "REVIEW_INTERNAL_LINK_ENABLED" {
			return "1", true
		}
		return "", false
	}
	servers, err := Parse(data, lookup)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range servers {
		if strings.Contains(s.Source, "INTERNAL") || strings.Contains(s.URL, "internal") {
			t.Fatalf("internal route registered for agents: %+v", s)
		}
	}
}

// リポジトリの docker-compose.yml の契約テストだけが読む型。ports / volumes は短い形式の前提で、
// 本番のパーサー（composeService）には持たせない: Compose の長形式を使う構成で register が失敗しないようにするため。
type repoComposeFile struct {
	Services map[string]struct {
		Image       string    `yaml:"image"`
		Environment yaml.Node `yaml:"environment"`
		Ports       []string  `yaml:"ports"`
		Volumes     []string  `yaml:"volumes"`
	} `yaml:"services"`
}

// Compose の長形式の ports / volumes（map）を含む構成でも、register のパーサーは失敗せず、ルートを読める。
func TestParseAcceptsLongFormPortsAndVolumes(t *testing.T) {
	data := []byte(`services:
  mcp-gateway:
    ports:
      - target: 8080
        published: "8080"
    volumes:
      - type: volume
        source: data
        target: /data
    environment:
      - ROUTE_GITHUB=/mcp/github|http://github-mcp:8082
  other:
    ports:
      - target: 9000
        published: "9000"
    volumes:
      - type: bind
        source: ./x
        target: /x
`)
	servers, err := Parse(data, func(string) (string, bool) { return "", false })
	if err != nil {
		t.Fatalf("long-form ports/volumes must not break the parser: %v", err)
	}
	if len(servers) != 1 || servers[0].Name != "github" {
		t.Fatalf("servers = %+v, want the github route", servers)
	}
}

// 内部連携を有効にするとき、thread-owl のイメージは最新リリース（内部面を含まない）の既定に頼らず、明示させる。
// 無効の間の既定は変えない。main 系の make ターゲットは、設定検証にも main イメージを渡す。
func TestRepositoryThreadOwlImageRequiresExplicitWhenInternalLinkEnabled(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}
	var file repoComposeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	image := file.Services["thread-owl"].Image
	for _, want := range []string{
		"${THREAD_OWL_IMAGE:-",
		"${REVIEW_INTERNAL_LINK_ENABLED:+${THREAD_OWL_IMAGE:?",
		"${REVIEW_INTERNAL_LINK_ENABLED:-ghcr.io/scottlz0310/thread-owl:latest}",
	} {
		if !strings.Contains(image, want) {
			t.Fatalf("services.thread-owl.image = %q, want it to contain %q", image, want)
		}
	}

	makefile, err := os.ReadFile(filepath.Join("..", "..", "Makefile"))
	if err != nil {
		t.Fatal(err)
	}
	const export = "pull-main start-main restart-main: export THREAD_OWL_IMAGE := $(THREAD_OWL_MAIN_IMAGE)"
	if !strings.Contains(string(makefile), export) {
		t.Fatalf("Makefile must pass the main thread-owl image to the main targets and their config check: %q", export)
	}
}

// review-raven と thread-owl の内部連携は、単一のスイッチで有効にし、必須の秘密と ACL が欠ければ設定の検証で止まり、
// 配送は gateway の内部ルートへ向ける。ホストへポートを公開せず、台帳の volume を持つ。
func TestRepositoryComposeInternalLinkServices(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "docker-compose.yml"))
	if err != nil {
		t.Fatal(err)
	}
	var file repoComposeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	const sw = "${REVIEW_INTERNAL_LINK_ENABLED:+"

	// 有効のときだけ値を持つ（既定は空）
	flags := []struct{ service, name, want string }{
		{"review-raven", "REVIEW_RAVEN_REVIEW_REQUESTS", sw + "true}"},
		{"review-raven", "REVIEW_RAVEN_INTERNAL_SURFACE", sw + "true}"},
		{"review-raven", "REVIEW_RAVEN_OWL_INTERNAL_ALLOW_PLAIN_HTTP", sw + "true}"},
		{"thread-owl", "THREAD_OWL_RAVEN_INTERNAL_ALLOW_PLAIN_HTTP", sw + "true}"},
		{"thread-owl", "THREAD_OWL_LEDGER_PATH", sw + "/data/ledger.sqlite}"},
	}
	// 有効のとき、欠ければ設定の検証で止まる（"${VAR:?...}" をスイッチの中に置く）
	required := []struct{ service, name string }{
		{"mcp-gateway", "REVIEW_RAVEN_INTERNAL_PROXY_SECRET"},
		{"mcp-gateway", "THREAD_OWL_INTERNAL_PROXY_SECRET"},
		{"review-raven", "REVIEW_RAVEN_REQUEST_ACL"},
		{"review-raven", "REVIEW_RAVEN_INTERNAL_PROXY_SECRET"},
		{"review-raven", "REVIEW_RAVEN_SERVICE_ACL"},
		{"review-raven", "REVIEW_RAVEN_OWL_INTERNAL_TOKEN"},
		{"thread-owl", "THREAD_OWL_INTERNAL_PROXY_SECRET"},
		{"thread-owl", "THREAD_OWL_SERVICE_ACL"},
		{"thread-owl", "THREAD_OWL_RAVEN_INTERNAL_TOKEN"},
	}
	// 配送の宛先は、gateway の内部ルートを、コンテナのネットワーク上のサービス名で引く
	urls := []struct{ service, name, route string }{
		{"review-raven", "REVIEW_RAVEN_OWL_INTERNAL_URL", "/mcp/thread-owl-internal}"},
		{"thread-owl", "THREAD_OWL_RAVEN_INTERNAL_URL", "/mcp/review-raven-internal}"},
	}

	env := func(service string) map[string]string {
		t.Helper()
		e, err := environmentMap(file.Services[service].Environment)
		if err != nil {
			t.Fatal(err)
		}
		return e
	}
	for _, f := range flags {
		t.Run(f.name, func(t *testing.T) {
			if got := env(f.service)[f.name]; got != f.want {
				t.Fatalf("%s.%s = %q, want %q", f.service, f.name, got, f.want)
			}
		})
	}
	for _, r := range required {
		t.Run(r.name, func(t *testing.T) {
			got := env(r.service)[r.name]
			if want := sw + "${" + r.name + ":?"; !strings.HasPrefix(got, want) {
				t.Fatalf("%s.%s = %q, want prefix %q (the variable must be required when enabled)", r.service, r.name, got, want)
			}
		})
	}
	for _, u := range urls {
		t.Run(u.name, func(t *testing.T) {
			got := env(u.service)[u.name]
			if !strings.HasPrefix(got, sw+"${REVIEW_INTERNAL_LINK_GATEWAY_URL:-http://mcp-gateway:${MCP_GATEWAY_PORT:-8080}}") || !strings.HasSuffix(got, u.route) {
				t.Fatalf("%s.%s = %q", u.service, u.name, got)
			}
		})
	}

	// 内部面専用の共有シークレットは、公開面のものと別の変数で、公開面のシークレットを流用しない
	for _, service := range []string{"mcp-gateway", "review-raven", "thread-owl"} {
		e := env(service)
		for name, value := range e {
			if strings.HasSuffix(name, "_INTERNAL_PROXY_SECRET") && strings.Contains(value, "REVIEW_RAVEN_PROXY_SECRET") {
				t.Fatalf("%s.%s must not reuse the public proxy secret", service, name)
			}
		}
	}

	// ホストへポートを公開せず、thread-owl は台帳の volume を持つ
	for _, service := range []string{"review-raven", "thread-owl"} {
		if ports := file.Services[service].Ports; len(ports) > 0 {
			t.Fatalf("services.%s must not publish ports: %v", service, ports)
		}
	}
	if !slices.Contains(file.Services["thread-owl"].Volumes, "thread-owl-data:/data") {
		t.Fatalf("services.thread-owl.volumes = %v, want thread-owl-data:/data", file.Services["thread-owl"].Volumes)
	}
	if !slices.Contains(file.Services["review-raven"].Volumes, "review-raven-data:/data") {
		t.Fatalf("services.review-raven.volumes = %v, want review-raven-data:/data", file.Services["review-raven"].Volumes)
	}
}
