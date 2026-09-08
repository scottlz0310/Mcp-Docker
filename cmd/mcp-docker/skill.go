package main

import (
	"bufio"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	mcpdocker "github.com/scottlz0310/mcp-docker/v2"
	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

const skillUsage = `mcp-docker skill は skill を各 CLI エージェントへ配置します。

使い方:
  mcp-docker skill list
  mcp-docker skill status    [--agent <csv>|all] [--skill <csv>|all] [--skills-dir path]
  mcp-docker skill install   [--agent <csv>|all] [--skill <csv>|all] [--skills-dir path] [--dry-run] [--yes] [--force]
  mcp-docker skill uninstall [--agent <csv>|all] [--skill <csv>|all] [--skills-dir path] [--dry-run] [--yes] [--force]

skill 本体は本リポジトリの skills/ に収蔵され、バイナリへ埋め込まれています。
--skills-dir を指定すると埋め込みではなく指定ディレクトリのカタログを使います。
`

type skillOptions struct {
	agent     string
	skill     string
	skillsDir string
	dryRun    bool
	yes       bool
	force     bool
}

func runSkill(args []string, stdout, stderr io.Writer, stdin io.Reader) error {
	if len(args) == 0 {
		fmt.Fprint(stdout, skillUsage)
		return nil
	}

	sub := args[0]
	switch sub {
	case "help", "-h", "--help":
		fmt.Fprint(stdout, skillUsage)
		return nil
	case "list", "status", "install", "uninstall":
	default:
		return fmt.Errorf("不明な skill サブコマンド %q\n\n%s", sub, skillUsage)
	}

	flags := flag.NewFlagSet("skill "+sub, flag.ContinueOnError)
	flags.SetOutput(stderr)
	opts := skillOptions{}
	flags.StringVar(&opts.agent, "agent", "all", "対象エージェント（カンマ区切り可）: "+strings.Join(skill.ClientNames(), ", ")+", all")
	flags.StringVar(&opts.skill, "skill", "all", "対象 skill（カンマ区切り可）: <name>, all")
	flags.StringVar(&opts.skillsDir, "skills-dir", "", "埋め込みではなく指定ディレクトリの skill カタログを使う")
	if sub != "list" && sub != "status" {
		flags.BoolVar(&opts.dryRun, "dry-run", false, "実行せず、配置計画を表示")
		flags.BoolVar(&opts.yes, "yes", false, "確認プロンプトを省略")
		flags.BoolVar(&opts.force, "force", false, "install: 最新でも再配置 / uninstall: 管理外の配置も削除")
	}
	if err := flags.Parse(args[1:]); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return fmt.Errorf("想定外の引数です: %s", strings.Join(flags.Args(), " "))
	}

	catalog, err := loadSkillCatalog(opts.skillsDir)
	if err != nil {
		return err
	}

	if sub == "list" {
		return printSkillList(stdout, catalog, opts.skillsDir)
	}

	skills, err := selectSkills(catalog, opts.skill)
	if err != nil {
		return err
	}
	clients, err := selectSkillClients(opts.agent)
	if err != nil {
		return err
	}

	switch sub {
	case "status":
		return runSkillStatus(stdout, clients, skills)
	case "install":
		return runSkillInstall(stdout, stdin, clients, skills, opts)
	default:
		return runSkillUninstall(stdout, stdin, clients, skills, opts)
	}
}

func loadSkillCatalog(dir string) ([]skill.Skill, error) {
	if dir == "" {
		return skill.LoadCatalog(mcpdocker.SkillsFS, mcpdocker.SkillsRoot)
	}
	return skill.LoadCatalog(os.DirFS(dir), ".")
}

func selectSkills(catalog []skill.Skill, value string) ([]skill.Skill, error) {
	names, err := resolveSelection(value, skill.Names(catalog), "skill")
	if err != nil {
		return nil, err
	}
	return skill.Select(catalog, names)
}

func selectSkillClients(value string) ([]skill.Client, error) {
	names, err := resolveSelection(value, skill.ClientNames(), "agent")
	if err != nil {
		return nil, err
	}
	home, err := skill.UserHome()
	if err != nil {
		return nil, err
	}
	return skill.SelectClients(skill.Clients(home), names)
}

func printSkillList(stdout io.Writer, catalog []skill.Skill, dir string) error {
	source := "埋め込みカタログ (skills/)"
	if dir != "" {
		source = dir
	}
	fmt.Fprintf(stdout, "skill カタログ: %s\n", source)
	for _, s := range catalog {
		fmt.Fprintf(stdout, "- %s (%d ファイル, %s)\n", s.Name, len(s.Files), shortHash(s.ContentHash))
	}
	return nil
}

func runSkillStatus(stdout io.Writer, clients []skill.Client, skills []skill.Skill) error {
	for _, client := range clients {
		fmt.Fprintf(stdout, "%s (%s):\n", client.Name, client.Dir)
		for _, s := range skills {
			status, err := skill.Inspect(client, s)
			if err != nil {
				return err
			}
			fmt.Fprintf(stdout, "- %s: %s%s\n", s.Name, status.State, versionSuffix(status))
		}
	}
	return nil
}

func versionSuffix(status skill.Status) string {
	if status.InstalledVersion == "" {
		return ""
	}
	return fmt.Sprintf(" (配置時 mcp-docker %s)", status.InstalledVersion)
}

