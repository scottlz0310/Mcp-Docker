package register

import (
	"context"
	"errors"
	"fmt"
	"io"
	"sort"
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
	fmt.Fprintf(out, "Registering %d MCP server(s) for %s\n", len(servers), agent.Name())

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
			return fmt.Errorf("invalid MCP server: name and URL are required")
		}
		if _, ok := existing[server.Name]; ok {
			fmt.Fprintf(out, "- %s: removing existing registration\n", server.Name)
			if err := agent.Remove(ctx, server.Name); err != nil {
				return fmt.Errorf("%s remove %q: %w", agent.Name(), server.Name, err)
			}
		}
		fmt.Fprintf(out, "- %s: adding %s\n", server.Name, server.URL)
		if err := agent.Add(ctx, server); err != nil {
			if errors.Is(err, ErrUnsupported) {
				fmt.Fprintf(out, "  skipped: %v\n", err)
				continue
			}
			return fmt.Errorf("%s add %q: %w", agent.Name(), server.Name, err)
		}
	}
	return nil
}

func PrintPlan(out io.Writer, agent Agent, servers []Server) {
	fmt.Fprintf(out, "Plan for %s:\n", agent.Name())
	for _, server := range servers {
		if server.TokenEnv != "" {
			if _, ok := agent.(tokenEnvAgent); !ok {
				fmt.Fprintf(out, "- skip %s: tokenEnv is not supported by %s without storing a secret header\n", server.Name, agent.Name())
				continue
			}
		}
		fmt.Fprintf(out, "- %s\n", shellish(agent.AddCommand(server)))
	}
}

func containsName(names []string, target string) bool {
	sort.Strings(names)
	i := sort.SearchStrings(names, target)
	return i < len(names) && names[i] == target
}
