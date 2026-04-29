package compose

import (
	"fmt"
	"os"
	"regexp"
	"sort"
	"strings"

	"github.com/scottlz0310/mcp-docker/tools/internal/register"
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
		port = resolveEnvExpression(raw, lookup, defaultGatewayPort)
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
		path, _, _ := strings.Cut(env[key], "|")
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

var envExpr = regexp.MustCompile(`^\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}$`)

func resolveEnvExpression(raw string, lookup func(string) (string, bool), fallback string) string {
	match := envExpr.FindStringSubmatch(raw)
	if match == nil {
		if raw == "" {
			return fallback
		}
		return raw
	}
	if val, ok := lookup(match[1]); ok && val != "" {
		return val
	}
	if match[3] != "" {
		return match[3]
	}
	return fallback
}