func runSkillInstall(stdout io.Writer, stdin io.Reader, clients []skill.Client, skills []skill.Skill, opts skillOptions) error {
	reader := bufio.NewReader(stdin)
	now := time.Now()
	for _, client := range clients {
		fmt.Fprintf(stdout, "%s (%s):\n", client.Name, client.Dir)
		for _, s := range skills {
			status, err := skill.Inspect(client, s)
			if err != nil {
				return err
			}
			plan := skill.PlanInstall(status, s, opts.force)
			if opts.dryRun {
				printSkillPlan(stdout, plan)
				continue
			}
			if plan.Action == skill.ActionSkip {
				fmt.Fprintf(stdout, "- %s: %s (%s)\n", s.Name, skill.ActionSkip, status.State)
				continue
			}
			if plan.NeedsConfirm() && !opts.yes {
				ok, err := confirmSkillAction(reader, stdout, plan)
				if err != nil {
					return err
				}
				if !ok {
					fmt.Fprintf(stdout, "- %s: 中止しました\n", s.Name)
					continue
				}
			}
			if err := skill.Install(plan, s, version, now); err != nil {
				return err
			}
			fmt.Fprintf(stdout, "- %s: %s (%d ファイル", s.Name, plan.Action, len(plan.Write))
			if len(plan.Delete) > 0 {
				fmt.Fprintf(stdout, ", %d ファイル削除", len(plan.Delete))
			}
			fmt.Fprintln(stdout, ")")
		}
	}
	return nil
}

func runSkillUninstall(stdout io.Writer, stdin io.Reader, clients []skill.Client, skills []skill.Skill, opts skillOptions) error {
	reader := bufio.NewReader(stdin)
	for _, client := range clients {
		fmt.Fprintf(stdout, "%s (%s):\n", client.Name, client.Dir)
		for _, s := range skills {
			status, err := skill.Inspect(client, s)
			if err != nil {
				return err
			}
			plan := skill.PlanRemove(status, opts.force)
			if opts.dryRun {
				printSkillPlan(stdout, plan)
				continue
			}
			if plan.Action == skill.ActionSkip {
				fmt.Fprintf(stdout, "- %s: %s (%s)%s\n", s.Name, skill.ActionSkip, status.State, unmanagedHint(status))
				continue
			}
			if !opts.yes {
				ok, err := confirmSkillAction(reader, stdout, plan)
				if err != nil {
					return err
				}
				if !ok {
					fmt.Fprintf(stdout, "- %s: 中止しました\n", s.Name)
					continue
				}
			}
			if err := skill.Remove(plan); err != nil {
				return err
			}
			fmt.Fprintf(stdout, "- %s: %s%s\n", s.Name, plan.Action, keptHint(plan))
		}
	}
	return nil
}

func unmanagedHint(status skill.Status) string {
	if status.State != skill.StateUnmanaged {
		return ""
	}
	return " — mcp-docker が配置したものではありません。削除するには --force を指定してください"
}

// keptHint は配置先に残したユーザーファイルを伝える。
func keptHint(plan skill.Plan) string {
	if plan.Action != skill.ActionRemovePartial {
		return ""
	}
	return fmt.Sprintf(" — %s は残しました（ディレクトリごと削除するには --force）", strings.Join(plan.Unmanaged, ", "))
}

func printSkillPlan(stdout io.Writer, plan skill.Plan) {
	fmt.Fprintf(stdout, "- %s: %s (現在: %s)\n", plan.Skill, plan.Action, plan.State)
	for _, rel := range plan.Write {
		fmt.Fprintf(stdout, "  - 書き込み: %s\n", rel)
	}
	for _, rel := range plan.Delete {
		fmt.Fprintf(stdout, "  - 削除: %s\n", rel)
	}
	if plan.RemoveDir {
		fmt.Fprintf(stdout, "  - 削除: %s\n", plan.Dir)
	}
	if plan.Action == skill.ActionRemovePartial {
		fmt.Fprintf(stdout, "  - 保持: %s\n", strings.Join(plan.Unmanaged, ", "))
	}
}

func confirmSkillAction(reader *bufio.Reader, stdout io.Writer, plan skill.Plan) (bool, error) {
	switch plan.Action {
	case skill.ActionAdopt:
		fmt.Fprintf(stdout, "- %s: %s に mcp-docker 管理外の配置があります。上書きすると既存の内容は失われます。\n", plan.Skill, plan.Dir)
	case skill.ActionRemove:
		fmt.Fprintf(stdout, "- %s: %s を削除します。\n", plan.Skill, plan.Dir)
	case skill.ActionRemovePartial:
		fmt.Fprintf(stdout, "- %s: %s から mcp-docker が配置したファイルを削除します（%s は残します）。\n",
			plan.Skill, plan.Dir, strings.Join(plan.Unmanaged, ", "))
	}
	fmt.Fprint(stdout, "実行しますか？ [y/N]: ")
	line, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return false, err
	}
	answer := strings.ToLower(strings.TrimSpace(line))
	return answer == "y" || answer == "yes", nil
}

func shortHash(hash string) string {
	if len(hash) <= 12 {
		return hash
	}
	return hash[:12]
}
