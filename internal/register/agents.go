package register

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type baseAgent struct {
	name   string
	runner Runner
}

func (a baseAgent) Name() string { return a.name }

type ClaudeAgent struct{ baseAgent }
type CopilotAgent struct{ baseAgent }
type CodexAgent struct{ baseAgent }

type tokenEnvAgent interface {
	supportsTokenEnv()
}

func NewClaudeAgent(r Runner) Agent {
	return ClaudeAgent{baseAgent{name: "claude", runner: r}}
}

func NewCopilotAgent(r Runner) Agent {
	return CopilotAgent{baseAgent{name: "copilot", runner: r}}
}

func NewCodexAgent(r Runner) Agent {
	return CodexAgent{baseAgent{name: "codex", runner: r}}
}

func NewAntigravityAgent(r Runner) Agent {
	return AntigravityAgent{baseAgent: baseAgent{name: "antigravity", runner: r}}
}

func (a ClaudeAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	out, err := a.runner.Run(ctx, "claude", "mcp", "list")
	return parseListEntries(out), err
}

func (a ClaudeAgent) Add(ctx context.Context, s Server) error {
	if s.TokenEnv != "" {
		return fmt.Errorf("%w: %s tokenEnv requires a header value; refusing to persist secrets for %s", ErrUnsupported, s.TokenEnv, a.Name())
	}
	return runCommand(ctx, a.runner, a.AddCommand(s))
}

func (a ClaudeAgent) Remove(ctx context.Context, name string) error {
	return runCommand(ctx, a.runner, a.RemoveCommand(name))
}

func (a ClaudeAgent) OverwritesOnAdd() bool { return false }

func (a ClaudeAgent) AddCommand(s Server) []string {
	return []string{"claude", "mcp", "add", "--transport", "http", "--scope", "user", s.Name, s.URL}
}

func (a ClaudeAgent) RemoveCommand(name string) []string {
	return []string{"claude", "mcp", "remove", "--scope", "user", name}
}

func (a CopilotAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	out, err := a.runner.Run(ctx, "gh", "copilot", "--", "mcp", "list")
	return parseListEntries(out), err
}

func (a CopilotAgent) Add(ctx context.Context, s Server) error {
	if s.TokenEnv != "" {
		return fmt.Errorf("%w: %s tokenEnv requires a header value; refusing to persist secrets for %s", ErrUnsupported, s.TokenEnv, a.Name())
	}
	return runCommand(ctx, a.runner, a.AddCommand(s))
}

func (a CopilotAgent) Remove(ctx context.Context, name string) error {
	return runCommand(ctx, a.runner, a.RemoveCommand(name))
}

func (a CopilotAgent) OverwritesOnAdd() bool { return false }

func (a CopilotAgent) AddCommand(s Server) []string {
	return []string{"gh", "copilot", "--", "mcp", "add", "--transport", "http", s.Name, s.URL}
}

func (a CopilotAgent) RemoveCommand(name string) []string {
	return []string{"gh", "copilot", "--", "mcp", "remove", name}
}

func (a CodexAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	out, err := a.runner.Run(ctx, "codex", "mcp", "list")
	return parseListEntries(out), err
}

func (a CodexAgent) Add(ctx context.Context, s Server) error {
	return runCommand(ctx, a.runner, a.AddCommand(s))
}

func (a CodexAgent) Remove(ctx context.Context, name string) error {
	return runCommand(ctx, a.runner, a.RemoveCommand(name))
}

func (a CodexAgent) OverwritesOnAdd() bool { return true }

func (a CodexAgent) supportsTokenEnv() {}

func (a CodexAgent) AddCommand(s Server) []string {
	args := []string{"codex", "mcp", "add", s.Name, "--url", s.URL}
	if s.TokenEnv != "" {
		args = append(args, "--bearer-token-env-var", s.TokenEnv)
	}
	return args
}

func (a CodexAgent) RemoveCommand(name string) []string {
	return []string{"codex", "mcp", "remove", name}
}

func runCommand(ctx context.Context, runner Runner, command []string) error {
	if len(command) == 0 {
		return nil
	}
	_, err := runner.Run(ctx, command[0], command[1:]...)
	return err
}

