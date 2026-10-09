package compose

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// Windowsのmakeは単純なrecipeを直接実行するため、shell scriptではなく実行可能なmockを使う。
func TestMain(m *testing.M) {
	if os.Getenv("MAKE_DOCKER_HELPER") == "1" && strings.TrimSuffix(filepath.Base(os.Args[0]), ".exe") == "docker" {
		args := os.Args[1:]
		if len(args) == 1 && args[0] == "--v4-make-test-marker" {
			fmt.Println("test-docker")
			os.Exit(0)
		}
		file, err := os.OpenFile(os.Getenv("MAKE_DOCKER_LOG"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		_, err = fmt.Fprintf(file, "%s|%s\n", os.Getenv("COMPOSE_FILE"), strings.Join(args, " "))
		closeErr := file.Close()
		if err != nil || closeErr != nil {
			os.Exit(2)
		}
		if strings.Join(args, " ") == "compose config --quiet" && os.Getenv("DOCKER_CONFIG_FAIL") == "1" {
			os.Exit(42)
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestMakeDedicatedAppLifecycle(t *testing.T) {
	for _, target := range []string{"pull", "pull-main", "restart", "restart-main"} {
		t.Run(target, func(t *testing.T) {
			output, calls, err := runMakeAppFixture(t, target, nil)
			if err != nil {
				t.Fatalf("make: %v\n%s", err, output)
			}
			if !strings.HasPrefix(calls, "docker-compose.yml|compose config --quiet\n") {
				t.Fatalf("設定検証が最初ではありません: %s", calls)
			}
			if strings.Contains(calls, "obsolete") {
				t.Fatalf("シェルの暫定Compose設定を使用しました: %s", calls)
			}
			if strings.HasPrefix(target, "restart") {
				down := strings.Index(calls, "compose --profile * down")
				up := strings.Index(calls, "compose up -d")
				if down < 0 || up <= down {
					t.Fatalf("停止・起動の順序が不正です: %s", calls)
				}
			} else if !strings.Contains(calls, "compose pull") {
				t.Fatalf("pullが実行されません: %s", calls)
			}
			if strings.Contains(output, "fixture-private-key") || strings.Contains(output, "proxy-secret") {
				t.Fatal("makeが秘密値を表示しました")
			}
		})
	}
}

func TestMakeRejectsInvalidAppConfigBeforeStopping(t *testing.T) {
	for _, tt := range []struct{ name, variable, value string }{
		{"App ID欠落", "REVIEW_RAVEN_GITHUB_APP_ID", ""},
		{"Installation ID欠落", "REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID", ""},
		{"組織欠落", "REVIEW_RAVEN_GITHUB_APP_OWNER", ""},
		{"鍵欠落", "REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64", ""},
		{"共有鍵欠落", "REVIEW_RAVEN_PROXY_SECRET", ""},
		{"短い共有鍵", "REVIEW_RAVEN_PROXY_SECRET", "short"},
		{"Compose不正", "DOCKER_CONFIG_FAIL", "1"},
	} {
		t.Run(tt.name, func(t *testing.T) {
			output, calls, err := runMakeAppFixture(t, "restart-main", map[string]string{tt.variable: tt.value})
			if err == nil {
				t.Fatalf("不正設定で成功しました: %s", output)
			}
			if strings.Contains(calls, " down") || strings.Contains(calls, " up") {
				t.Fatalf("不正設定でコンテナを変更しました: %s", calls)
			}
			if strings.Contains(output, "fixture-private-key") || strings.Contains(output, "proxy-secret") {
				t.Fatal("makeが秘密値を表示しました")
			}
		})
	}
}

func runMakeAppFixture(t *testing.T, target string, changed map[string]string) (string, string, error) {
	t.Helper()
	makePath, err := exec.LookPath("make")
	if err != nil {
		t.Skip("GNU Makeがありません")
	}
	dir := t.TempDir()
	data, err := os.ReadFile(filepath.Join("..", "..", "Makefile"))
	if err != nil {
		t.Fatal(err)
	}
	data = append(data, []byte("\n.PHONY: verify-docker-mock\nverify-docker-mock:\n\t@docker --v4-make-test-marker\n")...)
	if err := os.WriteFile(filepath.Join(dir, "Makefile"), data, 0o600); err != nil {
		t.Fatal(err)
	}
	scriptsDir := filepath.Join(dir, "scripts")
	if err := os.Mkdir(scriptsDir, 0o700); err != nil {
		t.Fatal(err)
	}
	script, err := os.ReadFile(filepath.Join("..", "..", "scripts", "check-review-raven-app.sh"))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(scriptsDir, "check-review-raven-app.sh"), script, 0o700); err != nil {
		t.Fatal(err)
	}
	binDir := filepath.Join(dir, "bin")
	if err := os.Mkdir(binDir, 0o700); err != nil {
		t.Fatal(err)
	}
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	mock, err := os.ReadFile(executable)
	if err != nil {
		t.Fatal(err)
	}
	mockName := "docker"
	if runtime.GOOS == "windows" {
		mockName += ".exe"
	}
	if err := os.WriteFile(filepath.Join(binDir, mockName), mock, 0o755); err != nil {
		t.Fatal(err)
	}
	logPath := filepath.Join(dir, "docker.log")
	env := map[string]string{
		"OAUTH_CLIENT_ID": "fixture-client", "OAUTH_CLIENT_SECRET": "fixture-secret",
		"GITHUB_APP_ID": "4076097", "GITHUB_APP_INSTALLATION_ID": "167771183",
		"GITHUB_APP_PRIVATE_KEY_B64": "fixture-gateway-key", "MCP_GATEWAY_INTERNAL_SECRET": strings.Repeat("x", 32),
		"REVIEW_RAVEN_GITHUB_APP_ID": "5184108", "REVIEW_RAVEN_GITHUB_APP_INSTALLATION_ID": "169443079",
		"REVIEW_RAVEN_GITHUB_APP_OWNER": "scottlz0310", "REVIEW_RAVEN_GITHUB_APP_PRIVATE_KEY_B64": "fixture-private-key",
		"REVIEW_RAVEN_PROXY_SECRET": "proxy-secret-" + strings.Repeat("x", 32), "PLAYWRIGHT_MCP_ENABLED": "",
		"COMPOSE_FILE": "obsolete.yml", "MAKE_DOCKER_LOG": filepath.ToSlash(logPath), "DOCKER_CONFIG_FAIL": "0",
		"MAKE_DOCKER_HELPER": "1",
	}
	for key, value := range changed {
		env[key] = value
	}
	processEnv := []string{}
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		if _, replaced := env[key]; !replaced && !strings.EqualFold(key, "PATH") {
			processEnv = append(processEnv, entry)
		}
	}
	processEnv = append(processEnv, "PATH="+binDir+string(os.PathListSeparator)+os.Getenv("PATH"))
	for key, value := range env {
		processEnv = append(processEnv, key+"="+value)
	}
	run := func(args ...string) ([]byte, error) {
		cmd := exec.Command(makePath, append([]string{"--no-print-directory"}, args...)...)
		cmd.Dir, cmd.Env = dir, processEnv
		return cmd.CombinedOutput()
	}
	marker, err := run("verify-docker-mock")
	if err != nil || !strings.Contains(string(marker), "test-docker") {
		t.Fatalf("Docker mockを解決できません: %v %s", err, marker)
	}
	output, runErr := run("-j4", target)
	log, err := os.ReadFile(logPath)
	if err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	return string(output), string(log), runErr
}
