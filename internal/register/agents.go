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

func (a ClaudeAgent) List(ctx context.Context) ([]string, error) {
	out, err := a.runner.Run(ctx, "claude", "mcp", "list")
	return parseListNames(out), err
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

func (a CopilotAgent) List(ctx context.Context) ([]string, error) {
	out, err := a.runner.Run(ctx, "gh", "copilot", "--", "mcp", "list")
	return parseListNames(out), err
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

func (a CodexAgent) List(ctx context.Context) ([]string, error) {
	out, err := a.runner.Run(ctx, "codex", "mcp", "list")
	return parseListNames(out), err
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

func parseListNames(output string) []string {
	var names []string
	seen := make(map[string]struct{})
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		lower := strings.ToLower(line)
		if strings.Contains(lower, "no mcp") || strings.Contains(lower, "not configured") || strings.HasPrefix(lower, "name ") {
			continue
		}

		name := line
		if before, _, ok := strings.Cut(name, ":"); ok {
			name = before
		} else {
			name = strings.Fields(name)[0]
		}
		name = strings.Trim(name, "`'\"")
		if name == "" {
			continue
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		names = append(names, name)
	}
	return names
}
