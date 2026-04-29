package register

import (
	"context"
	"errors"
	"fmt"
	"io"
)

var ErrUnsupported = errors.New("unsupported server for agent")

type Server struct {
	Name     string
	URL      string
	TokenEnv string
	Source   string
}

type Agent interface {
	Name() string
	List(context.Context) ([]string, error)
	Add(context.Context, Server) error
	Remove(context.Context, string) error
	OverwritesOnAdd() bool
	AddCommand(Server) []string
	RemoveCommand(string) []string
}

func Register(ctx context.Context, out io.Writer, agent Agent, servers []Server) error {
	fmt.Fprintf(out, "%s に %d 件の MCP サーバーを登録します\n", agent.Name(), len(servers))

	existing := make(map[string]struct{})
	if !agent.OverwritesOnAdd() {
		names, err := agent.List(ctx)
		if err != nil {
			return fmt.Errorf("%s list: %w", agent.Name(), err)
		}
		for _, name := range names {
			existing[name] = struct{}{}
		}
	}

	for _, server := range servers {
		if server.Name == "" || server.URL == "" {
			return fmt.Errorf("MCP サーバー定義が不正です: name と URL が必要です")
		}
		if reason, ok := unsupportedReason(agent, server); ok {
			fmt.Fprintf(out, "- %s: スキップ: %s\n", server.Name, reason)
			continue
		}
		if _, ok := existing[server.Name]; ok {
			fmt.Fprintf(out, "- %s: 既存登録を削除します\n", server.Name)
			if err := agent.Remove(ctx, server.Name); err != nil {
				return fmt.Errorf("%s remove %q: %w", agent.Name(), server.Name, err)
			}
		}
		fmt.Fprintf(out, "- %s: %s を追加します\n", server.Name, server.URL)
		if err := agent.Add(ctx, server); err != nil {
			if errors.Is(err, ErrUnsupported) {
				fmt.Fprintf(out, "  スキップ: %v\n", err)
				continue
			}
			return fmt.Errorf("%s add %q: %w", agent.Name(), server.Name, err)
		}
	}
	return nil
}

func PrintPlan(out io.Writer, agent Agent, servers []Server) {
	fmt.Fprintf(out, "%s の dry-run 計画:\n", agent.Name())
	if !agent.OverwritesOnAdd() {
		fmt.Fprintf(out, "- 既存登録確認: %s\n", shellish(listCommand(agent)))
	}
	for _, server := range servers {
		if reason, ok := unsupportedReason(agent, server); ok {
			fmt.Fprintf(out, "- %s: スキップ: %s\n", server.Name, reason)
			continue
		}
		fmt.Fprintf(out, "- %s:\n", server.Name)
		if agent.OverwritesOnAdd() {
			fmt.Fprintf(out, "  - 追加/上書き: %s\n", shellish(agent.AddCommand(server)))
			continue
		}
		fmt.Fprintf(out, "  - 既存登録があれば削除: %s\n", shellish(agent.RemoveCommand(server.Name)))
		fmt.Fprintf(out, "  - 追加: %s\n", shellish(agent.AddCommand(server)))
	}
}

func listCommand(agent Agent) []string {
	switch agent.Name() {
	case "claude":
		return []string{"claude", "mcp", "list"}
	case "copilot":
		return []string{"gh", "copilot", "--", "mcp", "list"}
	case "codex":
		return []string{"codex", "mcp", "list"}
	default:
		return []string{agent.Name(), "mcp", "list"}
	}
}

func unsupportedReason(agent Agent, server Server) (string, bool) {
	if server.TokenEnv == "" {
		return "", false
	}
	if _, ok := agent.(tokenEnvAgent); ok {
		return "", false
	}
	return fmt.Sprintf("tokenEnv %s は secret header を保存せずに %s へ登録できません", server.TokenEnv, agent.Name()), true
}
