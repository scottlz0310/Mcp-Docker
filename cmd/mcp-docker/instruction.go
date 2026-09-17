package main

import (
	"bufio"
	"errors"
	"flag"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/scottlz0310/mcp-docker/v2/internal/instruction"
)

const instructionUsage = `mcp-docker instruction は、ユーザー管理の instruction source を各 CLI 入口へリンクします。

使い方:
  mcp-docker instruction configure --source <path> [--mode symlink]
  mcp-docker instruction status    [--agent <csv>|all] [--source <path>]
  mcp-docker instruction link      [--agent <csv>|all] [--source <path>] [--dry-run] [--yes]
  mcp-docker instruction repair    [--agent <csv>|all] [--source <path>] [--dry-run] [--yes]

source の本文は本リポジトリへコピーしません。configure はユーザー設定へ source のパスだけを保存し、
link / repair は各 CLI のユーザー単位の入口から source への symlink を作成します。
`

type instructionOptions struct {
	agent  string
	source string
	mode   string
	dryRun bool
	yes    bool
}

func runInstruction(args []string, stdout, stderr io.Writer, stdin io.Reader) error {
	if len(args) == 0 {
		fmt.Fprint(stdout, instructionUsage)
		return nil
	}

	sub := args[0]
	switch sub {
	case "help", "-h", "--help":
		fmt.Fprint(stdout, instructionUsage)
		return nil
	case "configure", "status", "link", "repair":
	default:
		return fmt.Errorf("不明な instruction サブコマンド %q\n\n%s", sub, instructionUsage)
	}

	flags := flag.NewFlagSet("instruction "+sub, flag.ContinueOnError)
	flags.SetOutput(stderr)
	opts := instructionOptions{}
	if sub != "configure" {
		flags.StringVar(&opts.agent, "agent", "all", "対象エージェント（カンマ区切り可）: "+strings.Join(instruction.ClientNames(), ", ")+", all")
	}
	flags.StringVar(&opts.source, "source", "", "ユーザー管理の instruction source ファイル")
	switch sub {
	case "configure":
		flags.StringVar(&opts.mode, "mode", instruction.ModeSymlink, "配置方式（現在は symlink のみ）")
	case "link", "repair":
		flags.BoolVar(&opts.dryRun, "dry-run", false, "実行せず、リンク作成・バックアップ計画を表示")
		flags.BoolVar(&opts.yes, "yes", false, "既存の配置をバックアップして置き換える確認を省略")
	}
	if err := flags.Parse(args[1:]); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return fmt.Errorf("想定外の引数です: %s", strings.Join(flags.Args(), " "))
	}

	switch sub {
	case "configure":
		return runInstructionConfigure(stdout, opts)
	case "status":
		return runInstructionStatus(stdout, opts)
	default:
		return runInstructionLink(sub == "repair", stdout, stdin, opts)
	}
}

func runInstructionConfigure(stdout io.Writer, opts instructionOptions) error {
	if strings.TrimSpace(opts.source) == "" {
		return errors.New("instruction configure: --source は必須です")
	}
	if opts.mode == "" {
		opts.mode = instruction.ModeSymlink
	}
	if opts.mode != instruction.ModeSymlink {
		return fmt.Errorf("instruction configure: 未対応の mode %q です（現在は %q のみ対応）", opts.mode, instruction.ModeSymlink)
	}

	source, err := instruction.ValidateSource(opts.source)
	if err != nil {
		return err
	}
	if err := instruction.SaveConfig(instruction.Config{Source: source, Mode: opts.mode}); err != nil {
		return err
	}
	configPath, err := instruction.ConfigPath()
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "instruction source を設定しました: %s\n", source)
	fmt.Fprintf(stdout, "設定ファイル: %s\n", configPath)
	return nil
}

func selectInstructionClients(value string) ([]instruction.Client, error) {
	names, err := resolveSelection(value, instruction.ClientNames(), "agent")
	if err != nil {
		return nil, err
	}
	home, err := instruction.UserHome()
	if err != nil {
		return nil, fmt.Errorf("instruction: ユーザーホームを取得できません: %w", err)
	}
	return instruction.Select(instruction.Clients(home), names)
}

