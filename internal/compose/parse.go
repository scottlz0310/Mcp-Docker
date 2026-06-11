package compose

import (
	"fmt"
	"os"
	"regexp"
	"sort"
	"strings"

	"github.com/scottlz0310/mcp-docker/v2/internal/register"
	"gopkg.in/yaml.v3"
)

const defaultGatewayPort = "8080"

type composeFile struct {
	Services map[string]composeService `yaml:"services"`
}

type composeService struct {
	Environment yaml.Node `yaml:"environment"`
}

func Load(path string) ([]register.Server, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return Parse(data, os.LookupEnv)
}

func Parse(data []byte, lookup func(string) (string, bool)) ([]register.Server, error) {
	var file composeFile
	if err := yaml.Unmarshal(data, &file); err != nil {
		return nil, err
	}
	gateway, ok := file.Services["mcp-gateway"]
	if !ok {
		return nil, fmt.Errorf("services.mcp-gateway not found")
	}

	env, err := environmentMap(gateway.Environment)
	if err != nil {
		return nil, err
	}
	port := defaultGatewayPort
	if raw, ok := env["MCP_GATEWAY_PORT"]; ok {
		if expanded := strings.TrimSpace(expandComposeVars(raw, lookup)); expanded != "" {
			port = expanded
		}
	}
	if val, ok := lookup("MCP_GATEWAY_PORT"); ok && val != "" {
		port = val
	}

	var keys []string
	for key := range env {
		if strings.HasPrefix(key, "ROUTE_") {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)

	servers := make([]register.Server, 0, len(keys))
	for _, key := range keys {
		value := strings.TrimSpace(expandComposeVars(env[key], lookup))
		if value == "" {
			// ${VAR:+...} の変数未設定などで空になったルートは、
			// gateway 側（空 ROUTE_* スキップ）と同様に登録対象外とする
			continue
		}
		path, _, _ := strings.Cut(value, "|")
		path = strings.TrimSpace(path)
		if path == "" {
			return nil, fmt.Errorf("%s has empty route path", key)
		}
		if !strings.HasPrefix(path, "/") {
			path = "/" + path
		}
		name := routeName(key)
		servers = append(servers, register.Server{
			Name:   name,
			URL:    fmt.Sprintf("http://127.0.0.1:%s%s", port, path),
			Source: key,
		})
	}
	return servers, nil
}

func environmentMap(node yaml.Node) (map[string]string, error) {
	env := make(map[string]string)
	switch node.Kind {
	case 0:
		return env, nil
	case yaml.SequenceNode:
		for _, item := range node.Content {
			key, val, ok := strings.Cut(item.Value, "=")
			if !ok {
				env[strings.TrimSpace(item.Value)] = ""
				continue
			}
			env[strings.TrimSpace(key)] = strings.TrimSpace(val)
		}
	case yaml.MappingNode:
		for i := 0; i+1 < len(node.Content); i += 2 {
			env[strings.TrimSpace(node.Content[i].Value)] = strings.TrimSpace(node.Content[i+1].Value)
		}
	default:
		return nil, fmt.Errorf("unsupported mcp-gateway.environment YAML node kind %d", node.Kind)
	}
	return env, nil
}

func routeName(key string) string {
	name := strings.TrimPrefix(key, "ROUTE_")
	name = strings.ToLower(name)
	return strings.ReplaceAll(name, "_", "-")
}

var composeVarExpr = regexp.MustCompile(`\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([-+])([^}]*))?\}`)

// expandComposeVars は Compose 互換の変数展開
// （${VAR} / ${VAR:-default} / ${VAR:+alternative}）を raw 全体に適用する。
func expandComposeVars(raw string, lookup func(string) (string, bool)) string {
	return composeVarExpr.ReplaceAllStringFunc(raw, func(expr string) string {
		match := composeVarExpr.FindStringSubmatch(expr)
		val, ok := lookup(match[1])
		hasValue := ok && val != ""
		switch match[2] {
		case "-":
			if hasValue {
				return val
			}
			return match[3]
		case "+":
			if hasValue {
				return match[3]
			}
			return ""
		default:
			return val
		}
	})
}
