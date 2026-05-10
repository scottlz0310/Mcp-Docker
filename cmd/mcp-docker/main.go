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

	"github.com/scottlz0310/mcp-docker/v2/internal/compose"
	"github.com/scottlz0310/mcp-docker/v2/internal/external"
	"github.com/scottlz0310/mcp-docker/v2/internal/register"
)

const usage = `mcp-docker は MCP Docker の補助ワークフローを管理します。

使い方:
  mcp-docker register [--agent <csv>|all] [--server <csv>|all] [--compose path] [--external path] [--interactive] [--yes] [--dry-run]
  mcp-docker version
  mcp-docker --version
  mcp-docker -v

register に何も引数を指定せず TTY から実行した場合は対話モードで起動します
（agent と MCP サーバーを番号入力で複数選択できます）。
`

var version = "2.7.0"

var allAgentNames = []string{"claude", "copilot", "codex"}

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
	case "version", "-v", "--version":
		fmt.Fprintf(stdout, "mcp-docker %s\n", version)
		return nil
	case "help", "-h", "--help":
		fmt.Fprint(stdout, usage)
		return nil
	default:
		return fmt.Errorf("不明なコマンド %q\n\n%s", args[0], usage)
	}
}

func runRegister(ctx context.Context, args []string, stdout, stderr io.Writer, stdin io.Reader) error {
	fs := flag.NewFlagSet("register", flag.ContinueOnError)
	fs.SetOutput(stderr)

	opts := registerOptions{}
	fs.StringVar(&opts.agent, "agent", "all", "登録対象エージェント（カンマ区切り可）: claude, copilot, codex, all")
	fs.StringVar(&opts.server, "server", "all", "登録対象 MCP サーバー（カンマ区切り可）: <name>, all")
	fs.StringVar(&opts.composePath, "compose", "docker-compose.yml", "読み込む docker compose ファイル")
	fs.StringVar(&opts.externalPath, "external", "config/mcp-external.yml", "外部 MCP サーバー定義ファイル")
	fs.BoolVar(&opts.yes, "yes", false, "サジェスト名を確認なしで採用")
	fs.BoolVar(&opts.dryRun, "dry-run", false, "実行せず、登録時に使うコマンドと条件を表示")
	fs.BoolVar(&opts.interactive, "interactive", false, "agent/server を対話的に選択")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("想定外の引数です: %s", strings.Join(fs.Args(), " "))
	}

	explicit := map[string]bool{}
	fs.Visit(func(f *flag.Flag) { explicit[f.Name] = true })

	stdinIsTTY := isTerminal(stdin)
	stdoutIsTTY := isTerminal(stdout)

	if opts.interactive && (!stdinIsTTY || !stdoutIsTTY) {
		return errors.New("--interactive は TTY 環境でのみ利用可能です。代わりに --agent / --server / --yes を指定してください")
	}

	useInteractive := opts.interactive
	if !explicit["interactive"] && !explicit["yes"] && !explicit["dry-run"] &&
		!explicit["agent"] && !explicit["server"] &&
		stdinIsTTY && stdoutIsTTY {
		useInteractive = true
	}

	servers, err := loadServers(opts.composePath, opts.externalPath)
	if err != nil {
		return err
	}
	if len(servers) == 0 {
		return errors.New("MCP サーバーが見つかりませんでした")
	}

	availableServerNames := serverNames(servers)
	stdinReader := bufio.NewReader(stdin)

	var agentNames, selectedServerNames []string
	if useInteractive {
		agentNames, err = promptSelection(stdinReader, stdout, "登録する IDE/CLI を選択", allAgentNames)
		if err != nil {
			return err
		}
		selectedServerNames, err = promptSelection(stdinReader, stdout, "登録する MCP サーバーを選択", availableServerNames)
		if err != nil {
			return err
		}
	} else {
		agentNames, err = resolveSelection(opts.agent, allAgentNames, "agent")
		if err != nil {
			return err
		}
		selectedServerNames, err = resolveSelection(opts.server, availableServerNames, "server")
		if err != nil {
			return err
		}
	}

	selectedServers := filterServers(servers, selectedServerNames)
	if len(selectedServers) == 0 {
		return errors.New("選択された MCP サーバーがありません")
	}

	if !opts.yes && !opts.dryRun {
		if err := confirmRouteNames(stdinReader, stdout, selectedServers); err != nil {
			return err
		}
		if err := validateUniqueServers(selectedServers); err != nil {
			return err
		}
	}

	selected, err := selectAgentsByNames(agentNames)
	if err != nil {
		return err
	}
	execRunner := register.ExecRunner{}
	for _, spec := range selected {
		agent := spec.newAgent(execRunner)
		if opts.dryRun {
			register.PrintPlan(stdout, agent, selectedServers)
			continue
		}
		if err := register.Register(ctx, stdout, agent, selectedServers); err != nil {
			return err
		}
	}
	return nil
}

