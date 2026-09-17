package instruction

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

const ModeSymlink = "symlink"

// Config は、ユーザーが管理する instruction source と配置方式だけを保持する。
// instruction の本文やアクセストークンは保存しない。
type Config struct {
	Source string `json:"source"`
	Mode   string `json:"mode"`
}

// ConfigPath は、instruction 管理設定の保存先を返す。
// MCP_DOCKER_INSTRUCTION_CONFIG はテストまたは隔離環境向けの上書きである。
func ConfigPath() (string, error) {
	if value := os.Getenv("MCP_DOCKER_INSTRUCTION_CONFIG"); value != "" {
		return filepath.Abs(value)
	}
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "", fmt.Errorf("instruction config: ユーザー設定ディレクトリを取得できません: %w", err)
	}
	return filepath.Join(configDir, "mcp-docker", "instructions.json"), nil
}

// LoadConfig は設定がまだ存在しない場合、空の設定を返す。
func LoadConfig() (Config, error) {
	path, err := ConfigPath()
	if err != nil {
		return Config{}, err
	}
	data, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return Config{}, nil
	}
	if err != nil {
		return Config{}, fmt.Errorf("instruction config を読み込めません (%s): %w", path, err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return Config{}, fmt.Errorf("instruction config のJSONが不正です (%s): %w", path, err)
	}
	return config, nil
}

// SaveConfig は設定ファイルを作成または更新する。
func SaveConfig(config Config) error {
	source, err := ValidateSource(config.Source)
	if err != nil {
		return err
	}
	if config.Mode == "" {
		config.Mode = ModeSymlink
	}
	if config.Mode != ModeSymlink {
		return fmt.Errorf("instruction config: 未対応の mode %q です（現在は %q のみ対応）", config.Mode, ModeSymlink)
	}

	path, err := ConfigPath()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("instruction config のディレクトリを作成できません (%s): %w", filepath.Dir(path), err)
	}

	config.Source = source
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("instruction config をJSON化できません: %w", err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(path, data, 0o600); err != nil {
		return fmt.Errorf("instruction config を保存できません (%s): %w", path, err)
	}
	return nil
}

// Resolve は明示された source、または保存済み設定から source を解決する。
func Resolve(sourceOverride string) (Config, error) {
	if strings.TrimSpace(sourceOverride) != "" {
		source, err := ValidateSource(sourceOverride)
		if err != nil {
			return Config{}, err
		}
		return Config{Source: source, Mode: ModeSymlink}, nil
	}

	config, err := LoadConfig()
	if err != nil {
		return Config{}, err
	}
	if strings.TrimSpace(config.Source) == "" {
		return Config{}, errors.New("instruction source が未設定です。--source <path> または instruction configure --source <path> を指定してください")
	}
	if config.Mode == "" {
		config.Mode = ModeSymlink
	}
	if config.Mode != ModeSymlink {
		return Config{}, fmt.Errorf("instruction config: 未対応の mode %q です（現在は %q のみ対応）", config.Mode, ModeSymlink)
	}
	config.Source, err = ValidateSource(config.Source)
	if err != nil {
		return Config{}, err
	}
	return config, nil
}

// ValidateSource は source が存在する通常ファイルであることを検証し、絶対パスに正規化する。
func ValidateSource(source string) (string, error) {
	source = strings.TrimSpace(source)
	if source == "" {
		return "", errors.New("instruction source: パスが空です")
	}
	abs, err := filepath.Abs(source)
	if err != nil {
		return "", fmt.Errorf("instruction source の絶対パスを解決できません: %w", err)
	}
	abs = filepath.Clean(abs)
	info, err := os.Stat(abs)
	if err != nil {
		return "", fmt.Errorf("instruction source を読み込めません (%s): %w", abs, err)
	}
	if !info.Mode().IsRegular() {
		return "", fmt.Errorf("instruction source は通常ファイルである必要があります: %s", abs)
	}
	return abs, nil
}