func parseListEntries(output string) []Entry {
	var entries []Entry
	seen := make(map[string]struct{})
	for line := range strings.SplitSeq(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		lower := strings.ToLower(line)
		if strings.Contains(lower, "no mcp") || strings.Contains(lower, "not configured") || strings.HasPrefix(lower, "name ") {
			continue
		}

		name := strings.Fields(line)[0]
		name = strings.TrimSuffix(name, ":")
		name = strings.Trim(name, "`'\"")
		if name == "" {
			continue
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		entries = append(entries, Entry{Name: name, URL: firstURL(line)})
	}
	return entries
}

// firstURL は行内の最初の http(s) URL トークンを返す。見つからなければ空文字。
func firstURL(line string) string {
	for field := range strings.FieldsSeq(line) {
		if strings.HasPrefix(field, "http://") || strings.HasPrefix(field, "https://") {
			return field
		}
	}
	return ""
}

type AntigravityAgent struct {
	baseAgent
	configPath string
}

func (a AntigravityAgent) getConfigPath() (string, error) {
	if a.configPath != "" {
		return a.configPath, nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".gemini", "config", "mcp_config.json"), nil
}

func (a AntigravityAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	path, err := a.getConfigPath()
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var config map[string]any
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, err
	}
	mcpServersAny, exists := config["mcpServers"]
	if !exists {
		return nil, nil
	}
	mcpServers, ok := mcpServersAny.(map[string]any)
	if !ok {
		return nil, nil
	}
	entries := make([]Entry, 0, len(mcpServers))
	for name, raw := range mcpServers {
		entry := Entry{Name: name}
		if obj, ok := raw.(map[string]any); ok {
			if u, ok := obj["serverUrl"].(string); ok {
				entry.URL = u
			}
		}
		entries = append(entries, entry)
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name < entries[j].Name })
	return entries, nil
}

func (a AntigravityAgent) Add(ctx context.Context, s Server) error {
	path, err := a.getConfigPath()
	if err != nil {
		return err
	}

	var config map[string]any

	data, err := os.ReadFile(path)
	if err == nil {
		if err := json.Unmarshal(data, &config); err != nil {
			return err
		}
	} else if !os.IsNotExist(err) {
		return err
	}

	if config == nil {
		config = make(map[string]any)
	}

	mcpServersAny, exists := config["mcpServers"]
	var mcpServers map[string]any
	if exists {
		if m, ok := mcpServersAny.(map[string]any); ok {
			mcpServers = m
		}
	}
	if mcpServers == nil {
		mcpServers = make(map[string]any)
	}

	mcpServers[s.Name] = map[string]string{
		"serverUrl": s.URL,
	}

	config["mcpServers"] = mcpServers

	newData, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return err
	}

	return safeWriteFile(path, newData, 0644)
}

func (a AntigravityAgent) Remove(ctx context.Context, name string) error {
	path, err := a.getConfigPath()
	if err != nil {
		return err
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	var config map[string]any
	if err := json.Unmarshal(data, &config); err != nil {
		return err
	}

	mcpServersAny, exists := config["mcpServers"]
	if exists {
		if mcpServers, ok := mcpServersAny.(map[string]any); ok {
			delete(mcpServers, name)
			config["mcpServers"] = mcpServers
		}
	}

	newData, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return err
	}

	return safeWriteFile(path, newData, 0644)
}

func (a AntigravityAgent) OverwritesOnAdd() bool { return true }

func (a AntigravityAgent) AddCommand(s Server) []string {
	path, _ := a.getConfigPath()
	return []string{"update config:", path, "add", s.Name, "->", s.URL}
}

func (a AntigravityAgent) RemoveCommand(name string) []string {
	path, _ := a.getConfigPath()
	return []string{"update config:", path, "remove", name}
}

func safeWriteFile(path string, data []byte, perm os.FileMode) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	tmpFile, err := os.CreateTemp(dir, "mcp_config_tmp_*")
	if err != nil {
		return err
	}
	tmpPath := tmpFile.Name()
	defer func() {
		_ = tmpFile.Close()
		_ = os.Remove(tmpPath)
	}()

	if err := tmpFile.Chmod(perm); err != nil {
		return err
	}
	if _, err := tmpFile.Write(data); err != nil {
		return err
	}
	if err := tmpFile.Sync(); err != nil {
		return err
	}
	if err := tmpFile.Close(); err != nil {
		return err
	}
	return os.Rename(tmpPath, path)
}