func runInstructionStatus(stdout io.Writer, opts instructionOptions) error {
	config, err := instruction.ResolveStatus(opts.source)
	if err != nil {
		return err
	}
	clients, err := selectInstructionClients(opts.agent)
	if err != nil {
		return err
	}

	sourceStatus, err := instruction.InspectSource(config.Source)
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "instruction source: %s [%s]\n", config.Source, instruction.SourceStatusLabel(sourceStatus))
	for _, client := range clients {
		status, err := instruction.Inspect(config.Source, client)
		if err != nil {
			return fmt.Errorf("%s: %w", client.Name, err)
		}
		fmt.Fprintf(stdout, "- %s (%s): %s", client.Name, client.Path, instruction.StateLabel(status.State))
		if status.LinkType != "" {
			fmt.Fprintf(stdout, " [%s]", status.LinkType)
		}
		if status.CurrentTarget != "" {
			fmt.Fprintf(stdout, " -> %s", status.CurrentTarget)
		}
		fmt.Fprintln(stdout)
	}
	return nil
}

func runInstructionLink(repair bool, stdout io.Writer, stdin io.Reader, opts instructionOptions) error {
	config, err := instruction.Resolve(opts.source)
	if err != nil {
		return err
	}
	clients, err := selectInstructionClients(opts.agent)
	if err != nil {
		return err
	}

	reader := bufio.NewReader(stdin)
	now := time.Now()
	verb := "link"
	if repair {
		verb = "repair"
	}
	for _, client := range clients {
		status, err := instruction.Inspect(config.Source, client)
		if err != nil {
			return fmt.Errorf("%s: %w", client.Name, err)
		}
		if repair {
			if !instruction.NeedsRepair(status.State) {
				if status.State == instruction.StateLinked {
					fmt.Fprintf(stdout, "- %s: %s (%s)\n", client.Name, instruction.ActionLabel(instruction.ActionSkip), instruction.StateLabel(status.State))
				} else {
					fmt.Fprintf(stdout, "- %s: 修復対象外（%s）\n", client.Name, instruction.StateLabel(status.State))
				}
				continue
			}
		} else if status.State == instruction.StateDirectory || status.State == instruction.StateUnsupported {
			return fmt.Errorf("%s: %s (%s) は自動置換できません", client.Name, client.Path, instruction.StateLabel(status.State))
		}

		if status.State == instruction.StateLinked {
			fmt.Fprintf(stdout, "- %s: %s (%s)\n", client.Name, instruction.ActionLabel(instruction.ActionSkip), instruction.StateLabel(status.State))
			continue
		}

		backupPath := ""
		if instruction.NeedsReplacement(status.State) {
			backupPath = instruction.BackupPath(client.Path, now)
		}
		if opts.dryRun {
			printInstructionPlan(stdout, verb, client, status, backupPath)
			continue
		}
		if backupPath != "" && !opts.yes {
			ok, err := confirmInstructionReplace(reader, stdout, client, status, backupPath)
			if err != nil {
				return err
			}
			if !ok {
				fmt.Fprintf(stdout, "- %s: 中止しました\n", client.Name)
				continue
			}
		}

		result, err := instruction.Link(config.Source, client, now)
		if err != nil {
			return fmt.Errorf("%s: %w", client.Name, err)
		}
		fmt.Fprintf(stdout, "- %s: %s", client.Name, instruction.ActionLabel(result.Action))
		if result.BackupPath != "" {
			fmt.Fprintf(stdout, "（%s）", result.BackupPath)
		}
		fmt.Fprintln(stdout)
	}
	return nil
}

func printInstructionPlan(stdout io.Writer, verb string, client instruction.Client, status instruction.Status, backupPath string) {
	action := instruction.ActionLink
	if backupPath != "" {
		action = instruction.ActionReplace
	}
	fmt.Fprintf(stdout, "- %s: %s (%s, 現在: %s)\n", client.Name, verb, instruction.ActionLabel(action), instruction.StateLabel(status.State))
	fmt.Fprintf(stdout, "  - 配置先: %s\n", client.Path)
	fmt.Fprintf(stdout, "  - source: %s\n", status.Source)
	if backupPath != "" {
		fmt.Fprintf(stdout, "  - バックアップ: %s\n", backupPath)
	}
}

func confirmInstructionReplace(reader *bufio.Reader, stdout io.Writer, client instruction.Client, status instruction.Status, backupPath string) (bool, error) {
	fmt.Fprintf(stdout, "- %s: %s (%s) を置き換えます。既存の配置は次へ移動します: %s\n", client.Name, client.Path, instruction.StateLabel(status.State), backupPath)
	fmt.Fprint(stdout, "実行しますか？ [y/N]: ")
	line, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return false, err
	}
	answer := strings.ToLower(strings.TrimSpace(line))
	return answer == "y" || answer == "yes", nil
}
