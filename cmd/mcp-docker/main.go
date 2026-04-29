package main

import (
	"bufio"
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/scottlz0310/mcp-docker/tools/internal/compose"
	"github.com/scottlz0310/mcp-docker/tools/internal/external"
	"github.com/scottlz0310/mcp-docker/tools/internal/register"
)

const usage = `mcp-docker manages MCP Docker helper workflows.

Usage:
  mcp-docker register [--agent claude|copilot|codex|all] [--compose path] [--external path] [--yes] [--dry-run]
`

func main() {
	if err := run(context.Background(), os.Args[1:], os.Stdout, os.Stderr, os.Stdin); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer, stdin io.Reader) error {
	if len(args) == 0 {
		fmt.Fprint(stdout, usage)
		return nil
	}

	switch args[0] {
	case "register":
		return runRegister(ctx, args[1:], stdout, stderr, stdin)
	case "help", "-h", "--help":
		fmt.Fprint(stdout, usage)
		return nil
	default:
		return fmt.Errorf("unknown command %q\n\n%s", args[0], usage)
	}
}

func runRegister(ctx context.Context, args []string, stdout, stderr io.Writer, stdin io.Reader) error {
	fs := flag.NewFlagSet("register", flag.ContinueOnError)
	fs.SetOutput(stderr)

	opts := registerOptions{}
	fs.StringVar(&opts.agent, "agent", "all", "agent to register: claude, copilot, codex, or all")
	fs.StringVar(&opts.composePath, "compose", "docker-compose.yml", "docker compose file to inspect")
	fs.StringVar(&opts.externalPath, "external", "config/mcp-external.yml", "external MCP server definition file")
	fs.BoolVar(&opts.yes, "yes", false, "accept suggested names without prompting")
	fs.BoolVar(&opts.dryRun, "dry-run", false, "print planned commands without executing them")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected arguments: %s", strings.Join(fs.Args(), " "))
	}

	servers, err := loadServers(opts.composePath, opts.externalPath)
	if err != nil {
		return err
	}
	if len(servers) == 0 {
		return errors.New("no MCP servers were discovered")
	}

	if !opts.yes {
		if err := confirmRouteNames(stdin, stdout, servers); err != nil {
			return err
		}
		if err := validateUniqueServers(servers); err != nil {
			return err
		}
	}

	selected, err := selectAgents(opts.agent)
	if err != nil {
		return err
	}
	execRunner := register.ExecRunner{}
	for _, spec := range selected {
		agent := spec.newAgent(execRunner)
		if opts.dryRun {
			register.PrintPlan(stdout, agent, servers)
			continue
		}
		if err := register.Register(ctx, stdout, agent, servers); err != nil {
			return err
		}
	}
	return nil
}

type registerOptions struct {
	agent        string
	composePath  string
	externalPath string
	yes          bool
	dryRun       bool
}

func loadServers(composePath, externalPath string) ([]register.Server, error) {
	composeServers, err := compose.Load(composePath)
	if err != nil {
		return nil, err
	}
	externalServers, err := external.Load(externalPath)
	if err != nil {
		return nil, err
	}

	var servers []register.Server
	for _, server := range append(composeServers, externalServers...) {
		servers = append(servers, server)
	}
	return servers, validateUniqueServers(servers)
}

func confirmRouteNames(stdin io.Reader, stdout io.Writer, servers []register.Server) error {
	reader := bufio.NewReader(stdin)
	for i := range servers {
		if servers[i].Source == "" {
			continue
		}
		fmt.Fprintf(stdout, "%s -> suggested name %q [Enter to accept / type override]: ", servers[i].Source, servers[i].Name)
		line, err := reader.ReadString('\n')
		if err != nil && !errors.Is(err, io.EOF) {
			return err
		}
		override := strings.TrimSpace(line)
		if override != "" {
			servers[i].Name = override
		}
		if errors.Is(err, io.EOF) {
			break
		}
	}
	return nil
}

func validateUniqueServers(servers []register.Server) error {
	seen := make(map[string]string)
	for _, server := range servers {
		label := serverLabel(server)
		if prev, ok := seen[server.Name]; ok {
			return fmt.Errorf("duplicate MCP server name %q (%s and %s)", server.Name, prev, label)
		}
		seen[server.Name] = label
	}
	return nil
}

func serverLabel(server register.Server) string {
	if server.Source != "" {
		return server.Source
	}
	return server.URL
}

type agentSpec struct {
	name     string
	newAgent func(register.Runner) register.Agent
}

func selectAgents(name string) ([]agentSpec, error) {
	all := []agentSpec{
		{name: "claude", newAgent: register.NewClaudeAgent},
		{name: "copilot", newAgent: register.NewCopilotAgent},
		{name: "codex", newAgent: register.NewCodexAgent},
	}
	if name == "all" {
		return all, nil
	}
	for _, spec := range all {
		if name == spec.name {
			return []agentSpec{spec}, nil
		}
	}
	return nil, fmt.Errorf("unknown agent %q", name)
}
