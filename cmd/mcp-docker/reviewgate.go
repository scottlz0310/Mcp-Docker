package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	mcpdocker "github.com/scottlz0310/mcp-docker/v2"
	"github.com/scottlz0310/mcp-docker/v2/internal/reviewgate"
	"github.com/scottlz0310/mcp-docker/v2/internal/skill"
)

const reviewGateUsage = `mcp-docker reviewgate は reviewed-side 完了記録を検証します。

使い方:
  mcp-docker reviewgate validate --record <path> --repo <owner/repository> --pr <number> --head-sha <sha>
`

func runReviewGate(args []string, stdout, stderr io.Writer) error {
	if len(args) == 0 {
		fmt.Fprint(stdout, reviewGateUsage)
		return nil
	}
	if args[0] != "validate" {
		return fmt.Errorf("不明な reviewgate サブコマンド %q\n\n%s", args[0], reviewGateUsage)
	}

	flags := flag.NewFlagSet("reviewgate validate", flag.ContinueOnError)
	flags.SetOutput(stderr)
	var recordPath, repo, headSHA string
	var prNumber int
	flags.StringVar(&recordPath, "record", "", "完了記録 JSON のパス（必須）")
	flags.StringVar(&repo, "repo", "", "対象 repository（owner/repository、必須）")
	flags.IntVar(&prNumber, "pr", 0, "対象 PR 番号（必須）")
	flags.StringVar(&headSHA, "head-sha", "", "直前に固定した PR HEAD SHA（必須）")
	if err := flags.Parse(args[1:]); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return fmt.Errorf("想定外の引数です: %s", strings.Join(flags.Args(), " "))
	}
	if recordPath == "" {
		return fmt.Errorf("--record は必須です")
	}

	data, err := os.ReadFile(recordPath)
	if err != nil {
		return fmt.Errorf("完了記録 %q の読み込みに失敗しました: %w", recordPath, err)
	}
	record, err := reviewgate.DecodeCompletionRecord(data)
	if err != nil {
		return err
	}

	revision, err := embeddedReviewedSideRevision()
	if err != nil {
		return err
	}
	target := reviewgate.ValidationTarget{
		Repo:          repo,
		PRNumber:      prNumber,
		HeadSHA:       headSHA,
		SkillRevision: revision,
	}
	if err := record.ValidateFor(target); err != nil {
		return err
	}

	fmt.Fprintf(stdout, "reviewgate: valid repo=%s pr=%d head=%s skill=%s revision=%d\n",
		record.Repo, record.PRNumber, record.HeadSHA, record.SkillID, record.SkillRevision)
	return nil
}

func embeddedReviewedSideRevision() (int, error) {
	catalog, err := skill.LoadCatalog(mcpdocker.SkillsFS, mcpdocker.SkillsRoot)
	if err != nil {
		return 0, &reviewgate.StopError{
			Code:    reviewgate.StopSkillUnavailable,
			Field:   "skillCatalog",
			Message: "埋め込み skill カタログを読み込めません",
			Cause:   err,
		}
	}
	selected, err := skill.Select(catalog, []string{reviewgate.ReviewedSideSkillID})
	if err != nil {
		return 0, &reviewgate.StopError{
			Code:    reviewgate.StopSkillUnavailable,
			Field:   "skillId",
			Message: "reviewed-side skill が埋め込みカタログにありません",
			Cause:   err,
		}
	}
	return selected[0].Revision, nil
}
