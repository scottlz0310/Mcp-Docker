package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/scottlz0310/mcp-docker/v2/internal/register"
)

var errAborted = errors.New("ユーザーが中止しました")

func isTerminal(v any) bool {
	f, ok := v.(*os.File)
	if !ok {
		return false
	}
	info, err := f.Stat()
	if err != nil {
		return false
	}
	return (info.Mode() & os.ModeCharDevice) != 0
}

func promptSelection(reader *bufio.Reader, stdout io.Writer, label string, items []string) ([]string, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("%s: 選択肢がありません", label)
	}
	fmt.Fprintf(stdout, "%s [all]:\n", label)
	for i, item := range items {
		fmt.Fprintf(stdout, "  %d) %s\n", i+1, item)
	}
	fmt.Fprint(stdout, "入力 (例: 1,3 / all / none): ")
	line, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return nil, err
	}
	if errors.Is(err, io.EOF) && !strings.HasSuffix(line, "\n") {
		return nil, errAborted
	}
	return parseSelection(line, items)
}

func parseSelection(input string, items []string) ([]string, error) {
	input = strings.TrimSpace(input)
	if input == "" || strings.EqualFold(input, "all") {
		out := make([]string, len(items))
		copy(out, items)
		return out, nil
	}
	if strings.EqualFold(input, "none") || strings.EqualFold(input, "q") {
		return nil, errAborted
	}

	out, err := parseSelectionTokens(input, items)
	if err != nil {
		return nil, err
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("少なくとも 1 つ選択してください")
	}
	return out, nil
}

// parsePruneSelection は削除対象の選択を解析する。
// 削除は安全側に倒すため、parseSelection と異なり空入力・none は「何も削除しない」を意味する。
func parsePruneSelection(input string, items []string) ([]string, error) {
	input = strings.TrimSpace(input)
	if input == "" || strings.EqualFold(input, "none") {
		return nil, nil
	}
	if strings.EqualFold(input, "q") {
		return nil, errAborted
	}
	if strings.EqualFold(input, "all") {
		out := make([]string, len(items))
		copy(out, items)
		return out, nil
	}
	return parseSelectionTokens(input, items)
}

func parseSelectionTokens(input string, items []string) ([]string, error) {
	var out []string
	seen := make(map[string]struct{})
	for raw := range strings.SplitSeq(input, ",") {
		tok := strings.TrimSpace(raw)
		if tok == "" {
			continue
		}
		name, err := resolveSelectionToken(tok, items)
		if err != nil {
			return nil, err
		}
		if _, dup := seen[name]; dup {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, name)
	}
	return out, nil
}

func resolveSelectionToken(token string, items []string) (string, error) {
	if n, err := strconv.Atoi(token); err == nil {
		if n < 1 || n > len(items) {
			return "", fmt.Errorf("番号 %d は範囲外です (1-%d)", n, len(items))
		}
		return items[n-1], nil
	}
	for _, item := range items {
		if item == token {
			return item, nil
		}
	}
	return "", fmt.Errorf("不明な選択肢 %q (利用可能: %s)", token, strings.Join(items, ", "))
}

func promptPruneSelection(reader *bufio.Reader, stdout io.Writer, agentName string, entries []register.Entry) ([]register.Entry, error) {
	fmt.Fprintf(stdout, "%s: 計画に含まれない gateway 配下の登録が見つかりました。削除するものを選択 [none]:\n", agentName)
	for i, entry := range entries {
		fmt.Fprintf(stdout, "  %d) %s (%s)\n", i+1, entry.Name, entry.URL)
	}
	fmt.Fprint(stdout, "入力 (例: 1,3 / all / none): ")
	line, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return nil, err
	}
	if errors.Is(err, io.EOF) && !strings.HasSuffix(line, "\n") {
		return nil, errAborted
	}

	names := make([]string, len(entries))
	byName := make(map[string]register.Entry, len(entries))
	for i, entry := range entries {
		names[i] = entry.Name
		byName[entry.Name] = entry
	}
	selected, err := parsePruneSelection(line, names)
	if err != nil {
		return nil, err
	}
	out := make([]register.Entry, 0, len(selected))
	for _, name := range selected {
		out = append(out, byName[name])
	}
	return out, nil
}

func confirmPrune(reader *bufio.Reader, stdout io.Writer, agentName string, entries []register.Entry) (bool, error) {
	fmt.Fprintf(stdout, "%s: 以下の %d 件を削除します:\n", agentName, len(entries))
	for _, entry := range entries {
		fmt.Fprintf(stdout, "  - %s (%s)\n", entry.Name, entry.URL)
	}
	fmt.Fprint(stdout, "削除を実行しますか？ [y/N]: ")
	line, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return false, err
	}
	answer := strings.ToLower(strings.TrimSpace(line))
	return answer == "y" || answer == "yes", nil
}
