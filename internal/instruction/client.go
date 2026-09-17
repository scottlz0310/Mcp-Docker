package instruction

import (
	"fmt"
	"os"
	"path/filepath"
)

// Client は、ユーザー単位の instruction ファイルの配置先を表す。
type Client struct {
	Name string
	Path string
}

type clientLayout struct {
	name string
	rel  string
}

var clientLayouts = []clientLayout{
	{name: "claude", rel: ".claude/CLAUDE.md"},
	{name: "copilot", rel: ".copilot/copilot-instructions.md"},
	{name: "codex", rel: ".codex/AGENTS.md"},
	{name: "antigravity", rel: ".gemini/GEMINI.md"},
}

// ClientNames は、対応している CLI エージェント名を定義順に返す。
func ClientNames() []string {
	names := make([]string, 0, len(clientLayouts))
	for _, layout := range clientLayouts {
		names = append(names, layout.name)
	}
	return names
}

// Clients は、指定されたホームディレクトリを基準に配置先を返す。
func Clients(home string) []Client {
	clients := make([]Client, 0, len(clientLayouts))
	for _, layout := range clientLayouts {
		clients = append(clients, Client{
			Name: layout.name,
			Path: filepath.Join(home, filepath.FromSlash(layout.rel)),
		})
	}
	return clients
}

// Select は名前で配置先を選択する。
func Select(clients []Client, names []string) ([]Client, error) {
	byName := make(map[string]Client, len(clients))
	for _, client := range clients {
		byName[client.Name] = client
	}

	selected := make([]Client, 0, len(names))
	seen := make(map[string]struct{}, len(names))
	for _, name := range names {
		client, ok := byName[name]
		if !ok {
			return nil, fmt.Errorf("不明な instruction 対象エージェント %q", name)
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		selected = append(selected, client)
	}
	if len(selected) == 0 {
		return nil, fmt.Errorf("instruction 対象エージェントが選択されていません")
	}
	return selected, nil
}

// UserHome は instruction の配置先として使うユーザーホームを返す。
// テストや隔離した運用では MCP_DOCKER_INSTRUCTION_HOME で差し替えられる。
func UserHome() (string, error) {
	if value := os.Getenv("MCP_DOCKER_INSTRUCTION_HOME"); value != "" {
		return filepath.Abs(value)
	}
	return os.UserHomeDir()
}
