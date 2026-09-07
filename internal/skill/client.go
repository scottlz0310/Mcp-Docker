package skill

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Client は skill の配置先となる CLI エージェント。
type Client struct {
	Name string
	// Dir は skill を配置するディレクトリ（各 skill はこの直下にサブディレクトリを作る）。
	Dir string
}

// clientLayout はホームディレクトリからの相対パスで配置先を定義する。
type clientLayout struct {
	name string
	rel  []string
}

// clientLayouts は register が扱う 4 種の CLI エージェントと skill ディレクトリの対応。
var clientLayouts = []clientLayout{
	{name: "claude", rel: []string{".claude", "skills"}},
	{name: "copilot", rel: []string{".copilot", "skills"}},
	{name: "codex", rel: []string{".codex", "skills"}},
	{name: "antigravity", rel: []string{".gemini", "antigravity-cli", "skills"}},
}

// ClientNames は配置対象クライアント名の一覧を宣言順で返す。
func ClientNames() []string {
	names := make([]string, 0, len(clientLayouts))
	for _, l := range clientLayouts {
		names = append(names, l.name)
	}
	return names
}

// Clients は home を基準に全クライアントの配置先を解決する。
func Clients(home string) []Client {
	clients := make([]Client, 0, len(clientLayouts))
	for _, l := range clientLayouts {
		clients = append(clients, Client{
			Name: l.name,
			Dir:  filepath.Join(append([]string{home}, l.rel...)...),
		})
	}
	return clients
}

// UserHome は skill 配置先の基準ディレクトリを返す。
// MCP_DOCKER_SKILL_HOME が設定されていればそれを優先する（検証・隔離環境向け）。
func UserHome() (string, error) {
	if override := os.Getenv("MCP_DOCKER_SKILL_HOME"); override != "" {
		return override, nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("ホームディレクトリを特定できません: %w", err)
	}
	return home, nil
}

// SelectClients は names に含まれるクライアントだけを返す。names が空の場合はすべて返す。
func SelectClients(clients []Client, names []string) ([]Client, error) {
	if len(names) == 0 {
		return clients, nil
	}
	byName := make(map[string]Client, len(clients))
	for _, c := range clients {
		byName[c.Name] = c
	}
	out := make([]Client, 0, len(names))
	seen := make(map[string]struct{}, len(names))
	for _, name := range names {
		c, ok := byName[name]
		if !ok {
			return nil, fmt.Errorf("不明なクライアント %q (利用可能: %s)", name, strings.Join(ClientNames(), ", "))
		}
		if _, dup := seen[name]; dup {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, c)
	}
	if len(out) == 0 {
		return nil, errors.New("クライアントが選択されていません")
	}
	return out, nil
}
