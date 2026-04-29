package external

import (
	"fmt"
	"os"

	"github.com/scottlz0310/mcp-docker/tools/internal/register"
	"gopkg.in/yaml.v3"
)

type file struct {
	Servers []server `yaml:"servers"`
}

type server struct {
	Name     string `yaml:"name"`
	URL      string `yaml:"url"`
	TokenEnv string `yaml:"tokenEnv"`
}

func Load(path string) ([]register.Server, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	return Parse(data)
}

func Parse(data []byte) ([]register.Server, error) {
	var cfg file
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	servers := make([]register.Server, 0, len(cfg.Servers))
	for i, item := range cfg.Servers {
		if item.Name == "" {
			return nil, fmt.Errorf("servers[%d].name is required", i)
		}
		if item.URL == "" {
			return nil, fmt.Errorf("servers[%d].url is required", i)
		}
		servers = append(servers, register.Server{
			Name:     item.Name,
			URL:      item.URL,
			TokenEnv: item.TokenEnv,
		})
	}
	return servers, nil
}
