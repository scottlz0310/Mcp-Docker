package register

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
)

type Runner interface {
	Run(context.Context, string, ...string) (string, error)
}

type ExecRunner struct{}

func (ExecRunner) Run(ctx context.Context, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return string(out), fmt.Errorf("%s: %w\n%s", shellish(append([]string{name}, args...)), err, strings.TrimSpace(string(out)))
	}
	return string(out), nil
}

func shellish(parts []string) string {
	quoted := make([]string, 0, len(parts))
	for _, part := range parts {
		if part == "" || strings.ContainsAny(part, " \t\"'") {
			quoted = append(quoted, fmt.Sprintf("%q", part))
			continue
		}
		quoted = append(quoted, part)
	}
	return strings.Join(quoted, " ")
}
