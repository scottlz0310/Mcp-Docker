package register

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
)

var ErrUnsupported = errors.New("unsupported server for agent")

type Server struct {
	Name     string
	URL      string
	TokenEnv string
	Source   string
}

// Entry は agent に登録済みの MCP サーバー。URL が特定できない場合は空文字。
type Entry struct {
	Name string
	URL  string
}

type Agent interface {
	Name() string
	ListEntries(context.Context) ([]Entry, error)
	Add(context.Context, Server) error
	Remove(context.Context, string) error
	OverwritesOnAdd() bool
	AddCommand(Server) []string
	RemoveCommand(string) []string
}

func Register(ctx context.Context, out io.Writer, agent Agent, servers []Server, existing []Entry) error {
	fmt.Fprintf(out, "%s に %d 件の MCP サーバーを登録します\n", agent.Name(), len(servers))

	existingMap := make(map[string]struct{})
	if !agent.OverwritesOnAdd() {
		for _, entry := range existing {
			existingMap[entry.Name] = struct{}{}
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
		if _, ok := existingMap[server.Name]; ok {
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

// StaleEntries は agent に登録済みのエントリのうち、gateway 配下の URL を持ち、
// かつ定義ファイル（available）に含まれないものを返す。
// gatewayOrigins には現在の origin に加え、TLS 切替前のデフォルト origin など
// 既知の gateway origin を複数渡せる。
// URL が特定できないエントリは mcp-docker 管理外の可能性があるため候補にしない。
func StaleEntries(entries []Entry, available []Server, gatewayOrigins []string) []Entry {
	availableNames := make(map[string]struct{}, len(available))
	for _, server := range available {
		availableNames[server.Name] = struct{}{}
	}
	var stale []Entry
	for _, entry := range entries {
		if _, ok := availableNames[entry.Name]; ok {
			continue
		}
		if entry.URL == "" || !hasAnyPrefix(entry.URL, gatewayOrigins) {
			continue
		}
		stale = append(stale, entry)
	}
	return stale
}

func hasAnyPrefix(url string, prefixes []string) bool {
	for _, prefix := range prefixes {
		if strings.HasPrefix(url, prefix) {
			return true
		}
	}
	return false
}

func Prune(ctx context.Context, out io.Writer, agent Agent, entries []Entry) error {
	for _, entry := range entries {
		fmt.Fprintf(out, "- %s: %s を削除します\n", entry.Name, entry.URL)
		if err := agent.Remove(ctx, entry.Name); err != nil {
			return fmt.Errorf("%s remove %q: %w", agent.Name(), entry.Name, err)
		}
	}
	return nil
}

func PrintPrunePlan(out io.Writer, agent Agent, entries []Entry) {
	fmt.Fprintf(out, "%s の stale エントリ削除計画:\n", agent.Name())
	for _, entry := range entries {
		fmt.Fprintf(out, "- %s (%s):\n", entry.Name, entry.URL)
		fmt.Fprintf(out, "  - 削除: %s\n", shellish(agent.RemoveCommand(entry.Name)))
	}
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