type registerOptions struct {
	agent        string
	server       string
	composePath  string
	externalPath string
	yes          bool
	dryRun       bool
	interactive  bool
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

func confirmRouteNames(reader *bufio.Reader, stdout io.Writer, servers []register.Server) error {
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
			return fmt.Errorf("MCP サーバー名 %q が重複しています（%s と %s）", server.Name, prev, label)
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

func serverNames(servers []register.Server) []string {
	names := make([]string, 0, len(servers))
	seen := make(map[string]struct{}, len(servers))
	for _, s := range servers {
		if s.Name == "" {
			continue
		}
		if _, ok := seen[s.Name]; ok {
			continue
		}
		seen[s.Name] = struct{}{}
		names = append(names, s.Name)
	}
	return names
}

func filterServers(servers []register.Server, selected []string) []register.Server {
	want := make(map[string]struct{}, len(selected))
	for _, name := range selected {
		want[name] = struct{}{}
	}
	out := make([]register.Server, 0, len(selected))
	for _, s := range servers {
		if _, ok := want[s.Name]; ok {
			out = append(out, s)
		}
	}
	return out
}

func resolveSelection(value string, items []string, label string) ([]string, error) {
	value = strings.TrimSpace(value)
	if value == "" || strings.EqualFold(value, "all") {
		out := make([]string, len(items))
		copy(out, items)
		return out, nil
	}
	var out []string
	seen := make(map[string]struct{})
	for raw := range strings.SplitSeq(value, ",") {
		tok := strings.TrimSpace(raw)
		if tok == "" {
			continue
		}
		name, err := resolveSelectionToken(tok, items)
		if err != nil {
			return nil, fmt.Errorf("--%s: %w", label, err)
		}
		if _, dup := seen[name]; dup {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, name)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("--%s: 少なくとも 1 つ指定してください", label)
	}
	return out, nil
}

type agentSpec struct {
	name     string
	newAgent func(register.Runner) register.Agent
}

func selectAgentsByNames(names []string) ([]agentSpec, error) {
	all := []agentSpec{
		{name: "claude", newAgent: register.NewClaudeAgent},
		{name: "copilot", newAgent: register.NewCopilotAgent},
		{name: "codex", newAgent: register.NewCodexAgent},
	}
	specsByName := make(map[string]agentSpec, len(all))
	for _, spec := range all {
		specsByName[spec.name] = spec
	}
	out := make([]agentSpec, 0, len(names))
	seen := make(map[string]struct{}, len(names))
	for _, name := range names {
		spec, ok := specsByName[name]
		if !ok {
			return nil, fmt.Errorf("不明なエージェント %q", name)
		}
		if _, dup := seen[name]; dup {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, spec)
	}
	if len(out) == 0 {
		return nil, errors.New("エージェントが選択されていません")
	}
	return out, nil
}
