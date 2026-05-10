package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
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

func promptSelection(stdin io.Reader, stdout io.Writer, label string, items []string) ([]string, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("%s: 選択肢がありません", label)
	}
	reader := bufio.NewReader(stdin)
	fmt.Fprintf(stdout, "%s [all]:\n", label)
	for i, item := range items {
		fmt.Fprintf(stdout, "  %d) %s\n", i+1, item)
	}
	fmt.Fprint(stdout, "入力: ")
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
	if len(out) == 0 {
		return nil, fmt.Errorf("少なくとも 1 つ選択してください")
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
