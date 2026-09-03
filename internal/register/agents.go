package register

import (
	"context"
	"fmt"
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
type AntigravityAgent struct{ baseAgent }

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
	return AntigravityAgent{baseAgent{name: "antigravity", runner: r}}
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

func (a AntigravityAgent) ListEntries(ctx context.Context) ([]Entry, error) {
	out, err := a.runner.Run(ctx, "agy", "mcp", "list")
	return parseListEntries(out), err
}

func (a AntigravityAgent) Add(ctx context.Context, s Server) error {
	if s.TokenEnv != "" {
		return fmt.Errorf("%w: %s tokenEnv requires a header value; refusing to persist secrets for %s", ErrUnsupported, s.TokenEnv, a.Name())
	}
	return runCommand(ctx, a.runner, a.AddCommand(s))
}

func (a AntigravityAgent) Remove(ctx context.Context, name string) error {
	return runCommand(ctx, a.runner, a.RemoveCommand(name))
}

func (a AntigravityAgent) OverwritesOnAdd() bool { return true }

func (a AntigravityAgent) AddCommand(s Server) []string {
	return []string{"agy", "mcp", "add", s.Name, s.URL}
}

func (a AntigravityAgent) RemoveCommand(name string) []string {
	return []string{"agy", "mcp", "remove", name}
}
