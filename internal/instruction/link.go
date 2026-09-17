package instruction

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type State string

const (
	StateAbsent      State = "absent"
	StateLinked      State = "linked"
	StateBroken      State = "broken"
	StateWrongTarget State = "wrong-target"
	StateRegular     State = "regular-file"
	StateDirectory   State = "directory"
	StateUnsupported State = "unsupported"
)

type Status struct {
	Client        Client
	Source        string
	State         State
	LinkType      string
	CurrentTarget string
}

type Action string

const (
	ActionSkip    Action = "skip"
	ActionLink    Action = "link"
	ActionReplace Action = "replace"
)

type Result struct {
	Action     Action
	BackupPath string
}

// Inspect は配置先を変更せず、現在のリンク状態だけを調べる。
func Inspect(source string, client Client) (Status, error) {
	normalizedSource, err := ValidateSource(source)
	if err != nil {
		return Status{}, err
	}
	status := Status{
		Client: client,
		Source: normalizedSource,
		State:  StateAbsent,
	}

	info, err := os.Lstat(client.Path)
	if errors.Is(err, fs.ErrNotExist) {
		return status, nil
	}
	if err != nil {
		return Status{}, fmt.Errorf("instruction 配置先を調べられません (%s): %w", client.Path, err)
	}

	if info.Mode()&os.ModeSymlink != 0 {
		status.LinkType = "symlink"
		currentTarget, err := resolvedLinkTarget(client.Path)
		if err != nil {
			return Status{}, err
		}
		status.CurrentTarget = currentTarget
		if samePath(currentTarget, normalizedSource) {
			status.State = StateLinked
			return status, nil
		}
		if _, err := os.Stat(client.Path); errors.Is(err, fs.ErrNotExist) {
			status.State = StateBroken
			return status, nil
		} else if err != nil {
			return Status{}, fmt.Errorf("instruction リンク先を調べられません (%s): %w", client.Path, err)
		}
		status.State = StateWrongTarget
		return status, nil
	}

	switch {
	case info.IsDir():
		status.LinkType = "directory"
		status.State = StateDirectory
	case info.Mode().IsRegular():
		status.LinkType = "regular-file"
		status.State = StateRegular
	default:
		status.LinkType = "unsupported"
		status.State = StateUnsupported
	}
	return status, nil
}

// NeedsReplacement は、通常ファイルまたは別のリンクをバックアップして置き換えられる状態かを返す。
func NeedsReplacement(state State) bool {
	switch state {
	case StateBroken, StateWrongTarget, StateRegular:
		return true
	default:
		return false
	}
}

// NeedsRepair は、既存の symlink を修復できる状態かを返す。
// 通常ファイルや未配置の入口は repair の対象にせず、link の確認付き処理へ委ねる。
func NeedsRepair(state State) bool {
	return state == StateBroken || state == StateWrongTarget
}

// StateLabel は CLI 表示用の状態名を返す。
func StateLabel(state State) string {
	switch state {
	case StateAbsent:
		return "未配置"
	case StateLinked:
		return "リンク済み"
	case StateBroken:
		return "壊れたリンク"
	case StateWrongTarget:
		return "別の source へのリンク"
	case StateRegular:
		return "通常ファイル"
	case StateDirectory:
		return "ディレクトリ"
	case StateUnsupported:
		return "未対応の配置"
	default:
		return string(state)
	}
}

// ActionLabel は CLI 表示用の操作名を返す。
func ActionLabel(action Action) string {
	switch action {
	case ActionSkip:
		return "変更なし"
	case ActionLink:
		return "リンク作成"
	case ActionReplace:
		return "バックアップ後にリンク置換"
	default:
		return string(action)
	}
}

// BackupPath は、対象の隣に作るバックアップ名を返す。
func BackupPath(target string, now time.Time) string {
	base := target + ".mcp-docker-backup-" + now.UTC().Format("20060102T150405.000000000Z")
	candidate := base
	for suffix := 1; ; suffix++ {
		if _, err := os.Lstat(candidate); err != nil {
			return candidate
		}
		candidate = fmt.Sprintf("%s.%d", base, suffix)
	}
}

// Link は source への symlink を作成する。既存の通常ファイル／リンクは、先に backupPath へ移動する。
// ディレクトリや未対応のファイル種別は置き換えない。
func Link(source string, client Client, now time.Time) (Result, error) {
	normalizedSource, err := ValidateSource(source)
	if err != nil {
		return Result{}, err
	}
	if samePath(normalizedSource, client.Path) {
		return Result{}, fmt.Errorf("instruction source と配置先が同じです: %s", client.Path)
	}

	status, err := Inspect(normalizedSource, client)
	if err != nil {
		return Result{}, err
	}
	if status.State == StateLinked {
		return Result{Action: ActionSkip}, nil
	}
	if status.State == StateDirectory {
		return Result{}, fmt.Errorf("instruction 配置先はディレクトリのため置き換えません: %s", client.Path)
	}
	if status.State == StateUnsupported {
		return Result{}, fmt.Errorf("instruction 配置先は未対応のファイル種別のため置き換えません: %s", client.Path)
	}

	if err := os.MkdirAll(filepath.Dir(client.Path), 0o700); err != nil {
		return Result{}, fmt.Errorf("instruction 配置先の親ディレクトリを作成できません (%s): %w", filepath.Dir(client.Path), err)
	}

	backupPath := ""
	if NeedsReplacement(status.State) {
		backupPath = BackupPath(client.Path, now)
		if err := os.Rename(client.Path, backupPath); err != nil {
			return Result{}, fmt.Errorf("既存の instruction 配置をバックアップできません (%s -> %s): %w", client.Path, backupPath, err)
		}
	}

	if err := os.Symlink(normalizedSource, client.Path); err != nil {
		if backupPath != "" {
			if restoreErr := os.Rename(backupPath, client.Path); restoreErr != nil {
				return Result{}, fmt.Errorf("instruction のリンク作成に失敗し、バックアップの復元にも失敗しました (%s): %w", client.Path, errors.Join(err, restoreErr))
			}
		}
		return Result{}, fmt.Errorf("instruction の symlink を作成できません (%s -> %s): %w", client.Path, normalizedSource, err)
	}

	if backupPath == "" {
		return Result{Action: ActionLink}, nil
	}
	return Result{Action: ActionReplace, BackupPath: backupPath}, nil
}

func resolvedLinkTarget(path string) (string, error) {
	target, err := os.Readlink(path)
	if err != nil {
		return "", fmt.Errorf("instruction symlink のリンク先を読み込めません (%s): %w", path, err)
	}
	if !filepath.IsAbs(target) {
		target = filepath.Join(filepath.Dir(path), target)
	}
	abs, err := filepath.Abs(target)
	if err != nil {
		return "", fmt.Errorf("instruction symlink のリンク先を解決できません (%s): %w", path, err)
	}
	return filepath.Clean(abs), nil
}

func samePath(left, right string) bool {
	leftAbs, leftErr := filepath.Abs(left)
	rightAbs, rightErr := filepath.Abs(right)
	if leftErr == nil && rightErr == nil {
		left = filepath.Clean(leftAbs)
		right = filepath.Clean(rightAbs)
	}
	if runtime.GOOS == "windows" {
		return strings.EqualFold(left, right)
	}
	return left == right
}
