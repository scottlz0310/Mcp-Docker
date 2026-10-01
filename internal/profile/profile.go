// Package profile は、エージェント（CLI）ごとに登録する MCP サーバーを宣言するプロファイルを扱う。
package profile

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"slices"

	"gopkg.in/yaml.v3"
)

const supportedVersion = 1

type file struct {
	Version int                 `yaml:"version"`
	Agents  map[string][]string `yaml:"agents"`
}

// Profile は、エージェントごとに登録する MCP サーバー名の宣言。
// nil の Profile は「宣言なし」を表し、どのエージェントも宣言を持たない。
type Profile struct {
	agents map[string][]string
}

// Load は path のプロファイルを読む。ファイルが無い場合は errors.Is(err, fs.ErrNotExist) になる。
func Load(path string) (*Profile, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	p, err := Parse(data)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return p, nil
}

// Parse はプロファイルを解析する。未知のキー、version の不一致、サーバー名の欠落・重複を拒否する。
func Parse(data []byte) (*Profile, error) {
	var cfg file
	decoder := yaml.NewDecoder(bytes.NewReader(data))
	decoder.KnownFields(true)
	if err := decoder.Decode(&cfg); err != nil {
		if errors.Is(err, io.EOF) {
			return nil, errors.New("プロファイルが空です（version: 1 と agents が必要です）")
		}
		return nil, err
	}
	if cfg.Version != supportedVersion {
		return nil, fmt.Errorf("version は %d を指定してください（指定値: %d）", supportedVersion, cfg.Version)
	}
	if len(cfg.Agents) == 0 {
		return nil, errors.New("agents に少なくとも 1 つのエージェントを宣言してください")
	}
	for agent, servers := range cfg.Agents {
		// `claude:` のように値が無い場合は、登録を空にする意図か書き漏らしかを区別できない。
		// 何も登録しない場合は、明示的に `[]` と書く。
		if servers == nil {
			return nil, fmt.Errorf("agents.%s: サーバー名のリストを指定してください（何も登録しない場合は [] と書きます）", agent)
		}
		seen := make(map[string]struct{}, len(servers))
		for _, name := range servers {
			if name == "" {
				return nil, fmt.Errorf("agents.%s: 空のサーバー名があります", agent)
			}
			if _, dup := seen[name]; dup {
				return nil, fmt.Errorf("agents.%s: サーバー %q が重複しています", agent, name)
			}
			seen[name] = struct{}{}
		}
	}
	return &Profile{agents: cfg.Agents}, nil
}

// Validate は、宣言されたエージェントとサーバーが、既知のものであることを確認する。
// 定義に無い名前（誤記や、定義から外したサーバー）は、登録も prune も誤るため、実行前に拒否する。
func (p *Profile) Validate(agentNames, serverNames []string) error {
	if p == nil {
		return nil
	}
	for _, agent := range sortedKeys(p.agents) {
		if !slices.Contains(agentNames, agent) {
			return fmt.Errorf("agents.%s: 不明なエージェントです（指定できる値: %v）", agent, agentNames)
		}
		for _, name := range p.agents[agent] {
			if !slices.Contains(serverNames, name) {
				return fmt.Errorf("agents.%s: 定義にない MCP サーバー %q です（定義されているサーバー: %v）", agent, name, serverNames)
			}
		}
	}
	return nil
}

// Servers は agent に宣言されたサーバー名を返す。宣言がなければ ok は false。
func (p *Profile) Servers(agent string) (names []string, ok bool) {
	if p == nil {
		return nil, false
	}
	names, ok = p.agents[agent]
	return slices.Clone(names), ok
}

func sortedKeys(m map[string][]string) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	slices.Sort(keys)
	return keys
}
